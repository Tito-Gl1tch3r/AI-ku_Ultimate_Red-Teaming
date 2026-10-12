//! Tests for hook detection

#[cfg(test)]
mod tests {
    use ghost_core::hooks::{detect_hook_injection, HookType};

    #[test]
    fn test_hook_type_display() {
        assert_eq!(format!("{}", HookType::InlineHook), "InlineHook");
        assert_eq!(format!("{}", HookType::IATHook), "IATHook");
        assert_eq!(format!("{}", HookType::LdPreload), "LD_PRELOAD");
        assert_eq!(format!("{}", HookType::PtraceInjection), "PtraceInjection");
        assert_eq!(
            format!("{}", HookType::DyldInsertLibraries),
            "DYLD_INSERT_LIBRARIES"
        );
    }

    #[cfg(target_os = "macos")]
    #[test]
    fn test_dyld_detection_clean_process() {
        // Test on current process which should not have DYLD_INSERT_LIBRARIES
        let current_pid = std::process::id();

        let result = detect_hook_injection(current_pid);
        assert!(result.is_ok());

        let hook_result = result.unwrap();
        // Current test process should not have DYLD hooks
        assert!(
            !hook_result
                .hooks
                .iter()
                .any(|h| matches!(h.hook_type, HookType::DyldInsertLibraries)),
            "Test process should not have DYLD_INSERT_LIBRARIES"
        );
    }

    #[cfg(target_os = "macos")]
    #[test]
    fn test_dyld_hook_type() {
        // Just verify the hook type exists and can be created
        let hook_type = HookType::DyldInsertLibraries;
        assert_eq!(format!("{}", hook_type), "DYLD_INSERT_LIBRARIES");
    }

    #[cfg(target_os = "macos")]
    #[test]
    fn test_inline_hook_detection_framework() {
        // Test that inline hook detection runs without crashing
        let current_pid = std::process::id();

        let result = detect_hook_injection(current_pid);
        assert!(result.is_ok());

        // Inline hook detection framework should be present
        // Even if it doesn't find hooks in the test process
        let hook_result = result.unwrap();
        assert_eq!(hook_result.inline_hooks, 0);
    }

    #[cfg(not(target_os = "macos"))]
    #[test]
    fn test_hook_detector_on_current_platform() {
        let current_pid = std::process::id();

        let result = detect_hook_injection(current_pid);
        // Should succeed on all platforms
        assert!(result.is_ok());
    }
}
