// Command twitter-cti hunts X/Twitter for cyber threat intel: it searches
// tweets matching a query (or a curated CTI keyword/account list), extracts
// IOCs (IPs, domains, hashes, URLs — including defanged forms), deduplicates
// them, and writes the results as text, JSON, or CSV.
package main

import (
	"context"
	"flag"
	"fmt"
	"os"
	"time"

	"twitter-cti/internal/banner"
	"twitter-cti/internal/cti"
	"twitter-cti/internal/ioc"
	"twitter-cti/internal/output"
	"twitter-cti/internal/source"
)

func main() {
	start := time.Now()

	query := flag.String("H", "", "Keyword/hashtag query, e.g. \"#emotet\". Default: curated CTI keyword list (-list-defaults)")
	noTweets := flag.Int("n", 50, "Number of tweets to fetch")
	path := flag.String("p", "", "Output directory (writable). If empty, results print to stdout")
	format := flag.String("format", "text", "Output format: text, json, or csv")
	backend := flag.String("backend", "scraper", "Tweet source: \"scraper\" (free, session login) or \"api\" (official X API v2, needs a bearer token)")
	cookiesPath := flag.String("c", "cookies.json", "[scraper backend] session cache path")
	bearerToken := flag.String("bearer-token", "", "[api backend] X API v2 bearer token (or set X_BEARER_TOKEN / TWITTER_BEARER_TOKEN)")
	useAccounts := flag.Bool("accounts", false, "Restrict the search to curated CTI accounts (see -list-defaults)")
	accountsFile := flag.String("accounts-file", "", "Newline-delimited file of handles, used instead of the curated CTI account list")
	timeout := flag.Duration("timeout", 2*time.Minute, "Overall timeout for the search")
	listDefaults := flag.Bool("list-defaults", false, "Print the curated default keywords and CTI accounts, then exit")
	noBanner := flag.Bool("no-banner", false, "Suppress the startup banner")
	flag.Parse()

	if !*noBanner {
		fmt.Println(banner.ASCII())
		fmt.Println()
	}

	if *listDefaults {
		cti.PrintDefaults()
		return
	}

	finalQuery, err := buildQuery(*query, *useAccounts, *accountsFile, *backend)
	if err != nil {
		fmt.Fprintln(os.Stderr, "query error:", err)
		os.Exit(1)
	}
	fmt.Println("Searching:", finalQuery)
	if *path == "" {
		fmt.Println("Warning: -p not set, no output file will be created; results print below.")
	}

	src, err := newSource(*backend, *cookiesPath, *bearerToken)
	if err != nil {
		fmt.Fprintln(os.Stderr, "\nError:", err)
		switch *backend {
		case "api":
			fmt.Fprintln(os.Stderr, "Set -bearer-token or the X_BEARER_TOKEN/TWITTER_BEARER_TOKEN environment variable.")
		case "scraper":
			fmt.Fprintln(os.Stderr, "Set TWITTER_USERNAME and TWITTER_PASSWORD (and optionally TWITTER_EMAIL / TWITTER_2FA_CODE) environment variables, then re-run.")
		}
		os.Exit(1)
	}

	ctx, cancel := context.WithTimeout(context.Background(), *timeout)
	defer cancel()

	store := ioc.NewStore()
	scanned := 0
	for res := range src.Search(ctx, finalQuery, *noTweets) {
		if res.Err != nil {
			fmt.Fprintln(os.Stderr, "warning:", res.Err)
			continue
		}
		scanned++
		for _, m := range ioc.ExtractAll(res.Tweet.Text) {
			store.Add(m, res.Tweet.Permalink, res.Tweet.Author, res.Tweet.CreatedAt, finalQuery)
		}
	}

	records := store.All()
	if err := output.Write(*format, *path, records); err != nil {
		fmt.Fprintln(os.Stderr, "output error:", err)
		os.Exit(1)
	}

	fmt.Printf("\nScanned %d tweets, extracted %d unique IOC(s) in %s\n", scanned, len(records), time.Since(start))
}

// buildQuery composes the final search query from the user's keyword query
// (or the curated defaults) and, optionally, a curated/custom account list.
// The retweet-exclusion operator differs between the legacy search syntax
// the scraper uses and the official API v2 syntax.
func buildQuery(userQuery string, useAccounts bool, accountsFile, backend string) (string, error) {
	keywordPart := userQuery
	if keywordPart == "" {
		keywordPart = cti.BuildKeywordQuery(cti.DefaultKeywords)
	}

	parts := []string{}
	if useAccounts {
		accounts := cti.DefaultAccounts
		if accountsFile != "" {
			loaded, err := cti.LoadAccountsFile(accountsFile)
			if err != nil {
				return "", fmt.Errorf("reading -accounts-file: %w", err)
			}
			accounts = loaded
		}
		if accountsPart := cti.BuildAccountsQuery(accounts); accountsPart != "" {
			parts = append(parts, accountsPart)
		}
	}
	if keywordPart != "" {
		parts = append(parts, keywordPart)
	}

	retweetFilter := "-filter:retweets"
	if backend == "api" {
		retweetFilter = "-is:retweet"
	}
	parts = append(parts, retweetFilter)

	query := parts[0]
	for _, p := range parts[1:] {
		query += " " + p
	}
	return query, nil
}

func newSource(backend, cookiesPath, bearerToken string) (source.Source, error) {
	switch backend {
	case "scraper":
		return source.NewScraperSource(cookiesPath)
	case "api":
		if bearerToken == "" {
			bearerToken = os.Getenv("X_BEARER_TOKEN")
		}
		if bearerToken == "" {
			bearerToken = os.Getenv("TWITTER_BEARER_TOKEN")
		}
		if bearerToken == "" {
			return nil, fmt.Errorf("no bearer token supplied")
		}
		return source.NewAPISource(bearerToken), nil
	default:
		return nil, fmt.Errorf("unknown -backend %q (want scraper or api)", backend)
	}
}
