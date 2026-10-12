package internal

import (
	"context"
	"fmt"
	"os"
	"strings"

	"github.com/aws/aws-sdk-go-v2/aws"
)

// EnumerateAccountID discovers the 12-digit AWS account ID that owns the given
// S3 bucket by testing the s3:ResourceAccount condition key digit by digit.
//
// The role must have s3:GetObject or s3:ListBucket permissions on the target bucket.
// Each digit position (0-9) is tested sequentially until the correct digit is found.
// Displays a dynamic progress bar on stderr during enumeration.
func EnumerateAccountID(ctx context.Context, cfg aws.Config, roleArn, bucket, key string) (string, error) {
	fmt.Fprintf(os.Stderr, "[*] Verifying access to bucket: %s\n", bucket)
	accessible, err := CheckBucketAccess(ctx, cfg, roleArn, bucket, key, "")
	if err != nil {
		return "", fmt.Errorf("baseline access check failed: %w", err)
	}
	if !accessible {
		return "", fmt.Errorf("role %s cannot access bucket %s — ensure the role has s3:ListBucket or s3:GetObject permissions", roleArn, bucket)
	}
	fmt.Fprintf(os.Stderr, "[+] Access confirmed\n")

	if region := GetCachedBucketRegion(bucket); region != "" {
		fmt.Fprintf(os.Stderr, "[+] Bucket region: %s\n", region)
	}

	fmt.Fprintf(os.Stderr, "[*] Enumerating account ID...\n")

	pb := NewProgressBar(12, 30)
	digits := ""
	remaining := strings.Repeat("?", 12)
	pb.Set(0, "| "+remaining)

	for pos := 0; pos < 12; pos++ {
		found := false
		for d := 0; d <= 9; d++ {
			test := fmt.Sprintf("%s%d", digits, d)
			policy := EnumPolicy(test)

			ok, err := CheckBucketAccess(ctx, cfg, roleArn, bucket, key, policy)
			if err != nil {
				fmt.Fprintln(os.Stderr)
				return "", fmt.Errorf("error at position %d, digit %d: %w", pos+1, d, err)
			}
			if ok {
				digits = test
				display := digits + strings.Repeat("?", 12-len(digits))
				pb.Set(pos+1, "| "+display)
				found = true
				break
			}
		}
		if !found {
			fmt.Fprintln(os.Stderr)
			return "", fmt.Errorf("could not determine digit at position %d (partial: %s)", pos+1, digits)
		}
	}

	pb.Finish("| " + digits)
	return digits, nil
}
