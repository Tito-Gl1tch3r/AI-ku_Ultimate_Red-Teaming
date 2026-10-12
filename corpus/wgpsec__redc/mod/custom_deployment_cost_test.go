package mod

import (
	"red-cloud/mod/cost"
	"testing"
)

func TestCustomDeploymentService_EstimateCost(t *testing.T) {
	service := NewCustomDeploymentService()
	
	// Create a mock pricing service and cost calculator
	pricingService := cost.NewPricingService(":memory:")
	defer pricingService.Close()
	
	costCalculator := cost.NewCostCalculator()
	
	// Set up a fallback provider for testing
	pricingService.SetFallbackProvider(func(provider, region, resourceType string) (*cost.PricingData, error) {
		// Return mock pricing data
		return &cost.PricingData{
			Provider:     provider,
			Region:       region,
			ResourceType: resourceType,
			Currency:     "USD",
			HourlyPrice:  1.0,
			MonthlyPrice: 720.0,
		}, nil
	})
	
	tests := []struct {
		name        string
		config      *DeploymentConfig
		expectError bool
	}{
		{
			name:        "Nil config",
			config:      nil,
			expectError: true,
		},
		{
			name: "Invalid config - missing provider",
			config: &DeploymentConfig{
				Name:         "test-deployment",
				TemplateName: "nonexistent-template",
				Provider:     "",
				Region:       "cn-hangzhou",
				InstanceType: "ecs.t6-c1m1.large",
			},
			expectError: true,
		},
		{
			name: "Invalid config - missing region",
			config: &DeploymentConfig{
				Name:         "test-deployment",
				TemplateName: "nonexistent-template",
				Provider:     "alicloud",
				Region:       "",
				InstanceType: "ecs.t6-c1m1.large",
			},
			expectError: true,
		},
		{
			name: "Invalid config - missing instance type",
			config: &DeploymentConfig{
				Name:         "test-deployment",
				TemplateName: "nonexistent-template",
				Provider:     "alicloud",
				Region:       "cn-hangzhou",
				InstanceType: "",
			},
			expectError: true,
		},
	}
	
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			estimate, err := service.EstimateCost(tt.config, pricingService, costCalculator)
			
			if tt.expectError {
				if err == nil {
					t.Errorf("Expected error but got none")
				}
				return
			}
			
			if err != nil {
				t.Errorf("Unexpected error: %v", err)
				return
			}
			
			if estimate == nil {
				t.Error("Expected non-nil estimate")
				return
			}
			
			// Basic validation
			if estimate.Currency == "" {
				t.Error("Expected non-empty currency")
			}
			
			if estimate.MonthlyCost < 0 {
				t.Error("Expected non-negative monthly cost")
			}
		})
	}
}

func TestCustomDeploymentService_EstimateCost_NilServices(t *testing.T) {
	service := NewCustomDeploymentService()
	
	config := &DeploymentConfig{
		Name:         "test-deployment",
		TemplateName: "test-template",
		Provider:     "alicloud",
		Region:       "cn-hangzhou",
		InstanceType: "ecs.t6-c1m1.large",
	}
	
	// Test with nil pricing service
	_, err := service.EstimateCost(config, nil, cost.NewCostCalculator())
	if err == nil {
		t.Error("Expected error with nil pricing service")
	}
	
	// Test with nil cost calculator
	pricingService := cost.NewPricingService(":memory:")
	defer pricingService.Close()
	
	_, err = service.EstimateCost(config, pricingService, nil)
	if err == nil {
		t.Error("Expected error with nil cost calculator")
	}
}
