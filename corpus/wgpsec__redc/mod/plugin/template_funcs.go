// mod/plugin/template_funcs.go
package plugin

import (
	"encoding/base64"
	"encoding/json"
	"fmt"
	"net/url"
	"os"
	"strconv"
	"strings"
	"text/template"
)

func BuiltinFuncs() template.FuncMap {
	return template.FuncMap{
		"default":      fnDefault,
		"join":         fnJoin,
		"split":        fnSplit,
		"base64Encode": fnBase64Encode,
		"base64Decode": fnBase64Decode,
		"urlEncode":    url.QueryEscape,
		"toJSON":       fnToJSON,
		"jsonParse":    fnJsonParse,
		"jsonPath":     fnJsonPath,
		"dict":         fnDict,
		"trimSpace":    strings.TrimSpace,
		"upper":        strings.ToUpper,
		"lower":        strings.ToLower,
		"replace":      fnReplace,
		"contains":     strings.Contains,
		"printf":       fmt.Sprintf,
		"len":          fnLen,
		"env":          fnEnv,
		"add":          func(a, b int) int { return a + b },
		"httpGet":      fnHTTPGet,
		"httpPost":     fnHTTPPost,
		"httpPut":      fnHTTPPut,
		"httpDelete":   fnHTTPDelete,
		"exec":         fnExec,
	}
}

func fnDefault(defaultVal, val interface{}) interface{} {
	if val == nil {
		return defaultVal
	}
	if s, ok := val.(string); ok && s == "" {
		return defaultVal
	}
	return val
}

func fnJoin(sep string, elems interface{}) string {
	switch v := elems.(type) {
	case []string:
		return strings.Join(v, sep)
	case []interface{}:
		strs := make([]string, len(v))
		for i, e := range v {
			strs[i] = fmt.Sprintf("%v", e)
		}
		return strings.Join(strs, sep)
	default:
		return fmt.Sprintf("%v", elems)
	}
}

func fnSplit(sep, s string) []string {
	return strings.Split(s, sep)
}

func fnBase64Encode(s string) string {
	return base64.StdEncoding.EncodeToString([]byte(s))
}

func fnBase64Decode(s string) (string, error) {
	b, err := base64.StdEncoding.DecodeString(s)
	if err != nil {
		return "", err
	}
	return string(b), nil
}

func fnToJSON(v interface{}) (string, error) {
	b, err := json.Marshal(v)
	if err != nil {
		return "", err
	}
	return string(b), nil
}

func fnJsonParse(s string) (interface{}, error) {
	var result interface{}
	if err := json.Unmarshal([]byte(s), &result); err != nil {
		return nil, err
	}
	return result, nil
}

func fnJsonPath(path string, obj interface{}) (interface{}, error) {
	parts := strings.Split(path, ".")
	current := obj
	for _, part := range parts {
		if current == nil {
			return nil, fmt.Errorf("jsonPath: nil at %q", part)
		}
		switch v := current.(type) {
		case map[string]interface{}:
			current = v[part]
		case map[string]string:
			current = v[part]
		case []interface{}:
			idx, err := strconv.Atoi(part)
			if err != nil || idx < 0 || idx >= len(v) {
				return nil, fmt.Errorf("jsonPath: invalid index %q", part)
			}
			current = v[idx]
		default:
			return nil, fmt.Errorf("jsonPath: cannot navigate %T with key %q", current, part)
		}
	}
	return current, nil
}

func fnDict(pairs ...interface{}) (map[string]interface{}, error) {
	if len(pairs)%2 != 0 {
		return nil, fmt.Errorf("dict: odd number of arguments")
	}
	m := make(map[string]interface{}, len(pairs)/2)
	for i := 0; i < len(pairs); i += 2 {
		key := fmt.Sprintf("%v", pairs[i])
		m[key] = pairs[i+1]
	}
	return m, nil
}

func fnReplace(old, new, s string) string {
	return strings.ReplaceAll(s, old, new)
}

func fnLen(v interface{}) (int, error) {
	switch val := v.(type) {
	case string:
		return len(val), nil
	case []string:
		return len(val), nil
	case []interface{}:
		return len(val), nil
	case map[string]interface{}:
		return len(val), nil
	case map[string]string:
		return len(val), nil
	default:
		return 0, fmt.Errorf("len: unsupported type %T", v)
	}
}

func fnEnv(name string) string {
	if !strings.HasPrefix(name, "REDC_") {
		return ""
	}
	val, _ := os.LookupEnv(name)
	return val
}
