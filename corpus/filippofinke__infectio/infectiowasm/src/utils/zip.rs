use crate::analyzers::analyzer_report::Item;
use std::io::Read;

pub fn decrypt_and_extract_zip_contents(file_data: &[u8], password: Option<&str>) -> Vec<Item> {
    let mut items: Vec<Item> = Vec::new();
    let reader = std::io::Cursor::new(file_data);

    let mut zip = match zip::ZipArchive::new(reader) {
        Ok(archive) => archive,
        Err(e) => {
            log::error!("Failed to open ZIP archive: {:?}", e);
            return items;
        }
    };

    // Collect file names first to avoid borrowing issues
    let file_names: Vec<String> = zip.file_names().map(|name| name.to_string()).collect();

    log::debug!("Number of files in the zip: {}", file_names.len());

    for file_name in file_names {
        log::debug!("File name: {}", file_name);

        let mut data = Vec::new();
        let mut item = Item {
            name: file_name.to_string(),
            size: 0,
            data: Vec::new(),
            encrypted: true,
            item_type: "file".to_string(),
        };

        let zip_file;
        if let Some(password) = password {
            zip_file = zip.by_name_decrypt(&file_name, password.as_bytes());
        } else {
            zip_file = zip.by_name(&file_name);
        }

        match zip_file {
            Ok(mut file) => match file.read_to_end(&mut data) {
                Ok(_) => {
                    let file_type = if file.is_dir() { "directory" } else { "file" };
                    item.data = data;
                    item.size = file.size();
                    item.item_type = file_type.to_string();
                    item.encrypted = false;
                }
                Err(e) => {
                    log::error!("Failed to read file contents {}: {:?}", file_name, e);
                }
            },
            Err(e) => {
                log::error!("Failed to read file {}: {:?}", file_name, e);
            }
        }

        items.push(item);
    }

    items
}
