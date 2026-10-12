// Package cti holds curated starting points for hunting threat intel on
// X/Twitter: default keywords and known IOC-sharing accounts. Handles and
// hashtags on social media drift over time (renames, suspensions, new
// trends) — treat these as an editable seed list, not a guarantee, and
// prefer -accounts-file to maintain your own list long-term.
package cti

import (
	"bufio"
	"fmt"
	"os"
	"strings"
)

// DefaultKeywords is used when the user doesn't supply -H.
var DefaultKeywords = []string{
	"#malware", "#ioc", "#threatintel", "#opendir", "#c2", "#cobaltstrike",
	"#ransomware", "#phishing", "#apt", "#emotet", "#cti", "#infosec",
	"#0day", "#exploit", "#botnet", "#mitreattack",
}

// DefaultAccounts is used when -accounts is set without -accounts-file.
var DefaultAccounts = []string{
	"abuse_ch",
	"vxunderground",
	"malwrhunterteam",
	"ESETresearch",
	"Unit42_Intel",
	"Cryptolaemus1",
	"GossiTheDog",
	"TheDFIRReport",
	"MsftSecIntel",
}

// BuildKeywordQuery ORs the keywords together as one X search group.
func BuildKeywordQuery(keywords []string) string {
	if len(keywords) == 0 {
		return ""
	}
	return "(" + strings.Join(keywords, " OR ") + ")"
}

// BuildAccountsQuery ORs "from:<handle>" for each account as one search group.
func BuildAccountsQuery(accounts []string) string {
	if len(accounts) == 0 {
		return ""
	}
	parts := make([]string, len(accounts))
	for i, a := range accounts {
		parts[i] = "from:" + strings.TrimPrefix(a, "@")
	}
	return "(" + strings.Join(parts, " OR ") + ")"
}

// LoadAccountsFile reads one handle per line, ignoring blank lines and lines
// starting with '#'.
func LoadAccountsFile(path string) ([]string, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()

	var accounts []string
	scanner := bufio.NewScanner(f)
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		accounts = append(accounts, line)
	}
	return accounts, scanner.Err()
}

// PrintDefaults prints the built-in keyword and account lists for -list-defaults.
func PrintDefaults() {
	fmt.Println("Default keywords (-H):")
	for _, k := range DefaultKeywords {
		fmt.Println("  " + k)
	}
	fmt.Println("\nDefault CTI accounts (-accounts):")
	for _, a := range DefaultAccounts {
		fmt.Println("  @" + a)
	}
	fmt.Println("\nOverride the account list with -accounts-file <path> (one handle per line).")
}
