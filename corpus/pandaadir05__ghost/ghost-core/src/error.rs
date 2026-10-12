use thiserror::Error;

/// Error types for the Ghost detection framework.
///
/// This enum provides structured error handling for all operations
/// within the detection engine, ensuring proper error propagation
/// and meaningful error messages.
#[derive(Error, Debug, Clone)]
pub enum GhostError {
    #[error("Process access denied (PID: {pid})")]
    AccessDenied { pid: u32 },

    #[error("Process not found (PID: {pid})")]
    ProcessNotFound { pid: u32 },

    #[error("Memory enumeration failed: {reason}")]
    MemoryEnumeration { reason: String },

    #[error("Memory read error: {message}")]
    MemoryRead { message: String },

    #[error("Thread enumeration failed: {reason}")]
    ThreadEnumeration { reason: String },

    #[error("Insufficient privileges for operation")]
    InsufficientPrivileges,

    #[error("Windows API error: {message}")]
    WindowsApi { message: String },

    #[error("Detection engine error: {message}")]
    Detection { message: String },

    #[error("Configuration error: {message}")]
    Configuration { message: String },

    #[error("IO error: {message}")]
    Io { message: String },

    #[error("Serialization error: {message}")]
    Serialization { message: String },

    #[error("Lock acquisition failed: {resource}")]
    LockPoisoned { resource: String },

    #[error("Threat intelligence error: {message}")]
    ThreatIntel { message: String },

    #[error("MITRE ATT&CK analysis error: {message}")]
    MitreAnalysis { message: String },

    #[error("eBPF error: {message}")]
    Ebpf { message: String },

    #[error("Platform not supported: {feature}")]
    PlatformNotSupported { feature: String },

    #[error("Invalid input: {message}")]
    InvalidInput { message: String },
}

impl From<std::io::Error> for GhostError {
    fn from(err: std::io::Error) -> Self {
        GhostError::Io {
            message: err.to_string(),
        }
    }
}

impl From<serde_json::Error> for GhostError {
    fn from(err: serde_json::Error) -> Self {
        GhostError::Serialization {
            message: err.to_string(),
        }
    }
}

impl From<toml::de::Error> for GhostError {
    fn from(err: toml::de::Error) -> Self {
        GhostError::Configuration {
            message: err.to_string(),
        }
    }
}

/// Type alias for Result with GhostError as the error type.
pub type Result<T> = std::result::Result<T, GhostError>;
