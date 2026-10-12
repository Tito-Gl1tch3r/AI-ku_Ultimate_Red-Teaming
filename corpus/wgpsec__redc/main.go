package main

import (
	"embed"
	"fmt"
	"os"
	"os/signal"
	redc "red-cloud/mod"
	"runtime"
	"strings"
	"syscall"

	"github.com/wailsapp/wails/v2"
	"github.com/wailsapp/wails/v2/pkg/options"
	"github.com/wailsapp/wails/v2/pkg/options/assetserver"
	"github.com/wailsapp/wails/v2/pkg/options/mac"
	"github.com/wailsapp/wails/v2/pkg/options/windows"
)

//go:embed all:frontend/dist
//go:embed mod/providers
var assets embed.FS

func main() {
	// Check for server subcommand
	if len(os.Args) > 1 && os.Args[1] == "server" {
		runServerMode()
		return
	}

	// Create an instance of the app structure
	app := NewApp()

	// Create application with options
	appOptions := &options.App{
		Title:  "RedC - 红队基础设施管理",
		Width:  1600,
		Height: 1050,
		AssetServer: &assetserver.Options{
			Assets: assets,
		},
		BackgroundColour: &options.RGBA{R: 250, G: 251, B: 252, A: 1}, // 匹配 App.svelte 的 bg-[#fafbfc]
		OnStartup:        app.startup,
		OnShutdown:       app.shutdown,
		OnBeforeClose:    app.beforeClose,
		Bind: []interface{}{
			app,
		},
		Mac: &mac.Options{
			TitleBar: mac.TitleBarHiddenInset(),
		},
		Windows: &windows.Options{
			WebviewIsTransparent: false,
			WindowIsTranslucent:  false,
			DisableWindowIcon:    false,
			CustomTheme: &windows.ThemeSettings{
				DarkModeTitleBar:   windows.RGB(32, 32, 32),
				DarkModeTitleText:  windows.RGB(255, 255, 255),
				DarkModeBorder:     windows.RGB(32, 32, 32),
				LightModeTitleBar:  windows.RGB(250, 251, 252),
				LightModeTitleText: windows.RGB(0, 0, 0),
				LightModeBorder:    windows.RGB(250, 251, 252),
			},
		},
	}

	// 只在 Windows 上启用无边框模式
	if runtime.GOOS == "windows" {
		appOptions.Frameless = true
	}

	err := wails.Run(appOptions)

	if err != nil {
		println("Error:", err.Error())
	}
}

func runServerMode() {
	port := 8899
	host := "127.0.0.1"
	token := ""

	for i := 2; i < len(os.Args); i++ {
		arg := os.Args[i]
		if strings.HasPrefix(arg, "--port=") {
			fmt.Sscanf(strings.TrimPrefix(arg, "--port="), "%d", &port)
		} else if strings.HasPrefix(arg, "--host=") {
			host = strings.TrimPrefix(arg, "--host=")
		} else if strings.HasPrefix(arg, "--token=") {
			token = strings.TrimPrefix(arg, "--token=")
		}
	}

	if token == "" {
		token = GenerateToken()
	}

	app := NewApp()
	app.startupHeadless()

	// Load users from config
	var users []redc.HTTPUser
	if settings, err := redc.LoadGUISettings(); err == nil && settings != nil {
		users = settings.HTTPServerUsers
	}

	httpSrv := NewHTTPServer(app, host, port, token, users)
	app.httpSrv = httpSrv

	if err := httpSrv.Start(assets); err != nil {
		fmt.Printf("Failed to start HTTP server: %v\n", err)
		os.Exit(1)
	}

	fmt.Printf("\n┌─────────────────────────────────────────────────────┐\n")
	fmt.Printf("│  RedC HTTP Server 已启动                             │\n")
	fmt.Printf("│  访问地址: http://%s:%d\n", host, port)
	fmt.Printf("│  访问 Token: %s\n", token)
	fmt.Printf("└─────────────────────────────────────────────────────┘\n\n")

	quit := make(chan os.Signal, 1)
	signal.Notify(quit, os.Interrupt, syscall.SIGTERM)
	<-quit

	fmt.Println("Shutting down HTTP server...")
	httpSrv.Stop()
}
