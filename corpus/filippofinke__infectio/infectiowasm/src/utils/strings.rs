//! # String Extraction and Pattern Matching
//!
//! This module provides utilities for extracting strings, IP addresses, and URLs
//! from binary data. These are common indicators of interest (IOCs) in malware analysis.
//!
//! ## Capabilities
//!
//! - Extract ASCII and Unicode strings
//! - Identify IPv4 addresses
//! - Extract HTTP/HTTPS URLs
//! - Filter by minimum string length

use std::collections::HashSet;

use regex::Regex;
use rust_strings::{strings, BytesConfig};
use wasm_bindgen::prelude::*;

/// Extracts printable strings from binary data.
///
/// Extracts both ASCII and Unicode strings that meet the minimum length requirement.
/// Useful for finding:
/// - Embedded URLs and IP addresses
/// - File paths and registry keys
/// - Error messages and debug strings
/// - Encrypted/obfuscated strings
///
/// # Arguments
///
/// * `file_data` - The raw bytes to search
/// * `min_length` - Minimum string length to extract (typical: 4-8)
///
/// # Returns
///
/// Array of extracted strings.
///
/// # Examples
///
/// ```javascript
/// const strings = extract_strings(fileData, 5);
/// console.log(`Found ${strings.length} strings`);
/// ```
#[wasm_bindgen]
pub fn extract_strings(file_data: &[u8], min_length: usize) -> Vec<String> {
    let config = BytesConfig::new(file_data.to_vec()).with_min_length(min_length);
    let result = strings(&config).expect_throw("Failed to extract strings");

    result.iter().map(|s| s.0.to_string()).collect()
}

/// Extracts IPv4 addresses from a list of strings.
///
/// Searches for valid IPv4 address patterns and returns unique matches.
/// Useful for identifying:
/// - Command and control (C2) server addresses
/// - Network communication endpoints
/// - Hardcoded IP addresses
///
/// # Arguments
///
/// * `input` - Array of strings to search (typically from `extract_strings`)
///
/// # Returns
///
/// Array of unique IPv4 addresses found.
///
/// # Examples
///
/// ```javascript
/// const strings = extract_strings(fileData, 5);
/// const ips = extract_ips(strings);
/// console.log("Found IPs:", ips);
/// ```
#[wasm_bindgen]
pub fn extract_ips(input: Vec<String>) -> Vec<String> {
    let ip_regex = Regex::new(r"(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)").unwrap();
    let mut ips: HashSet<String> = HashSet::new();

    for string in input {
        for capture in ip_regex.captures_iter(&string) {
            if let Some(ip) = capture.get(0) {
                ips.insert(ip.as_str().to_string());
            }
        }
    }

    Vec::from_iter(ips)
}

/// Extracts HTTP/HTTPS URLs from a list of strings.
///
/// Searches for valid URL patterns and returns unique matches with proper domains.
/// Useful for identifying:
/// - Download URLs
/// - Phishing sites
/// - External resources
/// - Command and control servers
///
/// # Arguments
///
/// * `input` - Array of strings to search (typically from `extract_strings`)
///
/// # Returns
///
/// Array of unique URLs found.
///
/// # Examples
///
/// ```javascript
/// const strings = extract_strings(fileData, 5);
/// const urls = extract_urls(strings);
/// console.log("Found URLs:", urls);
/// ```
#[wasm_bindgen]
pub fn extract_urls(input: Vec<String>) -> Vec<String> {
    let url_regex = Regex::new(r"https?://[^\s]+").unwrap();
    let domain_regex =
        Regex::new(r"^(?:(?:https?://)?(?:www\.)?([a-zA-Z0-9-]+\.[a-zA-Z]{2,6}))").unwrap();
    let mut urls: HashSet<String> = HashSet::new();

    for string in input {
        for capture in url_regex.captures_iter(&string) {
            if let Some(url) = capture.get(0) {
                let url_str = url.as_str().to_string();

                if let Some(domain_capture) = domain_regex.captures(&url_str) {
                    if domain_capture.len() > 1 {
                        urls.insert(url_str);
                    }
                }
            }
        }
    }

    Vec::from_iter(urls)
}
