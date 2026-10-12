package function

import (
	"context"
	"fmt"
	"time"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/service/lambda"
	lambdaTypes "github.com/aws/aws-sdk-go-v2/service/lambda/types"
	"github.com/hupe1980/cfni/pkg/config"
)

type Client struct {
	lambdaClient *lambda.Client
}

func New(cfg *config.Config) *Client {
	return &Client{
		lambdaClient: lambda.NewFromConfig(cfg.AWSConfig),
	}
}

func (c *Client) CreateLambdaFunction(functionName string, handler []byte, roleARN string) (string, error) {
	zipFile, err := c.zipFile(handler)
	if err != nil {
		return "", err
	}

	createFunctionOutput, err := c.lambdaClient.CreateFunction(context.Background(), &lambda.CreateFunctionInput{
		FunctionName: aws.String(functionName),
		Code: &lambdaTypes.FunctionCode{
			ZipFile: zipFile,
		},
		Role:    aws.String(roleARN),
		Handler: aws.String("lambda_function.lambda_handler"),
		Runtime: lambdaTypes.RuntimePython39,
	})
	if err != nil {
		return "", err
	}

	waiter := lambda.NewFunctionActiveV2Waiter(c.lambdaClient)
	if err := waiter.Wait(context.Background(), &lambda.GetFunctionInput{
		FunctionName: createFunctionOutput.FunctionArn,
	}, 20*time.Second); err != nil {
		return "", err
	}

	return aws.ToString(createFunctionOutput.FunctionArn), nil
}

func (c *Client) AddS3Permission(id, functionName, bucket, sourceAccount string) error {
	_, err := c.lambdaClient.AddPermission(context.Background(), &lambda.AddPermissionInput{
		StatementId:   aws.String(id),
		FunctionName:  aws.String(functionName),
		Action:        aws.String("lambda:InvokeFunction"),
		Principal:     aws.String("s3.amazonaws.com"),
		SourceArn:     aws.String(fmt.Sprintf("arn:aws:s3:::%s", bucket)),
		SourceAccount: aws.String(sourceAccount),
	})

	return err
}

func (c *Client) DeleteLambdaFunction(functionName string) error {
	_, err := c.lambdaClient.DeleteFunction(context.Background(), &lambda.DeleteFunctionInput{
		FunctionName: aws.String(functionName),
	})

	return err
}
