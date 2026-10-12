use infectiowasm::utils::strings::*;
use wasm_bindgen_test::*;

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    #[wasm_bindgen_test]
    fn test_extract_strings() {
        let data = b"hello world\x00\x01\x02test string";
        let result = extract_strings(data, 5);
        assert_eq!(result, vec!["hello world", "test string"]);
    }

    #[test]
    #[wasm_bindgen_test]
    fn test_extract_ips() {
        let input = vec![
            "This is a test string with IP 192.168.1.1".to_string(),
            "Another string with IP 10.0.0.1".to_string(),
        ];
        let result = extract_ips(input);

        let expected = vec!["192.168.1.1", "10.0.0.1"];

        // Check the contents of the vectors is the same no matter the order
        assert_eq!(result.len(), expected.len());
        for ip in result {
            assert!(expected.contains(&ip.as_str()));
        }
    }

    #[test]
    #[wasm_bindgen_test]
    fn test_extract_urls() {
        let input = vec![
            "Check out https://example.com".to_string(),
            "Visit http://test.org for more info".to_string(),
        ];
        let result = extract_urls(input);
        let expected = vec!["https://example.com", "http://test.org"];

        // Check the contents of the vectors is the same no matter the order
        assert_eq!(result.len(), expected.len());
        for url in result {
            assert!(expected.contains(&url.as_str()));
        }
    }
}
