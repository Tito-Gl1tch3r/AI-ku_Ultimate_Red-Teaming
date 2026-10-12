package mod

import (
	"fmt"
	"strconv"

	"github.com/ucloud/ucloud-sdk-go/services/ubill"
	"github.com/ucloud/ucloud-sdk-go/ucloud"
	"github.com/ucloud/ucloud-sdk-go/ucloud/auth"
)

// QueryUCloudBalance queries UCloud account balance via UBilling API.
func QueryUCloudBalance(publicKey string, privateKey string, region string) (string, string, error) {
	if publicKey == "" || privateKey == "" {
		return "", "", fmt.Errorf("missing ucloud public key or private key")
	}
	if region == "" {
		region = "cn-bj2"
	}

	cfg := ucloud.NewConfig()
	cfg.Region = region

	credential := auth.NewCredential()
	credential.PublicKey = publicKey
	credential.PrivateKey = privateKey

	client := ubill.NewClient(&cfg, &credential)

	request := client.NewGetBalanceRequest()

	response, err := client.GetBalance(request)
	if err != nil {
		return "", "", err
	}
	if response == nil {
		return "", "", fmt.Errorf("empty ucloud balance response")
	}

	// UCloud 账户余额 = 可用余额 + 冻结金额 + 信用余额 + 赠送余额
	// 这些字段单位已经是"元"，不需要转换
	var totalBalance float64

	// 优先使用可用余额
	if response.AccountInfo.AmountAvailable != "" {
		if amount, err := strconv.ParseFloat(response.AccountInfo.AmountAvailable, 64); err == nil {
			totalBalance += amount
		}
	}

	// 加上冻结金额
	if response.AccountInfo.AmountFreeze != "" {
		if amount, err := strconv.ParseFloat(response.AccountInfo.AmountFreeze, 64); err == nil {
			totalBalance += amount
		}
	}

	// 加上信用余额
	if response.AccountInfo.AmountCredit != "" {
		if amount, err := strconv.ParseFloat(response.AccountInfo.AmountCredit, 64); err == nil {
			totalBalance += amount
		}
	}

	// 加上赠送余额
	if response.AccountInfo.AmountFree != "" {
		if amount, err := strconv.ParseFloat(response.AccountInfo.AmountFree, 64); err == nil {
			totalBalance += amount
		}
	}

	if totalBalance == 0 {
		// 如果都为0，尝试直接使用 Amount 字段
		if response.AccountInfo.Amount != "" {
			if amount, err := strconv.ParseFloat(response.AccountInfo.Amount, 64); err == nil {
				totalBalance = amount
			}
		}
	}

	if totalBalance == 0 {
		return "", "", fmt.Errorf("empty balance amount")
	}

	currency := "CNY"
	return fmt.Sprintf("%.2f", totalBalance), currency, nil
}
