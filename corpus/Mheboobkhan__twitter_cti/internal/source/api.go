package source

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strconv"
	"time"
)

// APISource pulls tweets via the official X API v2 recent-search endpoint
// (https://api.twitter.com/2/tweets/search/recent). It's ToS-compliant and
// stable, but recent search requires a paid API plan (the free tier has no
// search read access) and only covers the last 7 days.
type APISource struct {
	bearerToken string
	baseURL     string
	httpClient  *http.Client
}

func NewAPISource(bearerToken string) *APISource {
	return &APISource{
		bearerToken: bearerToken,
		baseURL:     "https://api.twitter.com/2/tweets/search/recent",
		httpClient:  &http.Client{Timeout: 30 * time.Second},
	}
}

type apiResponse struct {
	Data []struct {
		ID        string `json:"id"`
		Text      string `json:"text"`
		AuthorID  string `json:"author_id"`
		CreatedAt string `json:"created_at"`
	} `json:"data"`
	Includes struct {
		Users []struct {
			ID       string `json:"id"`
			Username string `json:"username"`
		} `json:"users"`
	} `json:"includes"`
	Meta struct {
		NextToken string `json:"next_token"`
	} `json:"meta"`
	Title  string `json:"title"`
	Detail string `json:"detail"`
}

func (a *APISource) Search(ctx context.Context, query string, max int) <-chan Result {
	out := make(chan Result)
	go func() {
		defer close(out)

		remaining := max
		nextToken := ""
		for remaining > 0 {
			pageSize := remaining
			if pageSize > 100 {
				pageSize = 100
			}
			if pageSize < 10 {
				pageSize = 10 // X API v2 minimum
			}

			resp, err := a.fetchPage(ctx, query, pageSize, nextToken)
			if err != nil {
				out <- Result{Err: err}
				return
			}

			users := make(map[string]string, len(resp.Includes.Users))
			for _, u := range resp.Includes.Users {
				users[u.ID] = u.Username
			}

			for _, t := range resp.Data {
				created, _ := time.Parse(time.RFC3339, t.CreatedAt)
				username := users[t.AuthorID]
				permalink := ""
				if username != "" {
					permalink = fmt.Sprintf("https://x.com/%s/status/%s", username, t.ID)
				}
				select {
				case out <- Result{Tweet: Tweet{
					ID:        t.ID,
					Text:      t.Text,
					Author:    username,
					CreatedAt: created,
					Permalink: permalink,
				}}:
					remaining--
				case <-ctx.Done():
					return
				}
				if remaining <= 0 {
					break
				}
			}

			if resp.Meta.NextToken == "" || len(resp.Data) == 0 {
				return
			}
			nextToken = resp.Meta.NextToken
		}
	}()
	return out
}

func (a *APISource) fetchPage(ctx context.Context, query string, maxResults int, nextToken string) (*apiResponse, error) {
	u, err := url.Parse(a.baseURL)
	if err != nil {
		return nil, err
	}
	q := u.Query()
	q.Set("query", query)
	q.Set("max_results", strconv.Itoa(maxResults))
	q.Set("tweet.fields", "created_at,author_id")
	q.Set("expansions", "author_id")
	q.Set("user.fields", "username")
	if nextToken != "" {
		q.Set("next_token", nextToken)
	}
	u.RawQuery = q.Encode()

	const maxAttempts = 5
	for attempt := 1; attempt <= maxAttempts; attempt++ {
		req, err := http.NewRequestWithContext(ctx, http.MethodGet, u.String(), nil)
		if err != nil {
			return nil, err
		}
		req.Header.Set("Authorization", "Bearer "+a.bearerToken)

		resp, err := a.httpClient.Do(req)
		if err != nil {
			return nil, err
		}
		body, readErr := io.ReadAll(resp.Body)
		resp.Body.Close()
		if readErr != nil {
			return nil, readErr
		}

		if resp.StatusCode == http.StatusTooManyRequests && attempt < maxAttempts {
			wait := 30 * time.Second
			if ra := resp.Header.Get("Retry-After"); ra != "" {
				if secs, err := strconv.Atoi(ra); err == nil {
					wait = time.Duration(secs) * time.Second
				}
			}
			select {
			case <-time.After(wait):
				continue
			case <-ctx.Done():
				return nil, ctx.Err()
			}
		}

		var parsed apiResponse
		if err := json.Unmarshal(body, &parsed); err != nil {
			return nil, fmt.Errorf("decoding X API response (status %d): %w", resp.StatusCode, err)
		}
		if resp.StatusCode != http.StatusOK {
			if parsed.Detail != "" {
				return nil, fmt.Errorf("X API error (%d): %s", resp.StatusCode, parsed.Detail)
			}
			return nil, fmt.Errorf("X API error (%d): %s", resp.StatusCode, string(body))
		}
		return &parsed, nil
	}
	return nil, fmt.Errorf("X API rate limit retries exhausted")
}
