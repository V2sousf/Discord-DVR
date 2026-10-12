#import <Foundation/Foundation.h>
#import <Security/Security.h>
#include <assert.h>
#include <stdbool.h>
#include <stdatomic.h>
#include <string.h>
static bool g_ready = true;
#include "DAVEKeychain.inc"
static NSDictionary *lastQuery;
static unsigned calls;
static OSStatus forced;
static BOOL failGroup = YES;
static OSStatus fakeItem(CFDictionaryRef q, CFTypeRef *out) {
    ++calls; lastQuery = (__bridge NSDictionary *)q;
    if (forced) return forced;
    if (failGroup && lastQuery[(__bridge id)kSecAttrAccessGroup]) return errSecMissingEntitlement;
    if (out) *out = CFRetain(CFSTR("SECRET-KEY"));
    return errSecSuccess;
}
static OSStatus fakeUpdate(CFDictionaryRef q, __unused CFDictionaryRef a) { return fakeItem(q, NULL); }
static OSStatus fakeDelete(CFDictionaryRef q) { return fakeItem(q, NULL); }
static SecKeyRef fakeKey(CFDictionaryRef q, CFErrorRef *error) {
    ++calls; lastQuery = (__bridge NSDictionary *)q;
    if (forced || lastQuery[(__bridge id)kSecAttrAccessGroup]) {
        *error = CFErrorCreate(NULL, kCFErrorDomainOSStatus, forced ?: errSecMissingEntitlement, NULL);
        return NULL;
    }
    return (SecKeyRef)CFRetain(CFSTR("SECRET-PRIVATE-KEY"));
}
int main(void) { @autoreleasepool {
    Real_SecItemCopyMatching = fakeItem; Real_SecItemAdd = fakeItem;
    Real_SecItemUpdate = fakeUpdate; Real_SecItemDelete = fakeDelete; Real_SecKeyCreateRandomKey = fakeKey;
    NSData *tag = [@"discord-secure-frames-key-SECRET-IDENTITY" dataUsingEncoding:NSUTF8StringEncoding];
    NSDictionary *q = @{(__bridge id)kSecAttrApplicationTag:tag, (__bridge id)kSecAttrAccessGroup:@"OLD-GROUP-SECRET",
        (__bridge id)kSecAttrKeyType:(__bridge id)kSecAttrKeyTypeECSECPrimeRandom,
        (__bridge id)kSecAttrAccessible:(__bridge id)kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly,
        (__bridge id)kSecClass:(__bridge id)kSecClassKey};
    CFTypeRef result = NULL;
    assert(Hook_SecItemCopyMatching((__bridge CFDictionaryRef)q, &result) == 0 && calls == 2 && result);
    CFRelease(result); result = NULL;
    assert(!lastQuery[(__bridge id)kSecAttrAccessGroup]);
    assert([lastQuery[(__bridge id)kSecAttrApplicationTag] isEqual:tag]);
    assert([lastQuery[(__bridge id)kSecAttrAccessible] isEqual:(__bridge id)kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly]);
    assert(q[(__bridge id)kSecAttrAccessGroup]); // caller dictionary unchanged
    calls = 0; assert(Hook_SecItemAdd((__bridge CFDictionaryRef)q, NULL) == 0 && calls == 2);
    calls = 0; assert(Hook_SecItemUpdate((__bridge CFDictionaryRef)q, (__bridge CFDictionaryRef)@{}) == 0 && calls == 2);
    calls = 0; assert(Hook_SecItemDelete((__bridge CFDictionaryRef)q) == 0 && calls == 2);
    calls = 0; forced = errSecAuthFailed;
    assert(Hook_SecItemCopyMatching((__bridge CFDictionaryRef)q, NULL) == errSecAuthFailed && calls == 1);
    forced = 0; calls = 0; 
    NSDictionary *account = @{(__bridge id)kSecAttrService:@"ACCOUNT-SECRET", (__bridge id)kSecAttrAccessGroup:@"OLD-GROUP-SECRET"};
    assert(Hook_SecItemCopyMatching((__bridge CFDictionaryRef)account, NULL) == errSecMissingEntitlement && calls == 1);
    assert(lastQuery == account);
    calls = 0; failGroup = NO;
    assert(Hook_SecItemCopyMatching((__bridge CFDictionaryRef)q, NULL) == 0 && calls == 1 && lastQuery == q);
    failGroup = YES;
    NSDictionary *params = @{(__bridge id)kSecAttrLabel:@"Discord Secure Frames Key: SECRET-IDENTITY",
        (__bridge id)kSecAttrAccessGroup:@"OLD-GROUP-SECRET",
        (__bridge id)kSecAttrKeyType:(__bridge id)kSecAttrKeyTypeECSECPrimeRandom,
        (__bridge id)kSecPrivateKeyAttrs:@{(__bridge id)kSecAttrIsPermanent:@YES,
            (__bridge id)kSecAttrAccessGroup:@"OLD-GROUP-SECRET",
            (__bridge id)kSecAttrAccessible:(__bridge id)kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly}};
    calls = 0; CFErrorRef error = NULL;
    SecKeyRef key = Hook_SecKeyCreateRandomKey((__bridge CFDictionaryRef)params, &error);
    assert(key && !error && calls == 2); CFRelease(key);
    assert(!lastQuery[(__bridge id)kSecAttrAccessGroup]);
    NSDictionary *attrs = lastQuery[(__bridge id)kSecPrivateKeyAttrs];
    assert(!attrs[(__bridge id)kSecAttrAccessGroup] && [attrs[(__bridge id)kSecAttrIsPermanent] boolValue]);
    assert([attrs[(__bridge id)kSecAttrAccessible] isEqual:(__bridge id)kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly]);
    forced = errSecAuthFailed; calls = 0;
    assert(!Hook_SecKeyCreateRandomKey((__bridge CFDictionaryRef)params, &error) && error && calls == 1);
    assert(CFErrorGetCode(error) == errSecAuthFailed); CFRelease(error);
    NSDictionary *noGroup = @{(__bridge id)kSecAttrService:@"Discord Secure Frames Key"};
    forced = errSecMissingEntitlement; calls = 0;
    assert(Hook_SecItemCopyMatching((__bridge CFDictionaryRef)noGroup, NULL) == forced && calls == 1);
    puts("DAVEKeychain: exact error retry, DAVE scope, private group, key protection, caller immutability, CF ownership and no diagnostic logging passed.");
} return 0; }
