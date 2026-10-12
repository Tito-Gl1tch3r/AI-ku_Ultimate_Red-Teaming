// Package ioc extracts indicators of compromise (IPs, domains, hashes, URLs)
// from free-form tweet text, including common "defanged" forms analysts use
// on social media (1.2.3[.]4, example[.]com, hxxps://...).
package ioc

import (
	"regexp"
	"sort"
	"strconv"
	"strings"
	"sync"
	"time"
)

// Match is a single indicator found in one piece of text.
type Match struct {
	Type     string // ip, domain, hash, url
	Subtype  string // hash algorithm (md5/sha1/sha256/sha512); empty otherwise
	Value    string // normalized ("fanged") value, safe to paste into a lookup tool
	Raw      string // the substring exactly as it appeared in the source text
	Defanged bool
}

// Record aggregates a deduplicated indicator across every tweet it was seen in.
type Record struct {
	Match
	FirstSeenAt  time.Time
	SeenCount    int
	FirstURL     string
	FirstAuthor  string
	MatchedQuery string
}

var (
	octet = `(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)`
	sep   = `(?:\.|\[\.\]|\(\.\)|\[dot\])`

	ipRe = regexp.MustCompile(`\b` + octet + sep + octet + sep + octet + sep + octet + `\b`)

	// Ordered longest-first so word boundaries can't let a 64-char hash
	// masquerade as a match for the 32-char alternative.
	hashRe = regexp.MustCompile(`\b[a-fA-F0-9]{128}\b|\b[a-fA-F0-9]{64}\b|\b[a-fA-F0-9]{40}\b|\b[a-fA-F0-9]{32}\b`)

	hashAlgoByLen = map[int]string{32: "md5", 40: "sha1", 64: "sha256", 128: "sha512"}

	// h..ps? tolerates the common "hxxp(s)" defang of the scheme itself;
	// sep (below) tolerates a bracketed/parenthesized dot in the body, so
	// one regex covers both fanged and defanged URLs.
	schemeRe  = `h..ps?`
	urlBodyRe = `[-a-zA-Z0-9@:%._\+~#=]{1,256}` + sep + `[a-zA-Z0-9()]{1,10}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&\/=]*)?`
	urlRe     = regexp.MustCompile(schemeRe + `:\/\/` + urlBodyRe)

	domainLabel = `[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?`
	domainRe    = regexp.MustCompile(`\b` + domainLabel + `(?:` + sep + domainLabel + `){1,}\b`)

	// A curated set of TLDs commonly seen in malicious/C2 infrastructure and
	// mainstream domains alike. Keeps the bare-domain regex from matching
	// every "word.word" pair (sentence endings, version numbers, etc).
	knownTLDs = buildTLDSet([]string{
		"com", "net", "org", "info", "biz", "xyz", "top", "club", "online", "site",
		"tech", "dev", "app", "co", "me", "tv", "cc", "ws", "us", "uk", "de", "fr",
		"nl", "pw", "link", "click", "live", "world", "space", "fun", "icu", "vip",
		"work", "gq", "tk", "ml", "ga", "cf", "ru", "su", "cn", "in", "id", "br",
		"pl", "it", "es", "ch", "io", "ai", "sh", "to", "gg", "la", "vc", "cyou",
		"cam", "monster", "rest", "bond", "sbs", "lol", "quest", "wiki", "life",
		"store", "host", "website", "email", "name", "pro", "mobi", "int", "gov",
		"edu", "onion",
	})
)

func buildTLDSet(list []string) map[string]bool {
	m := make(map[string]bool, len(list))
	for _, t := range list {
		m[t] = true
	}
	return m
}

func normalizeSeparators(s string) string {
	r := strings.NewReplacer("[.]", ".", "(.)", ".", "[dot]", ".")
	return r.Replace(s)
}

// normalizeScheme turns a defanged "hxxp(s)" scheme into a real one so the
// resulting Value is directly usable (e.g. pasted into a sandbox/VT lookup).
func normalizeScheme(s string) string {
	lower := strings.ToLower(s)
	switch {
	case strings.HasPrefix(lower, "hxxps"):
		return "https" + s[len("hxxps"):]
	case strings.HasPrefix(lower, "hxxp"):
		return "http" + s[len("hxxp"):]
	default:
		return s
	}
}

func isDefanged(raw string) bool {
	return strings.ContainsAny(raw, "[(")
}

func isURLDefanged(raw string) bool {
	return isDefanged(raw) || strings.HasPrefix(strings.ToLower(raw), "hxxp")
}

// ExtractAll returns every IOC found in text. URLs are extracted first so
// bare-domain matches that are just a substring of an already-found URL are
// skipped instead of double-reported.
func ExtractAll(text string) []Match {
	var matches []Match
	var urlRaws []string

	for _, raw := range urlRe.FindAllString(text, -1) {
		value := normalizeScheme(normalizeSeparators(raw))
		matches = append(matches, Match{Type: "url", Value: value, Raw: raw, Defanged: isURLDefanged(raw)})
		urlRaws = append(urlRaws, raw)
	}

	for _, raw := range ipRe.FindAllString(text, -1) {
		matches = append(matches, Match{Type: "ip", Value: normalizeSeparators(raw), Raw: raw, Defanged: isDefanged(raw)})
	}

	for _, raw := range hashRe.FindAllString(text, -1) {
		algo := hashAlgoByLen[len(raw)]
		matches = append(matches, Match{Type: "hash", Subtype: algo, Value: strings.ToLower(raw), Raw: raw})
	}

	for _, raw := range domainRe.FindAllString(text, -1) {
		norm := normalizeSeparators(raw)
		labels := strings.Split(norm, ".")
		tld := strings.ToLower(labels[len(labels)-1])
		if !knownTLDs[tld] {
			continue
		}
		if allNumeric(labels) {
			continue // this is an IP, not a domain
		}
		if containedInAny(raw, urlRaws) {
			continue // already reported as part of a URL
		}
		matches = append(matches, Match{Type: "domain", Value: strings.ToLower(norm), Raw: raw, Defanged: isDefanged(raw)})
	}

	return matches
}

func allNumeric(labels []string) bool {
	for _, l := range labels {
		if _, err := strconv.Atoi(l); err != nil {
			return false
		}
	}
	return true
}

func containedInAny(needle string, haystacks []string) bool {
	for _, h := range haystacks {
		if strings.Contains(h, needle) {
			return true
		}
	}
	return false
}

// Store deduplicates matches across many tweets into stable Records.
type Store struct {
	mu      sync.Mutex
	records map[string]*Record
}

func NewStore() *Store {
	return &Store{records: make(map[string]*Record)}
}

func (s *Store) Add(m Match, tweetURL, author string, seenAt time.Time, query string) {
	s.mu.Lock()
	defer s.mu.Unlock()

	key := m.Type + "|" + m.Value
	if rec, ok := s.records[key]; ok {
		rec.SeenCount++
		return
	}
	s.records[key] = &Record{
		Match:        m,
		FirstSeenAt:  seenAt,
		SeenCount:    1,
		FirstURL:     tweetURL,
		FirstAuthor:  author,
		MatchedQuery: query,
	}
}

// All returns every deduplicated record, sorted by type then value for
// stable, diffable output.
func (s *Store) All() []*Record {
	s.mu.Lock()
	defer s.mu.Unlock()

	out := make([]*Record, 0, len(s.records))
	for _, r := range s.records {
		out = append(out, r)
	}
	sort.Slice(out, func(i, j int) bool {
		if out[i].Type != out[j].Type {
			return out[i].Type < out[j].Type
		}
		return out[i].Value < out[j].Value
	})
	return out
}
