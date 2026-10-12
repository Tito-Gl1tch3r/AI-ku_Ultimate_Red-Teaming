// Copyright 2024 ff, Scalytics, Inc. - https://www.scalytics.io
// SPDX-License-Identifier: Apache-2.0

package normalize

import (
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"regexp"
	"sort"
	"strings"
	"time"

	"github.com/scalytics/kafSIEM/internal/collector/model"
)

var cvePattern = regexp.MustCompile(`(?i)\bCVE-\d{4}-\d{4,}\b`)

const (
	cveIncidentWindowHours      = 14 * 24
	entityIncidentWindowHours   = 7 * 24
	countryIncidentWindowHours  = 7 * 24
	countryWeakJaccardThreshold = 0.35
)

type incidentFingerprints struct {
	alert       model.Alert
	tokens      []string
	ts          time.Time
	cves        []string
	actors      []string
	malwareIOCs []string
	sectors     []string
	country     string
}

type alertUnion struct {
	parent map[string]string
}

func newAlertUnion() *alertUnion {
	return &alertUnion{parent: map[string]string{}}
}

func (u *alertUnion) find(id string) string {
	parent, ok := u.parent[id]
	if !ok {
		u.parent[id] = id
		return id
	}
	if parent == id {
		return id
	}
	root := u.find(parent)
	u.parent[id] = root
	return root
}

func (u *alertUnion) union(a, b string) {
	rootA := u.find(a)
	rootB := u.find(b)
	if rootA == rootB {
		return
	}
	if rootA < rootB {
		u.parent[rootB] = rootA
		return
	}
	u.parent[rootA] = rootB
}

// ApplyIncidentLinks annotates active alerts with incident clusters built from
// cross-source fingerprint similarity, shared CVE identifiers, shared actors,
// and shared event geography.
func ApplyIncidentLinks(alerts []model.Alert) ([]model.Alert, []model.IncidentSummary) {
	if len(alerts) == 0 {
		return alerts, nil
	}

	anchors := BuildRelationAnchors(alerts)
	dict := loadEntityDict()
	fps := make([]incidentFingerprints, 0, len(alerts))
	alertIndex := make(map[string]model.Alert, len(alerts))
	for _, alert := range alerts {
		alertIndex[alert.AlertID] = alert
		tokens := contentFingerprint(alert, dict)
		if len(tokens) < minFingerprintTokens {
			continue
		}
		fps = append(fps, incidentFingerprints{
			alert:       alert,
			tokens:      tokens,
			ts:          parseAlertTime(alert),
			cves:        extractCVEs(alert.Title),
			actors:      extractEntityNames(tokens),
			malwareIOCs: extractMalwareIOCs(alert),
			sectors:     extractSectorTargets(alert),
			country:     eventCountryCode(alert),
		})
	}

	union := newAlertUnion()
	reasonsByAlert := make(map[string][]string)
	cvesByAlert := make(map[string][]string)
	actorsByAlert := make(map[string][]string)
	malwareByAlert := make(map[string][]string)
	sectorsByAlert := make(map[string][]string)

	for _, fp := range fps {
		for _, cve := range fp.cves {
			cvesByAlert[fp.alert.AlertID] = appendUniqueString(cvesByAlert[fp.alert.AlertID], cve)
		}
		for _, actor := range fp.actors {
			actorsByAlert[fp.alert.AlertID] = appendUniqueString(actorsByAlert[fp.alert.AlertID], actor)
		}
		for _, ioc := range fp.malwareIOCs {
			malwareByAlert[fp.alert.AlertID] = appendUniqueString(malwareByAlert[fp.alert.AlertID], ioc)
		}
		for _, sector := range fp.sectors {
			sectorsByAlert[fp.alert.AlertID] = appendUniqueString(sectorsByAlert[fp.alert.AlertID], sector)
		}
	}

	// Sort by timestamp so every window-bounded scan can stop at the first
	// out-of-window candidate instead of skipping it and continuing.
	sort.Slice(fps, func(i, j int) bool { return fps[i].ts.Before(fps[j].ts) })

	addReason := func(left, right incidentFingerprints, reason string) {
		union.union(left.alert.AlertID, right.alert.AlertID)
		reasonsByAlert[left.alert.AlertID] = appendUniqueString(reasonsByAlert[left.alert.AlertID], reason)
		reasonsByAlert[right.alert.AlertID] = appendUniqueString(reasonsByAlert[right.alert.AlertID], reason)
	}

	// Jaccard similarity has no exact-match key to index on, so it stays a
	// pair scan — bounded by the 24h window over the time-sorted slice.
	for i := range fps {
		for j := i + 1; j < len(fps); j++ {
			left := fps[i]
			right := fps[j]
			if hoursApart(left.ts, right.ts) > fingerprintTimeWindowHours {
				break
			}
			if left.alert.SourceID == right.alert.SourceID {
				continue
			}
			if score := jaccardSimilarity(left.tokens, right.tokens); score >= fingerprintSimilarityThreshold {
				addReason(left, right, "cross_source:jaccard:"+formatScore(score))
			}
		}
	}

	cveBuckets := make(map[string][]int)
	actorBuckets := make(map[string][]int)
	countryBuckets := make(map[string][]int)
	malwareBuckets := make(map[string][]int)
	sectorBuckets := make(map[string][]int)
	for i, fp := range fps {
		for _, cve := range fp.cves {
			cveBuckets[cve] = append(cveBuckets[cve], i)
		}
		for _, actor := range fp.actors {
			actorBuckets[actor] = append(actorBuckets[actor], i)
		}
		if fp.country != "" {
			countryBuckets[fp.country] = append(countryBuckets[fp.country], i)
		}
		for _, ioc := range fp.malwareIOCs {
			malwareBuckets[ioc] = append(malwareBuckets[ioc], i)
		}
		for _, sector := range fp.sectors {
			sectorBuckets[sector] = append(sectorBuckets[sector], i)
		}
	}

	forBucketPairs(fps, cveBuckets, cveIncidentWindowHours, func(left, right incidentFingerprints) {
		if left.alert.SourceID == right.alert.SourceID {
			return
		}
		for _, cve := range intersectStrings(left.cves, right.cves) {
			addReason(left, right, "shared_cve:"+cve)
		}
	})

	forBucketPairs(fps, actorBuckets, entityIncidentWindowHours, func(left, right incidentFingerprints) {
		shared := intersectStrings(left.actors, right.actors)
		if len(shared) == 0 || !shouldEntityLink(left, right, shared) {
			return
		}
		for _, actor := range shared {
			reason := "shared_entity:" + actor
			if left.alert.Category != right.alert.Category {
				reason = "cross_category_entity:" + actor
			}
			addReason(left, right, reason)
		}
	})

	forBucketPairs(fps, countryBuckets, countryIncidentWindowHours, func(left, right incidentFingerprints) {
		if !shouldCountryLink(left, right) {
			return
		}
		addReason(left, right, "shared_country:"+strings.ToUpper(left.country))
	})

	forBucketPairs(fps, malwareBuckets, malwareIncidentWindowHours, func(left, right incidentFingerprints) {
		shared := intersectStrings(left.malwareIOCs, right.malwareIOCs)
		if len(shared) == 0 || !shouldMalwareLink(left, right, shared) {
			return
		}
		for _, ioc := range shared {
			addReason(left, right, formatSharedMalwareReason(ioc))
		}
	})

	forBucketPairs(fps, sectorBuckets, sectorIncidentWindowHours, func(left, right incidentFingerprints) {
		if !shouldSectorLink(left, right) {
			return
		}
		for _, sector := range intersectStrings(left.sectors, right.sectors) {
			addReason(left, right, formatTargetsSectorReason(sector))
		}
	})

	// Sanctioned-entity pairing only ever matches a sanctions-feed alert
	// against a terrorism tip, so index those two small sets by actor
	// instead of probing every pair.
	sanctionActorBuckets := make(map[string][]int)
	terrorActorBuckets := make(map[string][]int)
	for i, fp := range fps {
		if isSanctionsSource(fp.alert) {
			if actor := MatchActorInText(strings.Join([]string{fp.alert.Title, fp.alert.Subcategory}, "\n")); actor != "" {
				sanctionActorBuckets[actor] = append(sanctionActorBuckets[actor], i)
			}
		}
		if fp.alert.Category == "terrorism_tip" {
			if actor := MatchActorInText(strings.Join([]string{fp.alert.Title, fp.alert.Subcategory}, "\n")); actor != "" {
				terrorActorBuckets[actor] = append(terrorActorBuckets[actor], i)
			}
		}
	}
	for actor, sanctionIdxs := range sanctionActorBuckets {
		terrorIdxs := terrorActorBuckets[actor]
		if len(terrorIdxs) == 0 {
			continue
		}
		for _, si := range sanctionIdxs {
			for _, ti := range terrorIdxs {
				if si == ti {
					continue
				}
				left := fps[si]
				right := fps[ti]
				if hoursApart(left.ts, right.ts) > entityIncidentWindowHours {
					continue
				}
				if left.alert.SourceID == right.alert.SourceID {
					continue
				}
				addReason(left, right, "sanctioned_entity:"+actor)
			}
		}
	}

	groups := make(map[string][]string)
	for _, fp := range fps {
		root := union.find(fp.alert.AlertID)
		groups[root] = appendUniqueString(groups[root], fp.alert.AlertID)
	}

	out := make([]model.Alert, len(alerts))
	copy(out, alerts)
	outIndex := make(map[string]int, len(out))
	for i := range out {
		outIndex[out[i].AlertID] = i
	}
	summaries := make([]model.IncidentSummary, 0)

	for _, memberIDs := range groups {
		memberIDs = uniqueSorted(memberIDs)
		if len(memberIDs) < 2 {
			continue
		}
		incidentID := incidentIDFromParts("bundle", clusterAnchorID(memberIDs, alertIndex))
		primary := pickPrimaryAlert(memberIDs, alertIndex)
		reasons := uniqueSorted(collectReasons(memberIDs, reasonsByAlert))
		sharedCVEs := uniqueSorted(collectCVEs(memberIDs, cvesByAlert))
		sharedEntities := uniqueSorted(collectActors(memberIDs, actorsByAlert))
		sharedMalware := uniqueSorted(collectMalwareIOCs(memberIDs, malwareByAlert))
		sharedSectors := uniqueSorted(collectSectors(memberIDs, sectorsByAlert))
		memberAlerts := make([]model.Alert, 0, len(memberIDs))
		for _, id := range memberIDs {
			memberAlerts = append(memberAlerts, alertIndex[id])
		}
		sourceCount := countDistinctSources(memberAlerts)
		sharedCountries := collectCountries(memberIDs, alertIndex)
		reasons = addClusterGeographyReasons(reasons, sharedCountries, sourceCount)
		reasons = ApplyAnchorCorroboration(reasons, memberAlerts, sharedCVEs, sharedEntities, sharedMalware, anchors)
		for _, id := range memberIDs {
			if i, ok := outIndex[id]; ok {
				out[i].Incident = buildIncidentLink(incidentID, primary.AlertID, id, memberIDs, sourceCount, reasons, sharedCVEs, sharedEntities, sharedMalware, sharedSectors, sharedCountries)
			}
		}
		summary := model.IncidentSummary{
			IncidentID:     incidentID,
			Title:          primary.Title,
			Category:       primary.Category,
			Severity:       maxMemberSeverity(memberAlerts, primary.Severity),
			MemberCount:    len(memberIDs),
			SourceCount:    sourceCount,
			PrimaryAlertID: primary.AlertID,
			AlertIDs:       memberIDs,
			LinkReasons:    reasons,
			CVEs:           sharedCVEs,
			Entities:       sharedEntities,
			Malware:        sharedMalware,
			Sectors:        sharedSectors,
			Countries:      sharedCountries,
			FirstSeen:      earliestSeen(memberIDs, alertIndex),
			LastSeen:       latestSeen(memberIDs, alertIndex),
		}
		summary.AttackType = ClassifyAttackType(summary, memberAlerts)
		summaries = append(summaries, summary)
	}

	sort.Slice(summaries, func(i, j int) bool {
		return summaries[i].LastSeen > summaries[j].LastSeen
	})
	return out, summaries
}

// FinalizeActiveAlerts builds incident clusters before cross-source dedup
// collapses corroborating alerts out of the active feed.
func FinalizeActiveAlerts(alerts []model.Alert) ([]model.Alert, []model.IncidentSummary, int) {
	linked, summaries := ApplyIncidentLinks(alerts)
	finalized, suppressed := crossSourceDedup(linked)
	return finalized, summaries, suppressed
}

// forBucketPairs visits index pairs sharing a bucket key. Bucket lists ascend
// by fingerprint timestamp, so scans stop at the window edge. A pair sharing
// several keys is visited once per key; visitors must be idempotent.
func forBucketPairs(fps []incidentFingerprints, buckets map[string][]int, windowHours float64, visit func(left, right incidentFingerprints)) {
	for _, idxs := range buckets {
		for x := 0; x < len(idxs); x++ {
			for y := x + 1; y < len(idxs); y++ {
				left := fps[idxs[x]]
				right := fps[idxs[y]]
				if hoursApart(left.ts, right.ts) > windowHours {
					break
				}
				visit(left, right)
			}
		}
	}
}

func extractCVEs(text string) []string {
	matches := cvePattern.FindAllString(text, -1)
	if len(matches) == 0 {
		return nil
	}
	seen := make(map[string]bool, len(matches))
	out := make([]string, 0, len(matches))
	for _, match := range matches {
		normalized := strings.ToUpper(match)
		if seen[normalized] {
			continue
		}
		seen[normalized] = true
		out = append(out, normalized)
	}
	sort.Strings(out)
	return out
}

func extractEntityNames(tokens []string) []string {
	out := make([]string, 0)
	for _, token := range tokens {
		if !strings.HasPrefix(token, "entity:") {
			continue
		}
		out = appendUniqueString(out, strings.TrimPrefix(token, "entity:"))
	}
	return out
}

func buildIncidentLink(
	incidentID string,
	primaryAlertID string,
	alertID string,
	memberIDs []string,
	sourceCount int,
	reasons []string,
	sharedCVEs []string,
	sharedEntities []string,
	sharedMalware []string,
	sharedSectors []string,
	sharedCountries []string,
) *model.IncidentLink {
	related := make([]string, 0, len(memberIDs)-1)
	for _, id := range memberIDs {
		if id != alertID {
			related = append(related, id)
		}
	}
	role := "member"
	if alertID == primaryAlertID {
		role = "primary"
	}
	return &model.IncidentLink{
		IncidentID:      incidentID,
		MemberCount:     len(memberIDs),
		SourceCount:     sourceCount,
		PrimaryAlertID:  primaryAlertID,
		Role:            role,
		RelatedAlertIDs: related,
		LinkReasons:     reasons,
		SharedCVEs:      sharedCVEs,
		SharedEntities:  sharedEntities,
		SharedMalware:   sharedMalware,
		SharedSectors:   sharedSectors,
		SharedCountries: sharedCountries,
	}
}

func matchSanctionedEntityPair(left, right model.Alert) string {
	pairs := []struct {
		sanctions model.Alert
		terror    model.Alert
	}{
		{left, right},
		{right, left},
	}
	for _, pair := range pairs {
		if !isSanctionsSource(pair.sanctions) || pair.terror.Category != "terrorism_tip" {
			continue
		}
		sanctionActor := MatchActorInText(strings.Join([]string{pair.sanctions.Title, pair.sanctions.Subcategory}, "\n"))
		terrorActor := MatchActorInText(strings.Join([]string{pair.terror.Title, pair.terror.Subcategory}, "\n"))
		if sanctionActor != "" && terrorActor != "" && sanctionActor == terrorActor {
			return sanctionActor
		}
	}
	return ""
}

func collectMalwareIOCs(memberIDs []string, malwareByAlert map[string][]string) []string {
	out := make([]string, 0)
	for _, id := range memberIDs {
		out = append(out, malwareByAlert[id]...)
	}
	return uniqueSorted(out)
}

func collectSectors(memberIDs []string, sectorsByAlert map[string][]string) []string {
	out := make([]string, 0)
	for _, id := range memberIDs {
		out = append(out, sectorsByAlert[id]...)
	}
	return uniqueSorted(out)
}

func eventCountryCode(alert model.Alert) string {
	return strings.ToUpper(strings.TrimSpace(alert.EventCountryCode))
}

func countryLinkCategory(category string) bool {
	switch category {
	case "conflict_monitoring",
		"cyber_advisory",
		"disease_outbreak",
		"emergency_management",
		"environmental_disaster",
		"fraud_alert",
		"health_emergency",
		"humanitarian_security",
		"humanitarian_tasking",
		"intelligence_report",
		"logistics_incident",
		"maritime_security",
		"missing_person",
		"public_appeal",
		"public_safety",
		"terrorism_tip",
		"travel_warning",
		"wanted_suspect":
		return true
	default:
		return false
	}
}

func shouldCountryLink(left, right incidentFingerprints) bool {
	if left.country == "" || left.country != right.country {
		return false
	}
	if left.alert.SourceID == right.alert.SourceID {
		return false
	}
	if !countryLinkCategory(left.alert.Category) || left.alert.Category != right.alert.Category {
		return false
	}
	if hoursApart(left.ts, right.ts) > countryIncidentWindowHours {
		return false
	}
	if jaccardSimilarity(left.tokens, right.tokens) >= countryWeakJaccardThreshold {
		return true
	}
	if len(intersectStrings(left.actors, right.actors)) > 0 {
		return true
	}
	if len(intersectStrings(left.cves, right.cves)) > 0 {
		return true
	}
	return false
}

// collectCountries aggregates event geography only. Publisher/source country
// must not leak into the cluster footprint: a UK feed reporting on India would
// otherwise show GB in the geographic spread.
func collectCountries(memberIDs []string, alertIndex map[string]model.Alert) []string {
	out := make([]string, 0)
	for _, id := range memberIDs {
		if code := eventCountryCode(alertIndex[id]); code != "" {
			out = append(out, code)
		}
	}
	return uniqueSorted(out)
}

func addClusterGeographyReasons(reasons []string, countries []string, sourceCount int) []string {
	if sourceCount < 2 || len(countries) == 0 {
		return reasons
	}
	if len(countries) == 1 {
		return appendUniqueString(reasons, "shared_country:"+countries[0])
	}
	return appendUniqueString(reasons, "geographic_spread:"+strings.Join(countries, ","))
}

func shouldEntityLink(left, right incidentFingerprints, sharedActors []string) bool {
	leftOK := entityLinkCategory(left.alert.Category)
	rightOK := entityLinkCategory(right.alert.Category)
	if !leftOK && !rightOK {
		return false
	}
	if left.alert.Category == right.alert.Category {
		return true
	}
	for _, actor := range sharedActors {
		if isKnownThreatActor(actor) {
			return true
		}
	}
	return false
}

func entityLinkCategory(category string) bool {
	switch category {
	case "terrorism_tip", "conflict_monitoring", "cyber_advisory", "maritime_security":
		return true
	default:
		return false
	}
}

// clusterAnchorID picks the member with the earliest FirstSeen (alert ID as
// tie-break) so the incident ID survives new members joining the cluster.
// Hashing the union-find root would reassign the ID whenever a member with a
// smaller alert ID arrives.
func clusterAnchorID(memberIDs []string, alertIndex map[string]model.Alert) string {
	anchor := alertIndex[memberIDs[0]]
	for _, id := range memberIDs[1:] {
		candidate := alertIndex[id]
		if candidate.FirstSeen < anchor.FirstSeen ||
			(candidate.FirstSeen == anchor.FirstSeen && candidate.AlertID < anchor.AlertID) {
			anchor = candidate
		}
	}
	return anchor.AlertID
}

func countDistinctSources(memberAlerts []model.Alert) int {
	seen := make(map[string]struct{}, len(memberAlerts))
	for _, alert := range memberAlerts {
		if id := strings.TrimSpace(alert.SourceID); id != "" {
			seen[id] = struct{}{}
		}
	}
	return len(seen)
}

var severityRank = map[string]int{
	"critical":      5,
	"high":          4,
	"medium":        3,
	"moderate":      3,
	"low":           2,
	"info":          1,
	"informational": 1,
}

// maxMemberSeverity escalates the incident to the highest member severity so
// corroboration is never reported below its most severe constituent alert.
func maxMemberSeverity(memberAlerts []model.Alert, fallback string) string {
	best := fallback
	bestRank := severityRank[strings.ToLower(strings.TrimSpace(fallback))]
	for _, alert := range memberAlerts {
		if rank := severityRank[strings.ToLower(strings.TrimSpace(alert.Severity))]; rank > bestRank {
			best = alert.Severity
			bestRank = rank
		}
	}
	return best
}

func incidentIDFromParts(kind, key string) string {
	payload := kind + ":" + strings.TrimSpace(strings.ToLower(key))
	sum := sha256.Sum256([]byte(payload))
	return "inc-" + hex.EncodeToString(sum[:6])
}

func hoursApart(a, b time.Time) float64 {
	delta := a.Sub(b).Hours()
	if delta < 0 {
		return -delta
	}
	return delta
}

func formatScore(score float64) string {
	return fmt.Sprintf("%.2f", score)
}

func appendUniqueString(values []string, next string) []string {
	next = strings.TrimSpace(next)
	if next == "" {
		return values
	}
	for _, value := range values {
		if value == next {
			return values
		}
	}
	return append(values, next)
}

func intersectStrings(left, right []string) []string {
	if len(left) == 0 || len(right) == 0 {
		return nil
	}
	set := make(map[string]bool, len(left))
	for _, item := range left {
		set[item] = true
	}
	out := make([]string, 0)
	for _, item := range right {
		if set[item] {
			out = append(out, item)
		}
	}
	sort.Strings(out)
	return out
}

func uniqueSorted(values []string) []string {
	if len(values) == 0 {
		return nil
	}
	set := make(map[string]bool, len(values))
	for _, value := range values {
		if strings.TrimSpace(value) != "" {
			set[value] = true
		}
	}
	out := make([]string, 0, len(set))
	for value := range set {
		out = append(out, value)
	}
	sort.Strings(out)
	return out
}

func collectReasons(memberIDs []string, reasonsByAlert map[string][]string) []string {
	out := make([]string, 0)
	for _, id := range memberIDs {
		out = append(out, reasonsByAlert[id]...)
	}
	return out
}

func collectCVEs(memberIDs []string, cvesByAlert map[string][]string) []string {
	out := make([]string, 0)
	for _, id := range memberIDs {
		out = append(out, cvesByAlert[id]...)
	}
	return uniqueSorted(out)
}

func collectActors(memberIDs []string, actorsByAlert map[string][]string) []string {
	out := make([]string, 0)
	for _, id := range memberIDs {
		out = append(out, actorsByAlert[id]...)
	}
	return uniqueSorted(out)
}

func pickPrimaryAlert(memberIDs []string, alertIndex map[string]model.Alert) model.Alert {
	best := alertIndex[memberIDs[0]]
	bestScore := alertScore(best)
	for _, id := range memberIDs[1:] {
		candidate := alertIndex[id]
		score := alertScore(candidate)
		if score > bestScore {
			best = candidate
			bestScore = score
			continue
		}
		if score == bestScore && candidate.FirstSeen < best.FirstSeen {
			best = candidate
		}
	}
	return best
}

func earliestSeen(memberIDs []string, alertIndex map[string]model.Alert) string {
	earliest := ""
	for _, id := range memberIDs {
		seen := alertIndex[id].FirstSeen
		if earliest == "" || seen < earliest {
			earliest = seen
		}
	}
	return earliest
}

func latestSeen(memberIDs []string, alertIndex map[string]model.Alert) string {
	latest := ""
	for _, id := range memberIDs {
		seen := alertIndex[id].LastSeen
		if seen > latest {
			latest = seen
		}
	}
	return latest
}
