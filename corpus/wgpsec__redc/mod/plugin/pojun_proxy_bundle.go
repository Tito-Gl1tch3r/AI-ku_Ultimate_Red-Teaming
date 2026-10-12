package plugin

import (
	"crypto/sha256"
	"encoding/json"
	"fmt"
	"net"
	"os"
	"path/filepath"
	"regexp"
	"strconv"
	"time"
)

var (
	pojunPoolIDPattern = regexp.MustCompile(`^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$`)
	proxyPortPattern   = regexp.MustCompile(`^[0-9]+$`)
)

type pojunProxyBundle struct {
	SchemaVersion int                    `json:"schema_version"`
	PoolID        string                 `json:"pool_id"`
	Revision      string                 `json:"revision"`
	GeneratedAt   string                 `json:"generated_at"`
	NodeCount     int                    `json:"node_count"`
	Nodes         []pojunProxyBundleNode `json:"nodes"`
	Source        pojunProxyBundleSource `json:"source"`
}

// Fields are deliberately ordered lexicographically. json.Marshal(nodes) is the
// cross-language canonical revision payload for bundle schema v1.
type pojunProxyBundleNode struct {
	Cipher   string `json:"cipher"`
	Name     string `json:"name"`
	Password string `json:"password"`
	Port     int    `json:"port"`
	Server   string `json:"server"`
	Type     string `json:"type"`
}

type pojunProxyBundleSource struct {
	Kind     string `json:"kind"`
	CaseID   string `json:"case_id"`
	CaseName string `json:"case_name"`
	Template string `json:"template"`
}

func removePojunProxyBundle(ctx *TemplateContext) error {
	if ctx == nil || ctx.CasePath == "" {
		return fmt.Errorf("PoJun proxy bundle cleanup requires a case path")
	}
	bundleDir := filepath.Join(ctx.CasePath, "pojun-proxy")
	info, err := os.Lstat(bundleDir)
	if os.IsNotExist(err) {
		return nil
	}
	if err != nil {
		return fmt.Errorf("inspect bundle directory: %w", err)
	}
	if info.Mode()&os.ModeSymlink != 0 {
		return fmt.Errorf("bundle directory must not be a symlink")
	}
	if !info.IsDir() {
		return fmt.Errorf("bundle path must be a directory")
	}

	bundlePath := filepath.Join(bundleDir, "bundle.json")
	if err := os.Remove(bundlePath); err != nil && !os.IsNotExist(err) {
		return fmt.Errorf("remove PoJun proxy bundle: %w", err)
	}
	if err := syncDirectory(bundleDir); err != nil {
		return fmt.Errorf("sync PoJun proxy bundle cleanup: %w", err)
	}
	return nil
}

func writePojunProxyBundle(ctx *TemplateContext, poolID, portRaw, password string) (map[string]string, error) {
	if ctx == nil || ctx.CasePath == "" {
		return nil, fmt.Errorf("PoJun proxy bundle requires a case path")
	}
	if ctx.CaseID == "" {
		return nil, fmt.Errorf("PoJun proxy bundle requires a case ID")
	}
	if !pojunPoolIDPattern.MatchString(poolID) {
		return nil, fmt.Errorf("PoJun proxy pool ID contains unsupported characters or is too long")
	}
	if !proxyPortPattern.MatchString(portRaw) {
		return nil, fmt.Errorf("Shadowsocks port must be numeric")
	}
	port, err := strconv.Atoi(portRaw)
	if err != nil || port < 1 || port > 65535 {
		return nil, fmt.Errorf("Shadowsocks port must be between 1 and 65535")
	}
	if password == "" {
		return nil, fmt.Errorf("Shadowsocks password is required")
	}
	if len(ctx.IPs) == 0 {
		return nil, fmt.Errorf("at least one proxy node is required")
	}

	seen := make(map[string]struct{}, len(ctx.IPs))
	for _, address := range ctx.IPs {
		parsed := net.ParseIP(address)
		if parsed == nil || parsed.To4() == nil {
			return nil, fmt.Errorf("proxy node address is not a valid IPv4 literal")
		}
		if _, exists := seen[address]; exists {
			return nil, fmt.Errorf("duplicate proxy nodes are not allowed")
		}
		seen[address] = struct{}{}
	}

	bundleDir := filepath.Join(ctx.CasePath, "pojun-proxy")
	if info, err := os.Lstat(bundleDir); err == nil {
		if info.Mode()&os.ModeSymlink != 0 {
			return nil, fmt.Errorf("bundle directory must not be a symlink")
		}
		if !info.IsDir() {
			return nil, fmt.Errorf("bundle path must be a directory")
		}
	} else if !os.IsNotExist(err) {
		return nil, fmt.Errorf("inspect bundle directory: %w", err)
	}
	if err := os.MkdirAll(bundleDir, 0700); err != nil {
		return nil, fmt.Errorf("create bundle directory: %w", err)
	}
	if err := os.Chmod(bundleDir, 0700); err != nil {
		return nil, fmt.Errorf("secure bundle directory: %w", err)
	}

	nodes := make([]pojunProxyBundleNode, 0, len(ctx.IPs))
	for index, address := range ctx.IPs {
		nodes = append(nodes, pojunProxyBundleNode{
			Cipher:   "chacha20-ietf-poly1305",
			Name:     fmt.Sprintf("redc-node-%03d", index+1),
			Password: password,
			Port:     port,
			Server:   address,
			Type:     "ss",
		})
	}
	canonicalNodes, err := json.Marshal(nodes)
	if err != nil {
		return nil, fmt.Errorf("encode PoJun proxy nodes: %w", err)
	}
	revision := fmt.Sprintf("%x", sha256.Sum256(canonicalNodes))

	bundle := pojunProxyBundle{
		SchemaVersion: 1,
		PoolID:        poolID,
		Revision:      revision,
		GeneratedAt:   time.Now().UTC().Format(time.RFC3339),
		NodeCount:     len(ctx.IPs),
		Nodes:         nodes,
		Source: pojunProxyBundleSource{
			Kind:     "redc_case",
			CaseID:   ctx.CaseID,
			CaseName: ctx.CaseName,
			Template: ctx.CaseTemplate,
		},
	}
	bundleData, err := json.MarshalIndent(bundle, "", "  ")
	if err != nil {
		return nil, fmt.Errorf("encode PoJun proxy bundle: %w", err)
	}
	bundleData = append(bundleData, '\n')

	bundlePath := filepath.Join(bundleDir, "bundle.json")
	if err := writePrivateFileAtomic(bundlePath, bundleData); err != nil {
		return nil, fmt.Errorf("write PoJun proxy bundle: %w", err)
	}
	if err := syncDirectory(bundleDir); err != nil {
		return nil, fmt.Errorf("sync PoJun proxy bundle: %w", err)
	}

	absBundlePath, err := filepath.Abs(bundlePath)
	if err != nil {
		return nil, fmt.Errorf("resolve PoJun proxy bundle path: %w", err)
	}
	return map[string]string{
		"bundle_file": absBundlePath,
		"pool_id":     poolID,
		"node_count":  strconv.Itoa(len(ctx.IPs)),
		"revision":    revision,
	}, nil
}
