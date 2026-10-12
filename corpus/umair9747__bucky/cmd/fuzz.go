package cmd

import (
	"context"
	"fmt"
	"os"
	"regexp"
	"strings"

	"github.com/umair9747/bucky/internal"

	"github.com/spf13/cobra"
)

var fuzzCmd = &cobra.Command{
	Use:   "fuzz",
	Short: "Discover S3 buckets belonging to a specific AWS account ID",
	Example: `  bucky fuzz --account-id 987654321098 --wordlist buckets.txt
  bucky fuzz --account-id 987654321098 --wordlist buckets.txt --workers 20
  bucky fuzz --account-id 987654321098 --wordlist buckets.txt --regions ap-south-1,us-east-1
  bucky fuzz --account-id 987654321098 --wordlist buckets.txt --json`,
	Run: runFuzz,
}

var (
	fuzzAccountID string
	fuzzWordlist  string
	fuzzWorkers   int
	fuzzRegions   string
)

var accountIDPattern = regexp.MustCompile(`^\d{12}$`)

func init() {
	fuzzCmd.Flags().StringVar(&fuzzAccountID, "account-id", os.Getenv("BUCKY_ACCOUNT_ID"), "Target AWS account ID, 12 digits (env: BUCKY_ACCOUNT_ID)")
	fuzzCmd.Flags().StringVar(&fuzzWordlist, "wordlist", os.Getenv("BUCKY_WORDLIST"), "Path to wordlist file (env: BUCKY_WORDLIST)")
	fuzzCmd.Flags().IntVar(&fuzzWorkers, "workers", envInt("BUCKY_WORKERS", 10), "Number of concurrent workers (env: BUCKY_WORKERS)")
	fuzzCmd.Flags().StringVar(&fuzzRegions, "regions", "", "Comma-separated regions for name mutations (e.g. ap-south-1,us-east-1)")
	rootCmd.AddCommand(fuzzCmd)
}

func runFuzz(cmd *cobra.Command, args []string) {
	if roleArn == "" {
		fmt.Fprintln(os.Stderr, "[!] --role-arn is required (or set BUCKY_ROLE_ARN)")
		os.Exit(1)
	}
	if fuzzAccountID == "" {
		fmt.Fprintln(os.Stderr, "[!] --account-id is required (or set BUCKY_ACCOUNT_ID)")
		os.Exit(1)
	}
	if !accountIDPattern.MatchString(fuzzAccountID) {
		fmt.Fprintln(os.Stderr, "[!] --account-id must be exactly 12 digits")
		os.Exit(1)
	}
	if fuzzWordlist == "" {
		fmt.Fprintln(os.Stderr, "[!] --wordlist is required (or set BUCKY_WORDLIST)")
		os.Exit(1)
	}

	ctx := context.Background()
	cfg, err := internal.LoadConfig(ctx, newAWSOptions())
	if err != nil {
		fmt.Fprintf(os.Stderr, "[!] Failed to load AWS config: %v\n", err)
		os.Exit(1)
	}

	fmt.Fprintf(os.Stderr, "[*] Fuzzing buckets for account: %s\n", fuzzAccountID)

	var regions []string
	if fuzzRegions != "" {
		for _, r := range strings.Split(fuzzRegions, ",") {
			r = strings.TrimSpace(r)
			if r != "" {
				regions = append(regions, r)
			}
		}
	}

	var results []string
	err = internal.FuzzBuckets(ctx, cfg, internal.FuzzOptions{
		RoleARN:   roleArn,
		AccountID: fuzzAccountID,
		Wordlist:  fuzzWordlist,
		Workers:   fuzzWorkers,
		Regions:   regions,
	}, func(bucket string) {
		results = append(results, bucket)
	})
	if err != nil {
		fmt.Fprintf(os.Stderr, "[!] Fuzzing failed: %v\n", err)
		os.Exit(1)
	}

	if len(results) > 0 {
		fmt.Fprintf(os.Stderr, "\n[+] Discovered %d bucket(s) belonging to account %s:\n", len(results), fuzzAccountID)
		for _, b := range results {
			fmt.Fprintf(os.Stderr, "    - %s\n", b)
		}
	} else {
		fmt.Fprintf(os.Stderr, "\n[-] No additional buckets found\n")
	}

	writeJSONIfEnabled([]internal.BucketResult{
		{
			AccountID:  fuzzAccountID,
			Discovered: results,
		},
	})
}
