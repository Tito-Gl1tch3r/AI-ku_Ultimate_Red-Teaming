package cfni

import (
	"errors"
	"fmt"

	"github.com/aws/smithy-go"
)

func (c *CFNI) Cleanup(bucket string) error {
	policyARN := fmt.Sprintf("arn:aws:iam::%s:policy/%s", c.attackerAccount, c.opts.PolicyName)
	if err := c.iamClient.DetachRolePolicy(c.opts.ExecutionRoleName, policyARN); err != nil {
		var ae smithy.APIError
		if errors.As(err, &ae) && ae.ErrorCode() != "NoSuchEntity" {
			return err
		}
	}

	c.logInfof("Policy detached: %s\n", c.opts.PolicyName)

	if err := c.iamClient.DeleteExecutionRole(c.opts.ExecutionRoleName); err != nil {
		var ae smithy.APIError
		if errors.As(err, &ae) && ae.ErrorCode() != "NoSuchEntity" {
			return err
		}
	}

	c.logInfof("Execution Role deleted: %s\n", c.opts.ExecutionRoleName)

	if err := c.functionClient.DeleteLambdaFunction(c.opts.FunctionName); err != nil {
		var ae smithy.APIError
		if errors.As(err, &ae) && ae.ErrorCode() != "ResourceNotFoundException" {
			return err
		}
	}

	c.logInfof("Lambda Function deleted: %s\n", c.opts.FunctionName)

	if err := c.notificationClient.DeleteBucketNotification(c.opts.NotificationID, bucket); err != nil {
		var ae smithy.APIError
		if errors.As(err, &ae) && ae.ErrorCode() != "NoSuchEntity" {
			return err
		}
	}

	c.logInfof("Bucket Notification deleted: %s\n", c.opts.NotificationID)

	return nil
}
