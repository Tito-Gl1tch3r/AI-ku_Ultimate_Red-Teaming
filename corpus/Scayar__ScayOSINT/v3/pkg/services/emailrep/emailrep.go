/*
Copyright © 2024 github.com/Scayar
ScayOSINT - Next-Generation Email Intelligence Platform
*/
package emailrep

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"

	"github.com/Scayar/ScayOSINT/v3/internal/config"
	"github.com/Scayar/ScayOSINT/v3/internal/spinner"
	"github.com/fatih/color"
)

type Emailrep struct {
	Response EmailRepResponse
}

type EmailRepResponse struct {
	Email      string `json:"email"`
	Reputation string `json:"reputation"`
	Suspicious bool   `json:"suspicious"`
	References int    `json:"references"`
	Details    struct {
		Blacklisted             bool     `json:"blacklisted"`
		MaliciousActivity       bool     `json:"malicious_activity"`
		MaliciousActivityRecent bool     `json:"malicious_activity_recent"`
		CredentialsLeaked       bool     `json:"credentials_leaked"`
		CredentialsLeakedRecent bool     `json:"credentials_leaked_recent"`
		DataBreach              bool     `json:"data_breach"`
		FirstSeen               string   `json:"first_seen"`
		LastSeen                string   `json:"last_seen"`
		DomainExists            bool     `json:"domain_exists"`
		DomainReputation        string   `json:"domain_reputation"`
		NewDomain               bool     `json:"new_domain"`
		DaysSinceDomainCreation int      `json:"days_since_domain_creation"`
		SuspiciousTld           bool     `json:"suspicious_tld"`
		Spam                    bool     `json:"spam"`
		FreeProvider            bool     `json:"free_provider"`
		Disposable              bool     `json:"disposable"`
		Deliverable             bool     `json:"deliverable"`
		AcceptAll               bool     `json:"accept_all"`
		ValidMx                 bool     `json:"valid_mx"`
		PrimaryMx               string   `json:"primary_mx"`
		Spoofable               bool     `json:"spoofable"`
		SpfStrict               bool     `json:"spf_strict"`
		DmarcEnforced           bool     `json:"dmarc_enforced"`
		Profiles                []string `json:"profiles"`
	} `json:"details"`
}

func New() *Emailrep {
	return &Emailrep{}
}

func (e *Emailrep) Lookup(email string) {
	spinner := spinner.New("Analyzing Email Reputation")
	spinner.Start()

	key := config.Cfg.Services.EmailRepApiKey
	if strings.EqualFold(key, "") {
		spinner.StopFail()
		spinner.SetMessage("EmailRep API Key not configured")
		return
	}

	url := fmt.Sprintf("https://emailrep.io/%s", email)
	req, err := http.NewRequest("GET", url, nil)

	if err != nil {
		spinner.StopFail()
		spinner.SetMessage(err.Error())
		return
	}

	req.Header.Set("Key", key)
	req.Header.Set("User-Agent", "ScayOSINT")
	client := &http.Client{}
	resp, err := client.Do(req)

	if err != nil {
		spinner.StopFail()
		spinner.SetMessage(err.Error())
		return
	}

	body, err := io.ReadAll(resp.Body)

	if err != nil {
		spinner.StopFail()
		spinner.SetMessage(err.Error())
		return
	}

	defer resp.Body.Close()
	var response EmailRepResponse
	json.Unmarshal(body, &response)
	e.Response = response
	spinner.Stop()
}

func (e *Emailrep) Print() {
	key := config.Cfg.Services.EmailRepApiKey
	if strings.EqualFold(key, "") {
		return
	}

	if e.Response.Email == "" {
		return
	}

	fmt.Println("[*] Email Reputation Analysis")
	fmt.Println(color.GreenString("[+]"), "Reputation:", e.Response.Reputation)
	fmt.Println(color.GreenString("[+]"), "Suspicious:", e.Response.Suspicious)
	fmt.Println(color.GreenString("[+]"), "References:", e.Response.References)
	fmt.Println(color.GreenString("[+]"), "First Seen:", e.Response.Details.FirstSeen)
	fmt.Println(color.GreenString("[+]"), "Last Seen:", e.Response.Details.LastSeen)
	fmt.Println(color.GreenString("[+]"), "Domain Reputation:", e.Response.Details.DomainReputation)
	fmt.Println(color.GreenString("[+]"), "Disposable:", e.Response.Details.Disposable)
	fmt.Println(color.GreenString("[+]"), "Free Provider:", e.Response.Details.FreeProvider)
	fmt.Println(color.GreenString("[+]"), "Deliverable:", e.Response.Details.Deliverable)
	fmt.Println(color.GreenString("[+]"), "Valid MX:", e.Response.Details.ValidMx)
	fmt.Println(color.GreenString("[+]"), "SPF Strict:", e.Response.Details.SpfStrict)
	fmt.Println(color.GreenString("[+]"), "DMARC Enforced:", e.Response.Details.DmarcEnforced)
	fmt.Println()
}
