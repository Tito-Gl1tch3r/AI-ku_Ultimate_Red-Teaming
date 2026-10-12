use lopdf::Document;

use crate::analyzers::analyzer_report::{Item, Severity};

use super::{analyzer_report::AnalyzerReport, analyzer_trait::FileAnalyzer};

pub struct PDFAnalyzer {}

impl FileAnalyzer for PDFAnalyzer {
    fn analyze(&self, file_data: &[u8]) -> AnalyzerReport {
        let mut report = AnalyzerReport::default();

        let doc = match Document::load_mem(file_data) {
            Ok(doc) => doc,
            Err(e) => {
                log::error!("Failed to load PDF document: {:?}", e);
                return report;
            }
        };

        // Print all objects
        doc.objects.iter().for_each(|(key, value)| {
            // Check if the object is a dictionary
            if let lopdf::Object::Dictionary(dict) = value {
                if let Ok(lopdf::Object::Name(action_type)) = dict.get(b"S") {
                    if action_type == b"JavaScript" {
                        if let Ok(js_content) = dict.get(b"JS") {
                            let decoded_js = match js_content {
                                lopdf::Object::String(js, _) => {
                                    // Direct string, decode as UTF-8
                                    String::from_utf8_lossy(js).to_string()
                                }
                                _ => "Unsupported JS format".to_string(),
                            };

                            report.add_heuristic("Contains JavaScript", &Severity::High.as_str());

                            let js = decoded_js.as_bytes();

                            let file_name = format!("extracted/{:?}.js", key);

                            report.add_item(Item {
                                encrypted: false,
                                name: file_name,
                                data: js.to_vec(),
                                item_type: "file".to_string(),
                                size: js.len() as u64,
                            })
                        }
                    }
                }

                if let Ok(lopdf::Object::Dictionary(names)) = dict.get(b"Names") {
                    // Get the EmbeddedFiles reference
                    if let Ok(lopdf::Object::Reference(reference)) = names.get(b"EmbeddedFiles") {
                        let object = doc
                            .get_object(reference.to_owned())
                            .unwrap()
                            .as_dict()
                            .unwrap();
                        let names = object.get(b"Names").unwrap().as_array().unwrap();

                        // Go over the array where every two elements are a name and a reference
                        for i in (0..names.len()).step_by(2) {
                            let name = names[i].as_string().unwrap();
                            let reference = names[i + 1].as_reference().unwrap();

                            log::info!("Embedded file: {:?}: {:?}", name, reference);

                            let file_spec = doc.get_object(reference).unwrap().as_dict().unwrap();

                            let file_name = file_spec.get(b"F").unwrap().as_string().unwrap();
                            let file_reference = file_spec
                                .get(b"EF")
                                .unwrap()
                                .as_dict()
                                .unwrap()
                                .get(b"F")
                                .unwrap()
                                .as_reference()
                                .unwrap();

                            let file = doc.get_object(file_reference).unwrap().as_stream().unwrap();

                            let file_data = file.decompressed_content().unwrap();
                            let length = file_data.len();

                            report
                                .add_heuristic("Contains embedded file", &Severity::High.as_str());

                            report.add_item(Item {
                                name: file_name.to_string(),
                                data: file_data,
                                item_type: "file".to_string(),
                                size: length as u64,
                                encrypted: false,
                            });
                        }
                    }
                }
            }
        });

        report
    }
}
