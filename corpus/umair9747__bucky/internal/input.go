package internal

import (
	"bufio"
	"fmt"
	"net/url"
	"os"
	"strings"
)

// BucketInput represents a parsed bucket name and optional object key.
type BucketInput struct {
	Name string
	Key  string
}

// CollectBuckets gathers bucket inputs from a comma-separated flag value
// and/or a file with one bucket per line. Supports plain names, s3:// URIs,
// and full HTTPS S3 URLs.
func CollectBuckets(bucketFlag, bucketFile string) ([]BucketInput, error) {
	var inputs []BucketInput

	if bucketFlag != "" {
		for _, b := range strings.Split(bucketFlag, ",") {
			b = strings.TrimSpace(b)
			if b == "" {
				continue
			}
			name, key := ParseS3Path(b)
			inputs = append(inputs, BucketInput{Name: name, Key: key})
		}
	}

	if bucketFile != "" {
		file, err := os.Open(bucketFile)
		if err != nil {
			return nil, fmt.Errorf("open bucket file: %w", err)
		}
		defer file.Close()

		scanner := bufio.NewScanner(file)
		for scanner.Scan() {
			line := strings.TrimSpace(scanner.Text())
			if line == "" || strings.HasPrefix(line, "#") {
				continue
			}
			name, key := ParseS3Path(line)
			inputs = append(inputs, BucketInput{Name: name, Key: key})
		}
		if err := scanner.Err(); err != nil {
			return nil, fmt.Errorf("reading bucket file: %w", err)
		}
	}

	return inputs, nil
}

// ParseS3Path extracts bucket name and optional key from various S3 path formats:
//
//	mybucket
//	s3://mybucket/key
//	https://mybucket.s3.amazonaws.com/key
//	https://mybucket.s3.us-west-2.amazonaws.com/key
//	https://mybucket.s3-us-west-2.amazonaws.com/key
//	https://s3.amazonaws.com/mybucket/key
//	https://s3.us-west-2.amazonaws.com/mybucket/key
func ParseS3Path(path string) (bucket, key string) {
	// Handle HTTPS/HTTP URLs
	if strings.HasPrefix(path, "https://") || strings.HasPrefix(path, "http://") {
		u, err := url.Parse(path)
		if err == nil {
			host := u.Hostname()
			upath := strings.TrimPrefix(u.Path, "/")

			// Virtual-hosted style: mybucket.s3[.region|-region].amazonaws.com
			if idx := strings.Index(host, ".s3"); idx > 0 && strings.HasSuffix(host, ".amazonaws.com") {
				bucket = host[:idx]
				if upath != "" {
					key = upath
				}
				return
			}

			// Path style: s3[.region].amazonaws.com/mybucket
			if strings.HasPrefix(host, "s3") && strings.HasSuffix(host, ".amazonaws.com") {
				parts := strings.SplitN(upath, "/", 2)
				bucket = parts[0]
				if len(parts) > 1 {
					key = parts[1]
				}
				return
			}
		}
	}

	// Handle s3:// prefix
	path = strings.TrimPrefix(path, "s3://")

	parts := strings.SplitN(path, "/", 2)
	bucket = parts[0]
	if len(parts) > 1 {
		key = parts[1]
	}
	return
}
