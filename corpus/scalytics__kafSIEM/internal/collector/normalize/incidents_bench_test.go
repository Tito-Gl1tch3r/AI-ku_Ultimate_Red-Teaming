package normalize

import (
	"encoding/json"
	"fmt"
	"os"
	"testing"
	"time"

	"github.com/scalytics/kafSIEM/internal/collector/model"
)

// Real-corpus benchmarks: point KAFSIEM_BENCH_STATE at an alerts-state.json
// snapshot. Skipped when unset so CI stays green without the fixture.
func loadBenchAlerts(b *testing.B, limit int) []model.Alert {
	b.Helper()
	path := os.Getenv("KAFSIEM_BENCH_STATE")
	if path == "" {
		b.Skip("KAFSIEM_BENCH_STATE not set")
	}
	data, err := os.ReadFile(path)
	if err != nil {
		b.Fatal(err)
	}
	var alerts []model.Alert
	if err := json.Unmarshal(data, &alerts); err != nil {
		b.Fatal(err)
	}
	if limit > 0 && len(alerts) > limit {
		alerts = alerts[:limit]
	}
	return alerts
}

func benchApplyIncidentLinks(b *testing.B, limit int) {
	alerts := loadBenchAlerts(b, limit)
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		ApplyIncidentLinks(alerts)
	}
}

func BenchmarkApplyIncidentLinksState2k(b *testing.B)   { benchApplyIncidentLinks(b, 2000) }
func BenchmarkApplyIncidentLinksState4k(b *testing.B)   { benchApplyIncidentLinks(b, 4000) }
func BenchmarkApplyIncidentLinksState8k(b *testing.B)   { benchApplyIncidentLinks(b, 8000) }
func BenchmarkApplyIncidentLinksStateFull(b *testing.B) { benchApplyIncidentLinks(b, 0) }

// Synthetic benchmark: no fixture needed. Alerts spread over 90 days across
// rotating sources/countries with occasional shared CVEs, approximating the
// archive shape that made the demo collector spin.
func syntheticAlerts(n int) []model.Alert {
	base := time.Date(2026, 4, 1, 0, 0, 0, 0, time.UTC)
	countries := []string{"US", "DE", "FR", "AU", "IN", "BR", "UA", "NG"}
	categories := []string{"cyber_advisory", "public_safety", "conflict_monitoring", "terrorism_tip"}
	out := make([]model.Alert, 0, n)
	for i := 0; i < n; i++ {
		ts := base.Add(time.Duration(i) * 90 * 24 * time.Hour / time.Duration(n)).Format(time.RFC3339)
		title := fmt.Sprintf("Advisory %d on infrastructure exposure and remediation guidance", i)
		if i%17 == 0 {
			title = fmt.Sprintf("Exploitation of CVE-2026-%04d in the wild, patch immediately", i%40)
		}
		out = append(out, model.Alert{
			AlertID:          fmt.Sprintf("bench-%06d", i),
			SourceID:         fmt.Sprintf("source-%d", i%60),
			Title:            title,
			Category:         categories[i%len(categories)],
			Severity:         "high",
			EventCountryCode: countries[i%len(countries)],
			FirstSeen:        ts,
			LastSeen:         ts,
		})
	}
	return out
}

func BenchmarkApplyIncidentLinksSynthetic10k(b *testing.B) {
	alerts := syntheticAlerts(10000)
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		ApplyIncidentLinks(alerts)
	}
}
