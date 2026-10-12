//! # Analyzer Report Structures
//!
//! This module defines the data structures used to represent analysis results.
//! All analyzers return their findings in these standardized formats.

use serde::{Deserialize, Serialize};
use std::collections::{BTreeMap, HashMap};

/// Security severity levels for heuristic warnings.
#[derive(Debug)]
pub enum Severity {
    /// Informational message, not a security concern
    Low,
    /// Minor security concern
    Medium,
    /// Significant security risk
    High,
    /// General information
    Info,
}

impl Severity {
    /// Converts severity to a string representation.
    ///
    /// # Returns
    ///
    /// String representation of the severity level.
    pub fn as_str(&self) -> &'static str {
        match self {
            Severity::Low => "Low",
            Severity::Medium => "Medium",
            Severity::High => "High",
            Severity::Info => "Info",
        }
    }
}

/// Represents a nested item within a file (e.g., a file within an archive).
///
/// This structure is used to represent the hierarchical structure of
/// archive files, Office documents, and other container formats.
#[derive(Serialize, Deserialize, Debug)]
pub struct Item {
    /// Name or path of the item
    pub name: String,
    /// Type of item: "file" or "folder"
    pub item_type: String,
    /// Raw bytes of the item
    pub data: Vec<u8>,
    /// Size in bytes
    pub size: u64,
    /// Whether the item is encrypted
    pub encrypted: bool,
}

/// Comprehensive analysis report containing all extracted information.
///
/// This is the primary data structure returned by all analyzers.
/// Fields are optional to allow different analyzers to report different types of information.
#[derive(Serialize, Deserialize, Debug)]
pub struct AnalyzerReport {
    /// Nested items (files/folders within archives or containers)
    pub items: Option<Vec<Item>>,
    /// Key-value metadata about the file
    pub metadata: Option<HashMap<String, String>>,
    /// Security warnings and suspicious patterns (ordered by name)
    pub heuristics: Option<BTreeMap<String, String>>,
    /// Imported functions/libraries (for executables)
    pub imports: Option<HashMap<String, Vec<String>>>,
}

impl Default for AnalyzerReport {
    fn default() -> Self {
        AnalyzerReport {
            items: None,
            metadata: None,
            heuristics: None,
            imports: None,
        }
    }
}

impl AnalyzerReport {
    /// Adds a collection of imports for a specific library or DLL.
    ///
    /// # Arguments
    ///
    /// * `dll_name` - Name of the library/DLL
    /// * `imports_list` - List of imported function names
    ///
    /// # Examples
    ///
    /// ```no_run
    /// report.add_imports("kernel32.dll", vec!["CreateFileA".to_string()]);
    /// ```
    pub fn add_imports(&mut self, dll_name: &str, imports_list: Vec<String>) {
        let imports = self.imports.get_or_insert_with(HashMap::new);
        imports.insert(dll_name.to_string(), imports_list);
    }

    /// Adds a heuristic warning to the report.
    ///
    /// # Arguments
    ///
    /// * `key` - Name of the heuristic check
    /// * `value` - Severity level ("Low", "Medium", "High", "Info")
    ///
    /// # Examples
    ///
    /// ```no_run
    /// report.add_heuristic("Suspicious API calls", "High");
    /// ```
    pub fn add_heuristic(&mut self, key: &str, value: &str) {
        let heuristics = self.heuristics.get_or_insert_with(BTreeMap::new);
        heuristics.insert(key.to_string(), value.to_string());
    }

    /// Adds a nested item to the report.
    ///
    /// # Arguments
    ///
    /// * `item` - The item to add
    ///
    /// # Examples
    ///
    /// ```no_run
    /// report.add_item(Item {
    ///     name: "document.txt".to_string(),
    ///     item_type: "file".to_string(),
    ///     data: vec![],
    ///     size: 0,
    ///     encrypted: false,
    /// });
    /// ```
    pub fn add_item(&mut self, item: Item) {
        let items = self.items.get_or_insert_with(Vec::new);
        items.push(item);
    }
}
