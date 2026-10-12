//! # Entropy Calculation Utilities
//!
//! This module provides functions for calculating Shannon entropy of file data.
//! Entropy is useful for detecting packed, encrypted, or compressed content.
//!
//! ## What is Entropy?
//!
//! Shannon entropy measures the randomness of data. Values range from:
//! - **0.0**: Completely uniform (all same byte)
//! - **8.0**: Completely random (maximum entropy for bytes)
//!
//! Typical entropy values:
//! - Plain text: 3.5 - 5.0
//! - Compressed data: 7.5 - 8.0
//! - Encrypted data: 7.9 - 8.0
//! - Packed executables: Often > 7.0

use std::collections::HashMap;

use wasm_bindgen::prelude::*;

/// Calculates the Shannon entropy of file data.
///
/// Entropy measures the randomness or information density of data.
/// High entropy (> 7.0) often indicates encryption, compression, or packing.
///
/// # Arguments
///
/// * `file_data` - The raw bytes to analyze
///
/// # Returns
///
/// Entropy value between 0.0 (no randomness) and 8.0 (maximum randomness)
///
/// # Examples
///
/// ```javascript
/// const entropy = calculate_entropy(fileData);
/// if (entropy > 7.5) {
///     console.log("File appears encrypted or compressed");
/// }
/// ```
#[wasm_bindgen]
pub fn calculate_entropy(file_data: &[u8]) -> f64 {
    let mut freq_map = HashMap::new();
    let file_len = file_data.len() as f64;

    for &byte in file_data {
        *freq_map.entry(byte).or_insert(0) += 1;
    }

    let mut entropy = 0.0;
    for &count in freq_map.values() {
        let probability = (count as f64) / file_len;
        entropy -= probability * probability.log2();
    }

    entropy
}

/// Calculates entropy for each chunk of a file.
///
/// This function divides the file into chunks and calculates entropy for each,
/// allowing visualization of entropy distribution across the file. Useful for:
/// - Identifying encrypted sections within a file
/// - Detecting packed code segments
/// - Visualizing data randomness patterns
///
/// # Arguments
///
/// * `file_data` - The raw bytes to analyze
/// * `chunk_size` - Size of each chunk in bytes (e.g., 256, 512, 1024)
///
/// # Returns
///
/// Array of JavaScript objects, each containing:
/// - `index`: Chunk number (0-based)
/// - `entropy`: Entropy value for that chunk
///
/// Returns empty array if chunk_size is 0 or file_data is empty.
///
/// # Examples
///
/// ```javascript
/// const chunks = calculate_entropy_by_chunks(fileData, 256);
/// chunks.forEach(chunk => {
///     console.log(`Chunk ${chunk.index}: ${chunk.entropy}`);
/// });
/// ```
#[wasm_bindgen]
pub fn calculate_entropy_by_chunks(file_data: &[u8], chunk_size: usize) -> Vec<JsValue> {
    let mut result = Vec::new();
    let file_len = file_data.len();

    if chunk_size == 0 || file_len == 0 {
        return result;
    }

    let num_chunks = (file_len + chunk_size - 1) / chunk_size;

    for i in 0..num_chunks {
        let start = i * chunk_size;
        let end = ((i + 1) * chunk_size).min(file_len);
        let chunk = &file_data[start..end];

        let mut freq_map = HashMap::new();
        let chunk_len = chunk.len() as f64;

        for &byte in chunk {
            *freq_map.entry(byte).or_insert(0) += 1;
        }

        let mut entropy = 0.0;
        for &count in freq_map.values() {
            let probability = (count as f64) / chunk_len;
            entropy -= probability * probability.log2();
        }

        // Create a JavaScript object for each chunk
        let obj = js_sys::Object::new();
        js_sys::Reflect::set(&obj, &"index".into(), &JsValue::from(i)).unwrap();
        js_sys::Reflect::set(&obj, &"entropy".into(), &JsValue::from_f64(entropy)).unwrap();

        result.push(JsValue::from(obj));
    }

    result
}
