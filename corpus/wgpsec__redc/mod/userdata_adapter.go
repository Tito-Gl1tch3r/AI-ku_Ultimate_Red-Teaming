package mod

import (
	"encoding/base64"
)

// AdaptUserdata 根据云厂商处理 userdata 格式差异
// 不同云厂商的 userdata 格式要求：
// - alicloud: 支持 base64 编码
// - tencentcloud: 使用原始文本
// - aws: 支持 base64 编码
// - volcengine: 使用原始文本
// - huaweicloud: 使用原始文本
func AdaptUserdata(provider, userdata string) (string, error) {
	// 如果 userdata 为空，直接返回
	if userdata == "" {
		return "", nil
	}

	switch provider {
	case "alicloud":
		// 阿里云支持 base64 编码
		return base64.StdEncoding.EncodeToString([]byte(userdata)), nil
	case "tencentcloud":
		// 腾讯云直接使用原始文本
		return userdata, nil
	case "aws":
		// AWS 支持 base64 编码
		return base64.StdEncoding.EncodeToString([]byte(userdata)), nil
	case "volcengine":
		// 火山引擎使用原始文本
		return userdata, nil
	case "huaweicloud":
		// 华为云使用原始文本
		return userdata, nil
	default:
		// 不支持的云厂商，返回错误
		return "", &ValidationError{
			Field:   "provider",
			Message: "不支持的云厂商: " + provider,
			Code:    ErrCodeNotSupported,
		}
	}
}
