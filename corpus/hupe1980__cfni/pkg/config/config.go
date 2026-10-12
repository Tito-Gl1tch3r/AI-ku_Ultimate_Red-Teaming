package config

import (
	"context"
	"fmt"

	smithymiddleware "github.com/aws/smithy-go/middleware"
	smithyhttp "github.com/aws/smithy-go/transport/http"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/aws/retry"
	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/credentials/stscreds"
	"github.com/aws/aws-sdk-go-v2/service/sts"
)

const (
	DefaultUserAgent = "cfni"
)

type Config struct {
	// The Amazon Web Services account ID number of the account that owns or contains the calling entity
	Account string

	// ARN associated with the calling entity
	CallerIdentityARN string

	// The unique identifier of the calling entity
	UserID string

	// The SharedConfigProfile that is used
	Profile string

	// The region to send requests to.
	Region string

	// A Config provides service configuration for aws service clients
	AWSConfig aws.Config
}

func NewConfig(account, profile, region, userAgent string) (*Config, error) {
	if userAgent == "" {
		userAgent = DefaultUserAgent
	}

	awsCfg, err := config.LoadDefaultConfig(
		context.TODO(),
		config.WithRegion(region),
		config.WithSharedConfigProfile(profile),
		config.WithAssumeRoleCredentialOptions(func(aro *stscreds.AssumeRoleOptions) {
			aro.TokenProvider = CreateStdinTokenProvider(account)
		}),
		config.WithRetryer(func() aws.Retryer {
			return retry.AddWithMaxAttempts(retry.NewStandard(), 3)
		}),
		config.WithAPIOptions([]func(*smithymiddleware.Stack) error{
			smithyhttp.SetHeaderValue("User-Agent", userAgent),
		}),
	)
	if err != nil {
		return nil, err
	}

	client := sts.NewFromConfig(awsCfg)

	output, err := client.GetCallerIdentity(context.TODO(), &sts.GetCallerIdentityInput{})
	if err != nil {
		return nil, err
	}

	return &Config{
		Account:           aws.ToString(output.Account),
		CallerIdentityARN: aws.ToString(output.Arn),
		UserID:            aws.ToString(output.UserId),
		Profile:           profile,
		AWSConfig:         awsCfg,
		Region:            awsCfg.Region,
	}, nil
}

func CreateStdinTokenProvider(account string) func() (string, error) {
	return func() (string, error) {
		fmt.Printf("Assume Role MFA token code for %s account: ", account)

		var v string
		_, err := fmt.Scanln(&v)

		return v, err
	}
}
