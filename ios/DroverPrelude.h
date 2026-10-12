#ifndef DROVER_PRELUDE_H
#define DROVER_PRELUDE_H
#include <errno.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <sys/types.h>
typedef struct { ssize_t zero_result, one_result; int zero_errno, one_errno;
    bool packet_attempted; ssize_t packet_result; int packet_errno; } DTPreludeResult;
typedef ssize_t (*DTPreludeSender)(void *context, unsigned char byte);
typedef ssize_t (*DTPacketSender)(void *context, const void *buffer, size_t length);
typedef void (*DTPreludeDelay)(void *context);
static inline DTPreludeResult dt_run_direct_prelude(void *context, DTPacketSender sender,
        DTPreludeDelay delay, const void *packet, size_t packet_length) {
    DTPreludeResult r = {0};
    if (packet && packet_length) {
        r.packet_attempted = true;
        r.packet_result = sender(context, packet, packet_length);
        r.packet_errno = r.packet_result < 0 ? errno : 0;
    }
    unsigned char byte = 0;
    r.zero_result = sender(context, &byte, 1); r.zero_errno = r.zero_result < 0 ? errno : 0;
    byte = 1;
    r.one_result = sender(context, &byte, 1); r.one_errno = r.one_result < 0 ? errno : 0;
    delay(context);
    return r;
}
static inline DTPreludeResult dt_run_prelude(void *context, DTPreludeSender send_byte, DTPreludeDelay delay) {
    DTPreludeResult r = {0};
    r.zero_result = send_byte(context, 0); r.zero_errno = r.zero_result < 0 ? errno : 0;
    r.one_result = send_byte(context, 1); r.one_errno = r.one_result < 0 ? errno : 0;
    // Match upstream: wait even if an injected send fails, then caller sends original.
    delay(context);
    return r;
}
#endif
