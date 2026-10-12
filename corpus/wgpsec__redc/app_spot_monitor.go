package main

import (
	"encoding/json"
	"fmt"
	"net"
	"strings"
	"sync"
	"time"

	"red-cloud/i18n"
	redc "red-cloud/mod"
)

// SpotMonitor periodically checks running spot instances for termination
// by probing their SSH port (TCP :22).
type SpotMonitor struct {
	app      *App
	stopCh   chan struct{}
	wg       sync.WaitGroup
	interval time.Duration
	// alerted tracks IPs that have already been reported as terminated (key: "caseID:ip")
	alerted map[string]bool
	mu      sync.Mutex
}

// NewSpotMonitor creates a new SpotMonitor.
func NewSpotMonitor(app *App, interval time.Duration) *SpotMonitor {
	return &SpotMonitor{
		app:      app,
		stopCh:   make(chan struct{}),
		interval: interval,
		alerted:  make(map[string]bool),
	}
}

// Start begins the background monitoring loop.
func (m *SpotMonitor) Start() {
	m.wg.Add(1)
	go m.loop()
}

// Stop signals the monitor to stop and waits for it to finish.
func (m *SpotMonitor) Stop() {
	close(m.stopCh)
	m.wg.Wait()
}

func (m *SpotMonitor) loop() {
	defer m.wg.Done()

	// Initial delay: wait 60s before first scan so the app finishes loading
	select {
	case <-time.After(60 * time.Second):
	case <-m.stopCh:
		return
	}

	ticker := time.NewTicker(m.interval)
	defer ticker.Stop()

	m.scan()
	for {
		select {
		case <-ticker.C:
			m.scan()
		case <-m.stopCh:
			return
		}
	}
}

func (m *SpotMonitor) scan() {
	app := m.app
	if app.project == nil {
		return
	}

	cases, err := redc.LoadProjectCases(app.project.ProjectName)
	if err != nil {
		return
	}

	for _, c := range cases {
		if c.State != redc.StateRunning {
			continue
		}
		if !detectSpotFromTfFiles(c.Path) {
			continue
		}

		// Extract all public IPs from terraform outputs
		ips := m.getCasePublicIPs(c)
		if len(ips) == 0 {
			continue
		}

		// Check each IP individually
		var downIPs []string
		for _, ip := range ips {
			alertKey := c.Id + ":" + ip
			m.mu.Lock()
			alreadyAlerted := m.alerted[alertKey]
			m.mu.Unlock()
			if alreadyAlerted {
				continue
			}

			if !m.probeSSH(ip) {
				m.mu.Lock()
				m.alerted[alertKey] = true
				m.mu.Unlock()
				downIPs = append(downIPs, ip)
			}
		}

		if len(downIPs) > 0 {
			m.handleTerminated(c, downIPs, len(ips))
		}
	}
}

// getCasePublicIPs extracts all public IPs from terraform outputs.
// Handles various output key patterns (public_ip, ecs_ip, instance_ip, vps_ip, etc.)
// and both single-value and list-value outputs.
func (m *SpotMonitor) getCasePublicIPs(c *redc.Case) []string {
	outputs, err := c.TfOutput()
	if err != nil {
		return nil
	}

	var ips []string
	for name, meta := range outputs {
		lower := strings.ToLower(name)
		// Match output keys containing "ip" but skip private IPs
		if !strings.Contains(lower, "ip") || strings.Contains(lower, "private") {
			continue
		}

		raw := string(meta.Value)
		extracted := extractIPs(raw)
		ips = append(ips, extracted...)
	}
	return ips
}

// extractIPs parses terraform output value into individual IP strings.
// Handles: "1.2.3.4", ["1.2.3.4","5.6.7.8"], or bare 1.2.3.4
func extractIPs(raw string) []string {
	raw = strings.TrimSpace(raw)
	if raw == "" || raw == "null" || raw == "\"\"" || raw == "[]" {
		return nil
	}

	// Try JSON array: ["ip1", "ip2"]
	if strings.HasPrefix(raw, "[") {
		var arr []string
		if err := json.Unmarshal([]byte(raw), &arr); err == nil {
			var result []string
			for _, v := range arr {
				v = strings.TrimSpace(v)
				if v != "" && net.ParseIP(v) != nil {
					result = append(result, v)
				}
			}
			return result
		}
	}

	// Single quoted string: "1.2.3.4"
	if len(raw) >= 2 && raw[0] == '"' && raw[len(raw)-1] == '"' {
		raw = raw[1 : len(raw)-1]
	}

	if ip := net.ParseIP(raw); ip != nil {
		return []string{raw}
	}
	return nil
}

// probeSSH tries to TCP-connect to ip:22 up to 3 times.
// Returns true if at least one attempt succeeds.
func (m *SpotMonitor) probeSSH(ip string) bool {
	addr := net.JoinHostPort(ip, "22")
	for attempt := 0; attempt < 3; attempt++ {
		conn, err := net.DialTimeout("tcp", addr, 10*time.Second)
		if err == nil {
			conn.Close()
			return true
		}
		// Wait 15s between retries (except after the last attempt)
		if attempt < 2 {
			select {
			case <-time.After(15 * time.Second):
			case <-m.stopCh:
				return true // stopping, don't report false positive
			}
		}
	}
	return false
}

// handleTerminated reports terminated IPs and optionally recovers them.
func (m *SpotMonitor) handleTerminated(c *redc.Case, downIPs []string, totalIPs int) {
	allDown := len(downIPs) >= totalIPs

	// If all IPs are down, mark the case as terminated
	if allDown {
		c.StatusChange(redc.StateTerminated)
	}

	ipList := strings.Join(downIPs, ", ")
	detail := fmt.Sprintf("%s (%s)", c.Name, ipList)

	// Emit event to frontend
	m.app.emitEvent( "spot-terminated", map[string]interface{}{
		"caseId":   c.Id,
		"caseName": c.Name,
		"template": c.Type,
		"downIPs":  downIPs,
		"totalIPs": totalIPs,
		"allDown":  allDown,
	})

	// Log
	msg := fmt.Sprintf("⚠️ %s", i18n.Tf("app_spot_terminated", detail))
	m.app.emitLog(msg)
	m.app.logTimeline("spot", "spot_terminated", c.Id, c.Name, i18n.Tf("app_spot_terminated", detail), fmt.Sprintf(`{"downIPs":%q}`, ipList), "warning")

	// Send system notification
	if m.app.notificationMgr != nil {
		m.app.notificationMgr.SendSpotTerminated(c.Name, ipList)
	}

	// Trigger refresh
	m.app.emitRefresh()

	// Auto-recover if enabled
	if m.isAutoRecoverEnabled() {
		m.attemptRecover(c, downIPs)
	}
}

// isAutoRecoverEnabled checks the GUI settings for auto-recover flag.
func (m *SpotMonitor) isAutoRecoverEnabled() bool {
	settings, err := redc.LoadGUISettings()
	if err != nil {
		return false
	}
	return settings.SpotAutoRecoverEnabled
}

// attemptRecover runs terraform plan+apply to replenish terminated spot instances.
// Uses low-level TfPlan/TfApply directly to bypass the state==running check in Case.TfApply().
func (m *SpotMonitor) attemptRecover(c *redc.Case, downIPs []string) {
	m.app.emitLog(fmt.Sprintf("🔄 %s", i18n.Tf("app_spot_recovering", c.Name)))
	m.app.logTimeline("spot", "spot_recovering", c.Id, c.Name, i18n.Tf("app_spot_recovering", c.Name), "", "info")

	// Emit recovering event
	m.app.emitEvent( "spot-recovering", map[string]interface{}{
		"caseId":   c.Id,
		"caseName": c.Name,
	})

	// Run terraform plan + apply directly (bypass Case.TfApply which rejects running state)
	if err := redc.TfPlan(c.Path, c.Parameter...); err != nil {
		m.app.emitLog(fmt.Sprintf("❌ %s", i18n.Tf("app_spot_recover_failed", c.Name, err)))
		m.app.logTimeline("spot", "spot_recover_failed", c.Id, c.Name, i18n.Tf("app_spot_recover_failed", c.Name, err), "", "error")
		if m.app.notificationMgr != nil {
			m.app.notificationMgr.SendSpotRecoverFailed(c.Name)
		}
		m.app.emitEvent( "spot-recover-failed", map[string]interface{}{
			"caseId":   c.Id,
			"caseName": c.Name,
			"error":    err.Error(),
		})
		return
	}

	if err := redc.TfApply(c.Path, c.Parameter...); err != nil {
		m.app.emitLog(fmt.Sprintf("❌ %s", i18n.Tf("app_spot_recover_failed", c.Name, err)))
		m.app.logTimeline("spot", "spot_recover_failed", c.Id, c.Name, i18n.Tf("app_spot_recover_failed", c.Name, err), "", "error")
		// Rollback: destroy partially created resources to avoid orphaned instances
		m.app.emitLog(fmt.Sprintf("🧹 %s", i18n.Tf("app_spot_recover_rollback", c.Name)))
		if destroyErr := redc.TfDestroy(c.Path, c.Parameter); destroyErr != nil {
			m.app.emitLog(fmt.Sprintf("❌ %s", i18n.Tf("app_spot_recover_rollback_failed", c.Name, destroyErr)))
		} else {
			c.StatusChange(redc.StateStopped)
			m.app.emitLog(fmt.Sprintf("✅ %s", i18n.Tf("app_spot_recover_rollback_done", c.Name)))
		}
		if m.app.notificationMgr != nil {
			m.app.notificationMgr.SendSpotRecoverFailed(c.Name)
		}
		m.app.emitEvent( "spot-recover-failed", map[string]interface{}{
			"caseId":   c.Id,
			"caseName": c.Name,
			"error":    err.Error(),
		})
		m.app.emitRefresh()
		return
	}

	// Ensure state is running
	if c.State == redc.StateTerminated {
		c.StatusChange(redc.StateRunning)
	}

	// Refresh terraform outputs so Case has new IPs
	if _, err := c.TfOutput(); err != nil {
		m.app.emitLog(fmt.Sprintf("⚠️ %s", i18n.Tf("app_spot_recover_output_failed", c.Name, err)))
	}

	// Re-run plugin hooks so plugins (e.g. clash-config, upload-r2) pick up new IPs
	if m.app.pluginMgr != nil {
		m.app.setupPluginHooks(c)
		m.app.emitLog(fmt.Sprintf("🔌 %s", i18n.Tf("app_spot_recover_plugins", c.Name)))
		c.RunPluginHookPublic("post-apply")
	}

	// Success — clear alerts for this case so new IPs can be monitored
	m.ResetAlert(c.Id)

	m.app.emitLog(fmt.Sprintf("✅ %s", i18n.Tf("app_spot_recovered", c.Name)))
	m.app.logTimeline("spot", "spot_recovered", c.Id, c.Name, i18n.Tf("app_spot_recovered", c.Name), "", "success")
	if m.app.notificationMgr != nil {
		m.app.notificationMgr.SendSpotRecovered(c.Name)
	}

	m.app.emitEvent( "spot-recovered", map[string]interface{}{
		"caseId":   c.Id,
		"caseName": c.Name,
	})

	m.app.emitRefresh()
}

// ResetAlert removes all alerts for a case (e.g. when restarted).
func (m *SpotMonitor) ResetAlert(caseID string) {
	m.mu.Lock()
	for key := range m.alerted {
		if strings.HasPrefix(key, caseID+":") {
			delete(m.alerted, key)
		}
	}
	m.mu.Unlock()
}
