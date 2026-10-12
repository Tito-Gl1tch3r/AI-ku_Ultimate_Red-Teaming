//! # Analyzer Trait Definitions
//!
//! This module defines the common interface that all file analyzers must implement.
//! The trait-based design allows for consistent behavior across different file formats
//! while enabling format-specific analysis logic.

use super::analyzer_report::AnalyzerReport;

/// Trait for analyzing unencrypted files.
///
/// Implementers should extract relevant information from the file format
/// and return it in a standardized `AnalyzerReport` structure.
pub trait FileAnalyzer {
    /// Analyzes the given file data and returns a report.
    ///
    /// # Arguments
    ///
    /// * `file_data` - Raw bytes of the file to analyze
    ///
    /// # Returns
    ///
    /// An `AnalyzerReport` containing extracted information such as:
    /// - Nested items (for archives)
    /// - Metadata (file properties)
    /// - Heuristics (security warnings)
    /// - Imports (for executables)
    fn analyze(&self, file_data: &[u8]) -> AnalyzerReport;
}

/// Trait for analyzing encrypted or password-protected files.
///
/// Implementers should handle decryption and then perform analysis.
pub trait FileEncryptedAnalyzer {
    /// Analyzes an encrypted file using the provided password.
    ///
    /// # Arguments
    ///
    /// * `file_data` - Raw bytes of the encrypted file
    /// * `password` - Password for decryption
    ///
    /// # Returns
    ///
    /// An `AnalyzerReport` containing extracted information from the decrypted file.
    fn analyze_encrypted(&self, file_data: &[u8], password: &str) -> AnalyzerReport;
}
