package cmd

import (
	"context"
	"fmt"
	"os"
	"os/exec"
	"strconv"
	"time"

	"github.com/umair9747/bucky/internal"

	"github.com/spf13/cobra"
)

var (
	accessKey    string
	secretKey    string
	sessionToken string
	region       string
	profile      string
	roleArn      string

	// Global output flags
	jsonOutput bool
	outputFile string

	// Root-level flags for the full workflow (default command)
	rootBucket     string
	rootBucketFile string
	rootWordlist   string
	rootWorkers    int

	updateFlag    bool
	bannerPrinted bool
)

const banner = `
 _                _
| |__  _   _  ___| | ___   _
| '_ \| | | |/ __| |/ / | | | S3 account ID enumeration and bucket discovery tool.
| |_) | |_| | (__|   <| |_| | Developed by Umair Nehri (@umair9747)
|_.__/ \__,_|\___|_|\_\\__, |
                       |___/
`

var rootCmd = &cobra.Command{
	Use:   "bucky [flags]",
	Short: "S3 account ID enumeration and bucket discovery",
	Long: `Enumerates AWS account IDs from S3 buckets using the s3:ResourceAccount
condition key, then discovers additional buckets belonging to that account.

Run bucky with --bucket and --wordlist to execute the full workflow
(enumerate account ID → fuzz for more buckets). Use the 'enum' and 'fuzz'
subcommands for individual phases.`,
	PersistentPreRun: func(cmd *cobra.Command, args []string) {
		printBanner()
	},
	Example: `  # Full workflow — enumerate account ID then fuzz
  bucky --bucket target-bucket --wordlist wordlists/default.txt
  bucky --bucket s3://target-bucket/key --wordlist wordlists/default.txt --workers 20

  # Multiple buckets (comma-separated or from file)
  bucky --bucket bucket1,bucket2,bucket3 --wordlist wordlists/default.txt
  bucky --bucket-file targets.txt --wordlist wordlists/default.txt

  # Accepts full S3 URLs
  bucky --bucket https://mybucket.s3.us-west-2.amazonaws.com/ --wordlist wordlists/default.txt

  # Save results to JSON
  bucky --bucket target-bucket --wordlist wordlists/default.txt --json
  bucky --bucket target-bucket --wordlist wordlists/default.txt --json --output results.json`,
	RunE: func(cmd *cobra.Command, args []string) error {
		if updateFlag {
			return runUpdate()
		}
		if rootBucket == "" && rootBucketFile == "" && rootWordlist == "" {
			return cmd.Help()
		}
		if roleArn == "" {
			fmt.Fprintln(os.Stderr, "[!] --role-arn is required (or set BUCKY_ROLE_ARN)")
			os.Exit(1)
		}
		if rootBucket == "" && rootBucketFile == "" {
			fmt.Fprintln(os.Stderr, "[!] --bucket or --bucket-file is required")
			os.Exit(1)
		}
		if rootWordlist == "" {
			fmt.Fprintln(os.Stderr, "[!] --wordlist is required (or set BUCKY_WORDLIST)")
			os.Exit(1)
		}
		runFull(cmd, args)
		return nil
	},
}

func Execute() error {
	return rootCmd.Execute()
}

func init() {
	// Global AWS credential flags (available to all subcommands)
	rootCmd.PersistentFlags().StringVar(&accessKey, "access-key", os.Getenv("AWS_ACCESS_KEY_ID"), "AWS access key ID (env: AWS_ACCESS_KEY_ID)")
	rootCmd.PersistentFlags().StringVar(&secretKey, "secret-key", os.Getenv("AWS_SECRET_ACCESS_KEY"), "AWS secret access key (env: AWS_SECRET_ACCESS_KEY)")
	rootCmd.PersistentFlags().StringVar(&sessionToken, "session-token", os.Getenv("AWS_SESSION_TOKEN"), "AWS session token (env: AWS_SESSION_TOKEN)")
	rootCmd.PersistentFlags().StringVar(&region, "region", defaultRegion(), "AWS region (env: AWS_REGION)")
	rootCmd.PersistentFlags().StringVar(&profile, "profile", os.Getenv("AWS_PROFILE"), "AWS named profile (env: AWS_PROFILE)")
	rootCmd.PersistentFlags().StringVar(&roleArn, "role-arn", os.Getenv("BUCKY_ROLE_ARN"), "ARN of the role to assume (env: BUCKY_ROLE_ARN)")

	// Global output flags
	rootCmd.PersistentFlags().BoolVar(&jsonOutput, "json", false, "Save results to JSON file")
	rootCmd.PersistentFlags().StringVar(&outputFile, "output", "", "JSON output file path (default: bucky-{uuid}.json)")

	// Update flag
	rootCmd.Flags().BoolVar(&updateFlag, "update", false, "Update bucky to the latest version")

	// Root-level flags for the full workflow
	rootCmd.Flags().StringVar(&rootBucket, "bucket", os.Getenv("BUCKY_BUCKET"), "Target S3 bucket(s), comma-separated (env: BUCKY_BUCKET)")
	rootCmd.Flags().StringVar(&rootBucketFile, "bucket-file", "", "File with bucket names/URLs, one per line")
	rootCmd.Flags().StringVar(&rootWordlist, "wordlist", os.Getenv("BUCKY_WORDLIST"), "Path to wordlist file (env: BUCKY_WORDLIST)")
	rootCmd.Flags().IntVar(&rootWorkers, "workers", envInt("BUCKY_WORKERS", 10), "Concurrent fuzzing workers (env: BUCKY_WORKERS)")
}

func runFull(cmd *cobra.Command, args []string) {
	ctx := context.Background()
	cfg, err := internal.LoadConfig(ctx, newAWSOptions())
	if err != nil {
		fmt.Fprintf(os.Stderr, "[!] Failed to load AWS config: %v\n", err)
		os.Exit(1)
	}

	buckets, err := internal.CollectBuckets(rootBucket, rootBucketFile)
	if err != nil {
		fmt.Fprintf(os.Stderr, "[!] %v\n", err)
		os.Exit(1)
	}
	if len(buckets) == 0 {
		fmt.Fprintln(os.Stderr, "[!] No bucket targets provided")
		os.Exit(1)
	}

	// Phase 1: Enumerate account IDs
	fmt.Fprintf(os.Stderr, "\n=== Phase 1: Account ID Enumeration ===\n")

	type enumResult struct {
		bucket    string
		accountID string
		region    string
	}
	var enumResults []enumResult

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
		enumResults = append(enumResults, enumResult{bucket: b.Name, accountID: accountID, region: r})
	}

	if len(enumResults) == 0 {
		fmt.Fprintln(os.Stderr, "[!] No account IDs discovered")
		os.Exit(1)
	}

	// Deduplicate: group regions by account ID for fuzzing
	type fuzzTarget struct {
		accountID string
		regions   []string
	}
	accountMap := make(map[string]*fuzzTarget)
	for _, r := range enumResults {
		t, ok := accountMap[r.accountID]
		if !ok {
			t = &fuzzTarget{accountID: r.accountID}
			accountMap[r.accountID] = t
		}
		if r.region != "" {
			dup := false
			for _, existing := range t.regions {
				if existing == r.region {
					dup = true
					break
				}
			}
			if !dup {
				t.regions = append(t.regions, r.region)
			}
		}
	}

	// Phase 2: Fuzz per unique account ID
	fmt.Fprintf(os.Stderr, "\n=== Phase 2: Bucket Discovery ===\n")

	// accountID → discovered buckets
	discovered := make(map[string][]string)

	for _, target := range accountMap {
		fmt.Fprintf(os.Stderr, "[*] Fuzzing for account: %s\n", target.accountID)
		err := internal.FuzzBuckets(ctx, cfg, internal.FuzzOptions{
			RoleARN:   roleArn,
			AccountID: target.accountID,
			Wordlist:  rootWordlist,
			Workers:   rootWorkers,
			Regions:   target.regions,
		}, func(b string) {
			discovered[target.accountID] = append(discovered[target.accountID], b)
		})
		if err != nil {
			fmt.Fprintf(os.Stderr, "[!] Fuzzing failed for %s: %v\n", target.accountID, err)
		}
	}

	// Summary
	fmt.Fprintf(os.Stderr, "\n=== Summary ===\n")
	var scanResults []internal.BucketResult
	for _, er := range enumResults {
		found := discovered[er.accountID]
		if found == nil {
			found = []string{}
		}
		scanResults = append(scanResults, internal.BucketResult{
			Bucket:     er.bucket,
			AccountID:  er.accountID,
			Region:     er.region,
			Discovered: found,
		})

		fmt.Fprintf(os.Stderr, "Bucket     : %s\n", er.bucket)
		fmt.Fprintf(os.Stderr, "Account ID : %s\n", er.accountID)
		if er.region != "" {
			fmt.Fprintf(os.Stderr, "Region     : %s\n", er.region)
		}
		if len(found) > 0 {
			fmt.Fprintf(os.Stderr, "Discovered : %d bucket(s)\n", len(found))
			for _, b := range found {
				fmt.Fprintf(os.Stderr, "             - %s\n", b)
			}
		} else {
			fmt.Fprintf(os.Stderr, "Discovered : 0 additional buckets\n")
		}
		if len(enumResults) > 1 {
			fmt.Fprintln(os.Stderr)
		}
	}

	// JSON output
	writeJSONIfEnabled(scanResults)
}

func runUpdate() error {
	fmt.Fprintln(os.Stderr, "[*] Updating bucky to the latest version...")
	cmd := exec.Command("go", "install", "github.com/umair9747/bucky@latest")
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	if err := cmd.Run(); err != nil {
		return fmt.Errorf("update failed: %w", err)
	}
	fmt.Fprintln(os.Stderr, "[+] bucky updated successfully")
	return nil
}

func writeJSONIfEnabled(results []internal.BucketResult) {
	if !jsonOutput && outputFile == "" {
		return
	}
	path := outputFile
	if path == "" {
		path = internal.GenerateOutputPath()
	}
	out := internal.ScanOutput{
		Timestamp: time.Now().UTC().Format(time.RFC3339),
		Results:   results,
	}
	if err := internal.WriteJSON(path, out); err != nil {
		fmt.Fprintf(os.Stderr, "[!] Failed to write JSON: %v\n", err)
		return
	}
	fmt.Fprintf(os.Stderr, "[*] Results saved to %s\n", path)
}

func newAWSOptions() internal.AWSOptions {
	return internal.AWSOptions{
		AccessKey:    accessKey,
		SecretKey:    secretKey,
		SessionToken: sessionToken,
		Region:       region,
		Profile:      profile,
	}
}

func defaultRegion() string {
	if r := os.Getenv("AWS_REGION"); r != "" {
		return r
	}
	if r := os.Getenv("AWS_DEFAULT_REGION"); r != "" {
		return r
	}
	return "us-east-1"
}

func printBanner() {
	if bannerPrinted {
		return
	}
	bannerPrinted = true
	fmt.Fprint(os.Stderr, banner)
	internal.CheckForUpdate()
}

func envInt(key string, fallback int) int {
	v := os.Getenv(key)
	if v == "" {
		return fallback
	}
	n, err := strconv.Atoi(v)
	if err != nil {
		return fallback
	}
	return n
}
