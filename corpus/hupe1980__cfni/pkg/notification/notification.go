package notification

import (
	"context"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/service/s3"
	s3Types "github.com/aws/aws-sdk-go-v2/service/s3/types"
	"github.com/hupe1980/cfni/pkg/config"
)

type Client struct {
	s3Client *s3.Client
}

func New(cfg *config.Config) *Client {
	return &Client{
		s3Client: s3.NewFromConfig(cfg.AWSConfig),
	}
}

func (c *Client) CreateBucketNotification(id, bucket, lambdaFunctionArn string) error {
	_, err := c.s3Client.PutBucketNotificationConfiguration(context.Background(), &s3.PutBucketNotificationConfigurationInput{
		Bucket: aws.String(bucket),
		NotificationConfiguration: &s3Types.NotificationConfiguration{
			LambdaFunctionConfigurations: []s3Types.LambdaFunctionConfiguration{
				{
					Id: aws.String(id),
					Events: []s3Types.Event{
						s3Types.Event("s3:ObjectCreated:*"),
					},
					LambdaFunctionArn: aws.String(lambdaFunctionArn),
				},
			},
		},
	})

	return err
}

func (c *Client) DeleteBucketNotification(id, bucket string) error {
	out, err := c.s3Client.GetBucketNotificationConfiguration(context.Background(), &s3.GetBucketNotificationConfigurationInput{
		Bucket: aws.String(bucket),
	})
	if err != nil {
		return err
	}

	configs := []s3Types.LambdaFunctionConfiguration{}

	for _, cfg := range out.LambdaFunctionConfigurations {
		if aws.ToString(cfg.Id) == id {
			continue
		}

		configs = append(configs, cfg)
	}

	if _, err := c.s3Client.PutBucketNotificationConfiguration(context.Background(), &s3.PutBucketNotificationConfigurationInput{
		Bucket: aws.String(bucket),
		NotificationConfiguration: &s3Types.NotificationConfiguration{
			LambdaFunctionConfigurations: configs,
			EventBridgeConfiguration:     out.EventBridgeConfiguration,
			QueueConfigurations:          out.QueueConfigurations,
			TopicConfigurations:          out.TopicConfigurations,
		},
	}); err != nil {
		return err
	}

	return nil
}
