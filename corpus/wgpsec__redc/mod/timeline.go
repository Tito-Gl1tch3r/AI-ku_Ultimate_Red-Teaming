package mod

import (
	"database/sql"
	"fmt"
	"path/filepath"
	"sync"
	"time"

	_ "github.com/mattn/go-sqlite3"
)

// TimelineEvent represents a single event in the timeline
type TimelineEvent struct {
	ID        int    `json:"id"`
	Timestamp string `json:"timestamp"`
	Category  string `json:"category"`   // scene, plugin, spot, ssh, system
	EventType string `json:"eventType"`  // scene_started, spot_terminated, etc.
	CaseID    string `json:"caseId"`
	CaseName  string `json:"caseName"`
	Message   string `json:"message"`
	Detail    string `json:"detail"`     // JSON extra data
	Level     string `json:"level"`      // info, success, warning, error
}

// TimelineListResult contains paginated timeline results
type TimelineListResult struct {
	Events []TimelineEvent `json:"events"`
	Total  int             `json:"total"`
}

const timelineMaxEntries = 5000

// TimelineStore manages timeline event persistence
type TimelineStore struct {
	mu sync.Mutex
	db *sql.DB
}

// NewTimelineStore creates and initializes a timeline store
func NewTimelineStore() (*TimelineStore, error) {
	if err := ensureRedcPath(); err != nil {
		return nil, err
	}
	dbPath := filepath.Join(RedcPath, "timeline.db")
	db, err := sql.Open("sqlite3", dbPath)
	if err != nil {
		return nil, fmt.Errorf("failed to open timeline db: %v", err)
	}

	createSQL := `
	CREATE TABLE IF NOT EXISTS timeline_events (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		timestamp DATETIME NOT NULL,
		category TEXT NOT NULL,
		event_type TEXT NOT NULL,
		case_id TEXT DEFAULT '',
		case_name TEXT DEFAULT '',
		message TEXT NOT NULL,
		detail TEXT DEFAULT '',
		level TEXT DEFAULT 'info'
	);
	CREATE INDEX IF NOT EXISTS idx_timeline_timestamp ON timeline_events(timestamp);
	CREATE INDEX IF NOT EXISTS idx_timeline_category ON timeline_events(category);
	CREATE INDEX IF NOT EXISTS idx_timeline_case_id ON timeline_events(case_id);
	`
	if _, err := db.Exec(createSQL); err != nil {
		db.Close()
		return nil, fmt.Errorf("failed to create timeline table: %v", err)
	}

	return &TimelineStore{db: db}, nil
}

// Close closes the database connection
func (ts *TimelineStore) Close() {
	if ts.db != nil {
		ts.db.Close()
	}
}

// Log records a timeline event (fire-and-forget, does not return error)
func (ts *TimelineStore) Log(category, eventType, caseID, caseName, message, detail, level string) {
	ts.mu.Lock()
	defer ts.mu.Unlock()

	ts.db.Exec(
		"INSERT INTO timeline_events (timestamp, category, event_type, case_id, case_name, message, detail, level) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
		time.Now().Format("2006-01-02 15:04:05"), category, eventType, caseID, caseName, message, detail, level,
	)

	// Enforce max entries
	ts.db.Exec(`
		DELETE FROM timeline_events WHERE id NOT IN (
			SELECT id FROM timeline_events ORDER BY timestamp DESC LIMIT ?
		)
	`, timelineMaxEntries)
}

// List returns timeline events with optional filters
func (ts *TimelineStore) List(limit, offset int, category, search string) (*TimelineListResult, error) {
	ts.mu.Lock()
	defer ts.mu.Unlock()

	where := "1=1"
	args := []interface{}{}
	if category != "" {
		where += " AND category = ?"
		args = append(args, category)
	}
	if search != "" {
		where += " AND (message LIKE ? OR case_name LIKE ?)"
		args = append(args, "%"+search+"%", "%"+search+"%")
	}

	// Count total
	var total int
	countArgs := make([]interface{}, len(args))
	copy(countArgs, args)
	err := ts.db.QueryRow("SELECT COUNT(*) FROM timeline_events WHERE "+where, countArgs...).Scan(&total)
	if err != nil {
		return nil, err
	}

	if limit <= 0 {
		limit = 50
	}

	query := fmt.Sprintf("SELECT id, timestamp, category, event_type, case_id, case_name, message, detail, level FROM timeline_events WHERE %s ORDER BY timestamp DESC LIMIT ? OFFSET ?", where)
	args = append(args, limit, offset)

	rows, err := ts.db.Query(query, args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var events []TimelineEvent
	for rows.Next() {
		var e TimelineEvent
		if err := rows.Scan(&e.ID, &e.Timestamp, &e.Category, &e.EventType, &e.CaseID, &e.CaseName, &e.Message, &e.Detail, &e.Level); err != nil {
			continue
		}
		events = append(events, e)
	}
	if events == nil {
		events = []TimelineEvent{}
	}
	return &TimelineListResult{Events: events, Total: total}, nil
}

// Clear deletes all timeline events
func (ts *TimelineStore) Clear() error {
	ts.mu.Lock()
	defer ts.mu.Unlock()
	_, err := ts.db.Exec("DELETE FROM timeline_events")
	return err
}
