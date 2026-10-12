package mod

import (
	"fmt"
	"strings"
	"testing"
)

func TestGenerateProviderConfig(t *testing.T) {
	executor := NewDeploymentExecutor()

	tests := []struct {
		name           string
		provider       string
		region         string
		expectedName   string
		expectedSource string
		expectError    bool
	}{
		{
			name:           "alicloud provider",
			provider:       "alicloud",
			region:         "cn-hangzhou",
			expectedName:   "alicloud",
			expectedSource: "aliyun/alicloud",
			expectError:    false,
		},
		{
			name:           "tencentcloud provider",
			provider:       "tencentcloud",
			region:         "ap-guangzhou",
			expectedName:   "tencentcloud",
			expectedSource: "tencentcloudstack/tencentcloud",
			expectError:    false,
		},
		{
			name:           "aws provider",
			provider:       "aws",
			region:         "us-east-1",
			expectedName:   "aws",
			expectedSource: "hashicorp/aws",
			expectError:    false,
		},
		{
			name:           "volcengine provider",
			provider:       "volcengine",
			region:         "cn-beijing",
			expectedName:   "volcengine",
			expectedSource: "volcengine/volcengine",
			expectError:    false,
		},
		{
			name:           "huaweicloud provider",
			provider:       "huaweicloud",
			region:         "cn-north-1",
			expectedName:   "huaweicloud",
			expectedSource: "huaweicloud/huaweicloud",
			expectError:    false,
		},
		{
			name:        "unsupported provider",
			provider:    "unsupported",
			region:      "some-region",
			expectError: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			config, err := executor.GenerateProviderConfig(tt.provider, tt.region)

			if tt.expectError {
				if err == nil {
					t.Errorf("expected error for provider %s, but got none", tt.provider)
				}
				return
			}

			if err != nil {
				t.Errorf("unexpected error: %v", err)
				return
			}

			if config.Name != tt.expectedName {
				t.Errorf("expected provider name %s, got %s", tt.expectedName, config.Name)
			}

			if config.Source != tt.expectedSource {
				t.Errorf("expected provider source %s, got %s", tt.expectedSource, config.Source)
			}

			if config.Config["region"] != tt.region {
				t.Errorf("expected region %s, got %s", tt.region, config.Config["region"])
			}

			if config.Version == "" {
				t.Errorf("expected non-empty version for provider %s", tt.provider)
			}
		})
	}
}

func TestGenerateProviderBlock(t *testing.T) {
	executor := NewDeploymentExecutor()

	tests := []struct {
		name        string
		provider    string
		region      string
		expectError bool
	}{
		{
			name:        "alicloud provider block",
			provider:    "alicloud",
			region:      "cn-hangzhou",
			expectError: false,
		},
		{
			name:        "tencentcloud provider block",
			provider:    "tencentcloud",
			region:      "ap-guangzhou",
			expectError: false,
		},
		{
			name:        "aws provider block",
			provider:    "aws",
			region:      "us-east-1",
			expectError: false,
		},
		{
			name:        "volcengine provider block",
			provider:    "volcengine",
			region:      "cn-beijing",
			expectError: false,
		},
		{
			name:        "huaweicloud provider block",
			provider:    "huaweicloud",
			region:      "cn-north-1",
			expectError: false,
		},
		{
			name:        "unsupported provider block",
			provider:    "unsupported",
			region:      "some-region",
			expectError: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			hcl, err := executor.GenerateProviderBlock(tt.provider, tt.region)

			if tt.expectError {
				if err == nil {
					t.Errorf("expected error for provider %s, but got none", tt.provider)
				}
				return
			}

			if err != nil {
				t.Errorf("unexpected error: %v", err)
				return
			}

			// Verify the HCL contains required elements
			if !strings.Contains(hcl, fmt.Sprintf("provider \"%s\"", tt.provider)) {
				t.Errorf("expected HCL to contain provider block for %s", tt.provider)
			}

			if !strings.Contains(hcl, fmt.Sprintf("region = \"%s\"", tt.region)) {
				t.Errorf("expected HCL to contain region %s", tt.region)
			}
		})
	}
}

func TestProviderConfigMapping(t *testing.T) {
	executor := NewDeploymentExecutor()

	// Test that each supported provider maps to the correct Terraform provider
	providerMappings := map[string]string{
		"alicloud":     "aliyun/alicloud",
		"tencentcloud": "tencentcloudstack/tencentcloud",
		"aws":          "hashicorp/aws",
		"volcengine":   "volcengine/volcengine",
		"huaweicloud":  "huaweicloud/huaweicloud",
	}

	for provider, expectedSource := range providerMappings {
		t.Run(provider, func(t *testing.T) {
			config, err := executor.GenerateProviderConfig(provider, "test-region")
			if err != nil {
				t.Errorf("unexpected error for provider %s: %v", provider, err)
				return
			}

			if config.Source != expectedSource {
				t.Errorf("provider %s: expected source %s, got %s", provider, expectedSource, config.Source)
			}

			if config.Name != provider {
				t.Errorf("provider %s: expected name %s, got %s", provider, provider, config.Name)
			}
		})
	}
}

func TestProviderConfigRegionPropagation(t *testing.T) {
	executor := NewDeploymentExecutor()

	testRegions := []string{
		"cn-hangzhou",
		"ap-guangzhou",
		"us-east-1",
		"eu-west-1",
		"cn-north-1",
	}

	for _, region := range testRegions {
		t.Run(region, func(t *testing.T) {
			config, err := executor.GenerateProviderConfig("alicloud", region)
			if err != nil {
				t.Errorf("unexpected error: %v", err)
				return
			}

			if config.Config["region"] != region {
				t.Errorf("expected region %s in config, got %s", region, config.Config["region"])
			}
		})
	}
}

func TestGenerateVariablesFile(t *testing.T) {
	executor := NewDeploymentExecutor()

	tests := []struct {
		name        string
		config      *DeploymentConfig
		expectError bool
		checkFunc   func(t *testing.T, tfvars string)
	}{
		{
			name: "basic configuration",
			config: &DeploymentConfig{
				Provider:     "alicloud",
				Region:       "cn-hangzhou",
				InstanceType: "ecs.t6-c1m1.large",
			},
			expectError: false,
			checkFunc: func(t *testing.T, tfvars string) {
				if !strings.Contains(tfvars, `provider = "alicloud"`) {
					t.Errorf("expected tfvars to contain provider")
				}
				if !strings.Contains(tfvars, `region = "cn-hangzhou"`) {
					t.Errorf("expected tfvars to contain region")
				}
				if !strings.Contains(tfvars, `instance_type = "ecs.t6-c1m1.large"`) {
					t.Errorf("expected tfvars to contain instance_type")
				}
			},
		},
		{
			name: "configuration with userdata",
			config: &DeploymentConfig{
				Provider:     "aws",
				Region:       "us-east-1",
				InstanceType: "t3.medium",
				Userdata:     "#!/bin/bash\necho 'Hello World'",
			},
			expectError: false,
			checkFunc: func(t *testing.T, tfvars string) {
				if !strings.Contains(tfvars, "userdata = <<-EOT") {
					t.Errorf("expected tfvars to use heredoc for multiline userdata")
				}
				if !strings.Contains(tfvars, "#!/bin/bash") {
					t.Errorf("expected tfvars to contain userdata content")
				}
				if !strings.Contains(tfvars, "echo 'Hello World'") {
					t.Errorf("expected tfvars to contain userdata content")
				}
				if !strings.Contains(tfvars, "EOT") {
					t.Errorf("expected tfvars to close heredoc")
				}
			},
		},
		{
			name: "configuration with single line userdata",
			config: &DeploymentConfig{
				Provider:     "tencentcloud",
				Region:       "ap-guangzhou",
				InstanceType: "S6.MEDIUM4",
				Userdata:     "echo 'Hello'",
			},
			expectError: false,
			checkFunc: func(t *testing.T, tfvars string) {
				if !strings.Contains(tfvars, `userdata = "echo 'Hello'"`) {
					t.Errorf("expected tfvars to use quoted string for single line userdata")
				}
			},
		},
		{
			name: "configuration with custom variables",
			config: &DeploymentConfig{
				Name:         "my-instance",
				Provider:     "alicloud",
				Region:       "cn-shanghai",
				InstanceType: "ecs.g7.large",
				Variables: map[string]string{
					"instance_password": "MyPassword123!",
					"disk_size":         "100",
				},
			},
			expectError: false,
			checkFunc: func(t *testing.T, tfvars string) {
				if !strings.Contains(tfvars, `instance_name = "my-instance"`) {
					t.Errorf("expected tfvars to contain instance_name variable")
				}
				if !strings.Contains(tfvars, `instance_password = "MyPassword123!"`) {
					t.Errorf("expected tfvars to contain instance_password variable")
				}
				if !strings.Contains(tfvars, `disk_size = "100"`) {
					t.Errorf("expected tfvars to contain disk_size variable")
				}
			},
		},
		{
			name: "configuration with special characters in variables",
			config: &DeploymentConfig{
				Provider:     "aws",
				Region:       "us-west-2",
				InstanceType: "t3.small",
				Variables: map[string]string{
					"description": `This is a "test" with special chars: \n\t`,
				},
			},
			expectError: false,
			checkFunc: func(t *testing.T, tfvars string) {
				// Special characters should be escaped
				if !strings.Contains(tfvars, `description = "This is a \"test\" with special chars: \\n\\t"`) {
					t.Errorf("expected tfvars to escape special characters, got: %s", tfvars)
				}
			},
		},
		{
			name:        "nil configuration",
			config:      nil,
			expectError: true,
		},
		{
			name: "missing provider",
			config: &DeploymentConfig{
				Region:       "cn-hangzhou",
				InstanceType: "ecs.t6-c1m1.large",
			},
			expectError: true,
		},
		{
			name: "missing region",
			config: &DeploymentConfig{
				Provider:     "alicloud",
				InstanceType: "ecs.t6-c1m1.large",
			},
			expectError: true,
		},
		{
			name: "missing instance type",
			config: &DeploymentConfig{
				Provider: "alicloud",
				Region:   "cn-hangzhou",
			},
			expectError: true,
		},
		{
			name: "empty variables map",
			config: &DeploymentConfig{
				Provider:     "alicloud",
				Region:       "cn-hangzhou",
				InstanceType: "ecs.t6-c1m1.large",
				Variables:    map[string]string{},
			},
			expectError: false,
			checkFunc: func(t *testing.T, tfvars string) {
				// Should not contain custom variables section
				if strings.Contains(tfvars, "# 自定义变量") {
					t.Errorf("expected tfvars to not contain custom variables section for empty map")
				}
			},
		},
		{
			name: "variables with empty string values should be skipped",
			config: &DeploymentConfig{
				Provider:     "alicloud",
				Region:       "cn-hangzhou",
				InstanceType: "ecs.t6-c1m1.large",
				Variables: map[string]string{
					"zone_index":        "",
					"instance_password": "MyPassword123!",
					"empty_var":         "",
					"disk_size":         "100",
				},
			},
			expectError: false,
			checkFunc: func(t *testing.T, tfvars string) {
				// Should not contain empty variables
				if strings.Contains(tfvars, "zone_index") {
					t.Errorf("expected tfvars to skip empty zone_index variable")
				}
				if strings.Contains(tfvars, "empty_var") {
					t.Errorf("expected tfvars to skip empty_var variable")
				}
				// Should contain non-empty variables
				if !strings.Contains(tfvars, `instance_password = "MyPassword123!"`) {
					t.Errorf("expected tfvars to contain instance_password variable")
				}
				if !strings.Contains(tfvars, `disk_size = "100"`) {
					t.Errorf("expected tfvars to contain disk_size variable")
				}
			},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			tfvars, err := executor.GenerateVariablesFile(tt.config)

			if tt.expectError {
				if err == nil {
					t.Errorf("expected error but got none")
				}
				return
			}

			if err != nil {
				t.Errorf("unexpected error: %v", err)
				return
			}

			if tfvars == "" {
				t.Errorf("expected non-empty tfvars")
				return
			}

			if tt.checkFunc != nil {
				tt.checkFunc(t, tfvars)
			}
		})
	}
}

func TestGenerateVariablesFileFormat(t *testing.T) {
	executor := NewDeploymentExecutor()

	config := &DeploymentConfig{
		Provider:     "alicloud",
		Region:       "cn-hangzhou",
		InstanceType: "ecs.t6-c1m1.large",
		Userdata:     "#!/bin/bash\necho 'test'\n",
		Variables: map[string]string{
			"instance_name": "test-instance",
		},
	}

	tfvars, err := executor.GenerateVariablesFile(config)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	// Verify the format is valid tfvars
	lines := strings.Split(tfvars, "\n")
	
	// Should have multiple lines
	if len(lines) < 5 {
		t.Errorf("expected at least 5 lines in tfvars, got %d", len(lines))
	}

	// First line should be cloud_provider
	if !strings.HasPrefix(lines[0], "cloud_provider = ") {
		t.Errorf("expected first line to be cloud_provider, got: %s", lines[0])
	}

	// Should contain heredoc for multiline userdata
	foundHeredoc := false
	for _, line := range lines {
		if strings.Contains(line, "<<-EOT") {
			foundHeredoc = true
			break
		}
	}
	if !foundHeredoc {
		t.Errorf("expected heredoc syntax for multiline userdata")
	}
}

func TestEscapeString(t *testing.T) {
	tests := []struct {
		name     string
		input    string
		expected string
	}{
		{
			name:     "no special characters",
			input:    "hello world",
			expected: "hello world",
		},
		{
			name:     "with quotes",
			input:    `hello "world"`,
			expected: `hello \"world\"`,
		},
		{
			name:     "with backslash",
			input:    `hello\world`,
			expected: `hello\\world`,
		},
		{
			name:     "with newline",
			input:    "hello\nworld",
			expected: `hello\nworld`,
		},
		{
			name:     "with tab",
			input:    "hello\tworld",
			expected: `hello\tworld`,
		},
		{
			name:     "with carriage return",
			input:    "hello\rworld",
			expected: `hello\rworld`,
		},
		{
			name:     "multiple special characters",
			input:    "hello\n\"world\"\t\\test",
			expected: `hello\n\"world\"\t\\test`,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := escapeString(tt.input)
			if result != tt.expected {
				t.Errorf("expected %q, got %q", tt.expected, result)
			}
		})
	}
}

func TestContainsNewline(t *testing.T) {
	tests := []struct {
		name     string
		input    string
		expected bool
	}{
		{
			name:     "no newline",
			input:    "hello world",
			expected: false,
		},
		{
			name:     "with newline",
			input:    "hello\nworld",
			expected: true,
		},
		{
			name:     "with carriage return",
			input:    "hello\rworld",
			expected: true,
		},
		{
			name:     "with both",
			input:    "hello\r\nworld",
			expected: true,
		},
		{
			name:     "empty string",
			input:    "",
			expected: false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := containsNewline(tt.input)
			if result != tt.expected {
				t.Errorf("expected %v, got %v", tt.expected, result)
			}
		})
	}
}

func TestEndsWithNewline(t *testing.T) {
	tests := []struct {
		name     string
		input    string
		expected bool
	}{
		{
			name:     "no newline",
			input:    "hello world",
			expected: false,
		},
		{
			name:     "ends with newline",
			input:    "hello world\n",
			expected: true,
		},
		{
			name:     "ends with carriage return",
			input:    "hello world\r",
			expected: true,
		},
		{
			name:     "empty string",
			input:    "",
			expected: false,
		},
		{
			name:     "only newline",
			input:    "\n",
			expected: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := endsWithNewline(tt.input)
			if result != tt.expected {
				t.Errorf("expected %v, got %v", tt.expected, result)
			}
		})
	}
}

func TestGenerateVariablesFileAllProviders(t *testing.T) {
	executor := NewDeploymentExecutor()

	providers := []string{"alicloud", "tencentcloud", "aws", "volcengine", "huaweicloud"}

	for _, provider := range providers {
		t.Run(provider, func(t *testing.T) {
			config := &DeploymentConfig{
				Provider:     provider,
				Region:       "test-region",
				InstanceType: "test-instance-type",
			}

			tfvars, err := executor.GenerateVariablesFile(config)
			if err != nil {
				t.Errorf("unexpected error for provider %s: %v", provider, err)
				return
			}

			if !strings.Contains(tfvars, fmt.Sprintf(`provider = "%s"`, provider)) {
				t.Errorf("expected tfvars to contain provider %s", provider)
			}
		})
	}
}
