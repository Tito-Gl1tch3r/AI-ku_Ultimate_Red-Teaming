use infectiowasm::utils::entropy::{calculate_entropy, calculate_entropy_by_chunks};
use wasm_bindgen_test::*;

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    #[wasm_bindgen_test]
    fn test_calculate_entropy() {
        let data = b"hello world";
        let entropy = calculate_entropy(data);
        assert!((entropy - 2.845).abs() < 0.001);
    }
    #[test]
    #[wasm_bindgen_test]
    fn test_calculate_entropy_empty() {
        let data = b"";
        let entropy = calculate_entropy(data);
        assert_eq!(entropy, 0.0);
    }
    #[wasm_bindgen_test]
    #[test]
    fn test_calculate_entropy_by_chunks_empty() {
        let data = b"";
        let chunk_size = 5;
        let result = calculate_entropy_by_chunks(data, chunk_size);
        assert_eq!(result.len(), 0);
    }
    #[test]
    #[wasm_bindgen_test]
    fn test_calculate_entropy_by_chunks_zero_chunk_size() {
        let data = b"hello world";
        let chunk_size = 0;
        let result = calculate_entropy_by_chunks(data, chunk_size);
        assert_eq!(result.len(), 0);
    }
}
