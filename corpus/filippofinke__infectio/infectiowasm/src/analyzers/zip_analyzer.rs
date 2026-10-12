use crate::utils::zip::decrypt_and_extract_zip_contents;

use super::{
    analyzer_report::{AnalyzerReport, Item, Severity},
    analyzer_trait::{FileAnalyzer, FileEncryptedAnalyzer},
};

pub struct ZipAnalyzer;

impl FileAnalyzer for ZipAnalyzer {
    fn analyze(&self, file_data: &[u8]) -> AnalyzerReport {
        let items: Vec<Item> = decrypt_and_extract_zip_contents(file_data, None);

        let contains_encrypted_files = items.iter().any(|item| item.encrypted);

        let mut report = AnalyzerReport {
            items: Some(items),
            metadata: None,
            imports: None,
            heuristics: None,
        };

        if contains_encrypted_files {
            report.add_heuristic(
                "Encrypted files found in ZIP archive",
                &Severity::Medium.as_str(),
            );
        }

        report
    }
}

impl FileEncryptedAnalyzer for ZipAnalyzer {
    fn analyze_encrypted(&self, file_data: &[u8], password: &str) -> AnalyzerReport {
        let items: Vec<Item> = decrypt_and_extract_zip_contents(file_data, Some(password));

        let mut report = AnalyzerReport {
            items: Some(items),
            metadata: None,
            imports: None,
            heuristics: None,
        };

        report.add_heuristic("Archive is encrypted", &Severity::Info.as_str());

        report
    }
}
