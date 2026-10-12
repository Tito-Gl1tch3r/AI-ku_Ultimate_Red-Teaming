package internal

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"sync"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/credentials"
	"github.com/aws/aws-sdk-go-v2/service/s3"
	"github.com/aws/aws-sdk-go-v2/service/sts"
	smithyhttp "github.com/aws/smithy-go/transport/http"
)

// bucketRegionCache stores discovered bucket regions to avoid repeated lookups.
var (
	bucketRegionCache   = make(map[string]string)
	bucketRegionCacheMu sync.RWMutex
)

// AWSOptions holds configuration for creating an AWS session.
type AWSOptions struct {
	AccessKey    string
	SecretKey    string
	SessionToken string
	Region       string
	Profile      string
}

// policyDocument represents an IAM policy for inline session policies.
type policyDocument struct {
	Version   string            `json:"Version"`
	Statement []policyStatement `json:"Statement"`
}

type policyStatement struct {
	Effect    string                         `json:"Effect"`
	Action    string                         `json:"Action"`
	Resource  string                         `json:"Resource"`
	Condition map[string]map[string][]string `json:"Condition"`
}

// LoadConfig creates an AWS config from the provided options.
// Falls back to the default credential chain if no explicit credentials are given.
func LoadConfig(ctx context.Context, opts AWSOptions) (aws.Config, error) {
	cfgOpts := []func(*config.LoadOptions) error{
		config.WithRegion(opts.Region),
	}

	if opts.AccessKey != "" && opts.SecretKey != "" {
		cfgOpts = append(cfgOpts, config.WithCredentialsProvider(
			credentials.NewStaticCredentialsProvider(opts.AccessKey, opts.SecretKey, opts.SessionToken),
		))
	} else if opts.Profile != "" {
		cfgOpts = append(cfgOpts, config.WithSharedConfigProfile(opts.Profile))
	}

	return config.LoadDefaultConfig(ctx, cfgOpts...)
}

// CheckBucketAccess assumes the given role (optionally with an inline policy)
// and attempts to access the S3 bucket. Returns true if access is granted.
// Automatically handles 301 redirects by detecting the bucket's region.
func CheckBucketAccess(ctx context.Context, cfg aws.Config, roleArn, bucket, key, policy string) (bool, error) {
	stsClient := sts.NewFromConfig(cfg)

	input := &sts.AssumeRoleInput{
		RoleArn:         aws.String(roleArn),
		RoleSessionName: aws.String("bucky"),
	}
	if policy != "" {
		input.Policy = aws.String(policy)
	}

	result, err := stsClient.AssumeRole(ctx, input)
	if err != nil {
		return false, fmt.Errorf("assume role: %w", err)
	}

	creds := credentials.NewStaticCredentialsProvider(
		*result.Credentials.AccessKeyId,
		*result.Credentials.SecretAccessKey,
		*result.Credentials.SessionToken,
	)

	// Use cached region if we've seen this bucket before, otherwise start with cfg region
	region := GetCachedBucketRegion(bucket)
	s3Client := s3.NewFromConfig(cfg, func(o *s3.Options) {
		o.Credentials = creds
		if region != "" {
			o.Region = region
		}
	})

	ok, err := checkAccess(ctx, s3Client, bucket, key)
	if err == nil {
		return ok, nil
	}

	// On 301 (MovedPermanently), detect the real region and retry
	if isHTTPError(err, 301) {
		realRegion, regionErr := detectBucketRegion(ctx, cfg, creds, bucket)
		if regionErr != nil {
			return false, fmt.Errorf("bucket in different region, detection failed: %w", regionErr)
		}
		setCachedBucketRegion(bucket, realRegion)

		s3Client = s3.NewFromConfig(cfg, func(o *s3.Options) {
			o.Credentials = creds
			o.Region = realRegion
		})
		return checkAccess(ctx, s3Client, bucket, key)
	}

	return false, err
}

// checkAccess performs HeadObject (if key given) then HeadBucket against the S3 client.
func checkAccess(ctx context.Context, s3Client *s3.Client, bucket, key string) (bool, error) {
	if key != "" {
		_, err := s3Client.HeadObject(ctx, &s3.HeadObjectInput{
			Bucket: aws.String(bucket),
			Key:    aws.String(key),
		})
		if err == nil {
			return true, nil
		}
		if !isHTTPError(err, 403, 404) {
			return false, fmt.Errorf("head object: %w", err)
		}
	}

	_, err := s3Client.HeadBucket(ctx, &s3.HeadBucketInput{
		Bucket: aws.String(bucket),
	})
	if err == nil {
		return true, nil
	}
	if isHTTPError(err, 403, 404) {
		return false, nil
	}
	return false, fmt.Errorf("head bucket: %w", err)
}

// detectBucketRegion discovers a bucket's region by making a raw HTTP HEAD
// request to https://<bucket>.s3.amazonaws.com and reading the
// x-amz-bucket-region response header. This header is returned on all
// responses (200, 301, 403, 404) regardless of credentials.
func detectBucketRegion(_ context.Context, _ aws.Config, _ aws.CredentialsProvider, bucket string) (string, error) {
	client := &http.Client{
		CheckRedirect: func(req *http.Request, via []*http.Request) error {
			return http.ErrUseLastResponse // don't follow redirects
		},
	}

	resp, err := client.Head(fmt.Sprintf("https://%s.s3.amazonaws.com", bucket))
	if err != nil {
		return "", fmt.Errorf("region detection request failed: %w", err)
	}
	resp.Body.Close()

	region := resp.Header.Get("x-amz-bucket-region")
	if region != "" {
		return region, nil
	}

	return "", fmt.Errorf("x-amz-bucket-region header not present in response (status %d)", resp.StatusCode)
}

// GetCachedBucketRegion returns the cached region for a bucket, or "" if not yet detected.
func GetCachedBucketRegion(bucket string) string {
	bucketRegionCacheMu.RLock()
	defer bucketRegionCacheMu.RUnlock()
	return bucketRegionCache[bucket]
}

func setCachedBucketRegion(bucket, region string) {
	bucketRegionCacheMu.Lock()
	defer bucketRegionCacheMu.Unlock()
	bucketRegionCache[bucket] = region
}

// EnumPolicy generates an IAM inline policy that restricts S3 access
// to accounts whose ID starts with the given prefix (using StringLike with wildcard).
func EnumPolicy(prefix string) string {
	doc := policyDocument{
		Version: "2012-10-17",
		Statement: []policyStatement{
			{
				Effect:   "Allow",
				Action:   "s3:*",
				Resource: "*",
				Condition: map[string]map[string][]string{
					"StringLike": {
						"s3:ResourceAccount": {prefix + "*"},
					},
				},
			},
		},
	}
	b, _ := json.Marshal(doc)
	return string(b)
}

// AccountPolicy generates an IAM inline policy that restricts S3 access
// to a specific account ID (exact match using StringEquals).
func AccountPolicy(accountID string) string {
	doc := policyDocument{
		Version: "2012-10-17",
		Statement: []policyStatement{
			{
				Effect:   "Allow",
				Action:   "s3:*",
				Resource: "*",
				Condition: map[string]map[string][]string{
					"StringEquals": {
						"s3:ResourceAccount": {accountID},
					},
				},
			},
		},
	}
	b, _ := json.Marshal(doc)
	return string(b)
}

// isHTTPError checks if the error is an HTTP response error matching any of the given status codes.
func isHTTPError(err error, codes ...int) bool {
	var re *smithyhttp.ResponseError
	if errors.As(err, &re) {
		for _, code := range codes {
			if re.HTTPStatusCode() == code {
				return true
			}
		}
	}
	return false
}
