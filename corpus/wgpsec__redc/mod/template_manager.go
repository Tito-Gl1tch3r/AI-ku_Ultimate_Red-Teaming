package mod

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"

	"github.com/hashicorp/hcl/v2"
	"github.com/hashicorp/hcl/v2/hclsyntax"
	"github.com/zclconf/go-cty/cty"
)

// TemplateManager 模板管理器
type TemplateManager struct {
	templateDir string
}

// NewTemplateManager 创建模板管理器实例
func NewTemplateManager() *TemplateManager {
	return &TemplateManager{
		templateDir: TemplateDir,
	}
}

// caseJSON 用于解析 case.json 文件的结构
type caseJSON struct {
	Name           string       `json:"name"`
	Description    string       `json:"description"`
	DescriptionEN  string       `json:"description_en"`
	User           string       `json:"user"`
	Version        string       `json:"version"`
	RedcModule    string       `json:"redc_module"`
	TemplateType   TemplateType `json:"template"`
	Provider       string       `json:"provider"`           // 单一云厂商标识
	SupportedProviders []string  `json:"supported_providers"` // 支持的云厂商列表（向后兼容）
}

// ScanBaseTemplates 扫描并识别基础模板
func (m *TemplateManager) ScanBaseTemplates() ([]*BaseTemplate, error) {
	// 检查模板目录是否存在
	if _, err := os.Stat(m.templateDir); os.IsNotExist(err) {
		// 模板目录不存在，返回空列表
		return []*BaseTemplate{}, nil
	}

	// 扫描所有模板目录
	dirs, err := ScanTemplateDirs(m.templateDir, MaxTfDepth)
	if err != nil {
		return nil, fmt.Errorf("failed to scan template directories: %w", err)
	}

	var baseTemplates []*BaseTemplate

	// 遍历每个模板目录，检查是否为基础模板
	for _, dir := range dirs {
		isBase, err := m.IsBaseTemplate(dir)
		if err != nil {
			// 跳过无法读取的模板
			continue
		}

		if isBase {
			// 读取模板元数据
			template, err := m.readBaseTemplateMetadata(dir)
			if err != nil {
				// 跳过无法解析的模板
				continue
			}
			baseTemplates = append(baseTemplates, template)
		}
	}

	return baseTemplates, nil
}

// IsBaseTemplate 判断是否为基础模板
// 通过读取 case.json 中的 template 字段判断
func (m *TemplateManager) IsBaseTemplate(templatePath string) (bool, error) {
	caseFilePath := filepath.Join(templatePath, TmplCaseFile)

	// 读取 case.json 文件
	data, err := os.ReadFile(caseFilePath)
	if err != nil {
		return false, fmt.Errorf("failed to read case.json: %w", err)
	}

	// 解析 JSON
	var caseData caseJSON
	if err := json.Unmarshal(data, &caseData); err != nil {
		return false, fmt.Errorf("failed to parse case.json: %w", err)
	}

	return caseData.TemplateType == TemplateTypeBase, nil
}

// GetTemplateVariables 获取模板变量定义
// 解析 variables.tf 文件，提取变量定义（名称、类型、描述、默认值、验证规则）
func (m *TemplateManager) GetTemplateVariables(templateName string) ([]TemplateVariable, error) {
	// 构建模板路径
	templatePath := filepath.Join(m.templateDir, templateName)
	
	// 检查模板目录是否存在
	if _, err := os.Stat(templatePath); os.IsNotExist(err) {
		return nil, fmt.Errorf("template not found: %s", templateName)
	}

	// 构建 variables.tf 文件路径
	variablesFilePath := filepath.Join(templatePath, "variables.tf")
	
	// 检查 variables.tf 文件是否存在
	if _, err := os.Stat(variablesFilePath); os.IsNotExist(err) {
		// 如果没有 variables.tf 文件，返回空列表
		return []TemplateVariable{}, nil
	}

	// 解析 variables.tf 文件
	variables, err := parseVariablesFile(variablesFilePath)
	if err != nil {
		return nil, fmt.Errorf("failed to parse variables.tf: %w", err)
	}

	return variables, nil
}

// readBaseTemplateMetadata 读取基础模板的元数据
func (m *TemplateManager) readBaseTemplateMetadata(templatePath string) (*BaseTemplate, error) {
	caseFilePath := filepath.Join(templatePath, TmplCaseFile)

	// 读取 case.json 文件
	data, err := os.ReadFile(caseFilePath)
	if err != nil {
		return nil, fmt.Errorf("failed to read case.json: %w", err)
	}

	// 解析 JSON
	var caseData caseJSON
	if err := json.Unmarshal(data, &caseData); err != nil {
		return nil, fmt.Errorf("failed to parse case.json: %w", err)
	}

	// 计算相对路径作为模板名称
	relPath, err := filepath.Rel(m.templateDir, templatePath)
	if err != nil {
		relPath = filepath.Base(templatePath)
	}
	templateName := filepath.ToSlash(relPath)

	// 获取模板变量
	variables, err := m.GetTemplateVariables(templateName)
	if err != nil {
		// 如果无法解析变量，记录错误但不中断
		variables = []TemplateVariable{}
	}

	// 构建 BaseTemplate 对象
	template := &BaseTemplate{
		Name:         templateName,
		Description:  caseData.Description,
		DescriptionEN: caseData.DescriptionEN,
		Version:      caseData.Version,
		User:         caseData.User,
		RedcModule:   caseData.RedcModule,
		TemplateType: caseData.TemplateType,
		Provider:     caseData.Provider, // 单一云厂商
		Providers:    caseData.SupportedProviders, // 支持的云厂商列表（向后兼容）
		Variables:    variables,
	}

	return template, nil
}

// parseVariablesFile 解析 variables.tf 文件，提取变量定义
func parseVariablesFile(filePath string) ([]TemplateVariable, error) {
	// 读取文件内容
	content, err := os.ReadFile(filePath)
	if err != nil {
		return nil, fmt.Errorf("failed to read file: %w", err)
	}

	// 使用 HCL 解析器解析文件
	file, diags := hclsyntax.ParseConfig(content, filePath, hcl.Pos{Line: 1, Column: 1})
	if diags.HasErrors() {
		return nil, fmt.Errorf("failed to parse HCL: %s", diags.Error())
	}

	var variables []TemplateVariable

	// 遍历文件中的所有块
	for _, block := range file.Body.(*hclsyntax.Body).Blocks {
		// 只处理 variable 块
		if block.Type != "variable" {
			continue
		}

		// 变量名称是块的标签
		if len(block.Labels) == 0 {
			continue
		}
		varName := block.Labels[0]

		// 解析变量属性
		variable := TemplateVariable{
			Name:     varName,
			Required: true, // 默认为必需，除非有 default 值
		}

		// 遍历块中的属性
		attrs := block.Body.Attributes
		
		// 解析 type
		if typeAttr, exists := attrs["type"]; exists {
			variable.Type = extractTypeString(typeAttr.Expr)
		}

		// 解析 description
		if descAttr, exists := attrs["description"]; exists {
			if desc, err := extractStringValue(descAttr.Expr); err == nil {
				variable.Description = desc
			}
		}

		// 解析 default
		if defaultAttr, exists := attrs["default"]; exists {
			if defaultVal, err := extractDefaultValue(defaultAttr.Expr); err == nil {
				variable.DefaultValue = defaultVal
				variable.Required = false // 有默认值则不是必需的
			}
		}

		// 解析 sensitive
		// sensitive 属性不影响我们的数据结构，但可以记录

		// 解析 validation 块
		for _, validationBlock := range block.Body.Blocks {
			if validationBlock.Type == "validation" {
				validation := parseValidationBlock(validationBlock)
				if validation != nil {
					variable.Validation = validation
				}
			}
		}

		variables = append(variables, variable)
	}

	return variables, nil
}

// extractTypeString 从 HCL 表达式中提取类型字符串
func extractTypeString(expr hclsyntax.Expression) string {
	// 处理简单类型（string, number, bool）
	if scopeTraversal, ok := expr.(*hclsyntax.ScopeTraversalExpr); ok {
		if len(scopeTraversal.Traversal) > 0 {
			if root, ok := scopeTraversal.Traversal[0].(hcl.TraverseRoot); ok {
				return root.Name
			}
		}
	}

	// 处理复杂类型（list, map, object 等）
	if funcCall, ok := expr.(*hclsyntax.FunctionCallExpr); ok {
		return funcCall.Name
	}

	// 默认返回 string
	return "string"
}

// extractStringValue 从 HCL 表达式中提取字符串值
func extractStringValue(expr hclsyntax.Expression) (string, error) {
	if template, ok := expr.(*hclsyntax.TemplateExpr); ok {
		if len(template.Parts) == 1 {
			if literal, ok := template.Parts[0].(*hclsyntax.LiteralValueExpr); ok {
				return literal.Val.AsString(), nil
			}
		}
	}
	return "", fmt.Errorf("not a string literal")
}

// extractDefaultValue 从 HCL 表达式中提取默认值
func extractDefaultValue(expr hclsyntax.Expression) (string, error) {
	// 处理字符串字面量
	if template, ok := expr.(*hclsyntax.TemplateExpr); ok {
		if len(template.Parts) == 1 {
			if literal, ok := template.Parts[0].(*hclsyntax.LiteralValueExpr); ok {
				return literal.Val.AsString(), nil
			}
		}
	}

	// 处理其他字面量（数字、布尔值）
	if literal, ok := expr.(*hclsyntax.LiteralValueExpr); ok {
		val := literal.Val
		if val.Type().Equals(cty.String) {
			return val.AsString(), nil
		} else if val.Type().Equals(cty.Number) {
			f, _ := val.AsBigFloat().Float64()
			return fmt.Sprintf("%v", f), nil
		} else if val.Type().Equals(cty.Bool) {
			return fmt.Sprintf("%v", val.True()), nil
		}
	}

	// 对于复杂类型，返回空字符串
	return "", nil
}

// parseValidationBlock 解析 validation 块
func parseValidationBlock(block *hclsyntax.Block) *VariableValidation {
	validation := &VariableValidation{}

	// 解析 condition 表达式以提取验证规则
	if condAttr, exists := block.Body.Attributes["condition"]; exists {
		// 尝试从 condition 表达式中提取验证信息
		extractValidationRules(condAttr.Expr, validation)
	}

	// 如果没有提取到任何验证规则，返回 nil
	if validation.Pattern == "" && len(validation.AllowedValues) == 0 && 
	   validation.MinLength == 0 && validation.MaxLength == 0 {
		return nil
	}

	return validation
}

// extractValidationRules 从 condition 表达式中提取验证规则
func extractValidationRules(expr hclsyntax.Expression, validation *VariableValidation) {
	// 处理 contains() 函数调用
	if funcCall, ok := expr.(*hclsyntax.FunctionCallExpr); ok {
		if funcCall.Name == "contains" && len(funcCall.Args) == 2 {
			// 第一个参数是允许的值列表
			if tuple, ok := funcCall.Args[0].(*hclsyntax.TupleConsExpr); ok {
				var allowedValues []string
				for _, elem := range tuple.Exprs {
					if val, err := extractStringValue(elem); err == nil {
						allowedValues = append(allowedValues, val)
					}
				}
				validation.AllowedValues = allowedValues
			}
		}
	}

	// 可以扩展以支持其他验证模式（regex、length 等）
}
