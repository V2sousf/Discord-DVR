// Discord DVR 0.3.1 — always-on Direct release, no diagnostic UI or recording.
#import <Foundation/Foundation.h>
#include <dlfcn.h>
#include <errno.h>
#include <limits.h>
#include <mach/mach.h>
#include <mach/mach_time.h>
#include <mach-o/dyld.h>
#include <netinet/in.h>
#include <pthread.h>
#include <stdatomic.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/uio.h>
#include <time.h>
#include <unistd.h>
#include "DroverPrelude.h"
#include "fishhook.h"

#define DVR_RECORDS 4096
static int (*Real_socket)(int, int, int);
static int (*Real_close)(int);
static ssize_t (*Real_sendto)(int, const void *, size_t, int, const struct sockaddr *, socklen_t);
static ssize_t (*Real_sendmsg)(int, const struct msghdr *, int);
static ssize_t (*Real_send)(int, const void *, size_t, int);
static ssize_t (*Real_write)(int, const void *, size_t);
static ssize_t (*Real_writev)(int, const struct iovec *, int);
static atomic_bool g_ready;
static __thread unsigned g_inside;
static char g_bundle_root[PATH_MAX];
static mach_timebase_info_data_t g_timebase;
static pthread_mutex_t g_socket_lock = PTHREAD_MUTEX_INITIALIZER;

// These fields implement upstream's eligibility, not diagnostic traffic counters.
typedef struct { bool tracked, first_pending; uint64_t created_at_us, generation; } DVRSocket;
static DVRSocket g_sockets[DVR_RECORDS];
static uint64_t g_next_generation;
static uint64_t DVRNowUS(void) {
    return (uint64_t)((long double)mach_continuous_time() * g_timebase.numer / g_timebase.denom / 1000.0L);
}

// Conditional DAVE repair from the physically tested 0.3.0 implementation.
// No security, account or network information is recorded by this release.
#include "DAVEKeychain.inc"

static bool DVRConsumeFirst(int fd) {
    if (fd < 0 || fd >= DVR_RECORDS) return false;
    pthread_mutex_lock(&g_socket_lock);
    DVRSocket *s = &g_sockets[fd];
    bool first = s->tracked && s->first_pending;
    s->first_pending = false; // Consume before eligibility/result, exactly as upstream.
    pthread_mutex_unlock(&g_socket_lock);
    return first;
}
static bool DVRReadSafe(void *out, const void *in, size_t length) {
    if (!in || !length) return false;
    vm_size_t copied = 0;
    return vm_read_overwrite(mach_task_self(), (vm_address_t)(uintptr_t)in,
        length, (vm_address_t)(uintptr_t)out, &copied) == KERN_SUCCESS && copied == length;
}
typedef struct { int fd; const struct sockaddr *address; socklen_t address_size; } DVRInjection;
static ssize_t DVRInjectPacket(void *context, const void *buffer, size_t length) {
    DVRInjection *c = context;
    return Real_sendto(c->fd, buffer, length, 0, c->address, c->address_size);
}
static void DVRInjectionDelay(__unused void *context) {
    struct timespec duration = {.tv_nsec = 50000000};
    while (nanosleep(&duration, &duration) < 0 && errno == EINTR) {}
}
static void DVRMaybeInject(bool first, int fd, size_t length, const struct msghdr *message,
                           const struct sockaddr *address, socklen_t address_size) {
    if (!first) return;
    DVRInjection context = {.fd = fd, .address = address, .address_size = address_size};
    if (message) {
        struct msghdr header = {0}; struct iovec vector = {0};
        if (!DVRReadSafe(&header, message, sizeof(header)) || header.msg_iovlen < 1 ||
            !DVRReadSafe(&vector, header.msg_iov, sizeof(vector))) return;
        length = vector.iov_len;
        context.address = header.msg_name; context.address_size = header.msg_namelen;
    }
    // First buffer only. No Discovery header, total-length or payload inspection.
    if (length != 74) return;
    @autoreleasepool {
        // Discord's native UDP thread need not have an Objective-C pool.
        NSString *path = [NSString stringWithUTF8String:g_bundle_root];
        path = [path stringByAppendingPathComponent:@"drover-packet.bin"];
        NSDictionary *attrs = [NSFileManager.defaultManager attributesOfItemAtPath:path error:nil];
        NSData *packet = nil;
        if ([attrs fileSize] > 0 && [attrs fileSize] <= 65507)
            packet = [NSData dataWithContentsOfFile:path];
        // Always enabled: there is no preference, UI, session state, or restart latch.
        (void)dt_run_direct_prelude(&context, DVRInjectPacket, DVRInjectionDelay, packet.bytes, packet.length);
    }
}
static int Hook_socket(int domain, int type, int protocol) {
    if (!g_ready || g_inside) return Real_socket(domain, type, protocol);
    ++g_inside;
    int result = Real_socket(domain, type, protocol), saved = errno;
    if (result >= 0 && result < DVR_RECORDS) {
        bool udp = (domain == AF_INET || domain == AF_INET6) && type == SOCK_DGRAM &&
                   (protocol == 0 || protocol == IPPROTO_UDP);
        uint64_t now = DVRNowUS();
        pthread_mutex_lock(&g_socket_lock);
        // Original SocketManager prunes age >30s only when another socket is created.
        for (int i = 0; i < DVR_RECORDS; ++i)
            if (g_sockets[i].tracked && now > g_sockets[i].created_at_us &&
                now - g_sockets[i].created_at_us > 30000000) g_sockets[i].tracked = false;
        g_sockets[result] = (DVRSocket){.tracked = udp, .first_pending = udp,
            .created_at_us = now, .generation = ++g_next_generation};
        pthread_mutex_unlock(&g_socket_lock);
    }
    --g_inside; errno = saved; return result;
}
static int Hook_close(int fd) {
    if (!g_ready || g_inside) return Real_close(fd);
    ++g_inside;
    uint64_t generation = 0;
    if (fd >= 0 && fd < DVR_RECORDS) {
        pthread_mutex_lock(&g_socket_lock);
        generation = g_sockets[fd].generation;
        pthread_mutex_unlock(&g_socket_lock);
    }
    int result = Real_close(fd), saved = errno;
    if (result == 0 && fd >= 0 && fd < DVR_RECORDS) {
        pthread_mutex_lock(&g_socket_lock);
        if (g_sockets[fd].generation == generation) g_sockets[fd] = (DVRSocket){0};
        pthread_mutex_unlock(&g_socket_lock);
    }
    --g_inside; errno = saved; return result;
}
#define DVR_BEGIN(fd) int entry = errno; ++g_inside; bool first = DVRConsumeFirst(fd); errno = entry
#define DVR_END() --g_inside; errno = saved; return result
static ssize_t Hook_sendto(int fd, const void *buffer, size_t length, int flags,
                           const struct sockaddr *address, socklen_t address_size) {
    if (!g_ready || g_inside) return Real_sendto(fd, buffer, length, flags, address, address_size);
    DVR_BEGIN(fd);
    DVRMaybeInject(first, fd, length, NULL, address, address_size); errno = entry;
    ssize_t result = Real_sendto(fd, buffer, length, flags, address, address_size); int saved = errno;
    DVR_END();
}
static ssize_t Hook_sendmsg(int fd, const struct msghdr *message, int flags) {
    if (!g_ready || g_inside) return Real_sendmsg(fd, message, flags);
    DVR_BEGIN(fd);
    if (message) DVRMaybeInject(first, fd, 0, message, NULL, 0);
    errno = entry;
    ssize_t result = Real_sendmsg(fd, message, flags); int saved = errno;
    DVR_END();
}
// Like Windows send/WSASend, these consume first attempt without injecting.
static ssize_t Hook_send(int fd, const void *buffer, size_t length, int flags) {
    if (!g_ready || g_inside) return Real_send(fd, buffer, length, flags);
    DVR_BEGIN(fd); (void)first;
    ssize_t result = Real_send(fd, buffer, length, flags); int saved = errno;
    DVR_END();
}
static ssize_t Hook_write(int fd, const void *buffer, size_t length) {
    if (!g_ready || g_inside) return Real_write(fd, buffer, length);
    DVR_BEGIN(fd); (void)first;
    ssize_t result = Real_write(fd, buffer, length); int saved = errno;
    DVR_END();
}
static ssize_t Hook_writev(int fd, const struct iovec *vectors, int count) {
    if (!g_ready || g_inside) return Real_writev(fd, vectors, count);
    DVR_BEGIN(fd); (void)first;
    ssize_t result = Real_writev(fd, vectors, count); int saved = errno;
    DVR_END();
}
static struct rebinding g_hooks[] = {
    {"socket", (void *)Hook_socket, NULL}, {"close", (void *)Hook_close, NULL},
    {"sendto", (void *)Hook_sendto, NULL}, {"sendmsg", (void *)Hook_sendmsg, NULL},
    {"send", (void *)Hook_send, NULL}, {"write", (void *)Hook_write, NULL}, {"writev", (void *)Hook_writev, NULL},
    {"SecItemCopyMatching", (void *)Hook_SecItemCopyMatching, NULL},
    {"SecItemAdd", (void *)Hook_SecItemAdd, NULL}, {"SecItemUpdate", (void *)Hook_SecItemUpdate, NULL},
    {"SecItemDelete", (void *)Hook_SecItemDelete, NULL}, {"SecKeyCreateRandomKey", (void *)Hook_SecKeyCreateRandomKey, NULL},
};
#ifndef DVR_RELEASE_TEST
static void DVRImageAdded(const struct mach_header *header, intptr_t slide) {
    if (header->magic != MH_MAGIC_64) return;
    Dl_info info = {0};
    if (!dladdr(header, &info) || !info.dli_fname) return;
    size_t length = strlen(g_bundle_root);
    if (strncmp(info.dli_fname, g_bundle_root, length) || info.dli_fname[length] != '/') return;
    const char *name = strrchr(info.dli_fname, '/'); name = name ? name + 1 : info.dli_fname;
    if (!strcmp(name, "DiscordDVR.dylib")) return;
    (void)rebind_symbols_image((void *)header, slide, g_hooks, sizeof(g_hooks) / sizeof(g_hooks[0]));
}
#endif
__attribute__((constructor)) static void DVRInitialize(void) {
    @autoreleasepool {
#define DVR_RESOLVE(name) do { *(void **)&Real_##name = dlsym(RTLD_DEFAULT, #name); if (!Real_##name) return; } while (0)
        DVR_RESOLVE(socket); DVR_RESOLVE(close); DVR_RESOLVE(sendto); DVR_RESOLVE(sendmsg);
        DVR_RESOLVE(send); DVR_RESOLVE(write); DVR_RESOLVE(writev);
        DVR_RESOLVE(SecItemCopyMatching); DVR_RESOLVE(SecItemAdd); DVR_RESOLVE(SecItemUpdate);
        DVR_RESOLVE(SecItemDelete); DVR_RESOLVE(SecKeyCreateRandomKey);
#undef DVR_RESOLVE
        (void)mach_timebase_info(&g_timebase);
        if (!g_timebase.denom) return;
        const char *path = NSBundle.mainBundle.bundlePath.fileSystemRepresentation;
        if (!path || strlen(path) >= sizeof(g_bundle_root)) return;
        memcpy(g_bundle_root, path, strlen(path) + 1);
        // Release is ready BEFORE dyld registers/executes the image callbacks.
        g_ready = true;
#ifndef DVR_RELEASE_TEST
        _dyld_register_func_for_add_image(DVRImageAdded);
#endif
    }
}
