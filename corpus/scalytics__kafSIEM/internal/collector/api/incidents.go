// Copyright 2024 ff, Scalytics, Inc. - https://www.scalytics.io
// SPDX-License-Identifier: Apache-2.0

package api

import (
	"net/http"
	"strconv"
	"strings"

	"github.com/scalytics/kafSIEM/internal/collector/normalize"
)

func (s *Server) handleOSINTIncidentsList(w http.ResponseWriter, r *http.Request) {
	limit := 50
	if raw := strings.TrimSpace(r.URL.Query().Get("limit")); raw != "" {
		if n, err := strconv.Atoi(raw); err == nil && n > 0 && n <= 200 {
			limit = n
		}
	}
	incidents, err := s.db.ListOSINTIncidents(r.Context(), limit)
	if err != nil {
		writeJSON(w, http.StatusInternalServerError, map[string]string{"error": err.Error()})
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"items": incidents,
		"count": len(incidents),
	})
}

func (s *Server) handleOSINTIncident(w http.ResponseWriter, r *http.Request) {
	id := strings.TrimSpace(r.PathValue("id"))
	if id == "" {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "incident id required"})
		return
	}
	detail, ok, err := s.db.GetOSINTIncident(r.Context(), id)
	if err != nil {
		writeJSON(w, http.StatusInternalServerError, map[string]string{"error": err.Error()})
		return
	}
	if !ok {
		writeJSON(w, http.StatusNotFound, map[string]string{"error": "incident not found"})
		return
	}
	geo, timeline, graph := normalize.BuildIncidentOverview(detail.IncidentSummary, detail.Alerts)
	writeJSON(w, http.StatusOK, map[string]any{
		"incident_id":      detail.IncidentID,
		"title":            detail.Title,
		"category":         detail.Category,
		"severity":         detail.Severity,
		"member_count":     detail.MemberCount,
		"source_count":     detail.SourceCount,
		"primary_alert_id": detail.PrimaryAlertID,
		"alert_ids":        detail.AlertIDs,
		"link_reasons":     detail.LinkReasons,
		"cves":             detail.CVEs,
		"entities":         detail.Entities,
		"malware":          detail.Malware,
		"sectors":          detail.Sectors,
		"countries":        detail.Countries,
		"attack_type":      detail.AttackType,
		"first_seen":       detail.FirstSeen,
		"last_seen":        detail.LastSeen,
		"alerts":           detail.Alerts,
		"geo":              geo,
		"timeline":         timeline,
		"graph":            graph,
	})
}
