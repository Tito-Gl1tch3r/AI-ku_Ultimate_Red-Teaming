package mod

import (
	"strings"
	"testing"
)

// TestErrorMessagesCompleteness 测试所有验证错误是否包含字段名、错误原因和修复建议
func TestErrorMessagesCompleteness(t *testing.T) {
	validator := NewConfigValidator()

	tests := []struct {
		name             string
		testFunc         func() error
		expectedField    string
		expectedCode     string
		shouldHaveSuggestion bool
	}{
		{
			name: "ValidateProvider - unsupported provider",
			testFunc: func() error {
				return validator.ValidateProvider("azure")
			},
			expectedField:    "provider",
			expectedCode:     ErrCodeNotSupported,
			shouldHaveSuggestion: true,
		},
		{
			name: "ValidateRegion - invalid region",
			testFunc: func() error {
				return validator.ValidateRegion("alicloud", "invalid-region")
			},
			expectedField:    "region",
			expectedCode:     ErrCodeNotAvailable,
			shouldHaveSuggestion: true,
		},
		{
			name: "ValidateInstanceType - invalid instance type",
			testFunc: func() error {
				return validator.ValidateInstanceType("alicloud", "cn-hangzhou", "invalid-type")
			},
			expectedField:    "instance_type",
			expectedCode:     ErrCodeNotAvailable,
			shouldHaveSuggestion: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := tt.testFunc()
			if err == nil {
				t.Fatal("expected error, but got nil")
			}

			validationErr, ok := err.(*ValidationError)
			if !ok {
				t.Fatalf("expected ValidationError, got %T", err)
			}

			// 验证字段名
			if validationErr.Field != tt.expectedField {
				t.Errorf("expected field '%s', got '%s'", tt.expectedField, validationErr.Field)
			}

			// 验证错误代码
			if validationErr.Code != tt.expectedCode {
				t.Errorf("expected code '%s', got '%s'", tt.expectedCode, validationErr.Code)
			}

			// 验证错误消息不为空
			if validationErr.Message == "" {
				t.Error("error message should not be empty")
			}

			// 验证错误消息包含修复建议
			if tt.shouldHaveSuggestion {
				if !strings.Contains(validationErr.Message, "修复建议") {
					t.Errorf("error message should contain fix suggestion (修复建议), but got: %s", validationErr.Message)
				}
			}
		})
	}
}

// TestValidationErrorFormat 测试验证错误的格式
func TestValidationErrorFormat(t *testing.T) {
	tests := []struct {
		name     string
		err      *ValidationError
		wantField string
		wantCode  string
		wantMessageContains []string
	}{
		{
			name: "REQUIRED error",
			err: &ValidationError{
				Field:   "name",
				Message: "部署名称是必填项。修复建议: 请提供一个有效的部署名称",
				Code:    ErrCodeRequired,
			},
			wantField: "name",
			wantCode:  ErrCodeRequired,
			wantMessageContains: []string{"部署名称", "必填项", "修复建议"},
		},
		{
			name: "NOT_SUPPORTED error",
			err: &ValidationError{
				Field:   "provider",
				Message: "云厂商 'azure' 不在支持列表中。支持的云厂商: alicloud, tencentcloud, aws, volcengine, huaweicloud。修复建议: 请从支持的云厂商列表中选择一个有效的云厂商",
				Code:    ErrCodeNotSupported,
			},
			wantField: "provider",
			wantCode:  ErrCodeNotSupported,
			wantMessageContains: []string{"azure", "不在支持列表中", "修复建议"},
		},
		{
			name: "NOT_AVAILABLE error",
			err: &ValidationError{
				Field:   "region",
				Message: "地域 'invalid-region' 在云厂商 'alicloud' 中不可用。可用地域: cn-hangzhou, cn-beijing。修复建议: 请从可用地域列表中选择一个有效的地域",
				Code:    ErrCodeNotAvailable,
			},
			wantField: "region",
			wantCode:  ErrCodeNotAvailable,
			wantMessageContains: []string{"invalid-region", "不可用", "修复建议"},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			// 验证字段名
			if tt.err.Field != tt.wantField {
				t.Errorf("expected field '%s', got '%s'", tt.wantField, tt.err.Field)
			}

			// 验证错误代码
			if tt.err.Code != tt.wantCode {
				t.Errorf("expected code '%s', got '%s'", tt.wantCode, tt.err.Code)
			}

			// 验证错误消息包含所有必需的部分
			for _, want := range tt.wantMessageContains {
				if !strings.Contains(tt.err.Message, want) {
					t.Errorf("error message should contain '%s', but got: %s", want, tt.err.Message)
				}
			}

			// 验证 Error() 方法返回格式化的错误消息
			errorStr := tt.err.Error()
			if !strings.Contains(errorStr, tt.err.Field) {
				t.Errorf("Error() should contain field name, got: %s", errorStr)
			}
			if !strings.Contains(errorStr, tt.err.Code) {
				t.Errorf("Error() should contain error code, got: %s", errorStr)
			}
		})
	}
}

// TestErrorCodeConstants 测试所有错误代码常量都已定义
func TestErrorCodeConstants(t *testing.T) {
	expectedCodes := []string{
		ErrCodeRequired,
		ErrCodeInvalidFormat,
		ErrCodeInvalidValue,
		ErrCodeNotSupported,
		ErrCodeNotAvailable,
	}

	expectedValues := []string{
		"REQUIRED",
		"INVALID_FORMAT",
		"INVALID_VALUE",
		"NOT_SUPPORTED",
		"NOT_AVAILABLE",
	}

	if len(expectedCodes) != len(expectedValues) {
		t.Fatal("expectedCodes and expectedValues should have the same length")
	}

	for i, code := range expectedCodes {
		if code != expectedValues[i] {
			t.Errorf("expected error code constant to be '%s', got '%s'", expectedValues[i], code)
		}
	}
}

// TestNewValidationError 测试 NewValidationError 辅助函数
func TestNewValidationError(t *testing.T) {
	tests := []struct {
		name       string
		field      string
		reason     string
		suggestion string
		code       string
		wantMessage string
	}{
		{
			name:       "with suggestion",
			field:      "provider",
			reason:     "云厂商不在支持列表中",
			suggestion: "请从支持的云厂商列表中选择",
			code:       ErrCodeNotSupported,
			wantMessage: "云厂商不在支持列表中。修复建议: 请从支持的云厂商列表中选择",
		},
		{
			name:       "without suggestion",
			field:      "name",
			reason:     "名称不能为空",
			suggestion: "",
			code:       ErrCodeRequired,
			wantMessage: "名称不能为空",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := NewValidationError(tt.field, tt.reason, tt.suggestion, tt.code)

			if err.Field != tt.field {
				t.Errorf("expected field '%s', got '%s'", tt.field, err.Field)
			}

			if err.Code != tt.code {
				t.Errorf("expected code '%s', got '%s'", tt.code, err.Code)
			}

			if err.Message != tt.wantMessage {
				t.Errorf("expected message '%s', got '%s'", tt.wantMessage, err.Message)
			}
		})
	}
}

// TestValidationResultStructure 测试 ValidationResult 结构
func TestValidationResultStructure(t *testing.T) {
	result := &ValidationResult{
		Valid: false,
		Errors: []ValidationError{
			{
				Field:   "provider",
				Message: "云厂商不在支持列表中。修复建议: 请选择有效的云厂商",
				Code:    ErrCodeNotSupported,
			},
			{
				Field:   "region",
				Message: "地域不可用。修复建议: 请选择有效的地域",
				Code:    ErrCodeNotAvailable,
			},
		},
		Warnings: []ValidationWarning{
			{
				Field:   "userdata",
				Message: "userdata 为空，实例将使用默认配置",
			},
		},
	}

	// 验证结构
	if result.Valid {
		t.Error("expected Valid to be false")
	}

	if len(result.Errors) != 2 {
		t.Errorf("expected 2 errors, got %d", len(result.Errors))
	}

	if len(result.Warnings) != 1 {
		t.Errorf("expected 1 warning, got %d", len(result.Warnings))
	}

	// 验证每个错误都有必需的字段
	for i, err := range result.Errors {
		if err.Field == "" {
			t.Errorf("error %d: field should not be empty", i)
		}
		if err.Message == "" {
			t.Errorf("error %d: message should not be empty", i)
		}
		if err.Code == "" {
			t.Errorf("error %d: code should not be empty", i)
		}
		if !strings.Contains(err.Message, "修复建议") {
			t.Errorf("error %d: message should contain fix suggestion", i)
		}
	}
}

// TestAllValidationErrorsHaveFixSuggestions 测试所有实际的验证错误都包含修复建议
func TestAllValidationErrorsHaveFixSuggestions(t *testing.T) {
	validator := NewConfigValidator()

	// 测试所有可能产生错误的验证方法
	errorProducingCalls := []struct {
		name string
		call func() error
	}{
		{
			name: "ValidateProvider with invalid provider",
			call: func() error {
				return validator.ValidateProvider("invalid-provider")
			},
		},
		{
			name: "ValidateRegion with invalid region",
			call: func() error {
				return validator.ValidateRegion("alicloud", "invalid-region")
			},
		},
		{
			name: "ValidateInstanceType with invalid type",
			call: func() error {
				return validator.ValidateInstanceType("alicloud", "cn-hangzhou", "invalid-type")
			},
		},
	}

	for _, tc := range errorProducingCalls {
		t.Run(tc.name, func(t *testing.T) {
			err := tc.call()
			if err == nil {
				t.Fatal("expected error, but got nil")
			}

			validationErr, ok := err.(*ValidationError)
			if !ok {
				t.Fatalf("expected ValidationError, got %T", err)
			}

			// 验证错误消息包含修复建议
			if !strings.Contains(validationErr.Message, "修复建议") {
				t.Errorf("error message should contain fix suggestion (修复建议), but got: %s", validationErr.Message)
			}

			// 验证错误消息不只是"修复建议"，还包含具体的建议内容
			parts := strings.Split(validationErr.Message, "修复建议:")
			if len(parts) != 2 {
				t.Errorf("error message should have exactly one '修复建议:' separator, but got: %s", validationErr.Message)
			} else {
				suggestion := strings.TrimSpace(parts[1])
				if suggestion == "" {
					t.Errorf("fix suggestion should not be empty, but got: %s", validationErr.Message)
				}
			}
		})
	}
}
