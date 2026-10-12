use infectiowasm::utils::hashes::*;
use wasm_bindgen_test::*;

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    #[wasm_bindgen_test]
    fn test_md5() {
        let data = b"hello world";
        let hash = md5(data);
        assert_eq!(hash, "5eb63bbbe01eeed093cb22bb8f5acdc3");
    }

    #[test]
    #[wasm_bindgen_test]
    fn test_sha1() {
        let data = b"hello world";
        let hash = sha1(data);
        assert_eq!(hash, "2aae6c35c94fcfb415dbe95f408b9ce91ee846ed");
    }

    #[test]
    #[wasm_bindgen_test]
    fn test_sha256() {
        let data = b"hello world";
        let hash = sha256(data);
        assert_eq!(
            hash,
            "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"
        );
    }
}
