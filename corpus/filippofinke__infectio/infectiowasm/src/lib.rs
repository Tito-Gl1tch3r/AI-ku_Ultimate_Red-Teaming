//! # Infectio WebAssembly Module
//!
//! This module provides the core malware analysis functionality for Infectio,
//! compiled to WebAssembly for use in web browsers.
//!
//! ## Overview
//!
//! The module exposes file analysis capabilities through WebAssembly bindings,
//! allowing JavaScript code to analyze various file formats including:
//! - Windows PE executables
//! - Linux ELF binaries
//! - macOS Mach-O binaries
//! - PDF documents
//! - ZIP archives and Office documents
//! - OLE2 format files
//!
//! ## Architecture
//!
//! The analysis flow follows this pattern:
//! 1. File data and MIME type are passed from JavaScript
//! 2. MIME type is validated/detected using the `infer` library
//! 3. File is dispatched to the appropriate analyzer
//! 4. Analyzer extracts format-specific information
//! 5. Results are serialized and returned to JavaScript
//!
//! ## Usage
//!
//! ```javascript
//! import init, { analyze_file } from 'infectio-wasm';
//!
//! await init();
//! const fileData = new Uint8Array(await file.arrayBuffer());
//! const report = analyze_file(fileData, 'application/pdf');
//! ```

extern crate console_error_panic_hook;
use dispatcher::analyze_file_by_mime;
use serde_wasm_bindgen::to_value;
use std::panic;
use wasm_bindgen::{prelude::*, throw_str};
pub mod analyzers;
pub mod dispatcher;
pub mod utils;

/// Initializes the WebAssembly module.
///
/// This function is automatically called when the WASM module is loaded.
/// It sets up panic hooks for better error messages in the browser console
/// and initializes the logging system.
///
/// # Side Effects
///
/// - Configures panic hook to display panic messages in browser console
/// - Initializes wasm-logger with default configuration
#[wasm_bindgen(start)]
pub fn run() {
    panic::set_hook(Box::new(console_error_panic_hook::hook));
    wasm_logger::init(wasm_logger::Config::default());
}

/// Determines the actual MIME type of file data using content inspection.
///
/// This function uses the `infer` library to detect the file type by examining
/// the file's magic bytes, which is more reliable than trusting the provided
/// MIME type alone.
///
/// # Arguments
///
/// * `file_data` - The raw bytes of the file to analyze
/// * `mime_type` - The fallback MIME type if detection fails
///
/// # Returns
///
/// The detected MIME type string, or the provided fallback if detection fails.
///
/// # Examples
///
/// ```no_run
/// let data = &[0x50, 0x4B, 0x03, 0x04]; // ZIP magic bytes
/// let mime = determine_mime_type(data, "application/octet-stream");
/// assert_eq!(mime, "application/zip");
/// ```
fn determine_mime_type<'a>(file_data: &[u8], mime_type: &'a str) -> &'a str {
    if let Some(kind) = infer::get(file_data) {
        kind.mime_type()
    } else {
        mime_type
    }
}

/// Analyzes a file and returns detailed information about its structure and contents.
///
/// This is the main entry point for file analysis. It automatically detects the
/// actual file type, dispatches to the appropriate analyzer, and returns a
/// comprehensive report.
///
/// # Arguments
///
/// * `file_data` - The raw bytes of the file to analyze
/// * `mime_type` - The claimed MIME type (will be verified)
///
/// # Returns
///
/// A JavaScript value containing the analysis report with:
/// - `items`: Nested files (for archives)
/// - `metadata`: File properties and characteristics
/// - `heuristics`: Security warnings and suspicious patterns
/// - `imports`: Function imports and dependencies (for executables)
///
/// # Errors
///
/// Throws a JavaScript exception if:
/// - The file format is unsupported
/// - The file is corrupted or invalid
/// - Analysis fails for any reason
///
/// # Examples
///
/// ```javascript
/// const report = analyze_file(fileData, 'application/pdf');
/// console.log(report.metadata);
/// console.log(report.heuristics);
/// ```
#[wasm_bindgen]
pub fn analyze_file(file_data: &[u8], mime_type: &str) -> JsValue {
    let mime = determine_mime_type(file_data, mime_type);

    match analyze_file_by_mime(mime, file_data, None) {
        Ok(result) => to_value(&result).expect_throw("Failed to convert result to JsValue"),
        Err(err) => throw_str(&err.to_string()),
    }
}

/// Analyzes an encrypted or password-protected file.
///
/// Similar to `analyze_file`, but provides a password for encrypted content.
/// Commonly used for password-protected ZIP files and Office documents.
///
/// # Arguments
///
/// * `file_data` - The raw bytes of the encrypted file
/// * `mime_type` - The claimed MIME type (will be verified)
/// * `password` - The password to decrypt the file
///
/// # Returns
///
/// A JavaScript value containing the analysis report (same structure as `analyze_file`).
///
/// # Errors
///
/// Throws a JavaScript exception if:
/// - The password is incorrect
/// - The file format doesn't support encryption
/// - Analysis fails for any reason
///
/// # Examples
///
/// ```javascript
/// const report = analyze_encrypted_file(fileData, 'application/zip', 'password123');
/// console.log(report.items); // Decrypted contents
/// ```
#[wasm_bindgen]
pub fn analyze_encrypted_file(file_data: &[u8], mime_type: &str, password: &str) -> JsValue {
    let mime = determine_mime_type(file_data, mime_type);

    match analyze_file_by_mime(mime, file_data, Some(password)) {
        Ok(result) => to_value(&result).expect_throw("Failed to convert result to JsValue"),
        Err(err) => throw_str(&err.to_string()),
    }
}
