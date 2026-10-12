package internal

import (
	"bufio"
	"context"
	"fmt"
	"os"
	"strings"
	"sync"
	"sync/atomic"

	"github.com/aws/aws-sdk-go-v2/aws"
)

// FuzzOptions configures the bucket fuzzing operation.
type FuzzOptions struct {
	RoleARN   string
	AccountID string
	Wordlist  string
	Workers   int
	Regions   []string // regions to use for pattern mutations (e.g. from enum phase)
}

// generateCandidate produces the bucket name from a base word using the
// AWS naming pattern: {word}-{accountID}-{region}-an
func generateCandidate(word, accountID, region string) string {
	return word + "-" + accountID + "-" + region + "-an"
}

// FuzzBuckets reads bucket name candidates from a wordlist and checks which ones
// belong to the specified AWS account ID. When Regions is set, each word is expanded
// into multiple candidates using common AWS bucket naming patterns.
// The onFound callback is invoked for each matching bucket.
func FuzzBuckets(ctx context.Context, cfg aws.Config, opts FuzzOptions, onFound func(string)) error {
	file, err := os.Open(opts.Wordlist)
	if err != nil {
		return fmt.Errorf("open wordlist: %w", err)
	}
	defer file.Close()

	// Read all base words
	var baseWords []string
	scanner := bufio.NewScanner(file)
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line != "" && !strings.HasPrefix(line, "#") {
			baseWords = append(baseWords, line)
		}
	}
	if err := scanner.Err(); err != nil {
		return fmt.Errorf("reading wordlist: %w", err)
	}

	// Generate candidates using pattern: {word}-{accountID}-{region}-an
	var candidates []string
	if len(opts.Regions) > 0 {
		for _, word := range baseWords {
			for _, r := range opts.Regions {
				candidates = append(candidates, generateCandidate(word, opts.AccountID, r))
			}
		}
		fmt.Fprintf(os.Stderr, "[*] Loaded %d base words, expanded to %d candidates", len(baseWords), len(candidates))
	} else {
		candidates = baseWords
		fmt.Fprintf(os.Stderr, "[*] Loaded %d candidates from wordlist\n", len(candidates))
	}

	policy := AccountPolicy(opts.AccountID)
	total := len(candidates)
	pb := NewProgressBar(total, 30)

	var (
		wg      sync.WaitGroup
		sem     = make(chan struct{}, opts.Workers)
		checked atomic.Int64
		found   atomic.Int64
	)

	pb.Set(0, fmt.Sprintf("| %d found", 0))

	for _, bucket := range candidates {
		sem <- struct{}{}
		wg.Add(1)
		go func(b string) {
			defer wg.Done()
			defer func() { <-sem }()

			accessible, err := CheckBucketAccess(ctx, cfg, opts.RoleARN, b, "", policy)
			n := checked.Add(1)
			f := found.Load()

			if err == nil && accessible {
				f = found.Add(1)
				pb.PrintAbove(fmt.Sprintf("[+] FOUND: %s", b))
				onFound(b)
			}

			pb.Set(int(n), fmt.Sprintf("| %d found", f))
		}(bucket)
	}

	wg.Wait()

	pb.Finish(fmt.Sprintf("| %d found", found.Load()))
	return nil
}
