package mod

import (
	"encoding/base64"
	"testing"
)

func TestAdaptUserdata(t *testing.T) {
	testUserdata := "#!/bin/bash\necho 'Hello World'"

	tests := []struct {
		name           string
		provider       string
		userdata       string
		wantEncoded    bool
		wantErr        bool
		wantErrCode    string
	}{
		{
			name:        "alicloud should encode to base64",
			provider:    "alicloud",
			userdata:    testUserdata,
			wantEncoded: true,
			wantErr:     false,
		},
		{
			name:        "tencentcloud should use raw text",
			provider:    "tencentcloud",
			userdata:    testUserdata,
			wantEncoded: false,
			wantErr:     false,
		},
		{
			name:        "aws should encode to base64",
			provider:    "aws",
			userdata:    testUserdata,
			wantEncoded: true,
			wantErr:     false,
		},
		{
			name:        "volcengine should use raw text",
			provider:    "volcengine",
			userdata:    testUserdata,
			wantEncoded: false,
			wantErr:     false,
		},
		{
			name:        "huaweicloud should use raw text",
			provider:    "huaweicloud",
			userdata:    testUserdata,
			wantEncoded: false,
			wantErr:     false,
		},
		{
			name:        "empty userdata should return empty string",
			provider:    "alicloud",
			userdata:    "",
			wantEncoded: false,
			wantErr:     false,
		},
		{
			name:        "unsupported provider should return error",
			provider:    "unsupported",
			userdata:    testUserdata,
			wantErr:     true,
			wantErrCode: ErrCodeNotSupported,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, err := AdaptUserdata(tt.provider, tt.userdata)

			// Check error
			if (err != nil) != tt.wantErr {
				t.Errorf("AdaptUserdata() error = %v, wantErr %v", err, tt.wantErr)
				return
			}

			if tt.wantErr {
				// Verify error code
				if verr, ok := err.(*ValidationError); ok {
					if verr.Code != tt.wantErrCode {
						t.Errorf("AdaptUserdata() error code = %v, want %v", verr.Code, tt.wantErrCode)
					}
				} else {
					t.Errorf("AdaptUserdata() error is not ValidationError")
				}
				return
			}

			// Check empty userdata case
			if tt.userdata == "" {
				if got != "" {
					t.Errorf("AdaptUserdata() with empty userdata = %v, want empty string", got)
				}
				return
			}

			// Check encoding
			if tt.wantEncoded {
				// Should be base64 encoded
				expected := base64.StdEncoding.EncodeToString([]byte(tt.userdata))
				if got != expected {
					t.Errorf("AdaptUserdata() = %v, want %v", got, expected)
				}

				// Verify it can be decoded back
				decoded, err := base64.StdEncoding.DecodeString(got)
				if err != nil {
					t.Errorf("AdaptUserdata() result is not valid base64: %v", err)
				}
				if string(decoded) != tt.userdata {
					t.Errorf("AdaptUserdata() decoded = %v, want %v", string(decoded), tt.userdata)
				}
			} else {
				// Should be raw text
				if got != tt.userdata {
					t.Errorf("AdaptUserdata() = %v, want %v", got, tt.userdata)
				}
			}
		})
	}
}

func TestAdaptUserdataWithSpecialCharacters(t *testing.T) {
	tests := []struct {
		name        string
		provider    string
		userdata    string
		wantEncoded bool
	}{
		{
			name:        "userdata with special characters - alicloud",
			provider:    "alicloud",
			userdata:    "#!/bin/bash\necho 'Hello 世界'\necho \"Test $VAR\"\n",
			wantEncoded: true,
		},
		{
			name:        "userdata with special characters - tencentcloud",
			provider:    "tencentcloud",
			userdata:    "#!/bin/bash\necho 'Hello 世界'\necho \"Test $VAR\"\n",
			wantEncoded: false,
		},
		{
			name:        "userdata with newlines and tabs",
			provider:    "aws",
			userdata:    "#!/bin/bash\n\techo 'test'\n\tcd /tmp\n",
			wantEncoded: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, err := AdaptUserdata(tt.provider, tt.userdata)
			if err != nil {
				t.Errorf("AdaptUserdata() error = %v", err)
				return
			}

			if tt.wantEncoded {
				// Verify it's base64 and can be decoded back to original
				decoded, err := base64.StdEncoding.DecodeString(got)
				if err != nil {
					t.Errorf("AdaptUserdata() result is not valid base64: %v", err)
				}
				if string(decoded) != tt.userdata {
					t.Errorf("AdaptUserdata() decoded = %v, want %v", string(decoded), tt.userdata)
				}
			} else {
				// Verify it's unchanged
				if got != tt.userdata {
					t.Errorf("AdaptUserdata() = %v, want %v", got, tt.userdata)
				}
			}
		})
	}
}

func TestAdaptUserdataConsistency(t *testing.T) {
	// Test that the same input always produces the same output
	userdata := "#!/bin/bash\necho 'test'"
	
	providers := []string{"alicloud", "tencentcloud", "aws", "volcengine", "huaweicloud"}
	
	for _, provider := range providers {
		t.Run(provider, func(t *testing.T) {
			result1, err1 := AdaptUserdata(provider, userdata)
			result2, err2 := AdaptUserdata(provider, userdata)
			
			if err1 != nil || err2 != nil {
				t.Errorf("AdaptUserdata() unexpected error: err1=%v, err2=%v", err1, err2)
				return
			}
			
			if result1 != result2 {
				t.Errorf("AdaptUserdata() inconsistent results: %v != %v", result1, result2)
			}
		})
	}
}
