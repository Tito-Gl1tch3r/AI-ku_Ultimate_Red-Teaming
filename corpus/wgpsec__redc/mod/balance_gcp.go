package mod

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"strings"
	"time"
)

func init() {
}

type GCPServiceAccount struct {
	Type         string `json:"type"`
	ProjectID    string `json:"project_id"`
	PrivateKeyID string `json:"private_key_id"`
	ClientEmail  string `json:"client_email"`
	TokenURL     string `json:"token_url"`
}

type GCPTokenResponse struct {
	AccessToken string `json:"access_token"`
	ExpiresIn   int    `json:"expires_in"`
	TokenType   string `json:"token_type"`
}

func getGCPAccessToken(credentialsPath string) (string, error) {
	data, err := os.ReadFile(credentialsPath)
	if err != nil {
		return "", fmt.Errorf("failed to read credentials file: %w", err)
	}

	var sa GCPServiceAccount
	if err := json.Unmarshal(data, &sa); err != nil {
		return "", fmt.Errorf("failed to parse credentials: %w", err)
	}

	jwt := fmt.Sprintf("header.eyJzdWIiOiAi%ss.apps.googleusercontent.comIiwiaWF0IjoxNzAwMDAwMDAwfQ.signature", sa.ClientEmail)

	payload := []byte(fmt.Sprintf(`{
		"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
		"assertion": "%s"
	}`, jwt))

	req, err := http.NewRequest("POST", sa.TokenURL, strings.NewReader(string(payload)))
	if err != nil {
		return "", err
	}
	req.Header.Set("Content-Type", "application/json")

	client := NewProxyHTTPClient(10 * time.Second)
	resp, err := client.Do(req)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	body, _ := io.ReadAll(resp.Body)
	if resp.StatusCode != 200 {
		return "", fmt.Errorf("failed to get token: %s", string(body))
	}

	var tokenResp GCPTokenResponse
	if err := json.Unmarshal(body, &tokenResp); err != nil {
		return "", err
	}

	return tokenResp.AccessToken, nil
}

func QueryGCPBill(credentialsPath string, projectID string) (string, string, error) {
	if credentialsPath == "" {
		return "", "", fmt.Errorf("missing GCP credentials path")
	}
	if projectID == "" {
		return "", "", fmt.Errorf("missing GCP project ID")
	}

	token, err := getGCPAccessToken(credentialsPath)
	if err != nil {
		return "", "", fmt.Errorf("failed to get GCP access token: %w", err)
	}

	req, err := http.NewRequest("GET", 
		"https://cloudbilling.googleapis.com/v1/projects/"+projectID+"/billingInfo", 
		nil)
	if err != nil {
		return "", "", err
	}
	req.Header.Set("Authorization", "Bearer "+token)

	client := NewProxyHTTPClient(15 * time.Second)
	resp, err := client.Do(req)
	if err != nil {
		return "", "", err
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", "", err
	}

	if resp.StatusCode != 200 {
		return "", "", fmt.Errorf("failed to get billing info: %s", string(body))
	}

	var billingInfo struct {
		BillingAccountName string `json:"billingAccountName"`
		BillingEnabled     bool   `json:"billingEnabled"`
	}

	if err := json.Unmarshal(body, &billingInfo); err != nil {
		return "", "", err
	}

	if !billingInfo.BillingEnabled || billingInfo.BillingAccountName == "" {
		return "", "", fmt.Errorf("project has no billing account")
	}

	billingAccountName := strings.TrimPrefix(billingInfo.BillingAccountName, "billingAccounts/")

	now := time.Now()

	billReqURL := fmt.Sprintf(
		"https://cloudbilling.googleapis.com/v1/billingAccounts/%s/costs?startDate.year=%d&startDate.month=%d&endDate.year=%d&endDate.month=%d",
		billingAccountName,
		now.Year(), now.Month(),
		now.Year(), now.Month()+1)

	if now.Month() == 12 {
		billReqURL = fmt.Sprintf(
			"https://cloudbilling.googleapis.com/v1/billingAccounts/%s/costs?startDate.year=%d&startDate.month=%d&endDate.year=%d&endDate.month=1",
			billingAccountName,
			now.Year(), now.Month(),
			now.Year()+1)
	}

	billReq, err := http.NewRequest("GET", billReqURL, nil)
	if err != nil {
		return "", "", err
	}
	billReq.Header.Set("Authorization", "Bearer "+token)

	billResp, err := client.Do(billReq)
	if err != nil {
		return "", "", err
	}
	defer billResp.Body.Close()

	billBody, err := io.ReadAll(billResp.Body)
	if err != nil {
		return "", "", err
	}

	if billResp.StatusCode != 200 {
		return "0.00", "USD", nil
	}

	var billRespData struct {
		Cost []struct {
			CostAmount struct {
				Amount     string `json:"amount"`
				CurrencyCode string `json:"currencyCode"`
			} `json:"costAmount"`
		} `json:"cost"`
	}

	if err := json.Unmarshal(billBody, &billRespData); err != nil {
		return "0.00", "USD", nil
	}

	var totalAmount float64
	for _, cost := range billRespData.Cost {
		var amt float64
		fmt.Sscanf(cost.CostAmount.Amount, "%f", &amt)
		totalAmount += amt
	}

	return fmt.Sprintf("%.2f", totalAmount), "USD", nil
}

func QueryGCPBillFromConfig(credentials string, project string, region string) (string, string, error) {
	if credentials == "" {
		return "", "", fmt.Errorf("missing GCP credentials")
	}

	if project == "" {
		if strings.HasPrefix(credentials, "{") {
			var cred GCPServiceAccount
			if err := json.Unmarshal([]byte(credentials), &cred); err == nil {
				project = cred.ProjectID
			}
		}
	}

	if project == "" {
		return "", "", fmt.Errorf("missing GCP project ID")
	}

	credPath := credentials
	if !strings.HasPrefix(credPath, "/") && !strings.Contains(credPath, ":") {
		home, _ := os.UserHomeDir()
		credPath = home + "/.config/gcloud/" + credPath
	}

	return QueryGCPBill(credPath, project)
}
