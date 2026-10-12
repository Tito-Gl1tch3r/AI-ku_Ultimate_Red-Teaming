package source

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"os"

	twitterscraper "github.com/n0madic/twitter-scraper"
)

// ScraperSource pulls tweets via an authenticated, unofficial session
// (github.com/n0madic/twitter-scraper). It's free but relies on scraping
// X's frontend, so it can break whenever X changes that frontend and its
// use may fall outside X's terms of service.
type ScraperSource struct {
	scraper *twitterscraper.Scraper
}

// NewScraperSource restores a cached session from cookiesPath, or logs in
// with TWITTER_USERNAME/TWITTER_PASSWORD (and optionally TWITTER_EMAIL /
// TWITTER_2FA_CODE) and caches the resulting session for next time.
func NewScraperSource(cookiesPath string) (*ScraperSource, error) {
	scraper := twitterscraper.New()
	if err := loadSession(scraper, cookiesPath); err != nil {
		return nil, err
	}
	return &ScraperSource{scraper: scraper}, nil
}

func loadSession(scraper *twitterscraper.Scraper, cookiesPath string) error {
	if data, err := os.ReadFile(cookiesPath); err == nil {
		var cookies []*http.Cookie
		if err := json.Unmarshal(data, &cookies); err != nil {
			return fmt.Errorf("parsing cached cookies: %w", err)
		}
		scraper.SetCookies(cookies)
		if scraper.IsLoggedIn() {
			return nil
		}
	}

	username := os.Getenv("TWITTER_USERNAME")
	password := os.Getenv("TWITTER_PASSWORD")
	if username == "" || password == "" {
		return fmt.Errorf("no cached session and TWITTER_USERNAME/TWITTER_PASSWORD are not set")
	}

	credentials := []string{username, password}
	if email := os.Getenv("TWITTER_EMAIL"); email != "" {
		credentials = append(credentials, email)
	}
	if code := os.Getenv("TWITTER_2FA_CODE"); code != "" {
		credentials = append(credentials, code)
	}

	if err := scraper.Login(credentials...); err != nil {
		return fmt.Errorf("login failed: %w", err)
	}

	data, err := json.Marshal(scraper.GetCookies())
	if err != nil {
		return fmt.Errorf("serializing cookies: %w", err)
	}
	if err := os.WriteFile(cookiesPath, data, 0600); err != nil {
		return fmt.Errorf("caching cookies: %w", err)
	}
	return nil
}

func (s *ScraperSource) Search(ctx context.Context, query string, max int) <-chan Result {
	out := make(chan Result)
	go func() {
		defer close(out)
		for tr := range s.scraper.SearchTweets(ctx, query, max) {
			if tr.Error != nil {
				out <- Result{Err: tr.Error}
				continue
			}
			out <- Result{Tweet: Tweet{
				ID:        tr.ID,
				Text:      tr.Text,
				Author:    tr.Username,
				CreatedAt: tr.TimeParsed,
				Permalink: tr.PermanentURL,
			}}
		}
	}()
	return out
}
