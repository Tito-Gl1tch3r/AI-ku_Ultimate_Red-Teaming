// Package i18n provides internationalization support for redc CLI and GUI backend.
//
// Usage:
//
//	// In CLI: auto-detect from environment
//	i18n.Init("")
//
//	// In GUI: set language from user preference
//	i18n.SetLang("en")
//
//	// Get translated string
//	msg := i18n.T("config_load_failed")
//
//	// Get translated string with format args
//	msg := i18n.Tf("scene_init_failed", sceneName, err)
package i18n

import (
	"fmt"
	"os"
	"strings"
	"sync"
)

// Supported languages
const (
	LangZH = "zh"
	LangEN = "en"
)

var (
	currentLang string
	mu          sync.RWMutex
	messages    map[string]map[string]string // lang -> key -> message
)

func init() {
	messages = make(map[string]map[string]string)
	messages[LangZH] = zhMessages
	messages[LangEN] = enMessages
	// Default to Chinese for backward compatibility
	currentLang = LangZH
}

// Init initializes the i18n module.
// If lang is empty, it auto-detects from environment variables.
func Init(lang string) {
	if lang == "" {
		lang = detectLang()
	}
	SetLang(lang)
}

// SetLang sets the current language. Only "zh" and "en" are supported.
func SetLang(lang string) {
	mu.Lock()
	defer mu.Unlock()
	if lang == LangEN || lang == LangZH {
		currentLang = lang
	} else {
		currentLang = LangEN // fallback to English for unknown languages
	}
}

// GetLang returns the current language code.
func GetLang() string {
	mu.RLock()
	defer mu.RUnlock()
	return currentLang
}

// T returns the translated string for the given key.
// If the key is not found, it returns the key itself.
func T(key string) string {
	mu.RLock()
	lang := currentLang
	mu.RUnlock()

	if msgs, ok := messages[lang]; ok {
		if msg, ok := msgs[key]; ok {
			return msg
		}
	}
	// Fallback to Chinese
	if msgs, ok := messages[LangZH]; ok {
		if msg, ok := msgs[key]; ok {
			return msg
		}
	}
	return key
}

// Tf returns the translated string formatted with the given arguments.
// It uses fmt.Sprintf under the hood.
func Tf(key string, args ...interface{}) string {
	return fmt.Sprintf(T(key), args...)
}

// detectLang detects language from environment variables.
func detectLang() string {
	envVars := []string{"REDC_LANG", "LC_ALL", "LC_MESSAGES", "LANG", "LANGUAGE"}
	for _, env := range envVars {
		if val := os.Getenv(env); val != "" {
			lower := strings.ToLower(val)
			if strings.HasPrefix(lower, "zh") {
				return LangZH
			}
			if strings.HasPrefix(lower, "en") {
				return LangEN
			}
			// For other locales, check the first part
			parts := strings.Split(lower, "_")
			if len(parts) > 0 {
				switch parts[0] {
				case "zh":
					return LangZH
				default:
					return LangEN
				}
			}
		}
	}
	return LangZH // Default to Chinese for backward compatibility
}
