package main

import (
	"fmt"
	"strings"

	"fyne.io/fyne/v2"
	"fyne.io/fyne/v2/app"
	"fyne.io/fyne/v2/container"
	"fyne.io/fyne/v2/dialog"
	"fyne.io/fyne/v2/widget"
	"github.com/Scayar/ScayOSINT/v3/internal/runner"
	"github.com/Scayar/ScayOSINT/v3/pkg/verification"
)

func main() {
	myApp := app.New()
	myWindow := myApp.NewWindow("ScayOSINT - Email Intelligence Platform")
	myWindow.Resize(fyne.NewSize(800, 600))

	// Create the main content
	content := createMainContent(myWindow)
	myWindow.SetContent(content)
	myWindow.ShowAndRun()
}

func createMainContent(window fyne.Window) fyne.CanvasObject {
	// Create input field
	emailInput := widget.NewEntry()
	emailInput.SetPlaceHolder("Enter email address...")

	// Create results text area
	results := widget.NewMultiLineEntry()
	results.Disable() // Make it read-only

	// Create progress bar
	progress := widget.NewProgressBar()
	progress.Hide()

	// Create status label
	status := widget.NewLabel("Ready")

	// Create scan button
	scanButton := widget.NewButton("Scan Email", func() {
		email := emailInput.Text
		if email == "" {
			dialog.ShowError(fmt.Errorf("Please enter an email address"), window)
			return
		}

		// Validate email
		verifier := verification.New()
		if !verifier.Syntax(email) {
			dialog.ShowError(fmt.Errorf("Invalid email format"), window)
			return
		}

		// Start scan
		progress.Show()
		progress.SetValue(0)
		status.SetText("Scanning...")
		results.SetText("")

		// Run scan in a goroutine
		go func() {
			// Create runner
			r := runner.New(email)

			// Update progress
			progress.SetValue(0.1)
			results.SetText("Starting scan...\n\n")

			// Run the scan
			r.Start()

			// Collect results
			var resultText strings.Builder
			resultText.WriteString("=== Email Analysis Results ===\n\n")

			// Email Reputation
			if r.EmailRepC != nil {
				resultText.WriteString("Email Reputation:\n")
				resultText.WriteString(fmt.Sprintf("Reputation: %s\n", r.EmailRepC.Response.Reputation))
				resultText.WriteString(fmt.Sprintf("Suspicious: %v\n", r.EmailRepC.Response.Suspicious))
				resultText.WriteString(fmt.Sprintf("References: %d\n\n", r.EmailRepC.Response.References))
			}

			// Social Media
			resultText.WriteString("Social Media Presence:\n")
			if r.TwitterC != nil {
				resultText.WriteString(fmt.Sprintf("Twitter: %v\n", r.TwitterC.Exists))
			}
			if r.InstagramC != nil {
				resultText.WriteString(fmt.Sprintf("Instagram: %v\n", r.InstagramC.Exists))
			}
			if r.SpotifyC != nil {
				resultText.WriteString(fmt.Sprintf("Spotify: %v\n", r.SpotifyC.Exists))
			}
			resultText.WriteString("\n")

			// DNS Information
			if r.DnsC != nil {
				resultText.WriteString("DNS Records:\n")
				for _, record := range r.DnsC.Records {
					resultText.WriteString(fmt.Sprintf("%s: %s\n", record.Type, record.Value))
				}
				resultText.WriteString("\n")
			}

			// Location Information
			if r.IpApiC != nil {
				resultText.WriteString("Location Information:\n")
				resultText.WriteString(fmt.Sprintf("IP: %s\n", r.IpApiC.Response.IP))
				resultText.WriteString(fmt.Sprintf("City: %s\n", r.IpApiC.Response.City))
				resultText.WriteString(fmt.Sprintf("Country: %s\n", r.IpApiC.Response.Country))
				resultText.WriteString(fmt.Sprintf("Organization: %s\n\n", r.IpApiC.Response.Org))
			}

			// Update UI
			results.SetText(resultText.String())
			progress.SetValue(1.0)
			status.SetText("Scan completed")
		}()
	})

	// Create save button
	saveButton := widget.NewButton("Save Results", func() {
		if results.Text == "" {
			dialog.ShowError(fmt.Errorf("No results to save"), window)
			return
		}

		dialog.ShowFileSave(func(writer fyne.URIWriteCloser, err error) {
			if err != nil {
				dialog.ShowError(err, window)
				return
			}
			if writer == nil {
				return
			}
			defer writer.Close()

			writer.Write([]byte(results.Text))
			dialog.ShowInformation("Success", "Results saved successfully", window)
		}, window)
	})

	// Create buttons container
	buttons := container.NewHBox(scanButton, saveButton)

	// Create main layout
	mainContent := container.NewVBox(
		widget.NewLabel("ScayOSINT - Email Intelligence Platform"),
		widget.NewSeparator(),
		emailInput,
		buttons,
		progress,
		status,
		widget.NewSeparator(),
		container.NewScroll(results),
	)

	return container.NewPadded(mainContent)
}
