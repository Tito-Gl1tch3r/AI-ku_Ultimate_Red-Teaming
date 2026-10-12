package cost

import (
	"fmt"
	"sync"
	"time"
)

// Currency represents a currency code
type Currency string

const (
	CurrencyCNY Currency = "CNY" // 人民币
	CurrencyUSD Currency = "USD" // 美元
	CurrencyEUR Currency = "EUR" // 欧元
	CurrencyGBP Currency = "GBP" // 英镑
	CurrencyJPY Currency = "JPY" // 日元
)

// ExchangeRate represents an exchange rate between two currencies
type ExchangeRate struct {
	From      Currency  `json:"from"`
	To        Currency  `json:"to"`
	Rate      float64   `json:"rate"`
	Timestamp time.Time `json:"timestamp"`
}

// CurrencyConverter handles currency conversion with exchange rates
type CurrencyConverter struct {
	mu    sync.RWMutex
	rates map[string]float64 // key: "FROM_TO", value: rate
}

// NewCurrencyConverter creates a new currency converter with default exchange rates
func NewCurrencyConverter() *CurrencyConverter {
	converter := &CurrencyConverter{
		rates: make(map[string]float64),
	}
	
	// Initialize with default exchange rates (approximate values)
	// In production, these should be fetched from a real exchange rate API
	converter.setDefaultRates()
	
	return converter
}

// setDefaultRates sets default exchange rates
func (c *CurrencyConverter) setDefaultRates() {
	// Base rates (as of typical values, should be updated from API in production)
	// USD as base currency
	c.rates["USD_CNY"] = 7.2  // 1 USD = 7.2 CNY
	c.rates["USD_EUR"] = 0.92 // 1 USD = 0.92 EUR
	c.rates["USD_GBP"] = 0.79 // 1 USD = 0.79 GBP
	c.rates["USD_JPY"] = 149.0 // 1 USD = 149 JPY
	
	// CNY rates
	c.rates["CNY_USD"] = 1.0 / 7.2
	c.rates["CNY_EUR"] = 0.92 / 7.2
	c.rates["CNY_GBP"] = 0.79 / 7.2
	c.rates["CNY_JPY"] = 149.0 / 7.2
	
	// EUR rates
	c.rates["EUR_USD"] = 1.0 / 0.92
	c.rates["EUR_CNY"] = 7.2 / 0.92
	c.rates["EUR_GBP"] = 0.79 / 0.92
	c.rates["EUR_JPY"] = 149.0 / 0.92
	
	// GBP rates
	c.rates["GBP_USD"] = 1.0 / 0.79
	c.rates["GBP_CNY"] = 7.2 / 0.79
	c.rates["GBP_EUR"] = 0.92 / 0.79
	c.rates["GBP_JPY"] = 149.0 / 0.79
	
	// JPY rates
	c.rates["JPY_USD"] = 1.0 / 149.0
	c.rates["JPY_CNY"] = 7.2 / 149.0
	c.rates["JPY_EUR"] = 0.92 / 149.0
	c.rates["JPY_GBP"] = 0.79 / 149.0
	
	// Same currency rates (identity)
	c.rates["USD_USD"] = 1.0
	c.rates["CNY_CNY"] = 1.0
	c.rates["EUR_EUR"] = 1.0
	c.rates["GBP_GBP"] = 1.0
	c.rates["JPY_JPY"] = 1.0
}

// Convert converts an amount from one currency to another
func (c *CurrencyConverter) Convert(amount float64, from, to Currency) (float64, error) {
	// Validate currencies
	if !c.isValidCurrency(from) {
		return 0, fmt.Errorf("不支持的源货币: %s", from)
	}
	if !c.isValidCurrency(to) {
		return 0, fmt.Errorf("不支持的目标货币: %s", to)
	}
	
	// Same currency, no conversion needed
	if from == to {
		return amount, nil
	}
	
	// Get exchange rate
	rate, err := c.GetRate(from, to)
	if err != nil {
		return 0, err
	}
	
	// Convert
	return amount * rate, nil
}

// GetRate gets the exchange rate from one currency to another
func (c *CurrencyConverter) GetRate(from, to Currency) (float64, error) {
	c.mu.RLock()
	defer c.mu.RUnlock()
	
	key := fmt.Sprintf("%s_%s", from, to)
	rate, exists := c.rates[key]
	if !exists {
		return 0, fmt.Errorf("汇率不可用: %s -> %s", from, to)
	}
	
	return rate, nil
}

// SetRate sets a custom exchange rate
func (c *CurrencyConverter) SetRate(from, to Currency, rate float64) error {
	if !c.isValidCurrency(from) {
		return fmt.Errorf("不支持的源货币: %s", from)
	}
	if !c.isValidCurrency(to) {
		return fmt.Errorf("不支持的目标货币: %s", to)
	}
	if rate <= 0 {
		return fmt.Errorf("汇率必须大于 0")
	}
	
	c.mu.Lock()
	defer c.mu.Unlock()
	
	key := fmt.Sprintf("%s_%s", from, to)
	c.rates[key] = rate
	
	// Also set the inverse rate
	inverseKey := fmt.Sprintf("%s_%s", to, from)
	c.rates[inverseKey] = 1.0 / rate
	
	return nil
}

// UpdateRates updates exchange rates from a map
func (c *CurrencyConverter) UpdateRates(rates map[string]float64) {
	c.mu.Lock()
	defer c.mu.Unlock()
	
	for key, rate := range rates {
		c.rates[key] = rate
	}
}

// isValidCurrency checks if a currency is supported
func (c *CurrencyConverter) isValidCurrency(currency Currency) bool {
	switch currency {
	case CurrencyCNY, CurrencyUSD, CurrencyEUR, CurrencyGBP, CurrencyJPY:
		return true
	default:
		return false
	}
}

// GetSupportedCurrencies returns a list of supported currencies
func (c *CurrencyConverter) GetSupportedCurrencies() []Currency {
	return []Currency{
		CurrencyCNY,
		CurrencyUSD,
		CurrencyEUR,
		CurrencyGBP,
		CurrencyJPY,
	}
}

// ConvertCostEstimate converts a cost estimate to a different currency
func (c *CurrencyConverter) ConvertCostEstimate(estimate *CostEstimate, targetCurrency Currency) (*CostEstimate, error) {
	if estimate == nil {
		return nil, fmt.Errorf("成本估算不能为空")
	}
	
	// Parse source currency
	sourceCurrency := Currency(estimate.Currency)
	if !c.isValidCurrency(sourceCurrency) {
		return nil, fmt.Errorf("不支持的源货币: %s", estimate.Currency)
	}
	
	// If same currency, return a copy
	if sourceCurrency == targetCurrency {
		return estimate, nil
	}
	
	// Convert total costs
	convertedHourly, err := c.Convert(estimate.TotalHourlyCost, sourceCurrency, targetCurrency)
	if err != nil {
		return nil, fmt.Errorf("转换小时成本失败: %w", err)
	}
	
	convertedMonthly, err := c.Convert(estimate.TotalMonthlyCost, sourceCurrency, targetCurrency)
	if err != nil {
		return nil, fmt.Errorf("转换月度成本失败: %w", err)
	}
	
	// Create new estimate with converted values
	converted := &CostEstimate{
		TotalHourlyCost:  convertedHourly,
		TotalMonthlyCost: convertedMonthly,
		Currency:         string(targetCurrency),
		Breakdown:        make([]ResourceCostBreakdown, len(estimate.Breakdown)),
		ProviderBreakdown: make(map[string]*ProviderCostSummary),
		UnavailableCount: estimate.UnavailableCount,
		Timestamp:        estimate.Timestamp,
		Disclaimer:       estimate.Disclaimer,
		Warnings:         estimate.Warnings,
	}
	
	// Convert breakdown items
	for i, breakdown := range estimate.Breakdown {
		convertedBreakdown := breakdown
		
		if breakdown.Available {
			convertedBreakdown.UnitHourly, _ = c.Convert(breakdown.UnitHourly, sourceCurrency, targetCurrency)
			convertedBreakdown.UnitMonthly, _ = c.Convert(breakdown.UnitMonthly, sourceCurrency, targetCurrency)
			convertedBreakdown.TotalHourly, _ = c.Convert(breakdown.TotalHourly, sourceCurrency, targetCurrency)
			convertedBreakdown.TotalMonthly, _ = c.Convert(breakdown.TotalMonthly, sourceCurrency, targetCurrency)
			convertedBreakdown.Currency = string(targetCurrency)
		}
		
		converted.Breakdown[i] = convertedBreakdown
	}
	
	// Convert provider breakdown
	for provider, summary := range estimate.ProviderBreakdown {
		convertedSummary := &ProviderCostSummary{
			Provider:        summary.Provider,
			Currency:        string(targetCurrency),
			ResourceCount:   summary.ResourceCount,
		}
		
		convertedSummary.TotalHourlyCost, _ = c.Convert(summary.TotalHourlyCost, sourceCurrency, targetCurrency)
		convertedSummary.TotalMonthlyCost, _ = c.Convert(summary.TotalMonthlyCost, sourceCurrency, targetCurrency)
		
		converted.ProviderBreakdown[provider] = convertedSummary
	}
	
	return converted, nil
}
