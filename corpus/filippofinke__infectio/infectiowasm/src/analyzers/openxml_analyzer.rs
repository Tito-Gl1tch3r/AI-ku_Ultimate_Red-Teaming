use super::{
    analyzer_report::{AnalyzerReport, Severity},
    analyzer_trait::{FileAnalyzer, FileEncryptedAnalyzer},
    zip_analyzer::ZipAnalyzer,
};

pub struct OpenXMLAnalyzer {}

impl OpenXMLAnalyzer {
    fn analyze_with_macros_check(&self, zip_report: &mut AnalyzerReport) {
        if let Some(items) = zip_report.items.as_ref() {
            let has_macros = items.iter().any(|item| {
                item.name.contains("vbaProject.bin")
                    || item.name.contains("vbaProject")
                    || item.name.contains("vba")
            });

            if has_macros {
                zip_report.add_heuristic("Contain macros", &Severity::High.as_str());
            }
        }
    }
}

impl FileEncryptedAnalyzer for OpenXMLAnalyzer {
    fn analyze_encrypted(&self, file_data: &[u8], password: &str) -> AnalyzerReport {
        let zip_analyzer = ZipAnalyzer {};
        let mut zip_report = zip_analyzer.analyze_encrypted(file_data, password);
        self.analyze_with_macros_check(&mut zip_report);
        zip_report
    }
}

impl FileAnalyzer for OpenXMLAnalyzer {
    fn analyze(&self, file_data: &[u8]) -> AnalyzerReport {
        let zip_analyzer = ZipAnalyzer {};
        let mut zip_report = zip_analyzer.analyze(file_data);
        self.analyze_with_macros_check(&mut zip_report);
        zip_report
    }
}
