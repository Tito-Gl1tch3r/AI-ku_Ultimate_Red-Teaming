//! # PE (Portable Executable) File Analyzer
//!
//! This module provides analysis capabilities for Windows PE files (.exe, .dll).
//! It extracts import information, which is useful for understanding what
//! Windows APIs and DLLs the executable depends on.

use super::{analyzer_report::AnalyzerReport, analyzer_trait::FileAnalyzer};
use exe::{CCharString, ImportData, ImportDirectory, VecPE};

/// Analyzer for Windows PE (Portable Executable) format files.
///
/// Extracts information about imported DLLs and functions, which can help
/// identify the capabilities and behavior of the executable.
pub struct PeAnalyzer;

impl FileAnalyzer for PeAnalyzer {
    /// Analyzes a PE file and extracts import information.
    ///
    /// # Arguments
    ///
    /// * `file_data` - Raw bytes of the PE file
    ///
    /// # Returns
    ///
    /// An `AnalyzerReport` containing:
    /// - `imports`: Map of DLL names to lists of imported functions
    ///
    /// # Panics
    ///
    /// May panic if the PE file is corrupted or invalid.
    fn analyze(&self, file_data: &[u8]) -> AnalyzerReport {
        let mut report = AnalyzerReport::default();

        // Parse the PE file
        let image = VecPE::from_disk_data(file_data);

        // Parse import directory, return early if it fails
        let import_directory = match ImportDirectory::parse(&image) {
            Ok(dir) => dir,
            Err(e) => {
                log::error!("Failed to parse import directory: {:?}", e);
                return report;
            }
        };

        for descriptor in import_directory.descriptors {
            // Get DLL name, skip if unavailable
            let name = match descriptor.get_name(&image) {
                Ok(n) => match n.as_str() {
                    Ok(s) => s.to_string(),
                    Err(_) => continue,
                },
                Err(_) => continue,
            };

            let mut import_list: Vec<String> = Vec::new();

            log::debug!("Imported DLL: {}", name);

            // Get imports for this DLL
            if let Ok(imports) = descriptor.get_imports(&image) {
                for import in imports {
                    match import {
                        ImportData::Ordinal(x) => import_list.push(x.to_string()),
                        ImportData::ImportByName(s) => import_list.push(s.to_string()),
                    }
                }
            }

            report.add_imports(name.as_str(), import_list);
        }

        report
    }
}
