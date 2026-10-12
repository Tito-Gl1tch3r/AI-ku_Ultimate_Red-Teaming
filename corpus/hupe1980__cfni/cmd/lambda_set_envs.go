package cmd

import (
	"github.com/hupe1980/cfni/pkg/cfni"
	"github.com/spf13/cobra"
)

type lambdaSetEnvsOptions struct {
	attackOptions
	envs map[string]string
}

func newLambdaSetEnvsCmd(globalOpts *globalOptions) *cobra.Command {
	opts := &lambdaSetEnvsOptions{}
	cmd := &cobra.Command{
		Use:           "lambda-set-envs",
		Short:         "Sets lambda environment variables",
		Example:       "cfni lambda-set-envs --attacker-profile ap --bucket-profile bp --bucket pipeline-bucket --s3-access-key-id AKIAXXX --s3-secret-access-key Ey123XXX --env API_URL=https://mitm.org",
		SilenceUsage:  true,
		SilenceErrors: true,
		RunE: func(cmd *cobra.Command, args []string) error {
			c, err := newCFNI(globalOpts)
			if err != nil {
				return err
			}

			s3AccessKey := &cfni.S3AccessKey{
				AccessKeyID:     opts.accessKeyID,
				SecretAccessKey: opts.secretAccessKey,
				SessionToken:    opts.sessionToken,
			}

			handler, err := c.CreateLambdaSetEnvsHandler(&cfni.CreateLambdaSetEnvsOptions{
				Envs:        opts.envs,
				S3AccessKey: s3AccessKey,
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

	cmd.Flags().StringToStringVarP(&opts.envs, "env", "", nil, "lambda environment variable (required)")

	_ = cmd.MarkFlagRequired("env")

	return cmd
}
