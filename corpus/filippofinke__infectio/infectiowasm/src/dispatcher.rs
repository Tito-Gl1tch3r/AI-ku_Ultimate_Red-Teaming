//! # File Dispatcher Module
//!
//! This module routes files to the appropriate analyzer based on their MIME type.
//! It acts as the central dispatching mechanism for the analysis system.
//!
//! ## Supported File Types
//!
//! - **Windows Executables**: PE format (.exe, .dll)
//! - **Linux Executables**: ELF format
//! - **macOS Executables**: Mach-O format
//! - **Documents**: PDF files
//! - **Archives**: ZIP files
//! - **Office Documents**: DOCX, XLSX, PPTX (OpenXML format)
//! - **Legacy Office**: DOC, XLS, PPT (OLE2 format)
//!
//! ## Error Handling
//!
//! If a file type is not supported, the dispatcher returns an
//! `AnalyzeError::UnsupportedFileType` error.

use std::collections::HashMap;

use crate::analyzers::analyzer_report::AnalyzerReport;
use crate::analyzers::analyzer_trait::{FileAnalyzer, FileEncryptedAnalyzer};
use crate::analyzers::elf_analyzer::ElfAnalyzer;
use crate::analyzers::mach_analyzer::MachAnalyzer;
use crate::analyzers::ole_analyzer::OleAnalyzer;
use crate::analyzers::openxml_analyzer::OpenXMLAnalyzer;
use crate::analyzers::pdf_analyzer::PDFAnalyzer;
use crate::analyzers::pe_analyzer::PeAnalyzer;
/// Errors that can occur during file analysis.
#[derive(Debug)]
pub enum AnalyzeError {
    /// The file type is not supported by any analyzer.
    ///
    /// Contains the MIME type that was attempted.
    UnsupportedFileType(String),
}

impl std::fmt::Display for AnalyzeError {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        match self {
            AnalyzeError::UnsupportedFileType(mime_type) => {
                write!(f, "Unsupported file type: {}", mime_type)
            }
        }
    }
}

/// Routes a file to the appropriate analyzer based on its MIME type.
///
/// This function is the core dispatcher that examines the MIME type and
/// delegates analysis to the specialized analyzer for that format.
///
/// # Arguments
///
/// * `mime_type` - The MIME type of the file
/// * `file_data` - The raw file contents
/// * `password` - Optional password for encrypted files
///
/// # Returns
///
/// Returns `Ok(AnalyzerReport)` with the analysis results, or
/// `Err(AnalyzeError)` if the file type is unsupported.
///
/// # Supported MIME Types
///
/// - `application/vnd.microsoft.portable-executable` - Windows PE files
/// - `application/x-executable` - Linux ELF files
/// - `application/x-mach-binary` - macOS Mach-O files
/// - `application/pdf` - PDF documents
/// - `application/zip` - ZIP archives
/// - `application/vnd.openxmlformats-*` - Modern Office documents
/// - `application/msword`, `application/x-ole-storage` - Legacy Office
///
/// # Examples
///
/// ```no_run
/// let report = analyze_file_by_mime(
///     "application/pdf",
///     &file_data,
///     None
/// )?;
/// ```
pub fn analyze_file_by_mime(
    mime_type: &str,
    file_data: &[u8],
    password: Option<&str>,
) -> Result<AnalyzerReport, AnalyzeError> {
    let mut result = match mime_type {
        "application/zip"
        | "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        | "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        | "application/vnd.openxmlformats-officedocument.presentationml.presentation" => {
            let analyzer = OpenXMLAnalyzer {};
            match password {
                Some(password) => Ok(analyzer.analyze_encrypted(file_data, password)),
                None => Ok(analyzer.analyze(file_data)),
            }
        }
        "application/vnd.microsoft.portable-executable" => {
            let analyzer = PeAnalyzer {};
            Ok(analyzer.analyze(file_data))
        }
        "application/x-executable" => {
            let analyzer = ElfAnalyzer {};
            Ok(analyzer.analyze(file_data))
        }
        "application/x-mach-binary" => {
            let analyzer = MachAnalyzer {};
            Ok(analyzer.analyze(file_data))
        }
        "application/pdf" => {
            let analyzer = PDFAnalyzer {};
            Ok(analyzer.analyze(file_data))
        }
        "application/msword"
        | "application/x-ole-storage"
        | "application/vnd.ms-powerpoint"
        | "application/vnd.ms-excel" => {
            let analyzer = OleAnalyzer {};

            let ole_report = analyzer.analyze(file_data);

            let analyzer = OpenXMLAnalyzer {};

            let mut openxml = analyzer.analyze(file_data);

            openxml.heuristics = ole_report.heuristics;

            Ok(openxml)
        }
        _ => Err(AnalyzeError::UnsupportedFileType(mime_type.to_string())),
    };

    if let Ok(report) = &mut result {
        report.metadata.get_or_insert_with(HashMap::new);
    }
    result
}
