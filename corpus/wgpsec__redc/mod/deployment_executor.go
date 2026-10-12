package mod

import (
	"fmt"

	"red-cloud/mod/gologger"
)

// DeploymentExecutor 部署执行器
type DeploymentExecutor struct {
	tfWrapper *TerraformWrapper
	project   *RedcProject
}

// NewDeploymentExecutor 创建部署执行器实例
func NewDeploymentExecutor() *DeploymentExecutor {
	return &DeploymentExecutor{
		tfWrapper: NewTerraformWrapper(),
	}
}

// TerraformWrapper Terraform 包装器
type TerraformWrapper struct {
}

// NewTerraformWrapper 创建 Terraform 包装器实例
func NewTerraformWrapper() *TerraformWrapper {
	return &TerraformWrapper{}
}

// ProviderConfig Terraform Provider 配置
type ProviderConfig struct {
	Name    string            `json:"name"`
	Source  string            `json:"source"`
	Version string            `json:"version"`
	Config  map[string]string `json:"config"`
}

// GenerateProviderConfig 根据云厂商生成对应的 Terraform provider 配置
func (e *DeploymentExecutor) GenerateProviderConfig(provider string, region string) (*ProviderConfig, error) {
	switch provider {
	case "alicloud":
		return &ProviderConfig{
			Name:    "alicloud",
			Source:  "aliyun/alicloud",
			Version: "~> 1.0",
			Config: map[string]string{
				"region": region,
			},
		}, nil
	case "tencentcloud":
		return &ProviderConfig{
			Name:    "tencentcloud",
			Source:  "tencentcloudstack/tencentcloud",
			Version: "~> 1.0",
			Config: map[string]string{
				"region": region,
			},
		}, nil
	case "aws":
		return &ProviderConfig{
			Name:    "aws",
			Source:  "hashicorp/aws",
			Version: "~> 5.0",
			Config: map[string]string{
				"region": region,
			},
		}, nil
	case "volcengine":
		return &ProviderConfig{
			Name:    "volcengine",
			Source:  "volcengine/volcengine",
			Version: "~> 0.0",
			Config: map[string]string{
				"region": region,
			},
		}, nil
	case "huaweicloud":
		return &ProviderConfig{
			Name:    "huaweicloud",
			Source:  "huaweicloud/huaweicloud",
			Version: "~> 1.0",
			Config: map[string]string{
				"region": region,
			},
		}, nil
	case "ucloud":
		return &ProviderConfig{
			Name:    "ucloud",
			Source:  "ucloud/ucloud",
			Version: "~> 0.0",
			Config: map[string]string{
				"region": region,
			},
		}, nil
	case "ctyun":
		return &ProviderConfig{
			Name:    "ctyun",
			Source:  "ctyun-it/ctyun",
			Version: "~> 0.0",
			Config: map[string]string{
				"region": region,
			},
		}, nil
	default:
		return nil, &ValidationError{
			Field:   "provider",
			Message: fmt.Sprintf("不支持的云厂商: %s", provider),
			Code:    ErrCodeNotSupported,
		}
	}
}

// GenerateProviderBlock 生成 Terraform provider 块的 HCL 代码
func (e *DeploymentExecutor) GenerateProviderBlock(provider string, region string) (string, error) {
	config, err := e.GenerateProviderConfig(provider, region)
	if err != nil {
		return "", err
	}

	// 只生成 provider 块，不生成 terraform required_providers 块
	// terraform required_providers 块应该在模板的 versions.tf 或 main.tf 中定义
	// 或者由 Terraform 自动处理
	hcl := fmt.Sprintf(`provider "%s" {
  region = "%s"
}
`, config.Name, region)

	return hcl, nil
}

// GenerateVariablesFile 将部署配置转换为 Terraform 变量文件（tfvars 格式）
func (e *DeploymentExecutor) GenerateVariablesFile(config *DeploymentConfig) (string, error) {
	if config == nil {
		return "", fmt.Errorf("部署配置不能为空")
	}

	gologger.Debug().Msgf("GenerateVariablesFile: config.Name=%s, config.Provider=%s, config.Region=%s", 
		config.Name, config.Provider, config.Region)

	// 验证必需字段
	if config.Provider == "" {
		return "", &ValidationError{
			Field:   "provider",
			Message: "云厂商不能为空",
			Code:    ErrCodeRequired,
		}
	}
	if config.Region == "" {
		return "", &ValidationError{
			Field:   "region",
			Message: "地域不能为空",
			Code:    ErrCodeRequired,
		}
	}
	if config.InstanceType == "" {
		return "", &ValidationError{
			Field:   "instance_type",
			Message: "实例规格不能为空",
			Code:    ErrCodeRequired,
		}
	}

	// 构建 tfvars 内容
	tfvars := ""
	
	// 添加基本配置变量
	tfvars += fmt.Sprintf("cloud_provider = \"%s\"\n", escapeString(config.Provider))
	tfvars += fmt.Sprintf("region = \"%s\"\n", escapeString(config.Region))
	tfvars += fmt.Sprintf("instance_type = \"%s\"\n", escapeString(config.InstanceType))
	
	// 添加实例名称（如果配置中有名称，使用配置的名称；否则使用默认值）
	instanceName := config.Name
	if instanceName == "" {
		instanceName = "redc-instance"
	}
	tfvars += fmt.Sprintf("instance_name = \"%s\"\n", escapeString(instanceName))
	
	// 添加 userdata（如果存在）
	if config.Userdata != "" {
		// 对于多行字符串，使用 heredoc 语法
		if containsNewline(config.Userdata) {
			tfvars += "userdata = <<-EOT\n"
			tfvars += config.Userdata
			if !endsWithNewline(config.Userdata) {
				tfvars += "\n"
			}
			tfvars += "EOT\n"
		} else {
			tfvars += fmt.Sprintf("userdata = \"%s\"\n", escapeString(config.Userdata))
		}
	}
	
	// 添加抢占式实例配置
	tfvars += fmt.Sprintf("is_spot_instance = %v\n", config.IsSpotInstance)
	
	// 添加其他自定义变量（排除已经添加的核心变量）
	if config.Variables != nil && len(config.Variables) > 0 {
		tfvars += "\n# 自定义变量\n"
		for key, value := range config.Variables {
			// 跳过已经添加的核心变量
			if key == "cloud_provider" || key == "provider" || key == "region" || key == "instance_type" || key == "instance_name" || key == "userdata" || key == "is_spot_instance" {
				continue
			}
			// 跳过空字符串值的变量，避免类型不匹配错误
			if value == "" {
				continue
			}
			tfvars += fmt.Sprintf("%s = \"%s\"\n", key, escapeString(value))
		}
	}

	return tfvars, nil
}

// escapeString 转义字符串中的特殊字符
func escapeString(s string) string {
	// 转义反斜杠和双引号
	s = replaceAll(s, "\\", "\\\\")
	s = replaceAll(s, "\"", "\\\"")
	// 转义换行符（如果在单行字符串中）
	s = replaceAll(s, "\n", "\\n")
	s = replaceAll(s, "\r", "\\r")
	s = replaceAll(s, "\t", "\\t")
	return s
}

// replaceAll 替换字符串中的所有匹配项
func replaceAll(s, old, new string) string {
	result := ""
	for i := 0; i < len(s); i++ {
		if i+len(old) <= len(s) && s[i:i+len(old)] == old {
			result += new
			i += len(old) - 1
		} else {
			result += string(s[i])
		}
	}
	return result
}

// containsNewline 检查字符串是否包含换行符
func containsNewline(s string) bool {
	for i := 0; i < len(s); i++ {
		if s[i] == '\n' || s[i] == '\r' {
			return true
		}
	}
	return false
}

// endsWithNewline 检查字符串是否以换行符结尾
func endsWithNewline(s string) bool {
	if len(s) == 0 {
		return false
	}
	lastChar := s[len(s)-1]
	return lastChar == '\n' || lastChar == '\r'
}
