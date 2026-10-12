package mod

import (
	"fmt"
)

// ConfigValidator 配置验证器
type ConfigValidator struct {
	templateMgr *TemplateManager
}

// NewConfigValidator 创建配置验证器实例
func NewConfigValidator() *ConfigValidator {
	return &ConfigValidator{
		templateMgr: NewTemplateManager(),
	}
}

// NewValidationError 创建验证错误，包含字段名、错误原因和修复建议
func NewValidationError(field, reason, suggestion, code string) *ValidationError {
	message := reason
	if suggestion != "" {
		message = fmt.Sprintf("%s。修复建议: %s", reason, suggestion)
	}
	return &ValidationError{
		Field:   field,
		Message: message,
		Code:    code,
	}
}

// ValidateProvider 验证云厂商
// 验证云厂商在支持列表中
func (v *ConfigValidator) ValidateProvider(provider string) error {
	// 支持的云厂商列表
	supportedProviders := []string{"alicloud", "tencentcloud", "aws", "volcengine", "huaweicloud"}
	
	// 检查云厂商是否在支持列表中
	for _, supported := range supportedProviders {
		if provider == supported {
			return nil
		}
	}
	
	// 云厂商不在支持列表中，返回错误
	return &ValidationError{
		Field:   "provider",
		Message: fmt.Sprintf("云厂商 '%s' 不在支持列表中。支持的云厂商: alicloud, tencentcloud, aws, volcengine, huaweicloud。修复建议: 请从支持的云厂商列表中选择一个有效的云厂商", provider),
		Code:    ErrCodeNotSupported,
	}
}

// ValidateRegion 验证地域
// 验证地域对所选云厂商有效
func (v *ConfigValidator) ValidateRegion(provider, region string) error {
	// 获取云厂商支持的地域列表
	regions, err := GetProviderRegions(provider)
	if err != nil {
		return err
	}

	// 检查地域是否在支持列表中
	for _, r := range regions {
		if r.Code == region {
			return nil
		}
	}

	// 地域不在支持列表中，返回错误
	// 构建可用地域列表字符串
	availableRegions := ""
	for i, r := range regions {
		if i > 0 {
			availableRegions += ", "
		}
		availableRegions += r.Code
	}

	return &ValidationError{
		Field:   "region",
		Message: fmt.Sprintf("地域 '%s' 在云厂商 '%s' 中不可用。可用地域: %s。修复建议: 请从可用地域列表中选择一个有效的地域", region, provider, availableRegions),
		Code:    ErrCodeNotAvailable,
	}
}

// ValidateInstanceType 验证实例规格
// 验证实例规格在所选地域可用
func (v *ConfigValidator) ValidateInstanceType(provider, region, instanceType string) error {
	// 获取该云厂商和地域支持的实例规格列表
	instanceTypes, err := GetInstanceTypes(provider, region)
	if err != nil {
		return err
	}

	// 检查实例规格是否在支持列表中
	for _, it := range instanceTypes {
		if it.Code == instanceType {
			return nil
		}
	}

	// 实例规格不在支持列表中，返回错误
	// 构建可用实例规格列表字符串（最多显示前10个）
	availableTypes := ""
	maxDisplay := 10
	for i, it := range instanceTypes {
		if i >= maxDisplay {
			availableTypes += fmt.Sprintf(", ... (共 %d 个)", len(instanceTypes))
			break
		}
		if i > 0 {
			availableTypes += ", "
		}
		availableTypes += it.Code
	}

	return &ValidationError{
		Field:   "instance_type",
		Message: fmt.Sprintf("实例规格 '%s' 在云厂商 '%s' 的地域 '%s' 中不可用。可用实例规格: %s。修复建议: 请从可用实例规格列表中选择一个有效的实例规格", instanceType, provider, region, availableTypes),
		Code:    ErrCodeNotAvailable,
	}
}

// ValidateDeploymentConfig 验证部署配置
// 验证所有必需变量都已提供
func (v *ConfigValidator) ValidateDeploymentConfig(config *DeploymentConfig) (*ValidationResult, error) {
	result := &ValidationResult{
		Valid:    true,
		Errors:   []ValidationError{},
		Warnings: []ValidationWarning{},
	}

	// 获取模板变量定义
	variables, err := v.templateMgr.GetTemplateVariables(config.TemplateName)
	if err != nil {
		return nil, fmt.Errorf("failed to get template variables: %w", err)
	}

	// 验证所有必需变量都已提供
	for _, variable := range variables {
		if variable.Required {
			// 检查变量是否在配置中提供
			value, exists := config.Variables[variable.Name]
			
			if !exists || value == "" {
				result.Valid = false
				result.Errors = append(result.Errors, ValidationError{
					Field:   variable.Name,
					Message: fmt.Sprintf("必需变量 '%s' 未提供。修复建议: 请在配置中提供 '%s' 变量的值", variable.Name, variable.Name),
					Code:    ErrCodeRequired,
				})
			}
		}
	}

	// 验证核心配置字段
	if config.Name == "" {
		result.Valid = false
		result.Errors = append(result.Errors, ValidationError{
			Field:   "name",
			Message: "部署名称是必填项。修复建议: 请提供一个有效的部署名称",
			Code:    ErrCodeRequired,
		})
	}

	if config.Provider == "" {
		result.Valid = false
		result.Errors = append(result.Errors, ValidationError{
			Field:   "provider",
			Message: "云厂商是必填项。修复建议: 请选择一个云厂商 (alicloud, tencentcloud, aws, volcengine, huaweicloud)",
			Code:    ErrCodeRequired,
		})
	}

	if config.Region == "" {
		result.Valid = false
		result.Errors = append(result.Errors, ValidationError{
			Field:   "region",
			Message: "地域是必填项。修复建议: 请选择一个地域",
			Code:    ErrCodeRequired,
		})
	}

	if config.InstanceType == "" {
		result.Valid = false
		result.Errors = append(result.Errors, ValidationError{
			Field:   "instance_type",
			Message: "实例规格是必填项。修复建议: 请选择一个实例规格",
			Code:    ErrCodeRequired,
		})
	}

	return result, nil
}
