package mod

import (
	"fmt"
	"time"

	"github.com/aws/aws-sdk-go/aws"
	"github.com/aws/aws-sdk-go/aws/credentials"
	"github.com/aws/aws-sdk-go/aws/session"
	"github.com/aws/aws-sdk-go/service/costexplorer"
)

// QueryAWSBill queries AWS current month bill via Cost Explorer API
func QueryAWSBill(accessKey string, secretKey string, region string) (string, string, error) {
	if accessKey == "" || secretKey == "" {
		return "", "", fmt.Errorf("missing AWS access key or secret")
	}

	if region == "" {
		region = "us-east-1"
	}

	sess, err := session.NewSession(&aws.Config{
		Region:      aws.String(region),
		Credentials: credentials.NewStaticCredentials(accessKey, secretKey, ""),
	})
	if err != nil {
		return "", "", err
	}

	ce := costexplorer.New(sess)

	now := time.Now()
	startDate := time.Date(now.Year(), now.Month(), 1, 0, 0, 0, 0, now.Location()).Format("2006-01-02")
	endDate := now.Format("2006-01-02")

	input := &costexplorer.GetCostAndUsageInput{
		TimePeriod: &costexplorer.DateInterval{
			Start: aws.String(startDate),
			End:   aws.String(endDate),
		},
		Granularity: aws.String("MONTHLY"),
		Metrics:     []*string{aws.String("UnblendedCost"), aws.String("AmortizedCost")},
	}

	result, err := ce.GetCostAndUsage(input)
	if err != nil {
		return "", "", err
	}

	if result == nil || len(result.ResultsByTime) == 0 {
		return "0.00", "USD", nil
	}

	var totalAmount float64
	for _, res := range result.ResultsByTime {
		if res.Groups != nil && len(res.Groups) > 0 {
			for _, group := range res.Groups {
				if group.Metrics != nil {
					if metric, ok := group.Metrics["UnblendedCost"]; ok && metric != nil && metric.Amount != nil {
						var amt float64
						fmt.Sscanf(*metric.Amount, "%f", &amt)
						totalAmount += amt
					}
				}
			}
		}
	}

	if totalAmount == 0 {
		for _, res := range result.ResultsByTime {
			if res.Total != nil {
				if metric, ok := res.Total["UnblendedCost"]; ok && metric != nil && metric.Amount != nil {
					var amt float64
					fmt.Sscanf(*metric.Amount, "%f", &amt)
					totalAmount += amt
				}
			}
		}
	}

	return fmt.Sprintf("%.2f", totalAmount), "USD", nil
}

// QueryAWSBalance queries AWS account balance (credits and remaining)
// This is an estimate based on recent usage
func QueryAWSBalance(accessKey string, secretKey string, region string) (string, string, error) {
	amount, currency, err := QueryAWSBill(accessKey, secretKey, region)
	if err != nil {
		return "", "", err
	}
	return amount, currency, nil
}

// AWSBillingInfo represents detailed AWS billing information
type AWSBillingInfo struct {
	StartDate      string             `json:"startDate"`
	EndDate        string             `json:"endDate"`
	TotalAmount    string             `json:"totalAmount"`
	Currency       string             `json:"currency"`
	ServiceDetails []AWSServiceDetail `json:"serviceDetails"`
}

// AWSServiceDetail represents billing for a single service
type AWSServiceDetail struct {
	Service   string `json:"service"`
	Amount    string `json:"amount"`
	Currency  string `json:"currency"`
}

// QueryAWSBillingDetail queries detailed AWS billing by service
func QueryAWSBillingDetail(accessKey string, secretKey string, region string) (AWSBillingInfo, error) {
	var result AWSBillingInfo

	if accessKey == "" || secretKey == "" {
		return result, fmt.Errorf("missing AWS access key or secret")
	}

	if region == "" {
		region = "us-east-1"
	}

	sess, err := session.NewSession(&aws.Config{
		Region:      aws.String(region),
		Credentials: credentials.NewStaticCredentials(accessKey, secretKey, ""),
	})
	if err != nil {
		return result, err
	}

	ce := costexplorer.New(sess)

	now := time.Now()
	startDate := time.Date(now.Year(), now.Month(), 1, 0, 0, 0, 0, now.Location()).Format("2006-01-02")
	endDate := now.Format("2006-01-02")

	input := &costexplorer.GetCostAndUsageInput{
		TimePeriod: &costexplorer.DateInterval{
			Start: aws.String(startDate),
			End:   aws.String(endDate),
		},
		Granularity: aws.String("DAILY"),
		Metrics:     []*string{aws.String("UnblendedCost")},
		GroupBy: []*costexplorer.GroupDefinition{
			{
				Type: aws.String("DIMENSION"),
				Key:  aws.String("SERVICE"),
			},
		},
	}

	resp, err := ce.GetCostAndUsage(input)
	if err != nil {
		return result, err
	}

	result.StartDate = startDate
	result.EndDate = endDate
	result.Currency = "USD"

	if resp == nil || len(resp.ResultsByTime) == 0 {
		result.TotalAmount = "0.00"
		return result, nil
	}

	serviceMap := make(map[string]string)
	var totalAmount float64

	for _, res := range resp.ResultsByTime {
		if res.Groups != nil {
			for _, group := range res.Groups {
				if group.Metrics != nil && group.Metrics["UnblendedCost"] != nil {
					amount := group.Metrics["UnblendedCost"].Amount
					if amount != nil && *amount != "0" {
						serviceName := "Unknown"
						if group.Keys != nil && len(group.Keys) > 0 && group.Keys[0] != nil {
							serviceName = *group.Keys[0]
						}
						current, ok := serviceMap[serviceName]
						var currentVal float64
						if ok {
							fmt.Sscanf(current, "%f", &currentVal)
						}
						var newVal float64
						fmt.Sscanf(*amount, "%f", &newVal)
						totalAmount += newVal
						serviceMap[serviceName] = fmt.Sprintf("%.2f", currentVal+newVal)
					}
				}
			}
		}
	}

	result.TotalAmount = fmt.Sprintf("%.2f", totalAmount)

	for service, amount := range serviceMap {
		result.ServiceDetails = append(result.ServiceDetails, AWSServiceDetail{
			Service:   service,
			Amount:    amount,
			Currency:  "USD",
		})
	}

	return result, nil
}

func init() {
}
