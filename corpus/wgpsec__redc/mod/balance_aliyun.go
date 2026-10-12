package mod

import (
	"fmt"

	"github.com/aliyun/alibaba-cloud-sdk-go/services/bssopenapi"
)

// QueryAliyunBalance queries Aliyun account balance via BSS OpenAPI.
func QueryAliyunBalance(accessKey string, secretKey string, region string) (string, string, error) {
	if accessKey == "" || secretKey == "" {
		return "", "", fmt.Errorf("missing aliyun access key or secret")
	}
	if region == "" {
		region = "cn-hangzhou"
	}

	client, err := bssopenapi.NewClientWithAccessKey(region, accessKey, secretKey)
	if err != nil {
		return "", "", err
	}

	request := bssopenapi.CreateQueryAccountBalanceRequest()
	request.Scheme = "https"

	response, err := client.QueryAccountBalance(request)
	if err != nil {
		return "", "", err
	}
	if response == nil {
		return "", "", fmt.Errorf("empty aliyun balance response")
	}

	amount := response.Data.AvailableAmount
	currency := response.Data.Currency
	if amount == "" {
		return "", "", fmt.Errorf("empty aliyun balance amount")
	}
	if currency == "" {
		currency = "CNY"
	}
	return amount, currency, nil
}
