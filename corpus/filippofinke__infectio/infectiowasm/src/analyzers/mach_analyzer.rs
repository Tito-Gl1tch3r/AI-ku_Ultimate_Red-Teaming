//! # Mach-O File Analyzer
//!
//! This module provides analysis capabilities for macOS Mach-O binaries.
//! It handles both single-architecture and universal (fat) binaries.

use goblin::mach::{Mach, SingleArch};

use super::{analyzer_report::AnalyzerReport, analyzer_trait::FileAnalyzer};
use std::collections::HashMap;

/// Analyzer for macOS Mach-O format files.
///
/// Supports both:
/// - Single architecture binaries
/// - Universal (fat) binaries containing multiple architectures
pub struct MachAnalyzer;

/// Extracts the library name from a full dylib path.
///
/// # Arguments
///
/// * `name` - Full path to the dylib (e.g., "/usr/lib/libSystem.B.dylib")
///
/// # Returns
///
/// Just the library name without path or extension (e.g., "libSystem")
fn dylib_name(name: &str) -> &str {
    name.rsplit('/').next().unwrap().split('.').next().unwrap()
}

/// Extracts imports from a single Mach-O architecture.
///
/// # Arguments
///
/// * `arch` - The Mach-O architecture to analyze
///
/// # Returns
///
/// Map of library names to lists of imported symbols
fn extract_imports(arch: SingleArch) -> HashMap<String, Vec<String>> {
    let mut imports = HashMap::new();

    match arch {
        SingleArch::MachO(arch) => {
            let imports_list = arch.imports().expect("imports");

            for import in imports_list {
                let name = import.name.to_string();
                let module = dylib_name(import.dylib);

                let list = imports.entry(module.to_string()).or_insert(vec![]);
                list.push(name);
            }
        }
        _ => {}
    }

    imports
}

impl FileAnalyzer for MachAnalyzer {
    /// Analyzes a Mach-O file and extracts import information.
    ///
    /// Handles both single-architecture and universal (fat) binaries.
    /// For fat binaries, imports from all architectures are merged.
    ///
    /// # Arguments
    ///
    /// * `file_data` - Raw bytes of the Mach-O file
    ///
    /// # Returns
    ///
    /// An `AnalyzerReport` containing:
    /// - `imports`: Map of dylib names to lists of imported symbols
    ///
    /// # Panics
    ///
    /// May panic if the Mach-O file is corrupted or invalid.
    fn analyze(&self, file_data: &[u8]) -> AnalyzerReport {
        let mut imports: HashMap<String, Vec<String>> = HashMap::new();

        let mach = Mach::parse(file_data).unwrap();

        match mach {
            Mach::Binary(binary) => {
                imports.extend(extract_imports(SingleArch::MachO(binary)));
            }
            Mach::Fat(fat) => {
                for arch in fat.into_iter() {
                    match arch {
                        Ok(SingleArch::MachO(arch)) => {
                            imports.extend(extract_imports(SingleArch::MachO(arch)));
                        }
                        Ok(SingleArch::Archive(_)) => {
                            log::debug!("Archive");
                        }
                        Err(err) => {
                            log::error!("Error parsing Mach-O: {:?}", err);
                        }
                    }
                }
            }
        }

        AnalyzerReport {
            items: None,
            metadata: None,
            imports: Some(imports),
            heuristics: None,
        }
    }
}
