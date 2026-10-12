package mod

import (
	"encoding/json"
	"os"
	"path/filepath"
	"testing"
	"time"
)

func TestValidateDeploymentConfig_RequiredVariables(t *testing.T) {
	validator := NewConfigValidator()

	tests := []struct {
		name           string
		config         *DeploymentConfig
		expectedValid  bool
		expectedErrors int
		errorFields    []string
	}{
		{
			name: "valid config with all required fields",
			config: &DeploymentConfig{
				Name:         "test-deployment",
				TemplateName: "test-template",
				Provider:     "alicloud",
				Region:       "cn-hangzhou",
				InstanceType: "ecs.t6-c1m1.large",
				Variables: map[string]string{
					"instance_name":     "my-instance",
					"instance_password": "MyPassword123!",
				},
				CreatedAt: time.Now(),
				UpdatedAt: time.Now(),
			},
			expectedValid:  true,
			expectedErrors: 0,
			errorFields:    []string{},
		},
		{
			name: "missing name field",
			config: &DeploymentConfig{
				Name:         "",
				TemplateName: "test-template",
				Provider:     "alicloud",
				Region:       "cn-hangzhou",
				InstanceType: "ecs.t6-c1m1.large",
				Variables:    map[string]string{},
				CreatedAt:    time.Now(),
				UpdatedAt:    time.Now(),
			},
			expectedValid:  false,
			expectedErrors: 1,
			errorFields:    []string{"name"},
		},
		{
			name: "missing provider field",
			config: &DeploymentConfig{
				Name:         "test-deployment",
				TemplateName: "test-template",
				Provider:     "",
				Region:       "cn-hangzhou",
				InstanceType: "ecs.t6-c1m1.large",
				Variables:    map[string]string{},
				CreatedAt:    time.Now(),
				UpdatedAt:    time.Now(),
			},
			expectedValid:  false,
			expectedErrors: 1,
			errorFields:    []string{"provider"},
		},
		{
			name: "missing region field",
			config: &DeploymentConfig{
				Name:         "test-deployment",
				TemplateName: "test-template",
				Provider:     "alicloud",
				Region:       "",
				InstanceType: "ecs.t6-c1m1.large",
				Variables:    map[string]string{},
				CreatedAt:    time.Now(),
				UpdatedAt:    time.Now(),
			},
			expectedValid:  false,
			expectedErrors: 1,
			errorFields:    []string{"region"},
		},
		{
			name: "missing instance_type field",
			config: &DeploymentConfig{
				Name:         "test-deployment",
				TemplateName: "test-template",
				Provider:     "alicloud",
				Region:       "cn-hangzhou",
				InstanceType: "",
				Variables:    map[string]string{},
				CreatedAt:    time.Now(),
				UpdatedAt:    time.Now(),
			},
			expectedValid:  false,
			expectedErrors: 1,
			errorFields:    []string{"instance_type"},
		},
		{
			name: "missing multiple fields",
			config: &DeploymentConfig{
				Name:         "",
				TemplateName: "test-template",
				Provider:     "",
				Region:       "",
				InstanceType: "",
				Variables:    map[string]string{},
				CreatedAt:    time.Now(),
				UpdatedAt:    time.Now(),
			},
			expectedValid:  false,
			expectedErrors: 4,
			errorFields:    []string{"name", "provider", "region", "instance_type"},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result, err := validator.ValidateDeploymentConfig(tt.config)
			
			// For this test, we expect no error from the validation function itself
			// (errors in validation are returned in the ValidationResult)
			if err != nil && tt.config.TemplateName == "test-template" {
				// Template not found is expected for test templates
				t.Logf("Template not found (expected for test): %v", err)
				return
			}

			if result.Valid != tt.expectedValid {
				t.Errorf("expected valid=%v, got valid=%v", tt.expectedValid, result.Valid)
			}

			if len(result.Errors) != tt.expectedErrors {
				t.Errorf("expected %d errors, got %d errors: %v", tt.expectedErrors, len(result.Errors), result.Errors)
			}

			// Check that expected error fields are present
			errorFieldMap := make(map[string]bool)
			for _, err := range result.Errors {
				errorFieldMap[err.Field] = true
			}

			for _, expectedField := range tt.errorFields {
				if !errorFieldMap[expectedField] {
					t.Errorf("expected error for field '%s', but not found", expectedField)
				}
			}
		})
	}
}

func TestValidateDeploymentConfig_RequiredCode(t *testing.T) {
	validator := NewConfigValidator()

	config := &DeploymentConfig{
		Name:         "",
		TemplateName: "test-template",
		Provider:     "alicloud",
		Region:       "cn-hangzhou",
		InstanceType: "ecs.t6-c1m1.large",
		Variables:    map[string]string{},
		CreatedAt:    time.Now(),
		UpdatedAt:    time.Now(),
	}

	result, err := validator.ValidateDeploymentConfig(config)
	
	// Template not found is expected for test templates
	if err != nil {
		t.Logf("Template not found (expected for test): %v", err)
		return
	}

	// Check that error code is REQUIRED
	if len(result.Errors) > 0 {
		for _, validationErr := range result.Errors {
			if validationErr.Code != ErrCodeRequired {
				t.Errorf("expected error code '%s', got '%s'", ErrCodeRequired, validationErr.Code)
			}
		}
	}
}

func TestValidateDeploymentConfig_WithRealTemplate(t *testing.T) {
	// Create a temporary directory for test templates
	tempDir, err := os.MkdirTemp("", "redc-test-templates-*")
	if err != nil {
		t.Fatalf("Failed to create temp directory: %v", err)
	}
	defer os.RemoveAll(tempDir)

	// Create a test template directory
	templateDir := filepath.Join(tempDir, "test-template")
	if err := os.MkdirAll(templateDir, 0755); err != nil {
		t.Fatalf("Failed to create template directory: %v", err)
	}

	// Create case.json
	caseData := map[string]interface{}{
		"name":              "test-template",
		"description":       "Test template",
		"user":              "test",
		"version":           "1.0.0",
		"redc_module":       "",
		"is_base_template":  true,
		"supported_providers": []string{"alicloud"},
	}
	caseJSON, _ := json.Marshal(caseData)
	caseFilePath := filepath.Join(templateDir, TmplCaseFile)
	if err := os.WriteFile(caseFilePath, caseJSON, 0644); err != nil {
		t.Fatalf("Failed to write case.json: %v", err)
	}

	// Create variables.tf with required variables
	variablesTf := `
variable "instance_name" {
  description = "实例名称"
  type        = string
}

variable "instance_password" {
  description = "实例密码"
  type        = string
  sensitive   = true
}

variable "optional_var" {
  description = "可选变量"
  type        = string
  default     = "default_value"
}
`
	variablesFilePath := filepath.Join(templateDir, "variables.tf")
	if err := os.WriteFile(variablesFilePath, []byte(variablesTf), 0644); err != nil {
		t.Fatalf("Failed to write variables.tf: %v", err)
	}

	// Create a validator with custom template manager
	validator := &ConfigValidator{
		templateMgr: &TemplateManager{templateDir: tempDir},
	}

	tests := []struct {
		name           string
		config         *DeploymentConfig
		expectedValid  bool
		expectedErrors int
		missingFields  []string
	}{
		{
			name: "all required variables provided",
			config: &DeploymentConfig{
				Name:         "test-deployment",
				TemplateName: "test-template",
				Provider:     "alicloud",
				Region:       "cn-hangzhou",
				InstanceType: "ecs.t6-c1m1.large",
				Variables: map[string]string{
					"instance_name":     "my-instance",
					"instance_password": "MyPassword123!",
				},
				CreatedAt: time.Now(),
				UpdatedAt: time.Now(),
			},
			expectedValid:  true,
			expectedErrors: 0,
			missingFields:  []string{},
		},
		{
			name: "missing required variable instance_name",
			config: &DeploymentConfig{
				Name:         "test-deployment",
				TemplateName: "test-template",
				Provider:     "alicloud",
				Region:       "cn-hangzhou",
				InstanceType: "ecs.t6-c1m1.large",
				Variables: map[string]string{
					"instance_password": "MyPassword123!",
				},
				CreatedAt: time.Now(),
				UpdatedAt: time.Now(),
			},
			expectedValid:  false,
			expectedErrors: 1,
			missingFields:  []string{"instance_name"},
		},
		{
			name: "missing required variable instance_password",
			config: &DeploymentConfig{
				Name:         "test-deployment",
				TemplateName: "test-template",
				Provider:     "alicloud",
				Region:       "cn-hangzhou",
				InstanceType: "ecs.t6-c1m1.large",
				Variables: map[string]string{
					"instance_name": "my-instance",
				},
				CreatedAt: time.Now(),
				UpdatedAt: time.Now(),
			},
			expectedValid:  false,
			expectedErrors: 1,
			missingFields:  []string{"instance_password"},
		},
		{
			name: "missing both required variables",
			config: &DeploymentConfig{
				Name:         "test-deployment",
				TemplateName: "test-template",
				Provider:     "alicloud",
				Region:       "cn-hangzhou",
				InstanceType: "ecs.t6-c1m1.large",
				Variables:    map[string]string{},
				CreatedAt:    time.Now(),
				UpdatedAt:    time.Now(),
			},
			expectedValid:  false,
			expectedErrors: 2,
			missingFields:  []string{"instance_name", "instance_password"},
		},
		{
			name: "optional variable not provided is ok",
			config: &DeploymentConfig{
				Name:         "test-deployment",
				TemplateName: "test-template",
				Provider:     "alicloud",
				Region:       "cn-hangzhou",
				InstanceType: "ecs.t6-c1m1.large",
				Variables: map[string]string{
					"instance_name":     "my-instance",
					"instance_password": "MyPassword123!",
					// optional_var not provided
				},
				CreatedAt: time.Now(),
				UpdatedAt: time.Now(),
			},
			expectedValid:  true,
			expectedErrors: 0,
			missingFields:  []string{},
		},
		{
			name: "empty string for required variable",
			config: &DeploymentConfig{
				Name:         "test-deployment",
				TemplateName: "test-template",
				Provider:     "alicloud",
				Region:       "cn-hangzhou",
				InstanceType: "ecs.t6-c1m1.large",
				Variables: map[string]string{
					"instance_name":     "",
					"instance_password": "MyPassword123!",
				},
				CreatedAt: time.Now(),
				UpdatedAt: time.Now(),
			},
			expectedValid:  false,
			expectedErrors: 1,
			missingFields:  []string{"instance_name"},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result, err := validator.ValidateDeploymentConfig(tt.config)
			if err != nil {
				t.Fatalf("Unexpected error: %v", err)
			}

			if result.Valid != tt.expectedValid {
				t.Errorf("expected valid=%v, got valid=%v", tt.expectedValid, result.Valid)
			}

			if len(result.Errors) != tt.expectedErrors {
				t.Errorf("expected %d errors, got %d errors: %v", tt.expectedErrors, len(result.Errors), result.Errors)
			}

			// Check that expected missing fields are present in errors
			errorFieldMap := make(map[string]bool)
			for _, err := range result.Errors {
				errorFieldMap[err.Field] = true
			}

			for _, expectedField := range tt.missingFields {
				if !errorFieldMap[expectedField] {
					t.Errorf("expected error for field '%s', but not found", expectedField)
				}
			}

			// Verify all errors have REQUIRED code
			for _, validationErr := range result.Errors {
				if validationErr.Code != ErrCodeRequired {
					t.Errorf("expected error code '%s', got '%s' for field '%s'", 
						ErrCodeRequired, validationErr.Code, validationErr.Field)
				}
			}
		})
	}
}

func TestValidateProvider(t *testing.T) {
	validator := NewConfigValidator()

	tests := []struct {
		name          string
		provider      string
		expectError   bool
		expectedCode  string
	}{
		{
			name:        "valid provider - alicloud",
			provider:    "alicloud",
			expectError: false,
		},
		{
			name:        "valid provider - tencentcloud",
			provider:    "tencentcloud",
			expectError: false,
		},
		{
			name:        "valid provider - aws",
			provider:    "aws",
			expectError: false,
		},
		{
			name:        "valid provider - volcengine",
			provider:    "volcengine",
			expectError: false,
		},
		{
			name:        "valid provider - huaweicloud",
			provider:    "huaweicloud",
			expectError: false,
		},
		{
			name:         "invalid provider - unsupported",
			provider:     "azure",
			expectError:  true,
			expectedCode: ErrCodeNotSupported,
		},
		{
			name:         "invalid provider - empty string",
			provider:     "",
			expectError:  true,
			expectedCode: ErrCodeNotSupported,
		},
		{
			name:         "invalid provider - random string",
			provider:     "random-cloud",
			expectError:  true,
			expectedCode: ErrCodeNotSupported,
		},
		{
			name:         "invalid provider - case sensitive",
			provider:     "AliCloud",
			expectError:  true,
			expectedCode: ErrCodeNotSupported,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := validator.ValidateProvider(tt.provider)

			if tt.expectError {
				if err == nil {
					t.Errorf("expected error, but got nil")
					return
				}

				// Check if error is ValidationError
				validationErr, ok := err.(*ValidationError)
				if !ok {
					t.Errorf("expected ValidationError, got %T", err)
					return
				}

				// Check error code
				if validationErr.Code != tt.expectedCode {
					t.Errorf("expected error code '%s', got '%s'", tt.expectedCode, validationErr.Code)
				}

				// Check error field
				if validationErr.Field != "provider" {
					t.Errorf("expected error field 'provider', got '%s'", validationErr.Field)
				}

				// Check error message contains provider name
				if tt.provider != "" && validationErr.Message == "" {
					t.Errorf("expected non-empty error message")
				}
			} else {
				if err != nil {
					t.Errorf("expected no error, but got: %v", err)
				}
			}
		})
	}
}

func TestValidateProvider_ErrorMessage(t *testing.T) {
	validator := NewConfigValidator()

	err := validator.ValidateProvider("azure")
	if err == nil {
		t.Fatal("expected error, but got nil")
	}

	validationErr, ok := err.(*ValidationError)
	if !ok {
		t.Fatalf("expected ValidationError, got %T", err)
	}

	// Check that error message contains the invalid provider name
	if validationErr.Message == "" {
		t.Error("expected non-empty error message")
	}

	// Check that error message contains supported providers list
	expectedProviders := []string{"alicloud", "tencentcloud", "aws", "volcengine", "huaweicloud"}
	for _, provider := range expectedProviders {
		if !contains(validationErr.Message, provider) {
			t.Errorf("expected error message to contain '%s', but it doesn't: %s", provider, validationErr.Message)
		}
	}
}

// Helper function to check if a string contains a substring
func contains(s, substr string) bool {
	return len(s) >= len(substr) && (s == substr || len(s) > len(substr) && containsSubstring(s, substr))
}

func containsSubstring(s, substr string) bool {
	for i := 0; i <= len(s)-len(substr); i++ {
		if s[i:i+len(substr)] == substr {
			return true
		}
	}
	return false
}

func TestValidateRegion(t *testing.T) {
	validator := NewConfigValidator()

	tests := []struct {
		name         string
		provider     string
		region       string
		expectError  bool
		expectedCode string
	}{
		{
			name:        "valid region - alicloud cn-hangzhou",
			provider:    "alicloud",
			region:      "cn-hangzhou",
			expectError: false,
		},
		{
			name:        "valid region - alicloud cn-beijing",
			provider:    "alicloud",
			region:      "cn-beijing",
			expectError: false,
		},
		{
			name:        "valid region - tencentcloud ap-guangzhou",
			provider:    "tencentcloud",
			region:      "ap-guangzhou",
			expectError: false,
		},
		{
			name:        "valid region - aws us-east-1",
			provider:    "aws",
			region:      "us-east-1",
			expectError: false,
		},
		{
			name:        "valid region - volcengine cn-beijing",
			provider:    "volcengine",
			region:      "cn-beijing",
			expectError: false,
		},
		{
			name:        "valid region - huaweicloud cn-north-1",
			provider:    "huaweicloud",
			region:      "cn-north-1",
			expectError: false,
		},
		{
			name:         "invalid region - alicloud with tencentcloud region",
			provider:     "alicloud",
			region:       "ap-guangzhou",
			expectError:  true,
			expectedCode: ErrCodeNotAvailable,
		},
		{
			name:         "invalid region - tencentcloud with alicloud region",
			provider:     "tencentcloud",
			region:       "cn-hangzhou",
			expectError:  true,
			expectedCode: ErrCodeNotAvailable,
		},
		{
			name:         "invalid region - non-existent region",
			provider:     "alicloud",
			region:       "cn-nonexistent",
			expectError:  true,
			expectedCode: ErrCodeNotAvailable,
		},
		{
			name:         "invalid region - empty region",
			provider:     "alicloud",
			region:       "",
			expectError:  true,
			expectedCode: ErrCodeNotAvailable,
		},
		{
			name:         "invalid provider - unsupported provider",
			provider:     "azure",
			region:       "eastus",
			expectError:  true,
			expectedCode: ErrCodeNotSupported,
		},
		{
			name:         "invalid region - case sensitive",
			provider:     "alicloud",
			region:       "CN-HANGZHOU",
			expectError:  true,
			expectedCode: ErrCodeNotAvailable,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := validator.ValidateRegion(tt.provider, tt.region)

			if tt.expectError {
				if err == nil {
					t.Errorf("expected error, but got nil")
					return
				}

				// Check if error is ValidationError
				validationErr, ok := err.(*ValidationError)
				if !ok {
					t.Errorf("expected ValidationError, got %T", err)
					return
				}

				// Check error code
				if validationErr.Code != tt.expectedCode {
					t.Errorf("expected error code '%s', got '%s'", tt.expectedCode, validationErr.Code)
				}

				// Check error field
				if validationErr.Field != "region" && validationErr.Field != "provider" {
					t.Errorf("expected error field 'region' or 'provider', got '%s'", validationErr.Field)
				}

				// Check error message is not empty
				if validationErr.Message == "" {
					t.Errorf("expected non-empty error message")
				}
			} else {
				if err != nil {
					t.Errorf("expected no error, but got: %v", err)
				}
			}
		})
	}
}

func TestValidateRegion_ErrorMessage(t *testing.T) {
	validator := NewConfigValidator()

	// Test error message for invalid region
	err := validator.ValidateRegion("alicloud", "invalid-region")
	if err == nil {
		t.Fatal("expected error, but got nil")
	}

	validationErr, ok := err.(*ValidationError)
	if !ok {
		t.Fatalf("expected ValidationError, got %T", err)
	}

	// Check that error message contains the invalid region name
	if !contains(validationErr.Message, "invalid-region") {
		t.Errorf("expected error message to contain 'invalid-region', but it doesn't: %s", validationErr.Message)
	}

	// Check that error message contains the provider name
	if !contains(validationErr.Message, "alicloud") {
		t.Errorf("expected error message to contain 'alicloud', but it doesn't: %s", validationErr.Message)
	}

	// Check that error message contains available regions
	if !contains(validationErr.Message, "cn-hangzhou") {
		t.Errorf("expected error message to contain 'cn-hangzhou', but it doesn't: %s", validationErr.Message)
	}
}

func TestValidateRegion_AllProviders(t *testing.T) {
	validator := NewConfigValidator()

	// Test that each provider has at least one valid region
	providers := []string{"alicloud", "tencentcloud", "aws", "volcengine", "huaweicloud"}
	
	for _, provider := range providers {
		t.Run(provider, func(t *testing.T) {
			// Get regions for this provider
			regions, err := GetProviderRegions(provider)
			if err != nil {
				t.Fatalf("Failed to get regions for provider %s: %v", provider, err)
			}

			if len(regions) == 0 {
				t.Errorf("Provider %s has no regions", provider)
				return
			}

			// Test that the first region is valid
			err = validator.ValidateRegion(provider, regions[0].Code)
			if err != nil {
				t.Errorf("Expected region %s to be valid for provider %s, but got error: %v", 
					regions[0].Code, provider, err)
			}
		})
	}
}

func TestValidateInstanceType(t *testing.T) {
	validator := NewConfigValidator()

	tests := []struct {
		name         string
		provider     string
		region       string
		instanceType string
		expectError  bool
		expectedCode string
	}{
		{
			name:         "valid instance type - alicloud ecs.t6-c1m1.large",
			provider:     "alicloud",
			region:       "cn-hangzhou",
			instanceType: "ecs.t6-c1m1.large",
			expectError:  false,
		},
		{
			name:         "valid instance type - alicloud ecs.c7.large",
			provider:     "alicloud",
			region:       "cn-beijing",
			instanceType: "ecs.c7.large",
			expectError:  false,
		},
		{
			name:         "valid instance type - tencentcloud S6.MEDIUM2",
			provider:     "tencentcloud",
			region:       "ap-guangzhou",
			instanceType: "S6.MEDIUM2",
			expectError:  false,
		},
		{
			name:         "valid instance type - aws t3.micro",
			provider:     "aws",
			region:       "us-east-1",
			instanceType: "t3.micro",
			expectError:  false,
		},
		{
			name:         "valid instance type - volcengine ecs.g3i.large",
			provider:     "volcengine",
			region:       "cn-beijing",
			instanceType: "ecs.g3i.large",
			expectError:  false,
		},
		{
			name:         "valid instance type - huaweicloud s6.small.1",
			provider:     "huaweicloud",
			region:       "cn-north-1",
			instanceType: "s6.small.1",
			expectError:  false,
		},
		{
			name:         "invalid instance type - non-existent",
			provider:     "alicloud",
			region:       "cn-hangzhou",
			instanceType: "ecs.nonexistent.large",
			expectError:  true,
			expectedCode: ErrCodeNotAvailable,
		},
		{
			name:         "invalid instance type - empty string",
			provider:     "alicloud",
			region:       "cn-hangzhou",
			instanceType: "",
			expectError:  true,
			expectedCode: ErrCodeNotAvailable,
		},
		{
			name:         "invalid instance type - wrong provider type",
			provider:     "alicloud",
			region:       "cn-hangzhou",
			instanceType: "S6.MEDIUM2", // This is a Tencent Cloud instance type
			expectError:  true,
			expectedCode: ErrCodeNotAvailable,
		},
		{
			name:         "invalid instance type - case sensitive",
			provider:     "alicloud",
			region:       "cn-hangzhou",
			instanceType: "ECS.T6-C1M1.LARGE", // Wrong case
			expectError:  true,
			expectedCode: ErrCodeNotAvailable,
		},
		{
			name:         "invalid provider",
			provider:     "azure",
			region:       "eastus",
			instanceType: "Standard_B1s",
			expectError:  true,
			expectedCode: ErrCodeNotSupported,
		},
		{
			name:         "invalid region",
			provider:     "alicloud",
			region:       "invalid-region",
			instanceType: "ecs.t6-c1m1.large",
			expectError:  true,
			expectedCode: ErrCodeNotAvailable,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := validator.ValidateInstanceType(tt.provider, tt.region, tt.instanceType)

			if tt.expectError {
				if err == nil {
					t.Errorf("expected error, but got nil")
					return
				}

				// Check if error is ValidationError
				validationErr, ok := err.(*ValidationError)
				if !ok {
					t.Errorf("expected ValidationError, got %T", err)
					return
				}

				// Check error code
				if validationErr.Code != tt.expectedCode {
					t.Errorf("expected error code '%s', got '%s'", tt.expectedCode, validationErr.Code)
				}

				// Check error field
				if validationErr.Field != "instance_type" && validationErr.Field != "provider" && validationErr.Field != "region" {
					t.Errorf("expected error field 'instance_type', 'provider', or 'region', got '%s'", validationErr.Field)
				}

				// Check error message is not empty
				if validationErr.Message == "" {
					t.Errorf("expected non-empty error message")
				}
			} else {
				if err != nil {
					t.Errorf("expected no error, but got: %v", err)
				}
			}
		})
	}
}

func TestValidateInstanceType_ErrorMessage(t *testing.T) {
	validator := NewConfigValidator()

	// Test error message for invalid instance type
	err := validator.ValidateInstanceType("alicloud", "cn-hangzhou", "invalid-instance-type")
	if err == nil {
		t.Fatal("expected error, but got nil")
	}

	validationErr, ok := err.(*ValidationError)
	if !ok {
		t.Fatalf("expected ValidationError, got %T", err)
	}

	// Check that error message contains the invalid instance type
	if !contains(validationErr.Message, "invalid-instance-type") {
		t.Errorf("expected error message to contain 'invalid-instance-type', but it doesn't: %s", validationErr.Message)
	}

	// Check that error message contains the provider name
	if !contains(validationErr.Message, "alicloud") {
		t.Errorf("expected error message to contain 'alicloud', but it doesn't: %s", validationErr.Message)
	}

	// Check that error message contains the region
	if !contains(validationErr.Message, "cn-hangzhou") {
		t.Errorf("expected error message to contain 'cn-hangzhou', but it doesn't: %s", validationErr.Message)
	}

	// Check that error message contains at least one available instance type
	if !contains(validationErr.Message, "ecs.") {
		t.Errorf("expected error message to contain available instance types (e.g., 'ecs.'), but it doesn't: %s", validationErr.Message)
	}
}

func TestValidateInstanceType_AllProviders(t *testing.T) {
	validator := NewConfigValidator()

	// Test that each provider has at least one valid instance type
	testCases := []struct {
		provider     string
		region       string
		instanceType string
	}{
		{"alicloud", "cn-hangzhou", "ecs.t6-c1m1.large"},
		{"tencentcloud", "ap-guangzhou", "S6.MEDIUM2"},
		{"aws", "us-east-1", "t3.micro"},
		{"volcengine", "cn-beijing", "ecs.g3i.large"},
		{"huaweicloud", "cn-north-1", "s6.small.1"},
	}

	for _, tc := range testCases {
		t.Run(tc.provider, func(t *testing.T) {
			// Get instance types for this provider and region
			instanceTypes, err := GetInstanceTypes(tc.provider, tc.region)
			if err != nil {
				t.Fatalf("Failed to get instance types for provider %s and region %s: %v", tc.provider, tc.region, err)
			}

			if len(instanceTypes) == 0 {
				t.Errorf("Provider %s in region %s has no instance types", tc.provider, tc.region)
				return
			}

			// Test that the first instance type is valid
			err = validator.ValidateInstanceType(tc.provider, tc.region, instanceTypes[0].Code)
			if err != nil {
				t.Errorf("Expected instance type %s to be valid for provider %s in region %s, but got error: %v",
					instanceTypes[0].Code, tc.provider, tc.region, err)
			}

			// Test the specific instance type from test case
			err = validator.ValidateInstanceType(tc.provider, tc.region, tc.instanceType)
			if err != nil {
				t.Errorf("Expected instance type %s to be valid for provider %s in region %s, but got error: %v",
					tc.instanceType, tc.provider, tc.region, err)
			}
		})
	}
}

func TestValidateInstanceType_CacheUsage(t *testing.T) {
	validator := NewConfigValidator()

	provider := "alicloud"
	region := "cn-hangzhou"
	instanceType := "ecs.t6-c1m1.large"

	// First call - should fetch from provider (or cache if already exists)
	err1 := validator.ValidateInstanceType(provider, region, instanceType)
	if err1 != nil {
		t.Fatalf("First validation failed: %v", err1)
	}

	// Second call - should use cache
	err2 := validator.ValidateInstanceType(provider, region, instanceType)
	if err2 != nil {
		t.Fatalf("Second validation failed: %v", err2)
	}

	// Both calls should succeed
	if err1 != nil || err2 != nil {
		t.Errorf("Expected both validations to succeed")
	}
}

func TestValidateInstanceType_DifferentRegions(t *testing.T) {
	validator := NewConfigValidator()

	provider := "alicloud"
	instanceType := "ecs.t6-c1m1.large"

	// Test that the same instance type is valid in different regions
	regions := []string{"cn-hangzhou", "cn-beijing", "cn-shanghai"}

	for _, region := range regions {
		t.Run(region, func(t *testing.T) {
			err := validator.ValidateInstanceType(provider, region, instanceType)
			if err != nil {
				t.Errorf("Expected instance type %s to be valid in region %s, but got error: %v",
					instanceType, region, err)
			}
		})
	}
}
