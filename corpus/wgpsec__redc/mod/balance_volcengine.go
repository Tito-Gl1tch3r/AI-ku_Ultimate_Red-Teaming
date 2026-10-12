package mod

import (
	"encoding/json"
	"fmt"

	"github.com/volcengine/volcengine-go-sdk/service/billing"
	"github.com/volcengine/volcengine-go-sdk/volcengine"
	"github.com/volcengine/volcengine-go-sdk/volcengine/credentials"
	"github.com/volcengine/volcengine-go-sdk/volcengine/session"
)

// QueryVolcengineBalance queries Volcengine account balance via Billing API.
func QueryVolcengineBalance(accessKey string, secretKey string, region string) (string, string, error) {
	if accessKey == "" || secretKey == "" {
		return "", "", fmt.Errorf("missing volcengine access key or secret")
	}
	if region == "" {
		region = "cn-north-1"
	}

	config := volcengine.NewConfig().
		WithRegion(region).
		WithCredentials(credentials.NewStaticCredentials(accessKey, secretKey, ""))
	sess, err := session.NewSession(config)
	if err != nil {
		return "", "", err
	}
	svc := billing.New(sess)

	resp, err := svc.QueryBalanceAcct(&billing.QueryBalanceAcctInput{})
	if err != nil {
		return "", "", err
	}
	amount, ok := extractVolcBalance(resp)
	if !ok {
		return "0.00", "CNY", fmt.Errorf("未返回余额字段，可能无权限")
	}
	currency := "CNY"
	return amount, currency, nil
}

func extractVolcBalance(resp interface{}) (string, bool) {
	data, err := json.Marshal(resp)
	if err != nil {
		return "", false
	}
	var raw interface{}
	if err := json.Unmarshal(data, &raw); err != nil {
		return "", false
	}
	if val, ok := findBalanceValue(raw); ok {
		return val, true
	}
	return "", false
}

func findBalanceValue(v interface{}) (string, bool) {
	switch t := v.(type) {
	case map[string]interface{}:
		for k, val := range t {
			key := normalizeKey(k)
			if key == "balance" || key == "availablebalance" || key == "available_amount" || key == "availableamount" || key == "amount" {
				if s, ok := toString(val); ok {
					return s, true
				}
			}
			if s, ok := findBalanceValue(val); ok {
				return s, true
			}
		}
	case []interface{}:
		for _, item := range t {
			if s, ok := findBalanceValue(item); ok {
				return s, true
			}
		}
	}
	return "", false
}

func normalizeKey(k string) string {
	res := make([]rune, 0, len(k))
	for _, r := range k {
		if r >= 'A' && r <= 'Z' {
			res = append(res, r+('a'-'A'))
			continue
		}
		if r == '-' || r == '_' || r == ' ' {
			continue
		}
		res = append(res, r)
	}
	return string(res)
}

func toString(v interface{}) (string, bool) {
	switch val := v.(type) {
	case string:
		return val, true
	case float64:
		return fmt.Sprintf("%.2f", val), true
	case float32:
		return fmt.Sprintf("%.2f", val), true
	case int:
		return fmt.Sprintf("%d", val), true
	case int64:
		return fmt.Sprintf("%d", val), true
	case uint64:
		return fmt.Sprintf("%d", val), true
	default:
		return "", false
	}
}
