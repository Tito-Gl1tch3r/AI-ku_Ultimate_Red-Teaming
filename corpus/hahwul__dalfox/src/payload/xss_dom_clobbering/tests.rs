use super::*;

#[test]
fn test_get_dom_clobbering_payloads_non_empty() {
    let payloads = get_dom_clobbering_payloads();
    assert!(!payloads.is_empty());
}

#[test]
fn test_get_dom_clobbering_payloads_contains_markers() {
    let payloads = get_dom_clobbering_payloads();
    let cls = crate::scanning::markers::class_marker();
    let idm = crate::scanning::markers::id_marker();
    let has_marker = payloads.iter().any(|p| p.contains(cls) || p.contains(idm));
    assert!(has_marker, "DOM clobbering payloads should contain markers");
}

#[test]
fn test_get_dom_clobbering_payloads_contains_anchor() {
    let payloads = get_dom_clobbering_payloads();
    assert!(
        payloads.iter().any(|p| p.contains("<a ")),
        "should include anchor-based clobbering"
    );
}

#[test]
fn test_get_dom_clobbering_payloads_contains_form() {
    let payloads = get_dom_clobbering_payloads();
    assert!(
        payloads.iter().any(|p| p.contains("<form")),
        "should include form-based clobbering"
    );
}
