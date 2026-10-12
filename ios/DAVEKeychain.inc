// Re-sign compatibility: retry only DAVE queries with an inaccessible explicit group.
// Removing that group selects the signed app's own private default Keychain group.
// Never change key algorithms, permanence, accessibility, validation or account queries.
#import <Security/Security.h>
static OSStatus (*Real_SecItemCopyMatching)(CFDictionaryRef, CFTypeRef *);
static OSStatus (*Real_SecItemAdd)(CFDictionaryRef, CFTypeRef *);
static OSStatus (*Real_SecItemUpdate)(CFDictionaryRef, CFDictionaryRef);
static OSStatus (*Real_SecItemDelete)(CFDictionaryRef);
static SecKeyRef (*Real_SecKeyCreateRandomKey)(CFDictionaryRef, CFErrorRef *);
static __thread bool g_keychain_inside;

static BOOL DTDAVEQuery(NSDictionary *d) {
    if (![d isKindOfClass:NSDictionary.class]) return NO;
    id service = d[(__bridge id)kSecAttrService], label = d[(__bridge id)kSecAttrLabel];
    id tag = d[(__bridge id)kSecAttrApplicationTag];
    if ([service isKindOfClass:NSString.class] && [service isEqualToString:@"Discord Secure Frames Key"]) return YES;
    if ([label isKindOfClass:NSString.class] && [label hasPrefix:@"Discord Secure Frames Key: "]) return YES;
    static const char prefix[] = "discord-secure-frames-key-";
    if ([tag isKindOfClass:NSData.class] && [tag length] >= sizeof(prefix)-1 &&
        !memcmp([tag bytes], prefix, sizeof(prefix)-1)) return YES;
    return NO;
}
static BOOL DTDAVEScoped(NSDictionary *d) {
    return DTDAVEQuery(d) || DTDAVEQuery(d[(__bridge id)kSecPrivateKeyAttrs]);
}
static NSDictionary *DTPrivateGroupQuery(NSDictionary *d) {
    // Return nil unless an explicit group can actually be repaired.
    id nested = d[(__bridge id)kSecPrivateKeyAttrs];
    BOOL nestedDict = [nested isKindOfClass:NSDictionary.class];
    if (!d[(__bridge id)kSecAttrAccessGroup] && !(nestedDict && nested[(__bridge id)kSecAttrAccessGroup])) return nil;
    NSMutableDictionary *copy = [d mutableCopy];
    [copy removeObjectForKey:(__bridge id)kSecAttrAccessGroup];
    if (nestedDict) {
        NSMutableDictionary *attrs = [nested mutableCopy];
        [attrs removeObjectForKey:(__bridge id)kSecAttrAccessGroup];
        copy[(__bridge id)kSecPrivateKeyAttrs] = attrs;
    }
    return copy;
}
static OSStatus DTKeychainItem(CFDictionaryRef query, CFTypeRef *out,
                              CFDictionaryRef update, unsigned operation) {
    NSDictionary *d = (__bridge NSDictionary *)query;
    BOOL observe = g_ready && !g_keychain_inside && DTDAVEScoped(d);
    bool wasInside = g_keychain_inside;
    if (observe) g_keychain_inside = true;
    OSStatus status;
    if (operation == 0) status = Real_SecItemCopyMatching(query, out);
    else if (operation == 1) status = Real_SecItemAdd(query, out);
    else if (operation == 2) status = Real_SecItemUpdate(query, update);
    else status = Real_SecItemDelete(query);
    
    if (observe && status == errSecMissingEntitlement) {
        NSDictionary *privateQuery = DTPrivateGroupQuery(d);
        if (privateQuery) {
            CFDictionaryRef q = (__bridge CFDictionaryRef)privateQuery;
            if (operation == 0) status = Real_SecItemCopyMatching(q, out);
            else if (operation == 1) status = Real_SecItemAdd(q, out);
            else if (operation == 2) status = Real_SecItemUpdate(q, update);
            else status = Real_SecItemDelete(q);
        }
    }
    g_keychain_inside = wasInside;
    return status;
}
static OSStatus Hook_SecItemCopyMatching(CFDictionaryRef q, CFTypeRef *r) { return DTKeychainItem(q, r, NULL, 0); }
static OSStatus Hook_SecItemAdd(CFDictionaryRef q, CFTypeRef *r) { return DTKeychainItem(q, r, NULL, 1); }
static OSStatus Hook_SecItemUpdate(CFDictionaryRef q, CFDictionaryRef a) { return DTKeychainItem(q, NULL, a, 2); }
static OSStatus Hook_SecItemDelete(CFDictionaryRef q) { return DTKeychainItem(q, NULL, NULL, 3); }
static SecKeyRef Hook_SecKeyCreateRandomKey(CFDictionaryRef params, CFErrorRef *error) {
    NSDictionary *d = (__bridge NSDictionary *)params;
    if (!g_ready || g_keychain_inside || !DTDAVEScoped(d)) return Real_SecKeyCreateRandomKey(params, error);
    g_keychain_inside = true;
    CFErrorRef localError = NULL;
    SecKeyRef key = Real_SecKeyCreateRandomKey(params, &localError);
    NSInteger initial = key ? 0 : (localError ? CFErrorGetCode(localError) : -1);
    if (!key && localError && CFEqual(CFErrorGetDomain(localError), kCFErrorDomainOSStatus) && initial == errSecMissingEntitlement) {
        NSDictionary *privateQuery = DTPrivateGroupQuery(d);
        if (privateQuery) {
            CFRelease(localError); localError = NULL;
            key = Real_SecKeyCreateRandomKey((__bridge CFDictionaryRef)privateQuery, &localError);
        }
    }
    if (error) *error = localError; else if (localError) CFRelease(localError);
    g_keychain_inside = false;
    return key;
}
