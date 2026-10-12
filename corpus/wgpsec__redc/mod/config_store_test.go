package mod

import (
	"os"
	"path/filepath"
	"testing"
	"time"
)

func TestNewConfigStore(t *testing.T) {
	store := NewConfigStore()

	if store == nil {
		t.Fatal("NewConfigStore returned nil")
	}

	if store.configDir == "" {
		t.Error("configDir is empty")
	}

	// 验证配置目录路径格式
	homeDir, _ := os.UserHomeDir()
	expectedDir := filepath.Join(homeDir, ".redc", "custom-configs")
	if store.configDir != expectedDir {
		t.Errorf("configDir = %s, want %s", store.configDir, expectedDir)
	}
}

func TestConfigStore_SaveAndLoadConfigTemplate(t *testing.T) {
	store := NewConfigStore()

	// 创建测试配置
	config := &DeploymentConfig{
		Name:         "test-config",
		TemplateName: "universal-ecs",
		Provider:     "alicloud",
		Region:       "cn-hangzhou",
		InstanceType: "ecs.t6-c1m1.large",
		Userdata:     "#!/bin/bash\necho 'Hello World'",
		Variables: map[string]string{
			"instance_name":     "my-instance",
			"instance_password": "MyPassword123!",
		},
	}

	// 保存配置
	err := store.SaveConfigTemplate("test-config", config)
	if err != nil {
		t.Fatalf("SaveConfigTemplate failed: %v", err)
	}

	// 加载配置
	loadedConfig, err := store.LoadConfigTemplate("test-config")
	if err != nil {
		t.Fatalf("LoadConfigTemplate failed: %v", err)
	}

	// 验证配置内容
	if loadedConfig.Name != config.Name {
		t.Errorf("Name = %s, want %s", loadedConfig.Name, config.Name)
	}
	if loadedConfig.TemplateName != config.TemplateName {
		t.Errorf("TemplateName = %s, want %s", loadedConfig.TemplateName, config.TemplateName)
	}
	if loadedConfig.Provider != config.Provider {
		t.Errorf("Provider = %s, want %s", loadedConfig.Provider, config.Provider)
	}
	if loadedConfig.Region != config.Region {
		t.Errorf("Region = %s, want %s", loadedConfig.Region, config.Region)
	}
	if loadedConfig.InstanceType != config.InstanceType {
		t.Errorf("InstanceType = %s, want %s", loadedConfig.InstanceType, config.InstanceType)
	}
	if loadedConfig.Userdata != config.Userdata {
		t.Errorf("Userdata = %s, want %s", loadedConfig.Userdata, config.Userdata)
	}

	// 验证变量
	if len(loadedConfig.Variables) != len(config.Variables) {
		t.Errorf("Variables length = %d, want %d", len(loadedConfig.Variables), len(config.Variables))
	}
	for key, value := range config.Variables {
		if loadedConfig.Variables[key] != value {
			t.Errorf("Variables[%s] = %s, want %s", key, loadedConfig.Variables[key], value)
		}
	}

	// 验证时间戳
	if loadedConfig.CreatedAt.IsZero() {
		t.Error("CreatedAt is zero")
	}
	if loadedConfig.UpdatedAt.IsZero() {
		t.Error("UpdatedAt is zero")
	}

	// 清理测试文件
	defer store.DeleteConfigTemplate("test-config")
}

func TestConfigStore_SaveConfigTemplate_EmptyName(t *testing.T) {
	store := NewConfigStore()

	config := &DeploymentConfig{
		Name: "test",
	}

	err := store.SaveConfigTemplate("", config)
	if err == nil {
		t.Error("SaveConfigTemplate should fail with empty name")
	}
}

func TestConfigStore_SaveConfigTemplate_NilConfig(t *testing.T) {
	store := NewConfigStore()

	err := store.SaveConfigTemplate("test", nil)
	if err == nil {
		t.Error("SaveConfigTemplate should fail with nil config")
	}
}

func TestConfigStore_LoadConfigTemplate_NotExist(t *testing.T) {
	store := NewConfigStore()

	_, err := store.LoadConfigTemplate("non-existent-config")
	if err == nil {
		t.Error("LoadConfigTemplate should fail for non-existent config")
	}
}

func TestConfigStore_LoadConfigTemplate_EmptyName(t *testing.T) {
	store := NewConfigStore()

	_, err := store.LoadConfigTemplate("")
	if err == nil {
		t.Error("LoadConfigTemplate should fail with empty name")
	}
}

func TestConfigStore_ListConfigTemplates(t *testing.T) {
	store := NewConfigStore()

	// 创建测试配置
	config1 := &DeploymentConfig{Name: "test-config-1", Provider: "alicloud"}
	config2 := &DeploymentConfig{Name: "test-config-2", Provider: "tencentcloud"}

	// 保存配置
	if err := store.SaveConfigTemplate("test-config-1", config1); err != nil {
		t.Fatalf("SaveConfigTemplate failed: %v", err)
	}
	if err := store.SaveConfigTemplate("test-config-2", config2); err != nil {
		t.Fatalf("SaveConfigTemplate failed: %v", err)
	}

	// 列出配置
	templates, err := store.ListConfigTemplates()
	if err != nil {
		t.Fatalf("ListConfigTemplates failed: %v", err)
	}

	// 验证列表包含测试配置
	found1, found2 := false, false
	for _, name := range templates {
		if name == "test-config-1" {
			found1 = true
		}
		if name == "test-config-2" {
			found2 = true
		}
	}

	if !found1 {
		t.Error("test-config-1 not found in list")
	}
	if !found2 {
		t.Error("test-config-2 not found in list")
	}

	// 清理测试文件
	defer store.DeleteConfigTemplate("test-config-1")
	defer store.DeleteConfigTemplate("test-config-2")
}

func TestConfigStore_DeleteConfigTemplate(t *testing.T) {
	store := NewConfigStore()

	// 创建测试配置
	config := &DeploymentConfig{Name: "test-delete", Provider: "alicloud"}

	// 保存配置
	if err := store.SaveConfigTemplate("test-delete", config); err != nil {
		t.Fatalf("SaveConfigTemplate failed: %v", err)
	}

	// 删除配置
	if err := store.DeleteConfigTemplate("test-delete"); err != nil {
		t.Fatalf("DeleteConfigTemplate failed: %v", err)
	}

	// 验证配置已删除
	_, err := store.LoadConfigTemplate("test-delete")
	if err == nil {
		t.Error("LoadConfigTemplate should fail after deletion")
	}
}

func TestConfigStore_DeleteConfigTemplate_NotExist(t *testing.T) {
	store := NewConfigStore()

	err := store.DeleteConfigTemplate("non-existent-config")
	if err == nil {
		t.Error("DeleteConfigTemplate should fail for non-existent config")
	}
}

func TestConfigStore_DeleteConfigTemplate_EmptyName(t *testing.T) {
	store := NewConfigStore()

	err := store.DeleteConfigTemplate("")
	if err == nil {
		t.Error("DeleteConfigTemplate should fail with empty name")
	}
}

func TestConfigStore_ExportConfigTemplate(t *testing.T) {
	store := NewConfigStore()

	// 创建测试配置
	config := &DeploymentConfig{
		Name:         "test-export",
		Provider:     "alicloud",
		Region:       "cn-hangzhou",
		InstanceType: "ecs.t6-c1m1.large",
	}

	// 保存配置
	if err := store.SaveConfigTemplate("test-export", config); err != nil {
		t.Fatalf("SaveConfigTemplate failed: %v", err)
	}

	// 导出配置
	exportPath := filepath.Join(os.TempDir(), "test-export.json")
	if err := store.ExportConfigTemplate("test-export", exportPath); err != nil {
		t.Fatalf("ExportConfigTemplate failed: %v", err)
	}

	// 验证导出文件存在
	if _, err := os.Stat(exportPath); os.IsNotExist(err) {
		t.Error("Export file does not exist")
	}

	// 清理测试文件
	defer store.DeleteConfigTemplate("test-export")
	defer os.Remove(exportPath)
}

func TestConfigStore_ExportConfigTemplate_EmptyName(t *testing.T) {
	store := NewConfigStore()

	err := store.ExportConfigTemplate("", "/tmp/test.json")
	if err == nil {
		t.Error("ExportConfigTemplate should fail with empty name")
	}
}

func TestConfigStore_ExportConfigTemplate_EmptyPath(t *testing.T) {
	store := NewConfigStore()

	err := store.ExportConfigTemplate("test", "")
	if err == nil {
		t.Error("ExportConfigTemplate should fail with empty path")
	}
}

func TestConfigStore_ImportConfigTemplate(t *testing.T) {
	store := NewConfigStore()

	// 创建测试配置
	config := &DeploymentConfig{
		Name:         "test-import-source",
		Provider:     "alicloud",
		Region:       "cn-hangzhou",
		InstanceType: "ecs.t6-c1m1.large",
	}

	// 保存并导出配置
	if err := store.SaveConfigTemplate("test-import-source", config); err != nil {
		t.Fatalf("SaveConfigTemplate failed: %v", err)
	}

	exportPath := filepath.Join(os.TempDir(), "test-import.json")
	if err := store.ExportConfigTemplate("test-import-source", exportPath); err != nil {
		t.Fatalf("ExportConfigTemplate failed: %v", err)
	}

	// 导入配置
	if err := store.ImportConfigTemplate("test-import-target", exportPath); err != nil {
		t.Fatalf("ImportConfigTemplate failed: %v", err)
	}

	// 验证导入的配置
	importedConfig, err := store.LoadConfigTemplate("test-import-target")
	if err != nil {
		t.Fatalf("LoadConfigTemplate failed: %v", err)
	}

	if importedConfig.Name != config.Name {
		t.Errorf("Name = %s, want %s", importedConfig.Name, config.Name)
	}
	if importedConfig.Provider != config.Provider {
		t.Errorf("Provider = %s, want %s", importedConfig.Provider, config.Provider)
	}
	if importedConfig.Region != config.Region {
		t.Errorf("Region = %s, want %s", importedConfig.Region, config.Region)
	}

	// 清理测试文件
	defer store.DeleteConfigTemplate("test-import-source")
	defer store.DeleteConfigTemplate("test-import-target")
	defer os.Remove(exportPath)
}

func TestConfigStore_ImportConfigTemplate_EmptyName(t *testing.T) {
	store := NewConfigStore()

	err := store.ImportConfigTemplate("", "/tmp/test.json")
	if err == nil {
		t.Error("ImportConfigTemplate should fail with empty name")
	}
}

func TestConfigStore_ImportConfigTemplate_EmptyPath(t *testing.T) {
	store := NewConfigStore()

	err := store.ImportConfigTemplate("test", "")
	if err == nil {
		t.Error("ImportConfigTemplate should fail with empty path")
	}
}

func TestConfigStore_ImportConfigTemplate_NotExist(t *testing.T) {
	store := NewConfigStore()

	err := store.ImportConfigTemplate("test", "/non/existent/path.json")
	if err == nil {
		t.Error("ImportConfigTemplate should fail for non-existent file")
	}
}

func TestConfigStore_UpdateTimestamps(t *testing.T) {
	store := NewConfigStore()

	// 创建测试配置
	config := &DeploymentConfig{
		Name:     "test-timestamps",
		Provider: "alicloud",
	}

	// 第一次保存
	if err := store.SaveConfigTemplate("test-timestamps", config); err != nil {
		t.Fatalf("SaveConfigTemplate failed: %v", err)
	}

	// 加载配置
	loadedConfig, err := store.LoadConfigTemplate("test-timestamps")
	if err != nil {
		t.Fatalf("LoadConfigTemplate failed: %v", err)
	}

	createdAt := loadedConfig.CreatedAt
	updatedAt := loadedConfig.UpdatedAt

	// 等待一小段时间
	time.Sleep(10 * time.Millisecond)

	// 修改并再次保存
	loadedConfig.Region = "cn-shanghai"
	if err := store.SaveConfigTemplate("test-timestamps", loadedConfig); err != nil {
		t.Fatalf("SaveConfigTemplate failed: %v", err)
	}

	// 再次加载配置
	reloadedConfig, err := store.LoadConfigTemplate("test-timestamps")
	if err != nil {
		t.Fatalf("LoadConfigTemplate failed: %v", err)
	}

	// 验证 CreatedAt 没有改变
	if !reloadedConfig.CreatedAt.Equal(createdAt) {
		t.Error("CreatedAt should not change on update")
	}

	// 验证 UpdatedAt 已更新
	if !reloadedConfig.UpdatedAt.After(updatedAt) {
		t.Error("UpdatedAt should be updated")
	}

	// 清理测试文件
	defer store.DeleteConfigTemplate("test-timestamps")
}

func TestConfigStore_PathTraversalProtection(t *testing.T) {
	store := NewConfigStore()

	// 尝试使用路径遍历攻击
	config := &DeploymentConfig{Name: "test", Provider: "alicloud"}

	// 这些名称应该被清理，不会导致路径遍历
	dangerousNames := []string{
		"../../../etc/passwd",
		"..\\..\\..\\windows\\system32\\config\\sam",
		"/etc/passwd",
		"C:\\Windows\\System32\\config\\sam",
	}

	for _, name := range dangerousNames {
		err := store.SaveConfigTemplate(name, config)
		if err != nil {
			t.Logf("SaveConfigTemplate with dangerous name '%s' failed (expected): %v", name, err)
			continue
		}

		// 如果保存成功，验证文件确实在配置目录中
		filePath := store.getConfigFilePath(name)
		if !filepath.HasPrefix(filePath, store.configDir) {
			t.Errorf("File path '%s' is outside config directory '%s'", filePath, store.configDir)
		}

		// 清理
		store.DeleteConfigTemplate(name)
	}
}
