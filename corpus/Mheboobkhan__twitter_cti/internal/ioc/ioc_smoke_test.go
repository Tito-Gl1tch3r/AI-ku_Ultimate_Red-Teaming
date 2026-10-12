package ioc

import "testing"

func TestExtractAllSmoke(t *testing.T) {
	text := `New C2 seen: 185.220.101[.]45 and 1.2.3.4 also hxxps://evil-domain[.]com/panel/login.php ` +
		`and https://good.example.org/path plus a fanged url http://t.co/abc123 ` +
		`hashes: 44d88612fea8a8f36de82e1278abb02f e242ed3bffccdf271b7fbaf34ed72d089537b42f ` +
		`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 also mention godotengine.org and evil[.]example[.]net`

	matches := ExtractAll(text)
	if len(matches) == 0 {
		t.Fatal("expected matches, got none")
	}
	byType := map[string][]Match{}
	for _, m := range matches {
		byType[m.Type] = append(byType[m.Type], m)
	}

	for _, ipVal := range []string{"185.220.101.45", "1.2.3.4"} {
		found := false
		for _, m := range byType["ip"] {
			if m.Value == ipVal {
				found = true
			}
		}
		if !found {
			t.Errorf("expected ip %s in %+v", ipVal, byType["ip"])
		}
	}

	foundDefangedURL := false
	for _, m := range byType["url"] {
		if m.Value == "https://evil-domain.com/panel/login.php" && m.Defanged && m.Raw == "hxxps://evil-domain[.]com/panel/login.php" {
			foundDefangedURL = true
		}
	}
	if !foundDefangedURL {
		t.Errorf("expected defanged url https://evil-domain.com/panel/login.php, got %+v", byType["url"])
	}
	// evil-domain.com is inside the defanged URL above and should NOT also
	// be reported separately as a standalone domain.
	for _, m := range byType["domain"] {
		if m.Value == "evil-domain.com" {
			t.Errorf("evil-domain.com should have been suppressed as part of the defanged URL, got %+v", byType["domain"])
		}
	}

	plainURLCount := 0
	for _, m := range byType["url"] {
		if m.Value == "https://good.example.org/path" {
			plainURLCount++
			if m.Defanged {
				t.Errorf("plain url incorrectly marked Defanged: %+v", m)
			}
		}
	}
	if plainURLCount != 1 {
		t.Errorf("expected exactly 1 match for good.example.org url, got %d", plainURLCount)
	}

	foundStandaloneDefangedDomain := false
	for _, m := range byType["domain"] {
		if m.Value == "evil.example.net" && m.Defanged {
			foundStandaloneDefangedDomain = true
		}
	}
	if !foundStandaloneDefangedDomain {
		t.Errorf("expected standalone defanged domain evil.example.net, got %+v", byType["domain"])
	}

	for _, hv := range []string{"44d88612fea8a8f36de82e1278abb02f", "e242ed3bffccdf271b7fbaf34ed72d089537b42f", "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"} {
		found := false
		for _, m := range byType["hash"] {
			if m.Value == hv {
				found = true
			}
		}
		if !found {
			t.Errorf("expected hash %s, got %+v", hv, byType["hash"])
		}
	}

	foundURL := false
	for _, m := range byType["url"] {
		if m.Value == "https://good.example.org/path" {
			foundURL = true
		}
	}
	if !foundURL {
		t.Errorf("expected url https://good.example.org/path, got %+v", byType["url"])
	}

	for _, m := range byType["domain"] {
		if m.Value == "good.example.org" || m.Value == "example.org" {
			t.Errorf("domain %s should have been suppressed as part of an already-found URL", m.Value)
		}
	}
}
