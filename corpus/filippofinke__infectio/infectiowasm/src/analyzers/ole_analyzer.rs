use ole::OleFile;

use super::{
    analyzer_report::{AnalyzerReport, Severity},
    analyzer_trait::FileAnalyzer,
};

pub struct OleAnalyzer {}

impl FileAnalyzer for OleAnalyzer {
    fn analyze(&self, file_data: &[u8]) -> AnalyzerReport {
        let file = OleFile::from_bytes(file_data.to_vec()).unwrap();
        let mut report = AnalyzerReport::default();

        self.add_file_type_info(&file, &mut report);
        self.log_directory_entries(&file);
        self.check_encrypted_streams(&file, &mut report);
        self.check_vba_projects(&file, &mut report);
        self.check_embedded_objects(&file, &mut report);
        self.check_encryption_flag(&file, &mut report);

        report
    }
}

impl OleAnalyzer {
    /// Adds OLE file type information to the report.
    fn add_file_type_info(&self, file: &OleFile, report: &mut AnalyzerReport) {
        report.add_heuristic(
            format!("OLE file type: {:?}", file.file_type).as_str(),
            &Severity::Info.as_str(),
        );
    }

    /// Logs all directory entries in the OLE file.
    fn log_directory_entries(&self, file: &OleFile) {
        file.directory_entries.iter().for_each(|entry| {
            log::debug!("Entry: {:?} {:?}", entry.object_type, entry.name);
        });
    }

    /// Checks for encrypted streams and adds heuristics to the report.
    fn check_encrypted_streams(&self, file: &OleFile, report: &mut AnalyzerReport) {
        if file.list_streams().contains(&"EncryptionInfo".to_string())
            || file
                .list_streams()
                .contains(&"EncryptedPackage".to_string())
        {
            report.add_heuristic("Contains an encrypted stream", &Severity::High.as_str());
        }
    }

    /// Checks for VBA projects and adds heuristics to the report.
    fn check_vba_projects(&self, file: &OleFile, report: &mut AnalyzerReport) {
        let macro_keys = vec!["_VBA_PROJECT_CUR", "VBA", "_VBA_PROJECT"];

        for key in macro_keys {
            if file.list_streams().contains(&key.to_string()) {
                report.add_heuristic(
                    "Contains a VBA project, likely to contain macros",
                    &Severity::High.as_str(),
                );
                break;
            }
        }
    }

    /// Checks for embedded objects and adds heuristics to the report.
    fn check_embedded_objects(&self, file: &OleFile, report: &mut AnalyzerReport) {
        if file
            .directory_entries
            .iter()
            .any(|entry| entry.name == "ObjectPool")
        {
            report.add_heuristic(
                "List of objects in the file, may contain embedded objects",
                &Severity::Medium.as_str(),
            );
        }
    }

    /// Checks if the OLE file is encrypted and adds heuristics to the report.
    fn check_encryption_flag(&self, file: &OleFile, report: &mut AnalyzerReport) {
        if file.encrypted {
            report.add_heuristic("OLE file is encrypted", &Severity::Low.as_str());
        }
    }
}
