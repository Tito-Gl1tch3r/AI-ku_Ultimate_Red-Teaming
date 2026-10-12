package cmd

import (
	"fmt"
	"log"
	"os"

	"github.com/hupe1980/cfni/pkg/cfni"
	"github.com/hupe1980/cfni/pkg/config"
	"github.com/hupe1980/golog"
	"github.com/spf13/cobra"
)

func PrintLogo() {
	fmt.Fprint(os.Stderr, ` 
  ██████ ███████ ███    ██ ██ 
 ██      ██      ████   ██  
 ██      █████   ██ ██  ██ ██ 
 ██      ██      ██  ██ ██ ██ 
  ██████ ██      ██   ████ ██ `, "\n\n")
}

func Execute(version string) {
	PrintLogo()

	rootCmd := newRootCmd(version)
	if err := rootCmd.Execute(); err != nil {
		log.Println(golog.ERROR, err)
		os.Exit(1)
	}
}

type globalOptions struct {
	attackerProfile string
	attackerRegion  string
	bucketProfile   string
	bucketRegion    string
	userAgent       string
}

func newRootCmd(version string) *cobra.Command {
	globalOpts := &globalOptions{}

	cmd := &cobra.Command{
		Use:           "cfni",
		Version:       version,
		Short:         "cfni is a proof-of-concept to demonstrate an attack on the aws cdk pipeline",
		SilenceErrors: true,
	}

	cmd.PersistentFlags().StringVarP(&globalOpts.attackerProfile, "attacker-profile", "", "", "attacker AWS profile")
	cmd.PersistentFlags().StringVarP(&globalOpts.attackerRegion, "attacker-region", "", "", "attacker AWS region")
	cmd.PersistentFlags().StringVarP(&globalOpts.bucketProfile, "bucket-profile", "", "", "bucket AWS profile")
	cmd.PersistentFlags().StringVarP(&globalOpts.bucketRegion, "bucket-region", "", "", "bucket AWS region")
	cmd.PersistentFlags().StringVarP(&globalOpts.userAgent, "user-agent", "A", config.DefaultUserAgent, "user-agent to use for sdk calls")

	cmd.AddCommand(
		newCFNCodeExecutionCmd(globalOpts),
		newCleanupCmd(globalOpts),
		newIAMRoleBackdoorCmd(globalOpts),
		newLambdaExfiltrationCmd(globalOpts),
		newLambdaSetEnvsCmd(globalOpts),
	)

	return cmd
}

func newCFNI(globalOpts *globalOptions) (*cfni.CFNI, error) {
	log := &logger{}

	attackerConfig, err := config.NewConfig("attacker", globalOpts.attackerProfile, globalOpts.attackerRegion, globalOpts.userAgent)
	if err != nil {
		return nil, err
	}

	log.Printf(golog.INFO, "Attacker account: %s [%s]\n", attackerConfig.Account, attackerConfig.Region)

	bucketConfig := attackerConfig
	if globalOpts.attackerProfile != globalOpts.bucketProfile {
		bucketConfig, err = config.NewConfig("bucket", globalOpts.bucketProfile, globalOpts.bucketRegion, globalOpts.userAgent)
		if err != nil {
			return nil, err
		}
	}

	log.Printf(golog.INFO, "Bucket account: %s [%s]\n", bucketConfig.Account, bucketConfig.Region)

	cfni := cfni.New(attackerConfig, bucketConfig, func(o *cfni.Options) {
		o.Logger = log
	})

	return cfni, nil
}

type attackOptions struct {
	bucket string

	// S3 Access Key
	accessKeyID     string
	secretAccessKey string
	sessionToken    string

	// Filter
	environments []string
	stackNames   []string
}

func addAttackCommands(cmd *cobra.Command, opts *attackOptions) {
	cmd.Flags().StringVarP(&opts.bucket, "bucket", "b", "", "bucket name (required)")
	_ = cmd.MarkPersistentFlagRequired("bucket")

	cmd.Flags().StringVarP(&opts.accessKeyID, "s3-access-key-id", "", "", "s3 access key id")
	cmd.Flags().StringVarP(&opts.secretAccessKey, "s3-secret-access-key", "", "", "s3 secret access key")
	cmd.Flags().StringVarP(&opts.sessionToken, "s3-session-token", "", "", "s3 session token")

	cmd.Flags().StringSliceVarP(&opts.environments, "environment", "", nil, "filter environments (default all environments)")
	cmd.Flags().StringSliceVarP(&opts.stackNames, "stack", "", nil, "filter stacks (default all stacks)")
}
