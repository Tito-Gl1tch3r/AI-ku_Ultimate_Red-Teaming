package mod

import (
	"fmt"
	"sort"
)

// GetUsageStats builds a usage statistics string from existing cases
func GetUsageStats(projectName string) string {
	cases, err := LoadProjectCases(projectName)
	if err != nil || len(cases) == 0 {
		return ""
	}

	// Count template usage
	templateCount := make(map[string]int)
	providerCount := make(map[string]int)
	for _, c := range cases {
		templateCount[c.Type]++
		// Extract provider from type (e.g., "aws/ec2" → "aws")
		provider := c.Type
		for i, ch := range c.Type {
			if ch == '/' {
				provider = c.Type[:i]
				break
			}
		}
		providerCount[provider]++
	}

	// Sort templates by usage count
	type kv struct {
		Key   string
		Count int
	}
	var sorted []kv
	for k, v := range templateCount {
		sorted = append(sorted, kv{k, v})
	}
	sort.Slice(sorted, func(i, j int) bool { return sorted[i].Count > sorted[j].Count })

	// Build output
	result := "### 使用统计\n"

	// Top 5 templates
	result += "- 常用模板："
	limit := 5
	if len(sorted) < limit {
		limit = len(sorted)
	}
	for i := 0; i < limit; i++ {
		if i > 0 {
			result += ", "
		}
		result += fmt.Sprintf("%s (%d次)", sorted[i].Key, sorted[i].Count)
	}
	result += "\n"

	// Provider distribution
	var provSorted []kv
	for k, v := range providerCount {
		provSorted = append(provSorted, kv{k, v})
	}
	sort.Slice(provSorted, func(i, j int) bool { return provSorted[i].Count > provSorted[j].Count })
	result += "- 云厂商偏好："
	for i, p := range provSorted {
		if i > 0 {
			result += " > "
		}
		result += p.Key
	}
	result += "\n"

	return result
}
