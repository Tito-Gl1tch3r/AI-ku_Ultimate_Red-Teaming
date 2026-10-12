package iam

import (
	"context"
	"encoding/json"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/service/iam"
	"github.com/hupe1980/cfni/pkg/config"
)

const (
	awsLambdaBasicExecutionRolePolicyARN = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
)

type Client struct {
	iamClient *iam.Client
}

func New(cfg *config.Config) *Client {
	return &Client{
		iamClient: iam.NewFromConfig(cfg.AWSConfig),
	}
}

// PolicyDocument is our definition of our policies to be uploaded to IAM.
type PolicyDocument struct {
	Version   string            `json:"Version"`
	Statement []PolicyStatement `json:"Statement"`
}

type Principal struct {
	Service string `json:"Service,omitempty"`
}

// PolicyStatement will dictate what this policy will allow or not allow.
type PolicyStatement struct {
	Effect    string    `json:"Effect"`
	Principal Principal `json:"Principal,omitempty"`
	Action    []string  `json:"Action"`
	Resource  []string  `json:"Resource,omitempty"`
}

func (c *Client) CreateExecutionRole(roleName string) (string, error) {
	executionPolicyBytes, err := json.Marshal(&PolicyDocument{
		Version: "2012-10-17",
		Statement: []PolicyStatement{
			{
				Effect: "Allow",
				Principal: Principal{
					Service: "lambda.amazonaws.com",
				},
				Action: []string{"sts:AssumeRole"},
			},
		},
	})
	if err != nil {
		return "", err
	}

	createRoleOutput, err := c.iamClient.CreateRole(context.Background(), &iam.CreateRoleInput{
		RoleName:                 aws.String(roleName),
		AssumeRolePolicyDocument: aws.String(string(executionPolicyBytes)),
	})
	if err != nil {
		return "", err
	}

	if _, err := c.iamClient.AttachRolePolicy(context.Background(), &iam.AttachRolePolicyInput{
		RoleName:  aws.String(roleName),
		PolicyArn: aws.String(awsLambdaBasicExecutionRolePolicyARN),
	}); err != nil {
		return "", err
	}

	return aws.ToString(createRoleOutput.Role.Arn), nil
}

func (c *Client) AttachRolePolicy(roleName, policyName string, policyDoc *PolicyDocument) error {
	policyBytes, err := json.Marshal(policyDoc)
	if err != nil {
		return err
	}

	createPolicyOutput, err := c.iamClient.CreatePolicy(context.Background(), &iam.CreatePolicyInput{
		PolicyName:     aws.String(policyName),
		PolicyDocument: aws.String(string(policyBytes)),
	})
	if err != nil {
		return err
	}

	if _, err := c.iamClient.AttachRolePolicy(context.Background(), &iam.AttachRolePolicyInput{
		RoleName:  aws.String(roleName),
		PolicyArn: createPolicyOutput.Policy.Arn,
	}); err != nil {
		return err
	}

	return nil
}

func (c *Client) DeleteExecutionRole(roleName string) error {
	if _, err := c.iamClient.DetachRolePolicy(context.Background(), &iam.DetachRolePolicyInput{
		RoleName:  aws.String(roleName),
		PolicyArn: aws.String(awsLambdaBasicExecutionRolePolicyARN),
	}); err != nil {
		return err
	}

	if _, err := c.iamClient.DeleteRole(context.Background(), &iam.DeleteRoleInput{
		RoleName: aws.String(roleName),
	}); err != nil {
		return err
	}

	return nil
}

func (c *Client) DetachRolePolicy(roleName, policyARN string) error {
	if _, err := c.iamClient.DetachRolePolicy(context.Background(), &iam.DetachRolePolicyInput{
		RoleName:  aws.String(roleName),
		PolicyArn: aws.String(policyARN),
	}); err != nil {
		return err
	}

	if _, err := c.iamClient.DeletePolicy(context.Background(), &iam.DeletePolicyInput{
		PolicyArn: aws.String(policyARN),
	}); err != nil {
		return err
	}

	return nil
}
