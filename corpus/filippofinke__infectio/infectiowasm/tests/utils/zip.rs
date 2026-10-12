use infectiowasm::utils::zip::*;
use std::fs::File;
use std::io::Read;
use wasm_bindgen_test::*;

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    #[wasm_bindgen_test]
    fn test_decrypt_and_extract_zip_contents() {
        let mut file = File::open("tests/test_files/test.zip").expect("Failed to open test.zip");
        let mut data = Vec::new();
        file.read_to_end(&mut data)
            .expect("Failed to read test.zip");

        let items = decrypt_and_extract_zip_contents(&data, None);
        assert_eq!(items.len(), 1);
        assert_eq!(items[0].name, "test.txt");
        assert_eq!(items[0].item_type, "file");
        assert_eq!(items[0].encrypted, false);
    }

    #[test]
    #[wasm_bindgen_test]
    fn test_decrypt_and_extract_encrypted_zip_contents() {
        let mut file = File::open("tests/test_files/encrypted_test.zip")
            .expect("Failed to open encrypted_test.zip");
        let mut data = Vec::new();
        file.read_to_end(&mut data)
            .expect("Failed to read encrypted_test.zip");

        let items = decrypt_and_extract_zip_contents(&data, Some("password"));
        assert_eq!(items.len(), 1);
        assert_eq!(items[0].name, "test.txt");
        assert_eq!(items[0].item_type, "file");
        assert_eq!(items[0].encrypted, false);
    }
}
