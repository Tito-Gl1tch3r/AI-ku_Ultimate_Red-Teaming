package sshutil

import (
	"encoding/json"
	"fmt"
	"io"
	"sync"

	"golang.org/x/crypto/ssh"
)

// TerminalSession 表示一个 SSH 终端会话
type TerminalSession struct {
	client  *Client
	session *ssh.Session
	stdin   io.WriteCloser
	stdout  io.Reader
	stderr  io.Reader
	mu      sync.Mutex
	closed  bool
}

// TerminalMessage 终端消息
type TerminalMessage struct {
	Type string `json:"type"` // "input", "output", "resize", "close"
	Data string `json:"data"`
	Rows int    `json:"rows,omitempty"`
	Cols int    `json:"cols,omitempty"`
}

// NewTerminalSession 创建新的终端会话
func (c *Client) NewTerminalSession(rows, cols int) (*TerminalSession, error) {
	session, err := c.NewSession()
	if err != nil {
		return nil, fmt.Errorf("创建 SSH 会话失败: %v", err)
	}

	// 设置终端模式
	modes := ssh.TerminalModes{
		ssh.ECHO:          1,
		ssh.TTY_OP_ISPEED: 14400,
		ssh.TTY_OP_OSPEED: 14400,
	}

	// 请求 PTY
	if err := session.RequestPty("xterm-256color", rows, cols, modes); err != nil {
		session.Close()
		return nil, fmt.Errorf("请求 PTY 失败: %v", err)
	}

	// 获取 stdin/stdout/stderr
	stdin, err := session.StdinPipe()
	if err != nil {
		session.Close()
		return nil, fmt.Errorf("获取 stdin 失败: %v", err)
	}

	stdout, err := session.StdoutPipe()
	if err != nil {
		session.Close()
		return nil, fmt.Errorf("获取 stdout 失败: %v", err)
	}

	stderr, err := session.StderrPipe()
	if err != nil {
		session.Close()
		return nil, fmt.Errorf("获取 stderr 失败: %v", err)
	}

	// 启动 shell
	if err := session.Shell(); err != nil {
		session.Close()
		return nil, fmt.Errorf("启动 shell 失败: %v", err)
	}

	return &TerminalSession{
		client:  c,
		session: session,
		stdin:   stdin,
		stdout:  stdout,
		stderr:  stderr,
	}, nil
}

// Write 写入数据到终端
func (t *TerminalSession) Write(data []byte) error {
	t.mu.Lock()
	defer t.mu.Unlock()

	if t.closed {
		return fmt.Errorf("终端会话已关闭")
	}

	_, err := t.stdin.Write(data)
	return err
}

// Read 从终端读取数据
func (t *TerminalSession) Read(buf []byte) (int, error) {
	return t.stdout.Read(buf)
}

// Resize 调整终端大小
func (t *TerminalSession) Resize(rows, cols int) error {
	t.mu.Lock()
	defer t.mu.Unlock()

	if t.closed {
		return fmt.Errorf("终端会话已关闭")
	}

	return t.session.WindowChange(rows, cols)
}

// Close 关闭终端会话
func (t *TerminalSession) Close() error {
	t.mu.Lock()
	defer t.mu.Unlock()

	if t.closed {
		return nil
	}

	t.closed = true
	t.stdin.Close()
	return t.session.Close()
}

// Wait 等待会话结束
func (t *TerminalSession) Wait() error {
	return t.session.Wait()
}

// HandleMessage 处理终端消息
func (t *TerminalSession) HandleMessage(msgData []byte) error {
	var msg TerminalMessage
	if err := json.Unmarshal(msgData, &msg); err != nil {
		return fmt.Errorf("解析消息失败: %v", err)
	}

	switch msg.Type {
	case "input":
		return t.Write([]byte(msg.Data))
	case "resize":
		return t.Resize(msg.Rows, msg.Cols)
	case "close":
		return t.Close()
	default:
		return fmt.Errorf("未知消息类型: %s", msg.Type)
	}
}
