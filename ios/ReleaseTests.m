// Exercise the actual production hook bodies without patching the test runner's imports.
#define DVR_RELEASE_TEST 1
#import "DiscordDVR.m"
#include <assert.h>
#include <arpa/inet.h>
#include <stdio.h>
#include <sys/time.h>

static unsigned char packet[1200], original[74];
static struct sockaddr_in destination;
static uint64_t monotonicNS(void) {
    struct timespec t; assert(clock_gettime(CLOCK_MONOTONIC, &t) == 0);
    return (uint64_t)t.tv_sec * 1000000000 + t.tv_nsec;
}
static void expectDatagram(int receiver, int sender, const void *bytes, size_t length) {
    unsigned char buffer[1300]; struct sockaddr_in source = {0}, local = {0};
    socklen_t sourceLength = sizeof(source), localLength = sizeof(local);
    assert(getsockname(sender, (struct sockaddr *)&local, &localLength) == 0);
    assert(recvfrom(receiver, buffer, sizeof(buffer), 0, (struct sockaddr *)&source, &sourceLength) == (ssize_t)length);
    assert(!memcmp(buffer, bytes, length) && source.sin_port == local.sin_port);
}
static void expectEmpty(int receiver) {
    unsigned char byte;
    assert(recv(receiver, &byte, 1, MSG_DONTWAIT) == -1 && (errno == EAGAIN || errno == EWOULDBLOCK));
}
static void expectPrelude(int receiver, int sender) {
    unsigned char zero = 0, one = 1;
    expectDatagram(receiver, sender, packet, sizeof(packet));
    expectDatagram(receiver, sender, &zero, 1); expectDatagram(receiver, sender, &one, 1);
}
static unsigned failingCalls, originalCalls;
static int fakeSocket(__unused int domain, __unused int type, __unused int protocol) { return 100; }
static int fakeClose(__unused int fd) { errno = EBUSY; return 0; }
static ssize_t failingSendto(int fd, const void *b, size_t n, int flags,
                             const struct sockaddr *a, socklen_t alen) {
    assert(fd == 100 && flags == 0 && a == (struct sockaddr *)&destination && alen == sizeof(destination));
    assert(failingCalls < 3);
    if (!failingCalls) assert(n == 1200 && !memcmp(b, packet, n));
    else assert(n == 1 && *(const unsigned char *)b == failingCalls - 1);
    ++failingCalls; errno = EAGAIN; return -1;
}
static ssize_t preserveSendmsg(int fd, const struct msghdr *message, int flags) {
    assert(fd == 100 && message && flags == MSG_DONTWAIT);
    assert(message->msg_iovlen == 2 && message->msg_iov[0].iov_len == 74 && message->msg_iov[1].iov_len == 3);
    assert(message->msg_control && message->msg_controllen == 12);
    ++originalCalls; errno = ENETUNREACH; return -1;
}
int main(void) { @autoreleasepool {
    // The real production constructor has run, without a mode file or UI action.
    assert(atomic_load(&g_ready));
    assert(sizeof(g_hooks) / sizeof(g_hooks[0]) == 12);
    for (size_t i = 0; i < sizeof(g_hooks) / sizeof(g_hooks[0]); ++i)
        assert(strncmp(g_hooks[i].name, "recv", 4) && strcmp(g_hooks[i].name, "read"));
    char temporary[] = "/tmp/discord-dvr-release-XXXXXX";
    assert(mkdtemp(temporary));
    snprintf(g_bundle_root, sizeof(g_bundle_root), "%s", temporary);
    NSString *directory = [NSString stringWithUTF8String:temporary];
    const char *actualPacket = getenv("DVR_TEST_PACKET_PATH");
    if (actualPacket) {
        FILE *f = fopen(actualPacket, "rb"); assert(f);
        assert(fread(packet, 1, sizeof(packet), f) == sizeof(packet) && fgetc(f) == EOF); fclose(f);
    } else for (unsigned i = 0; i < sizeof(packet); ++i) packet[i] = (unsigned char)(i * 17u + 3u);
    NSString *packetPath = [directory stringByAppendingPathComponent:@"drover-packet.bin"];
    assert([[NSData dataWithBytes:packet length:sizeof(packet)] writeToFile:packetPath atomically:YES]);
    // Legacy disabled preference exists. Release never reads or changes it.
    NSData *normal = [@"0\n" dataUsingEncoding:NSUTF8StringEncoding];
    NSString *modePath = [directory stringByAppendingPathComponent:@"drover-mode-v1"];
    assert([normal writeToFile:modePath atomically:YES]);
    // Re-initialize with an existing valid 0.3.0 Normal setting. It is ignored.
    atomic_store(&g_ready, false); DVRInitialize(); assert(atomic_load(&g_ready));
    snprintf(g_bundle_root, sizeof(g_bundle_root), "%s", temporary);
    NSArray *before = [NSFileManager.defaultManager contentsOfDirectoryAtPath:directory error:nil];
    memset(original, 0xff, sizeof(original)); // Not a Discovery header: length alone is eligible.
    int receiver = socket(AF_INET, SOCK_DGRAM, 0); assert(receiver >= 0);
    destination = (struct sockaddr_in){.sin_len = sizeof(destination), .sin_family = AF_INET,
                                     .sin_addr.s_addr = htonl(INADDR_LOOPBACK)};
    assert(bind(receiver, (struct sockaddr *)&destination, sizeof(destination)) == 0);
    socklen_t addressLength = sizeof(destination);
    assert(getsockname(receiver, (struct sockaddr *)&destination, &addressLength) == 0);
    struct timeval timeout = {2, 0}; assert(setsockopt(receiver, SOL_SOCKET, SO_RCVTIMEO, &timeout, sizeof(timeout)) == 0);

    int sender = Hook_socket(AF_INET, SOCK_DGRAM, 0); assert(sender >= 0);
    uint64_t began = monotonicNS();
    assert(Hook_sendto(sender, original, sizeof(original), 0, (struct sockaddr *)&destination, sizeof(destination)) == 74);
    assert(monotonicNS() - began >= 45000000);
    expectPrelude(receiver, sender); expectDatagram(receiver, sender, original, sizeof(original)); expectEmpty(receiver);
    assert(Hook_sendto(sender, original, 74, 0, (struct sockaddr *)&destination, sizeof(destination)) == 74);
    expectDatagram(receiver, sender, original, 74); expectEmpty(receiver); assert(Hook_close(sender) == 0);

    // First iovec 74, total 77, original pointer/flags/bytes unmodified.
    sender = Hook_socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP); assert(sender >= 0);
    struct iovec vectors[] = {{original, 74}, {original, 3}};
    struct msghdr message = {.msg_name = &destination, .msg_namelen = sizeof(destination), .msg_iov = vectors, .msg_iovlen = 2};
    struct msghdr savedMessage = message; struct iovec savedVectors[2]; memcpy(savedVectors, vectors, sizeof(vectors));
    unsigned char joined[77]; memcpy(joined, original, 74); memcpy(joined + 74, original, 3);
    assert(Hook_sendmsg(sender, &message, MSG_DONTWAIT) == 77);
    expectPrelude(receiver, sender); expectDatagram(receiver, sender, joined, sizeof(joined)); expectEmpty(receiver);
    assert(!memcmp(&message, &savedMessage, sizeof(message)) && !memcmp(vectors, savedVectors, sizeof(vectors)));
    assert(Hook_close(sender) == 0);

    // A failed or ineligible first attempt still consumes eligibility.
    sender = Hook_socket(AF_INET, SOCK_DGRAM, 0); assert(sender >= 0);
    vectors[0].iov_len = 1; vectors[1].iov_len = 73;
    assert(Hook_sendmsg(sender, &message, 0) == 74); expectDatagram(receiver, sender, original, 74);
    assert(Hook_sendto(sender, original, 74, 0, (struct sockaddr *)&destination, sizeof(destination)) == 74);
    expectDatagram(receiver, sender, original, 74); expectEmpty(receiver); assert(Hook_close(sender) == 0);
    sender = Hook_socket(AF_INET, SOCK_DGRAM, 0); assert(sender >= 0);
    assert(Hook_sendmsg(sender, NULL, 0) == -1);
    assert(Hook_sendto(sender, original, 74, 0, (struct sockaddr *)&destination, sizeof(destination)) == 74);
    expectDatagram(receiver, sender, original, 74); expectEmpty(receiver); assert(Hook_close(sender) == 0);

    // Unobserved creations are never adopted; no receive hooks or traffic parsing.
    sender = socket(AF_INET, SOCK_DGRAM, 0); assert(sender >= 0);
    assert(Hook_sendto(sender, original, 74, 0, (struct sockaddr *)&destination, sizeof(destination)) == 74);
    expectDatagram(receiver, sender, original, 74); expectEmpty(receiver); close(sender);
    sender = Hook_socket(AF_INET, SOCK_DGRAM, 0); assert(sender >= 0);
    assert(connect(sender, (struct sockaddr *)&destination, sizeof(destination)) == 0);
    assert(Hook_send(sender, original, 1, 0) == 1); expectDatagram(receiver, sender, original, 1);
    // Darwin connected UDP uses the existing peer, with no explicit msg_name.
    struct msghdr connectedMessage = message;
    connectedMessage.msg_name = NULL; connectedMessage.msg_namelen = 0;
    assert(Hook_sendmsg(sender, &connectedMessage, 0) == 74); expectDatagram(receiver, sender, original, 74);
    expectEmpty(receiver); assert(Hook_close(sender) == 0);

    sender = Hook_socket(AF_INET, SOCK_DGRAM, 0); assert(sender >= 0);
    assert(connect(sender, (struct sockaddr *)&destination, sizeof(destination)) == 0);
    assert(Hook_write(sender, original, 1) == 1); expectDatagram(receiver, sender, original, 1);
    assert(Hook_sendto(sender, original, 74, 0, NULL, 0) == 74);
    expectDatagram(receiver, sender, original, 74); expectEmpty(receiver); assert(Hook_close(sender) == 0);
    sender = Hook_socket(AF_INET, SOCK_DGRAM, 0); assert(sender >= 0);
    assert(connect(sender, (struct sockaddr *)&destination, sizeof(destination)) == 0);
    struct iovec oneVector = {original, 1};
    assert(Hook_writev(sender, &oneVector, 1) == 1); expectDatagram(receiver, sender, original, 1);
    assert(Hook_sendto(sender, original, 74, 0, NULL, 0) == 74);
    expectDatagram(receiver, sender, original, 74); expectEmpty(receiver); assert(Hook_close(sender) == 0);

    // Upstream prunes only on another creation, not automatically after 30 seconds.
    sender = Hook_socket(AF_INET, SOCK_DGRAM, 0); assert(sender >= 0);
    g_sockets[sender].created_at_us = DVRNowUS() - 31000000;
    int other = Hook_socket(AF_INET, SOCK_STREAM, 0); assert(other >= 0);
    assert(!g_sockets[sender].tracked);
    assert(Hook_sendto(sender, original, 74, 0, (struct sockaddr *)&destination, sizeof(destination)) == 74);
    expectDatagram(receiver, sender, original, 74); expectEmpty(receiver);
    assert(Hook_close(sender) == 0 && Hook_close(other) == 0);

    // Injected failures never suppress original; original args, ancillary and errno survive.
    Real_socket = fakeSocket; Real_close = fakeClose; Real_sendto = failingSendto; Real_sendmsg = preserveSendmsg;
    assert(Hook_socket(AF_INET, SOCK_DGRAM, 0) == 100);
    unsigned char ancillary[12] = {1, 2, 3};
    vectors[0].iov_len = 74; vectors[1].iov_len = 3;
    message.msg_control = ancillary; message.msg_controllen = sizeof(ancillary);
    began = monotonicNS(); errno = EDOM;
    assert(Hook_sendmsg(100, &message, MSG_DONTWAIT) == -1 && errno == ENETUNREACH);
    assert(monotonicNS() - began >= 45000000 && failingCalls == 3 && originalCalls == 1);
    assert(Hook_close(100) == 0 && errno == EBUSY);
    assert([[NSData dataWithContentsOfFile:modePath] isEqual:normal]);
    NSArray *after = [NSFileManager.defaultManager contentsOfDirectoryAtPath:directory error:nil];
    assert([[NSSet setWithArray:before] isEqual:[NSSet setWithArray:after]]); // No NDJSON or export files.
    close(receiver);
    assert([NSFileManager.defaultManager removeItemAtPath:directory error:nil]);
    puts("Release: constructor enabled before hooks; legacy Normal ignored; real same-socket 1200,00,01,50ms,original; first-buffer policy; one attempt; errors/ancillary/errno preserved; no log or UI dependency passed.");
} return 0; }
