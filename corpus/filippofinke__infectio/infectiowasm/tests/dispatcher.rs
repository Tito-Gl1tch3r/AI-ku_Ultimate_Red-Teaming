use infectiowasm::dispatcher::*;
use std::fs::File;
use std::io::Read;
use wasm_bindgen_test::*;

#[cfg(test)]
mod tests {
    use super::*;

    fn read_file(file_path: &str) -> Vec<u8> {
        let mut file = File::open(file_path).expect(&format!("Failed to open {}", file_path));
        let mut data = Vec::new();
        file.read_to_end(&mut data)
            .expect(&format!("Failed to read {}", file_path));
        data
    }

    #[test]
    #[wasm_bindgen_test]
    fn test_analyzer_macho_file() {
        let data = read_file("tests/test_files/fd.match-o");
        let result = analyze_file_by_mime("application/x-mach-binary", &data, None);
        assert!(result.is_ok());
    }

    #[test]
    #[wasm_bindgen_test]
    fn test_analyze_zip_file() {
        let data = read_file("tests/test_files/test.zip");
        let report = analyze_file_by_mime("application/zip", &data, None)
            .expect("Failed to analyze zip file");
        assert!(report.metadata.is_some());
    }

    #[test]
    #[wasm_bindgen_test]
    fn test_analyze_pe_file() {
        let data = read_file("tests/test_files/putty.exe");
        let report =
            analyze_file_by_mime("application/vnd.microsoft.portable-executable", &data, None)
                .expect("Failed to analyze pe file");
        assert!(report.metadata.is_some());
    }

    #[test]
    #[wasm_bindgen_test]
    fn test_analyze_unsupported_file() {
        let data = b"unsupported file content";
        let result = analyze_file_by_mime("application/unsupported", data, None);
        assert!(result.is_err());
    }

    #[test]
    #[wasm_bindgen_test]
    fn test_analyze_encrypted_zip_file() {
        let data = read_file("tests/test_files/encrypted_test.zip");
        let report = analyze_file_by_mime("application/zip", &data, Some("password"))
            .expect("Failed to analyze encrypted zip file");
        assert!(report.metadata.is_some());
    }

    #[test]
    #[wasm_bindgen_test]
    fn test_analyze_dummy_with_attachment_pdf() {
        let data = read_file("tests/test_files/dummy_with_attachment.pdf");
        let report = analyze_file_by_mime("application/pdf", &data, None)
            .expect("Failed to analyze dummy_with_attachment.pdf");
        assert!(report.metadata.is_some());
    }

    #[test]
    #[wasm_bindgen_test]
    fn test_analyze_dummy_with_attachment3_pdf() {
        let data = read_file("tests/test_files/dummy_with_attachment3.pdf");
        let report = analyze_file_by_mime("application/pdf", &data, None)
            .expect("Failed to analyze dummy_with_attachment3.pdf");
        assert!(report.metadata.is_some());
    }

    #[test]
    #[wasm_bindgen_test]
    fn test_analyze_dummy_pdf() {
        let data = read_file("tests/test_files/dummy.pdf");
        let report = analyze_file_by_mime("application/pdf", &data, None)
            .expect("Failed to analyze dummy.pdf");
        assert!(report.metadata.is_some());
    }

    #[test]
    #[wasm_bindgen_test]
    fn test_analyze_maldoc_xls() {
        let data = read_file("tests/test_files/maldoc.xls");
        let report = analyze_file_by_mime("application/vnd.ms-excel", &data, None)
            .expect("Failed to analyze maldoc.xls");
        assert!(report.metadata.is_some());
    }

    #[test]
    #[wasm_bindgen_test]
    fn test_analyze_plain_doc() {
        let data = read_file("tests/test_files/plain.doc");
        let report = analyze_file_by_mime("application/msword", &data, None)
            .expect("Failed to analyze plain.doc");
        assert!(report.metadata.is_some());
    }

    #[test]
    #[wasm_bindgen_test]
    fn test_analyze_plain_ppt() {
        let data = read_file("tests/test_files/plain.ppt");
        let report = analyze_file_by_mime("application/vnd.ms-powerpoint", &data, None)
            .expect("Failed to analyze plain.ppt");
        assert!(report.metadata.is_some());
    }

    #[test]
    #[wasm_bindgen_test]
    fn test_analyze_plain_xls() {
        let data = read_file("tests/test_files/plain.xls");
        let report = analyze_file_by_mime("application/vnd.ms-excel", &data, None)
            .expect("Failed to analyze plain.xls");
        assert!(report.metadata.is_some());
    }

    #[test]
    #[wasm_bindgen_test]
    fn test_analyze_test_txt() {
        let data = read_file("tests/test_files/test.txt");
        let result = analyze_file_by_mime("text/plain", &data, None);
        assert!(result.is_err());
    }
}
