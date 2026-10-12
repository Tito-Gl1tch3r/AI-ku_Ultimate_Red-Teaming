package database

import (
	"database/sql/driver"
	"encoding/json"
	"fmt"
	"time"
)

type Agent struct {
	ID           string      `json:"id"`
	IP           string      `json:"ip"`
	Hostname     string      `json:"hostname"`
	OS           string      `json:"os"`
	Arch         string      `json:"arch"`
	Token        string      `json:"token"`
	LastSeen     time.Time   `json:"last_seen"`
	RegisteredAt time.Time   `json:"registered_at"`
	Tags         StringArray `json:"tags"`
	Notes        string      `json:"notes"`
}

type User struct {
	ID       int    `json:"id"`
	Username string `json:"username"`
	Password string `json:"password"`
	Token    string `json:"token"`
}

type Log struct {
	ID        int       `json:"id"`
	AgentID   string    `json:"agent_id"`
	Message   string    `json:"message"`
	Timestamp time.Time `json:"timestamp"`
}

type Command struct {
	ID         int        `json:"id"`
	AgentID    string     `json:"agent_id"`
	Command    string     `json:"command"`
	Status     string     `json:"status"`
	Result     string     `json:"result"`
	CreatedAt  time.Time  `json:"created_at"`
	ExecutedAt *time.Time `json:"executed_at"`
}

type ErrorResponse struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
}

type StringArray []string

func (a *StringArray) Scan(value interface{}) error {
	if value == nil {
		*a = []string{}
		return nil
	}
	bytes, ok := value.([]byte)
	if !ok {
		return fmt.Errorf("failed to parse tags")
	}
	return json.Unmarshal(bytes, a)
}

func (a StringArray) Value() (driver.Value, error) {
	return json.Marshal(a)
}
