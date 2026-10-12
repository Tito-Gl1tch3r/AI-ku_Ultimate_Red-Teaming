/*
Copyright © 2024 github.com/Scayar
ScayOSINT - Next-Generation Email Intelligence Platform
*/
package haveibeenpwned

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"
	"time"

	"github.com/Scayar/ScayOSINT/v3/internal/config"
	"github.com/Scayar/ScayOSINT/v3/internal/spinner"
	"github.com/fatih/color"
)

type HaveIBeenPwned struct {
	Response HaveIBeenPwnedResponse
}

type HaveIBeenPwnedResponse []struct {
	Name               string    `json:"Name"`
	Title              string    `json:"Title"`
	Domain             string    `json:"Domain"`
	BreachDate         string    `json:"BreachDate"`
	AddedDate          time.Time `json:"AddedDate"`
	ModifiedDate       time.Time `json:"ModifiedDate"`
	PwnCount           int       `json:"PwnCount"`
	Description        string    `json:"Description"`
	LogoPath           string    `json:"LogoPath"`
	DataClasses        []string  `json:"DataClasses"`
	IsVerified         bool      `json:"IsVerified"`
	IsFabricated       bool      `json:"IsFabricated"`
	IsSensitive        bool      `json:"IsSensitive"`
	IsRetired          bool      `json:"IsRetired"`
	IsSpamList         bool      `json:"IsSpamList"`
	IsMalware          bool      `json:"IsMalware"`
	IsSubscriptionFree bool      `json:"IsSubscriptionFree"`
}

func New() *HaveIBeenPwned {
	return &HaveIBeenPwned{}
}

func (h *HaveIBeenPwned) Lookup(email string) {
	spinner := spinner.New("Checking HaveIBeenPwned Database")
	spinner.Start()

	key := config.Cfg.Services.HaveIBeenPwnedApiKey
	if strings.EqualFold(key, "") {
		spinner.Stop()
		spinner.SetMessage("HaveIBeenPwned API Key not configured - skipping check")
		return
	}

	url := fmt.Sprintf("https://haveibeenpwned.com/api/v3/breachedaccount/%s?truncateResponse=false", email)
	req, err := http.NewRequest("GET", url, nil)

	if err != nil {
		spinner.Stop()
		spinner.SetMessage("Error creating request - skipping check")
		return
	}

	req.Header.Set("hibp-api-key", key)
	req.Header.Set("User-Agent", "ScayOSINT")

	client := &http.Client{}
	resp, err := client.Do(req)

	if err != nil {
		spinner.Stop()
		spinner.SetMessage("Error making request - skipping check")
		return
	}

	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)

	if err != nil {
		spinner.Stop()
		spinner.SetMessage("Error reading response - skipping check")
		return
	}

	var response HaveIBeenPwnedResponse
	if err := json.Unmarshal(body, &response); err != nil {
		spinner.Stop()
		spinner.SetMessage("Error parsing response - skipping check")
		return
	}

	h.Response = response
	spinner.Stop()
}

func (h *HaveIBeenPwned) Print() {
	key := config.Cfg.Services.HaveIBeenPwnedApiKey
	if strings.EqualFold(key, "") {
		return
	}

	if len(h.Response) == 0 {
		return
	}

	fmt.Println("[*] HaveIBeenPwned Breach Results")
	for _, v := range h.Response {
		fmt.Println(color.GreenString("[+]"), "Name:", v.Name)
		fmt.Println(color.GreenString("[+]"), "Domain:", v.Domain)
		fmt.Println(color.GreenString("[+]"), "Breach Date:", v.BreachDate)
		fmt.Println(color.GreenString("[+]"), "Compromised Data:")
		for _, d := range v.DataClasses {
			fmt.Println("    -", d)
		}
		fmt.Println()
	}
}
