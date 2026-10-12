package mod

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"
)

// QueryVultrBalance queries Vultr account balance via API.
func QueryVultrBalance(apiKey string) (string, string, error) {
	if apiKey == "" {
		return "", "", fmt.Errorf("missing vultr api key")
	}

	req, err := http.NewRequest("GET", "https://api.vultr.com/v2/account", nil)
	if err != nil {
		return "", "", err
	}

	req.Header.Set("Authorization", "Bearer "+apiKey)

	client := NewProxyHTTPClient(0)
	resp, err := client.Do(req)
	if err != nil {
		return "", "", err
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", "", err
	}

	if resp.StatusCode != http.StatusOK {
		return "", "", fmt.Errorf("vultr api error: %s", string(body))
	}

	var result struct {
		Account struct {
			Balance         float64 `json:"balance"`
			PendingCharges  float64 `json:"pending_charges"`
			LastPaymentDate string  `json:"last_payment_date"`
			LastPaymentAmount float64 `json:"last_payment_amount"`
		} `json:"account"`
	}

	if err := json.Unmarshal(body, &result); err != nil {
		return "", "", fmt.Errorf("failed to parse vultr response: %v", err)
	}

	// Vultr 返回的余额是负数（表示欠费），pending_charges 是待结算金额
	// 账户实际余额 = balance + pending_charges (因为 pending 是预估的未结算费用)
	totalBalance := result.Account.Balance + result.Account.PendingCharges

	currency := "USD"
	return fmt.Sprintf("%.2f", totalBalance), currency, nil
}

// QueryVultrBill queries Vultr current month bill via API.
func QueryVultrBill(apiKey string) (string, string, error) {
	if apiKey == "" {
		return "", "", fmt.Errorf("missing vultr api key")
	}

	now := time.Now()
	startDate := time.Date(now.Year(), now.Month(), 1, 0, 0, 0, 0, now.Location()).Format("2006-01-02")
	endDate := now.Format("2006-01-02")

	req, err := http.NewRequest("GET", "https://api.vultr.com/v2/billing/history?start_date="+startDate+"&end_date="+endDate, nil)
	if err != nil {
		return "", "", err
	}

	req.Header.Set("Authorization", "Bearer "+apiKey)

	client := NewProxyHTTPClient(30 * time.Second)
	resp, err := client.Do(req)
	if err != nil {
		return "", "", err
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", "", err
	}

	if resp.StatusCode != http.StatusOK {
		return "", "", fmt.Errorf("vultr billing api error: %s", string(body))
	}

	var result struct {
		BillingHistory []struct {
			Amount     float64 `json:"amount"`
			Category   string  `json:"category"`
			Date       string  `json:"date"`
			Description string  `json:"description"`
		} `json:"billing_history"`
	}

	if err := json.Unmarshal(body, &result); err != nil {
		return "", "", fmt.Errorf("failed to parse vultr billing response: %v", err)
	}

	var totalBill float64
	for _, item := range result.BillingHistory {
		// 只计算消耗类费用（instance, bandwidth 等），不包括充值
		if item.Category == "instance" || item.Category == "bandwidth" || item.Category == "snapshot" {
			totalBill += item.Amount
		}
	}

	return fmt.Sprintf("%.2f", totalBill), "USD", nil
}
