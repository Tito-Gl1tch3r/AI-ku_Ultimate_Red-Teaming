package mod

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"
)

// ConfigStore 配置存储
type ConfigStore struct {
	configDir string
}

// NewConfigStore 创建配置存储实例
func NewConfigStore() *ConfigStore {
	homeDir, _ := os.UserHomeDir()
	configDir := filepath.Join(homeDir, ".redc", "custom-configs")
	return &ConfigStore{
		configDir: configDir,
	}
}

// ensureConfigDir 确保配置目录存在
func (s *ConfigStore) ensureConfigDir() error {
	if err := os.MkdirAll(s.configDir, 0755); err != nil {
		return fmt.Errorf("无法创建配置目录: %w", err)
	}
	return nil
}

// getConfigFilePath 获取配置文件路径
func (s *ConfigStore) getConfigFilePath(name string) string {
	// 清理文件名，防止路径遍历攻击
	cleanName := filepath.Base(name)
	if !strings.HasSuffix(cleanName, ".json") {
		cleanName += ".json"
	}
	return filepath.Join(s.configDir, cleanName)
}

// SaveConfigTemplate 保存配置模板
func (s *ConfigStore) SaveConfigTemplate(name string, config *DeploymentConfig) error {
	if name == "" {
		return fmt.Errorf("配置模板名称不能为空")
	}

	if config == nil {
		return fmt.Errorf("配置不能为空")
	}

	// 确保配置目录存在
	if err := s.ensureConfigDir(); err != nil {
		return err
	}

	// 更新时间戳
	now := time.Now()
	if config.CreatedAt.IsZero() {
		config.CreatedAt = now
	}
	config.UpdatedAt = now

	// 序列化配置
	data, err := json.MarshalIndent(config, "", "  ")
	if err != nil {
		return fmt.Errorf("序列化配置失败: %w", err)
	}

	// 写入文件
	filePath := s.getConfigFilePath(name)
	if err := os.WriteFile(filePath, data, 0644); err != nil {
		return fmt.Errorf("写入配置文件失败: %w", err)
	}

	return nil
}

// LoadConfigTemplate 加载配置模板
func (s *ConfigStore) LoadConfigTemplate(name string) (*DeploymentConfig, error) {
	if name == "" {
		return nil, fmt.Errorf("配置模板名称不能为空")
	}

	filePath := s.getConfigFilePath(name)

	// 读取文件
	data, err := os.ReadFile(filePath)
	if err != nil {
		if os.IsNotExist(err) {
			return nil, fmt.Errorf("配置模板不存在: %s", name)
		}
		return nil, fmt.Errorf("读取配置文件失败: %w", err)
	}

	// 反序列化配置
	var config DeploymentConfig
	if err := json.Unmarshal(data, &config); err != nil {
		return nil, fmt.Errorf("解析配置文件失败: %w", err)
	}

	return &config, nil
}

// ListConfigTemplates 列出所有配置模板
func (s *ConfigStore) ListConfigTemplates() ([]string, error) {
	// 确保配置目录存在
	if err := s.ensureConfigDir(); err != nil {
		return nil, err
	}

	// 读取目录
	entries, err := os.ReadDir(s.configDir)
	if err != nil {
		return nil, fmt.Errorf("读取配置目录失败: %w", err)
	}

	// 收集配置模板名称
	var templates []string
	for _, entry := range entries {
		if entry.IsDir() {
			continue
		}
		name := entry.Name()
		if strings.HasSuffix(name, ".json") {
			// 移除 .json 后缀
			templates = append(templates, strings.TrimSuffix(name, ".json"))
		}
	}

	return templates, nil
}

// DeleteConfigTemplate 删除配置模板
func (s *ConfigStore) DeleteConfigTemplate(name string) error {
	if name == "" {
		return fmt.Errorf("配置模板名称不能为空")
	}

	filePath := s.getConfigFilePath(name)

	// 检查文件是否存在
	if _, err := os.Stat(filePath); os.IsNotExist(err) {
		return fmt.Errorf("配置模板不存在: %s", name)
	}

	// 删除文件
	if err := os.Remove(filePath); err != nil {
		return fmt.Errorf("删除配置文件失败: %w", err)
	}

	return nil
}

// ExportConfigTemplate 导出配置模板到指定路径
func (s *ConfigStore) ExportConfigTemplate(name string, exportPath string) error {
	if name == "" {
		return fmt.Errorf("配置模板名称不能为空")
	}

	if exportPath == "" {
		return fmt.Errorf("导出路径不能为空")
	}

	// 加载配置
	config, err := s.LoadConfigTemplate(name)
	if err != nil {
		return err
	}

	// 序列化配置
	data, err := json.MarshalIndent(config, "", "  ")
	if err != nil {
		return fmt.Errorf("序列化配置失败: %w", err)
	}

	// 写入导出文件
	if err := os.WriteFile(exportPath, data, 0644); err != nil {
		return fmt.Errorf("写入导出文件失败: %w", err)
	}

	return nil
}

// ImportConfigTemplate 从指定路径导入配置模板
func (s *ConfigStore) ImportConfigTemplate(name string, importPath string) error {
	if name == "" {
		return fmt.Errorf("配置模板名称不能为空")
	}

	if importPath == "" {
		return fmt.Errorf("导入路径不能为空")
	}

	// 读取导入文件
	data, err := os.ReadFile(importPath)
	if err != nil {
		if os.IsNotExist(err) {
			return fmt.Errorf("导入文件不存在: %s", importPath)
		}
		return fmt.Errorf("读取导入文件失败: %w", err)
	}

	// 反序列化配置
	var config DeploymentConfig
	if err := json.Unmarshal(data, &config); err != nil {
		return fmt.Errorf("解析导入文件失败: %w", err)
	}

	// 保存配置
	if err := s.SaveConfigTemplate(name, &config); err != nil {
		return err
	}

	return nil
}
