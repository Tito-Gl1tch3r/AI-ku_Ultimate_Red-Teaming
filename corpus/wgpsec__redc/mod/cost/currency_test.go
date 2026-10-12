package cost

import (
	"math"
	"testing"
)

func TestCurrencyConverter_Convert(t *testing.T) {
	converter := NewCurrencyConverter()
	
	tests := []struct {
		name        string
		amount      float64
		from        Currency
		to          Currency
		expectError bool
	}{
		{
			name:        "Convert USD to CNY",
			amount:      100.0,
			from:        CurrencyUSD,
			to:          CurrencyCNY,
			expectError: false,
		},
		{
			name:        "Convert CNY to USD",
			amount:      720.0,
			from:        CurrencyCNY,
			to:          CurrencyUSD,
			expectError: false,
		},
		{
			name:        "Convert USD to EUR",
			amount:      100.0,
			from:        CurrencyUSD,
			to:          CurrencyEUR,
			expectError: false,
		},
		{
			name:        "Same currency (USD to USD)",
			amount:      100.0,
			from:        CurrencyUSD,
			to:          CurrencyUSD,
			expectError: false,
		},
		{
			name:        "Invalid source currency",
			amount:      100.0,
			from:        Currency("INVALID"),
			to:          CurrencyUSD,
			expectError: true,
		},
		{
			name:        "Invalid target currency",
			amount:      100.0,
			from:        CurrencyUSD,
			to:          Currency("INVALID"),
			expectError: true,
		},
	}
	
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result, err := converter.Convert(tt.amount, tt.from, tt.to)
			
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
			
			// For same currency, result should equal input
			if tt.from == tt.to {
				if result != tt.amount {
					t.Errorf("Same currency conversion failed: expected %f, got %f", tt.amount, result)
				}
			} else {
				// For different currencies, result should be positive
				if result <= 0 {
					t.Errorf("Conversion result should be positive, got %f", result)
				}
			}
		})
	}
}

func TestCurrencyConverter_RoundTrip(t *testing.T) {
	converter := NewCurrencyConverter()
	
	tests := []struct {
		name   string
		amount float64
		from   Currency
		to     Currency
	}{
		{
			name:   "USD -> CNY -> USD",
			amount: 100.0,
			from:   CurrencyUSD,
			to:     CurrencyCNY,
		},
		{
			name:   "CNY -> EUR -> CNY",
			amount: 1000.0,
			from:   CurrencyCNY,
			to:     CurrencyEUR,
		},
		{
			name:   "EUR -> GBP -> EUR",
			amount: 500.0,
			from:   CurrencyEUR,
			to:     CurrencyGBP,
		},
	}
	
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			// Convert from -> to
			intermediate, err := converter.Convert(tt.amount, tt.from, tt.to)
			if err != nil {
				t.Fatalf("First conversion failed: %v", err)
			}
			
			// Convert back to -> from
			result, err := converter.Convert(intermediate, tt.to, tt.from)
			if err != nil {
				t.Fatalf("Second conversion failed: %v", err)
			}
			
			// Check if we got back to the original amount (with small tolerance for floating point errors)
			tolerance := 0.01 // 1% tolerance
			diff := math.Abs(result - tt.amount)
			if diff > tt.amount*tolerance {
				t.Errorf("Round-trip conversion failed: started with %f, ended with %f (diff: %f)", 
					tt.amount, result, diff)
			}
		})
	}
}

func TestCurrencyConverter_SetRate(t *testing.T) {
	converter := NewCurrencyConverter()
	
	// Set a custom rate
	err := converter.SetRate(CurrencyUSD, CurrencyCNY, 7.5)
	if err != nil {
		t.Fatalf("Failed to set rate: %v", err)
	}
	
	// Get the rate back
	rate, err := converter.GetRate(CurrencyUSD, CurrencyCNY)
	if err != nil {
		t.Fatalf("Failed to get rate: %v", err)
	}
	
	if rate != 7.5 {
		t.Errorf("Expected rate 7.5, got %f", rate)
	}
	
	// Check inverse rate was also set
	inverseRate, err := converter.GetRate(CurrencyCNY, CurrencyUSD)
	if err != nil {
		t.Fatalf("Failed to get inverse rate: %v", err)
	}
	
	expectedInverse := 1.0 / 7.5
	if math.Abs(inverseRate-expectedInverse) > 0.0001 {
		t.Errorf("Expected inverse rate %f, got %f", expectedInverse, inverseRate)
	}
	
	// Test invalid rate
	err = converter.SetRate(CurrencyUSD, CurrencyCNY, -1.0)
	if err == nil {
		t.Error("Expected error for negative rate")
	}
	
	err = converter.SetRate(CurrencyUSD, CurrencyCNY, 0)
	if err == nil {
		t.Error("Expected error for zero rate")
	}
}

func TestCurrencyConverter_GetSupportedCurrencies(t *testing.T) {
	converter := NewCurrencyConverter()
	
	currencies := converter.GetSupportedCurrencies()
	
	if len(currencies) == 0 {
		t.Error("Expected non-empty list of supported currencies")
	}
	
	// Check that common currencies are supported
	expectedCurrencies := []Currency{CurrencyCNY, CurrencyUSD, CurrencyEUR}
	for _, expected := range expectedCurrencies {
		found := false
		for _, currency := range currencies {
			if currency == expected {
				found = true
				break
			}
		}
		if !found {
			t.Errorf("Expected currency %s to be supported", expected)
		}
	}
}

func TestCurrencyConverter_ConvertCostEstimate(t *testing.T) {
	converter := NewCurrencyConverter()
	
	// Create a sample cost estimate in USD
	estimate := &CostEstimate{
		TotalHourlyCost:  10.0,
		TotalMonthlyCost: 7200.0,
		Currency:         "USD",
		Breakdown: []ResourceCostBreakdown{
			{
				ResourceType: "alicloud_instance",
				ResourceName: "test-instance",
				Provider:     "alicloud",
				Count:        1,
				UnitHourly:   10.0,
				UnitMonthly:  7200.0,
				TotalHourly:  10.0,
				TotalMonthly: 7200.0,
				Currency:     "USD",
				Available:    true,
			},
		},
		ProviderBreakdown: map[string]*ProviderCostSummary{
			"alicloud": {
				Provider:         "alicloud",
				TotalHourlyCost:  10.0,
				TotalMonthlyCost: 7200.0,
				Currency:         "USD",
				ResourceCount:    1,
			},
		},
		UnavailableCount: 0,
	}
	
	// Convert to CNY
	converted, err := converter.ConvertCostEstimate(estimate, CurrencyCNY)
	if err != nil {
		t.Fatalf("Failed to convert cost estimate: %v", err)
	}
	
	// Check currency was updated
	if converted.Currency != "CNY" {
		t.Errorf("Expected currency CNY, got %s", converted.Currency)
	}
	
	// Check that costs were converted (should be higher in CNY)
	if converted.TotalMonthlyCost <= estimate.TotalMonthlyCost {
		t.Errorf("Expected CNY cost to be higher than USD cost")
	}
	
	// Check breakdown was converted
	if len(converted.Breakdown) != len(estimate.Breakdown) {
		t.Errorf("Expected %d breakdown items, got %d", len(estimate.Breakdown), len(converted.Breakdown))
	}
	
	if converted.Breakdown[0].Currency != "CNY" {
		t.Errorf("Expected breakdown currency CNY, got %s", converted.Breakdown[0].Currency)
	}
	
	// Check provider breakdown was converted
	if converted.ProviderBreakdown["alicloud"].Currency != "CNY" {
		t.Errorf("Expected provider breakdown currency CNY, got %s", 
			converted.ProviderBreakdown["alicloud"].Currency)
	}
	
	// Test same currency conversion (should return same estimate)
	sameConverted, err := converter.ConvertCostEstimate(estimate, CurrencyUSD)
	if err != nil {
		t.Fatalf("Failed to convert cost estimate to same currency: %v", err)
	}
	
	if sameConverted.TotalMonthlyCost != estimate.TotalMonthlyCost {
		t.Errorf("Same currency conversion should not change costs")
	}
}

func TestCurrencyConverter_ConversionConsistency(t *testing.T) {
	converter := NewCurrencyConverter()
	
	// Test that converting through intermediate currency gives consistent results
	amount := 1000.0
	
	// Direct conversion: USD -> CNY
	directResult, err := converter.Convert(amount, CurrencyUSD, CurrencyCNY)
	if err != nil {
		t.Fatalf("Direct conversion failed: %v", err)
	}
	
	// Indirect conversion: USD -> EUR -> CNY
	toEUR, err := converter.Convert(amount, CurrencyUSD, CurrencyEUR)
	if err != nil {
		t.Fatalf("USD to EUR conversion failed: %v", err)
	}
	
	indirectResult, err := converter.Convert(toEUR, CurrencyEUR, CurrencyCNY)
	if err != nil {
		t.Fatalf("EUR to CNY conversion failed: %v", err)
	}
	
	// Results should be close (within 5% due to rounding in intermediate steps)
	tolerance := 0.05
	diff := math.Abs(directResult - indirectResult)
	if diff > directResult*tolerance {
		t.Errorf("Conversion inconsistency: direct=%f, indirect=%f, diff=%f", 
			directResult, indirectResult, diff)
	}
}
