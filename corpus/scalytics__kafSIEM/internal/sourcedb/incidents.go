// Copyright 2024 ff, Scalytics, Inc. - https://www.scalytics.io
// SPDX-License-Identifier: Apache-2.0

package sourcedb

import (
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
	"strings"
	"time"

	"github.com/scalytics/kafSIEM/internal/collector/model"
)

type OSINTIncidentDetail struct {
	model.IncidentSummary
	Alerts   []model.Alert                 `json:"alerts"`
	Geo      model.IncidentGeoSummary      `json:"geo"`
	Timeline []model.IncidentTimelineEntry `json:"timeline"`
	Graph    model.IncidentGraph           `json:"graph"`
}

func (db *DB) SaveOSINTIncidents(ctx context.Context, incidents []model.IncidentSummary) error {
	if err := db.Init(ctx); err != nil {
		return err
	}
	tx, err := db.sql.BeginTx(ctx, nil)
	if err != nil {
		return fmt.Errorf("begin osint incident tx: %w", err)
	}
	defer tx.Rollback()

	if _, err := tx.ExecContext(ctx, `DELETE FROM osint_incidents`); err != nil {
		return fmt.Errorf("clear osint incidents: %w", err)
	}

	updatedAt := time.Now().UTC().Format(time.RFC3339)
	for _, incident := range incidents {
		alertIDsJSON, _ := json.Marshal(incident.AlertIDs)
		reasonsJSON, _ := json.Marshal(incident.LinkReasons)
		cvesJSON, _ := json.Marshal(incident.CVEs)
		entitiesJSON, _ := json.Marshal(incident.Entities)
		malwareJSON, _ := json.Marshal(incident.Malware)
		sectorsJSON, _ := json.Marshal(incident.Sectors)
		countriesJSON, _ := json.Marshal(incident.Countries)
		if _, err := tx.ExecContext(ctx, `
INSERT INTO osint_incidents (
  incident_id, title, category, severity, member_count, source_count, primary_alert_id,
  alert_ids_json, link_reasons_json, cves_json, entities_json, malware_json, sectors_json, countries_json, attack_type,
  first_seen, last_seen, updated_at
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
`, incident.IncidentID, incident.Title, incident.Category, incident.Severity, incident.MemberCount,
			incident.SourceCount, incident.PrimaryAlertID, string(alertIDsJSON), string(reasonsJSON), string(cvesJSON),
			string(entitiesJSON), string(malwareJSON), string(sectorsJSON), string(countriesJSON), incident.AttackType,
			incident.FirstSeen, incident.LastSeen, updatedAt); err != nil {
			return fmt.Errorf("insert osint incident %s: %w", incident.IncidentID, err)
		}
	}

	if err := tx.Commit(); err != nil {
		return fmt.Errorf("commit osint incidents: %w", err)
	}
	return nil
}

func (db *DB) ListOSINTIncidents(ctx context.Context, limit int) ([]model.IncidentSummary, error) {
	if err := db.Init(ctx); err != nil {
		return nil, err
	}
	if limit <= 0 || limit > 200 {
		limit = 50
	}
	rows, err := db.sql.QueryContext(ctx, `
SELECT incident_id, title, category, severity, member_count, source_count, primary_alert_id,
       alert_ids_json, link_reasons_json, cves_json, entities_json, malware_json, sectors_json, countries_json,
       attack_type, first_seen, last_seen
  FROM osint_incidents
 ORDER BY last_seen DESC, incident_id ASC
 LIMIT ?
`, limit)
	if err != nil {
		return nil, fmt.Errorf("list osint incidents: %w", err)
	}
	defer rows.Close()

	out := make([]model.IncidentSummary, 0)
	for rows.Next() {
		item, err := scanIncidentSummaryRow(rows)
		if err != nil {
			return nil, err
		}
		out = append(out, item)
	}
	return out, rows.Err()
}

func (db *DB) GetOSINTIncident(ctx context.Context, incidentID string) (OSINTIncidentDetail, bool, error) {
	if err := db.Init(ctx); err != nil {
		return OSINTIncidentDetail{}, false, err
	}
	incidentID = strings.TrimSpace(incidentID)
	if incidentID == "" {
		return OSINTIncidentDetail{}, false, nil
	}

	row := db.sql.QueryRowContext(ctx, `
SELECT incident_id, title, category, severity, member_count, source_count, primary_alert_id,
       alert_ids_json, link_reasons_json, cves_json, entities_json, malware_json, sectors_json, countries_json,
       attack_type, first_seen, last_seen
  FROM osint_incidents
 WHERE incident_id = ?
`, incidentID)
	summary, err := scanIncidentSummaryRow(row)
	if err == sql.ErrNoRows {
		return OSINTIncidentDetail{}, false, nil
	}
	if err != nil {
		return OSINTIncidentDetail{}, false, err
	}

	alerts := make([]model.Alert, 0, len(summary.AlertIDs))
	for _, alertID := range summary.AlertIDs {
		alert, ok, err := db.loadAlertByID(ctx, alertID)
		if err != nil {
			return OSINTIncidentDetail{}, false, err
		}
		if ok {
			alerts = append(alerts, alert)
		}
	}

	return OSINTIncidentDetail{
		IncidentSummary: summary,
		Alerts:          alerts,
	}, true, nil
}

func (db *DB) loadAlertByID(ctx context.Context, alertID string) (model.Alert, bool, error) {
	row := db.sql.QueryRowContext(ctx, `
SELECT alert_id, source_id, status, first_seen, last_seen, title, canonical_url,
       category, subcategory, severity, signal_lane, region_tag, lat, lng, event_country,
       event_country_code, event_geo_source, event_geo_confidence, freshness_hours,
       source_json, reporting_json, triage_json
  FROM alerts
 WHERE alert_id = ?
`, alertID)
	var alert model.Alert
	var sourceJSON, reportingJSON, triageJSON string
	if err := row.Scan(
		&alert.AlertID, &alert.SourceID, &alert.Status, &alert.FirstSeen, &alert.LastSeen,
		&alert.Title, &alert.CanonicalURL, &alert.Category, &alert.Subcategory, &alert.Severity,
		&alert.SignalLane, &alert.RegionTag, &alert.Lat, &alert.Lng, &alert.EventCountry,
		&alert.EventCountryCode, &alert.EventGeoSource, &alert.EventGeoConfidence, &alert.FreshnessHours,
		&sourceJSON, &reportingJSON, &triageJSON,
	); err == sql.ErrNoRows {
		return model.Alert{}, false, nil
	} else if err != nil {
		return model.Alert{}, false, err
	}
	_ = json.Unmarshal([]byte(sourceJSON), &alert.Source)
	_ = json.Unmarshal([]byte(reportingJSON), &alert.Reporting)
	if triageJSON != "" && triageJSON != "null" {
		var triage model.Triage
		if json.Unmarshal([]byte(triageJSON), &triage) == nil {
			alert.Triage = &triage
		}
	}
	return alert, true, nil
}

type incidentScanner interface {
	Scan(dest ...any) error
}

func scanIncidentSummaryRow(row incidentScanner) (model.IncidentSummary, error) {
	var item model.IncidentSummary
	var alertIDsJSON, reasonsJSON, cvesJSON, entitiesJSON, malwareJSON, sectorsJSON, countriesJSON string
	if err := row.Scan(
		&item.IncidentID, &item.Title, &item.Category, &item.Severity, &item.MemberCount,
		&item.SourceCount, &item.PrimaryAlertID, &alertIDsJSON, &reasonsJSON, &cvesJSON, &entitiesJSON, &malwareJSON, &sectorsJSON,
		&countriesJSON, &item.AttackType,
		&item.FirstSeen, &item.LastSeen,
	); err != nil {
		return model.IncidentSummary{}, err
	}
	_ = json.Unmarshal([]byte(alertIDsJSON), &item.AlertIDs)
	_ = json.Unmarshal([]byte(reasonsJSON), &item.LinkReasons)
	_ = json.Unmarshal([]byte(cvesJSON), &item.CVEs)
	_ = json.Unmarshal([]byte(entitiesJSON), &item.Entities)
	_ = json.Unmarshal([]byte(malwareJSON), &item.Malware)
	_ = json.Unmarshal([]byte(sectorsJSON), &item.Sectors)
	_ = json.Unmarshal([]byte(countriesJSON), &item.Countries)
	return item, nil
}
