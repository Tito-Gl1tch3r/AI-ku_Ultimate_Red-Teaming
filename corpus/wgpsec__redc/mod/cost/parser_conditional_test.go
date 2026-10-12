package cost

import (
	"os"
	"path/filepath"
	"testing"
)

// TestParseTemplate_ConditionalCount tests parsing templates with conditional count expressions
func TestParseTemplate_ConditionalCount(t *testing.T) {
	// Create a temporary directory for test files
	tmpDir := t.TempDir()

	// Create a test template with conditional count
	tfContent := `
variable "cloud_provider" {
  type = string
}

resource "alicloud_instance" "this" {
  count = var.cloud_provider == "alicloud" ? 1 : 0
  instance_type = "ecs.t5-lc1m1.small"
}

resource "aws_instance" "this" {
  count = var.cloud_provider == "aws" ? 1 : 0
  instance_type = "t2.micro"
}

resource "volcengine_ecs_instance" "this" {
  count = var.cloud_provider == "volcengine" ? 1 : 0
  instance_type = "ecs.c3i.large"
}
`

	// Write the template file
	tfFile := filepath.Join(tmpDir, "main.tf")
	if err := os.WriteFile(tfFile, []byte(tfContent), 0644); err != nil {
		t.Fatalf("Failed to write test file: %v", err)
	}

	// Test case 1: cloud_provider = "alicloud"
	t.Run("Provider=alicloud", func(t *testing.T) {
		variables := map[string]string{
			"cloud_provider": "alicloud",
		}

		resources, err := ParseTemplate(tmpDir, variables)
		if err != nil {
			t.Fatalf("ParseTemplate failed: %v", err)
		}

		// Should only have 1 resource (alicloud_instance)
		if len(resources.Resources) != 1 {
			t.Errorf("Expected 1 resource, got %d", len(resources.Resources))
			for i, r := range resources.Resources {
				t.Logf("Resource %d: %s (count=%d)", i, r.Type, r.Count)
			}
		}

		// Verify it's the alicloud instance
		if len(resources.Resources) > 0 {
			if resources.Resources[0].Type != "alicloud_instance" {
				t.Errorf("Expected alicloud_instance, got %s", resources.Resources[0].Type)
			}
			if resources.Resources[0].Count != 1 {
				t.Errorf("Expected count=1, got %d", resources.Resources[0].Count)
			}
		}
	})

	// Test case 2: cloud_provider = "aws"
	t.Run("Provider=aws", func(t *testing.T) {
		variables := map[string]string{
			"cloud_provider": "aws",
		}

		resources, err := ParseTemplate(tmpDir, variables)
		if err != nil {
			t.Fatalf("ParseTemplate failed: %v", err)
		}

		// Should only have 1 resource (aws_instance)
		if len(resources.Resources) != 1 {
			t.Errorf("Expected 1 resource, got %d", len(resources.Resources))
			for i, r := range resources.Resources {
				t.Logf("Resource %d: %s (count=%d)", i, r.Type, r.Count)
			}
		}

		// Verify it's the AWS instance
		if len(resources.Resources) > 0 {
			if resources.Resources[0].Type != "aws_instance" {
				t.Errorf("Expected aws_instance, got %s", resources.Resources[0].Type)
			}
			if resources.Resources[0].Count != 1 {
				t.Errorf("Expected count=1, got %d", resources.Resources[0].Count)
			}
		}
	})

	// Test case 3: cloud_provider = "volcengine"
	t.Run("Provider=volcengine", func(t *testing.T) {
		variables := map[string]string{
			"cloud_provider": "volcengine",
		}

		resources, err := ParseTemplate(tmpDir, variables)
		if err != nil {
			t.Fatalf("ParseTemplate failed: %v", err)
		}

		// Should only have 1 resource (volcengine_ecs_instance)
		if len(resources.Resources) != 1 {
			t.Errorf("Expected 1 resource, got %d", len(resources.Resources))
			for i, r := range resources.Resources {
				t.Logf("Resource %d: %s (count=%d)", i, r.Type, r.Count)
			}
		}

		// Verify it's the Volcengine instance
		if len(resources.Resources) > 0 {
			if resources.Resources[0].Type != "volcengine_ecs_instance" {
				t.Errorf("Expected volcengine_ecs_instance, got %s", resources.Resources[0].Type)
			}
			if resources.Resources[0].Count != 1 {
				t.Errorf("Expected count=1, got %d", resources.Resources[0].Count)
			}
		}
	})
}
