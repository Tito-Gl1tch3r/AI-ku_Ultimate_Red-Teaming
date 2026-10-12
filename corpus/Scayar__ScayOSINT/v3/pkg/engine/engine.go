/*
Copyright © 2024 github.com/Scayar
ScayOSINT - Next-Generation Email Intelligence Platform
*/
package engine

import (
	"fmt"
	"os"
	"strings"
	"time"

	"github.com/Scayar/ScayOSINT/v3/internal/config"
	. "github.com/Scayar/ScayOSINT/v3/internal/config"
	"github.com/Scayar/ScayOSINT/v3/internal/output"
	"github.com/Scayar/ScayOSINT/v3/internal/runner"
	"github.com/Scayar/ScayOSINT/v3/pkg/verification"
	"github.com/dimiro1/banner"
	"github.com/fatih/color"
	"github.com/mattn/go-colorable"
	"github.com/spf13/cobra"
)

var (
	cfgFile    string
	outputPath string
	silent     bool
	coffee     bool
	menu       bool
	rootCmd    *cobra.Command
)

func init() {
	rootCmd = &cobra.Command{
		Use:     "scayosint [email]",
		Short:   "\n🔍 Next-Generation Email Intelligence Platform",
		Long:    "\nScayOSINT is a powerful email intelligence platform designed for security researchers and cybersecurity professionals.",
		Run:     magic,
		Version: "v3.0.0",
	}

	rootCmd.PersistentFlags().StringVarP(&cfgFile, "config", "c", "", "config file (default is $HOME/.scayosint.yaml)")
	rootCmd.PersistentFlags().StringVarP(&outputPath, "output", "o", "", "output file path")
	rootCmd.PersistentFlags().BoolVarP(&silent, "silent", "s", false, "silent mode (no progress bars)")
	rootCmd.PersistentFlags().BoolVarP(&coffee, "coffee", "", false, "enjoy a coffee break")
	rootCmd.PersistentFlags().BoolVarP(&menu, "menu", "m", false, "show interactive menu")

	template := `{{ .Title "ScayOSINT" "" 2 }}
	{{ .AnsiColor.BrightWhite }}v3.0{{ .AnsiColor.Default }}
	{{ .AnsiColor.BrightCyan }}https://github.com/Scayar/ScayOSINT{{ .AnsiColor.Default }}
	Now: {{ .Now "Monday, 2 Jan 2006" }}`

	banner.InitString(colorable.NewColorableStdout(), true, true, template)
	println()
}

func Start() {
	// Always show menu by default if no arguments are provided
	if len(os.Args) == 1 {
		os.Args = append(os.Args, "--menu")
	}

	err := rootCmd.Execute()
	if err != nil {
		panic(err)
	}
}

func showBanner() {
	banner := `
	███████╗ ██████╗ █████╗ ██╗   ██╗ ██████╗ ███████╗██╗███╗   ██╗████████╗
	██╔════╝██╔════╝██╔══██╗╚██╗ ██╔╝██╔═══██╗██╔════╝██║████╗  ██║╚══██╔══╝
	███████╗██║     ███████║ ╚████╔╝ ██║   ██║███████╗██║██╔██╗ ██║   ██║   
	╚════██║██║     ██╔══██║  ╚██╔╝  ██║   ██║╚════██║██║██║╚██╗██║   ██║   
	███████║╚██████╗██║  ██║   ██║   ╚██████╔╝███████║██║██║ ╚████║   ██║   
	╚══════╝ ╚═════╝╚═╝  ╚═╝   ╚═╝    ╚═════╝ ╚══════╝╚═╝╚═╝  ╚═══╝   ╚═╝   
	`
	fmt.Println(color.CyanString(banner))
	fmt.Println(color.YellowString("🔍 Next-Generation Email Intelligence Platform"))
	fmt.Println(color.GreenString("Developed by Scayar"))
	fmt.Println()
}

func clearScreen() {
	fmt.Print("\033[H\033[2J")
}

func showModernMenu() {
	clearScreen()
	showBanner()

	menuItems := []struct {
		icon  string
		title string
		desc  string
	}{
		{"🔍", "Quick Email Scan", "Perform a basic email analysis"},
		{"🔎", "Full Email Analysis", "Complete email investigation with all services"},
		{"💾", "Save Results", "Save analysis results to a file"},
		{"⚙️", "Configuration", "Manage API keys and settings"},
		{"❓", "Help", "Show help and documentation"},
		{"☕", "Coffee Break", "Take a break with a coffee"},
		{"🚪", "Exit", "Exit the program"},
	}

	fmt.Println(color.CyanString("\n╔════════════════════════════════════════════════════════════╗"))
	fmt.Println(color.CyanString("║                     ScayOSINT Menu                         ║"))
	fmt.Println(color.CyanString("╠════════════════════════════════════════════════════════════╣"))

	for i, item := range menuItems {
		fmt.Printf(color.CyanString("║ ")+color.YellowString("%d. ")+color.GreenString("%s ")+color.WhiteString("%-20s")+color.CyanString("║\n"),
			i+1, item.icon, item.title)
		fmt.Printf(color.CyanString("║    ")+color.WhiteString("%-50s")+color.CyanString("║\n"), item.desc)
		if i < len(menuItems)-1 {
			fmt.Println(color.CyanString("╟────────────────────────────────────────────────────────╢"))
		}
	}

	fmt.Println(color.CyanString("╚════════════════════════════════════════════════════════════╝"))
	fmt.Println()

	var choice string
	fmt.Print(color.GreenString("Enter your choice (1-7): "))
	fmt.Scanln(&choice)

	switch choice {
	case "1":
		clearScreen()
		showBanner()
		fmt.Print(color.GreenString("Enter email address: "))
		var email string
		fmt.Scanln(&email)
		runScan(email, false)
		time.Sleep(2 * time.Second)
		showModernMenu()
	case "2":
		clearScreen()
		showBanner()
		fmt.Print(color.GreenString("Enter email address: "))
		var email string
		fmt.Scanln(&email)
		runScan(email, true)
		time.Sleep(2 * time.Second)
		showModernMenu()
	case "3":
		clearScreen()
		showBanner()
		fmt.Print(color.GreenString("Enter email address: "))
		var email string
		fmt.Scanln(&email)
		fmt.Print(color.GreenString("Enter output file path: "))
		var path string
		fmt.Scanln(&path)
		runScanWithOutput(email, path)
		time.Sleep(2 * time.Second)
		showModernMenu()
	case "4":
		clearScreen()
		showBanner()
		showConfigHelp()
		fmt.Print(color.YellowString("\nPress Enter to return to menu..."))
		fmt.Scanln()
		showModernMenu()
	case "5":
		clearScreen()
		showBanner()
		rootCmd.Help()
		fmt.Print(color.YellowString("\nPress Enter to return to menu..."))
		fmt.Scanln()
		showModernMenu()
	case "6":
		clearScreen()
		showBanner()
		showCoffee()
		time.Sleep(2 * time.Second)
		showModernMenu()
	case "7":
		clearScreen()
		showBanner()
		fmt.Println(color.YellowString("\nThank you for using ScayOSINT!"))
		fmt.Println(color.GreenString("Goodbye! 👋"))
		time.Sleep(1 * time.Second)
		os.Exit(0)
	default:
		fmt.Println(color.RedString("\nInvalid choice! Please try again."))
		time.Sleep(1 * time.Second)
		showModernMenu()
	}
}

func showCoffee() {
	coffee := `
	( (
		) )
	  ........
	  |      |]
	  \      / 
	   '----'

	enjoy your coffee ☕️
	`
	fmt.Println(color.YellowString(coffee))
}

func runScan(email string, full bool) {
	startTime := time.Now()

	verification := verification.New()
	if !verification.Syntax(email) {
		color.Red("Email syntax is not valid! Process stopped.")
		return
	}

	runner := runner.New(email)
	runner.Start()

	if !silent {
		runner.Print()
	}

	duration := time.Since(startTime)
	fmt.Printf(color.GreenString("\nScan completed in %v\n"), duration)
}

func runScanWithOutput(email, path string) {
	startTime := time.Now()

	verification := verification.New()
	if !verification.Syntax(email) {
		color.Red("Email syntax is not valid! Process stopped.")
		return
	}

	runner := runner.New(email)
	runner.Start()

	if !silent {
		runner.Print()
	}

	output := output.New()
	output.SetFilePath(path)
	output.JSON(runner)

	duration := time.Since(startTime)
	fmt.Printf(color.GreenString("\nScan completed in %v\n"), duration)
}

func showConfigHelp() {
	fmt.Println(color.CyanString("\n╔════════════════════════════════════════════════════════════╗"))
	fmt.Println(color.CyanString("║                   Configuration Help                       ║"))
	fmt.Println(color.CyanString("╠════════════════════════════════════════════════════════════╣"))
	fmt.Println(color.CyanString("║ ") + color.YellowString("Create a config file at: $HOME/.scayosint.yaml") + color.CyanString("              ║"))
	fmt.Println(color.CyanString("║ ") + color.YellowString("Or use the --config flag to specify a config file") + color.CyanString("        ║"))
	fmt.Println(color.CyanString("╠════════════════════════════════════════════════════════════╣"))
	fmt.Println(color.CyanString("║ ") + color.GreenString("Example config file:") + color.CyanString("                                    ║"))
	fmt.Println(color.CyanString("╚════════════════════════════════════════════════════════════╝"))
	fmt.Println(color.GreenString(`
services:
  breach_directory_api_key: "your-key-here"
  emailrep_api_key: "your-key-here"
  hunter_api_key: "your-key-here"
  intelx_api_key: "your-key-here"
  haveibeenpwned_api_key: "your-key-here"

settings:
  intelx_max_results: 10
  search_timeout: 30
  output_format: "json"
  save_results: true
  theme: "dark"
  show_progress: true
  verbose_output: false
  encrypt_results: false
  proxy_enabled: false
  proxy_url: ""
`))
}

func magic(cmd *cobra.Command, args []string) {
	showBanner()

	if coffee {
		showCoffee()
		os.Exit(0)
	}

	if menu || len(args) == 0 {
		showModernMenu()
		return
	}

	Cfg = config.New()
	if !Cfg.Exists(cfgFile) {
		showConfigHelp()
		os.Exit(1)
	}

	err := Cfg.Parse(cfgFile)
	if err != nil {
		panic(err)
	}

	email := args[0]
	fmt.Println(color.YellowString("\nTarget Email:"), color.GreenString(email), color.GreenString("✓"))
	fmt.Println()

	runScan(email, false)

	if !strings.EqualFold(outputPath, "") {
		output := output.New()
		output.SetFilePath(outputPath)
		output.JSON(runner.New(email))
	}
}
