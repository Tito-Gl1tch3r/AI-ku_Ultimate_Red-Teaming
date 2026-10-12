//! # ELF (Executable and Linkable Format) File Analyzer
//!
//! This module provides analysis capabilities for Linux ELF binaries.
//! It extracts both dynamic and static symbol information.

use super::{analyzer_report::AnalyzerReport, analyzer_trait::FileAnalyzer};
use elf::{endian::AnyEndian, ElfBytes};
use std::collections::HashMap;

/// Analyzer for Linux ELF (Executable and Linkable Format) files.
///
/// Extracts symbol information from both the dynamic symbol table (dynsyms)
/// and the static symbol table (symtab).
pub struct ElfAnalyzer;

impl FileAnalyzer for ElfAnalyzer {
    /// Analyzes an ELF file and extracts symbol information.
    ///
    /// # Arguments
    ///
    /// * `file_data` - Raw bytes of the ELF file
    ///
    /// # Returns
    ///
    /// An `AnalyzerReport` containing:
    /// - `imports`: Map of library names to lists of imported functions
    ///
    /// # Panics
    ///
    /// May panic if the ELF file is corrupted or missing expected sections.
    fn analyze(&self, file_data: &[u8]) -> AnalyzerReport {
        let mut report = AnalyzerReport::default();

        // Parse ELF file, return early if invalid
        let file = match ElfBytes::<AnyEndian>::minimal_parse(file_data) {
            Ok(f) => f,
            Err(e) => {
                log::error!("Failed to parse ELF file: {:?}", e);
                return report;
            }
        };

        let mut imports: HashMap<String, Vec<String>> = HashMap::new();

        // Find common data sections
        let common = match file.find_common_data() {
            Ok(c) => c,
            Err(e) => {
                log::error!("Failed to find common ELF sections: {:?}", e);
                return report;
            }
        };

        // Process dynamic symbols if available
        if let (Some(dynsyms), Some(strtab)) = (common.dynsyms, common.dynsyms_strs) {
            for sym in dynsyms {
                if let Ok(name) = strtab.get(sym.st_name as usize) {
                    let parts: Vec<&str> = name.split("::").collect();
                    if parts.len() >= 2 {
                        let lib = parts[0].to_string();
                        let func = parts[parts.len() - 1].to_string();

                        if !lib.is_empty() && !func.is_empty() {
                            imports.entry(lib).or_insert_with(Vec::new).push(func);
                        }
                    }
                }
            }
        }

        // Process static symbols if available
        if let (Some(syms), Some(strtab)) = (common.symtab, common.symtab_strs) {
            for sym in syms {
                if let Ok(name) = strtab.get(sym.st_name as usize) {
                    let parts: Vec<&str> = name.split("::").collect();
                    if parts.len() >= 2 {
                        let lib = parts[0].to_string();
                        let func = parts[parts.len() - 1].to_string();

                        if !lib.is_empty() && !func.is_empty() {
                            imports.entry(lib).or_insert_with(Vec::new).push(func);
                        }
                    }
                }
            }
        }

        report.imports = Some(imports);
        report
    }
}
