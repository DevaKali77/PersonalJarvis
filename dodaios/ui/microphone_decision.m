// Complete WebKit's native decision block without Python block introspection.
#import <Foundation/Foundation.h>
void dodaios_complete_media_decision(void *block_pointer, long decision) {
    void (^handler)(NSInteger) = (__bridge id)block_pointer;
    handler((NSInteger)decision);
}
