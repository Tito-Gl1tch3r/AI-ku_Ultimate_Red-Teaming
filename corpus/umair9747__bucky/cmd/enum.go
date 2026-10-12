package cmd

import (
	"context"
	"fmt"
	"os"

	"github.com/umair9747/bucky/internal"

	"github.com/spf13/cobra"
)

var enumCmd = &cobra.Command{
	Use:   "enum",
	Short: "Enumerate the AWS account ID that owns an S3 bucket",
	Example: `  bucky enum --bucket target-bucket
  bucky enum --bucket s3://target-bucket/index.html
  bucky enum --bucket https://mybucket.s3.us-west-2.amazonaws.com/
  bucky enum --bucket bucket1,bucket2,bucket3
  bucky enum --bucket-file targets.txt
  bucky enum --bucket target-bucket --json`,
	Run: runEnum,
}

var (
	enumBucket     string
	enumBucketFile string
)

func init() {
	enumCmd.Flags().StringVar(&enumBucket, "bucket", os.Getenv("BUCKY_BUCKET"), "Target S3 bucket(s), comma-separated (env: BUCKY_BUCKET)")
	enumCmd.Flags().StringVar(&enumBucketFile, "bucket-file", "", "File with bucket names/URLs, one per line")
	rootCmd.AddCommand(enumCmd)
}

func runEnum(cmd *cobra.Command, args []string) {
	if roleArn == "" {
		fmt.Fprintln(os.Stderr, "[!] --role-arn is required (or set BUCKY_ROLE_ARN)")
		os.Exit(1)
	}
	if enumBucket == "" && enumBucketFile == "" {
		fmt.Fprintln(os.Stderr, "[!] --bucket or --bucket-file is required")
		os.Exit(1)
	}

	ctx := context.Background()
	cfg, err := internal.LoadConfig(ctx, newAWSOptions())
	if err != nil {
		fmt.Fprintf(os.Stderr, "[!] Failed to load AWS config: %v\n", err)
		os.Exit(1)
	}

	buckets, err := internal.CollectBuckets(enumBucket, enumBucketFile)
	if err != nil {
		fmt.Fprintf(os.Stderr, "[!] %v\n", err)
		os.Exit(1)
	}
	if len(buckets) == 0 {
		fmt.Fprintln(os.Stderr, "[!] No bucket targets provided")
		os.Exit(1)
	}

	var scanResults []internal.BucketResult

	for i, b := range buckets {
		if len(buckets) > 1 {
			fmt.Fprintf(os.Stderr, "\n--- Bucket %d/%d: %s ---\n", i+1, len(buckets), b.Name)
		}
		accountID, err := internal.EnumerateAccountID(ctx, cfg, roleArn, b.Name, b.Key)
		if err != nil {
			fmt.Fprintf(os.Stderr, "[!] Failed for %s: %v\n", b.Name, err)
			continue
		}
		r := internal.GetCachedBucketRegion(b.Name)
		fmt.Fprintf(os.Stderr, "\n[+] Account ID: %s\n", accountID)

		scanResults = append(scanResults, internal.BucketResult{
			Bucket:     b.Name,
			AccountID:  accountID,
			Region:     r,
			Discovered: []string{},
		})
	}

	writeJSONIfEnabled(scanResults)
}
