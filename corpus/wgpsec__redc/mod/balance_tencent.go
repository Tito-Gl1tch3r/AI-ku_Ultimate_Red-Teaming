package mod

import (
	"fmt"

	"github.com/tencentcloud/tencentcloud-sdk-go/tencentcloud/common"
	"github.com/tencentcloud/tencentcloud-sdk-go/tencentcloud/common/profile"
	billing "github.com/tencentcloud/tencentcloud-sdk-go/tencentcloud/billing/v20180709"
)

// QueryTencentBalance queries Tencent Cloud account balance via Billing API.
func QueryTencentBalance(secretId string, secretKey string, region string) (string, string, error) {
	if secretId == "" || secretKey == "" {
		return "", "", fmt.Errorf("missing tencentcloud secret id or key")
	}
	if region == "" {
		region = "ap-guangzhou"
	}

	cred := common.NewCredential(secretId, secretKey)
	cpf := profile.NewClientProfile()
	cpf.HttpProfile.ReqMethod = "POST"
	cpf.HttpProfile.ReqTimeout = 10
	cpf.HttpProfile.Endpoint = "billing.tencentcloudapi.com"

	client, err := billing.NewClient(cred, region, cpf)
	if err != nil {
		return "", "", err
	}

	request := billing.NewDescribeAccountBalanceRequest()
	response, err := client.DescribeAccountBalance(request)
	if err != nil {
		return "", "", err
	}
	if response == nil || response.Response == nil || response.Response.Balance == nil {
		return "", "", fmt.Errorf("empty tencentcloud balance response")
	}

	amount := float64(*response.Response.Balance) / 100.0
	currency := "CNY"
	return fmt.Sprintf("%.2f", amount), currency, nil
}
