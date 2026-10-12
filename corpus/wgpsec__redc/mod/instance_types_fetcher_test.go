package mod

import (
	"os"
	"testing"
)

// TestFetchVolcengineInstanceTypesFromAPI 测试火山引擎 API 调用
// 注意：这个测试需要配置真实的凭证才能通过
func TestFetchVolcengineInstanceTypesFromAPI(t *testing.T) {
	// 从环境变量获取凭证
	accessKey := os.Getenv("VOLCENGINE_ACCESS_KEY")
	secretKey := os.Getenv("VOLCENGINE_SECRET_KEY")
	
	if accessKey == "" || secretKey == "" {
		t.Skip("跳过测试: 未配置 VOLCENGINE_ACCESS_KEY 或 VOLCENGINE_SECRET_KEY 环境变量")
	}
	
	// 测试北京区域
	region := "cn-beijing"
	types, err := fetchVolcengineInstanceTypesFromAPI(region, accessKey, secretKey)
	
	if err != nil {
		t.Fatalf("调用火山引擎 API 失败: %v", err)
	}
	
	if len(types) == 0 {
		t.Fatal("返回的实例规格列表为空")
	}
	
	// 验证返回的数据格式
	for i, it := range types {
		if it.Code == "" {
			t.Errorf("实例规格 %d 的 Code 为空", i)
		}
		if it.CPU <= 0 {
			t.Errorf("实例规格 %s 的 CPU 数量无效: %d", it.Code, it.CPU)
		}
		if it.Memory <= 0 {
			t.Errorf("实例规格 %s 的内存大小无效: %d", it.Code, it.Memory)
		}
		
		// 打印所有实例规格
		t.Logf("实例规格 %d: %s - %s (%d核%dMB)", i+1, it.Code, it.Name, it.CPU, it.Memory)
	}
	
	t.Logf("成功获取 %d 个实例规格", len(types))
}

// TestFetchInstanceTypesFromProviderAPI_Fallback 测试 API 调用失败时的降级行为
func TestFetchInstanceTypesFromProviderAPI_Fallback(t *testing.T) {
	// 测试火山引擎（不配置凭证，应该返回错误并降级到静态数据）
	types, err := fetchInstanceTypesFromProviderAPI("volcengine", "cn-beijing")
	
	// 应该返回错误（因为没有凭证）
	if err == nil {
		t.Log("警告: 预期返回错误（凭证未配置），但调用成功了")
	}
	
	// 但是通过 fetchInstanceTypesFromProvider 应该能获取到静态数据
	types, err = fetchInstanceTypesFromProvider("volcengine", "cn-beijing")
	if err != nil {
		t.Fatalf("获取静态数据失败: %v", err)
	}
	
	if len(types) == 0 {
		t.Fatal("静态数据为空")
	}
	
	t.Logf("降级到静态数据成功，获取 %d 个实例规格", len(types))
}

// TestFetchVolcengineInstanceTypesStatic 测试静态数据
func TestFetchVolcengineInstanceTypesStatic(t *testing.T) {
	testCases := []struct {
		region        string
		expectTypes   bool
		expectMinimum int
	}{
		{"cn-beijing", true, 2},
		{"cn-shanghai", true, 2},
		{"cn-guangzhou", true, 2},
		{"cn-unknown", true, 2}, // 未知区域应该返回默认列表
	}
	
	for _, tc := range testCases {
		t.Run(tc.region, func(t *testing.T) {
			types, err := fetchVolcengineInstanceTypesStatic(tc.region)
			
			if err != nil {
				t.Fatalf("获取静态数据失败: %v", err)
			}
			
			if tc.expectTypes && len(types) < tc.expectMinimum {
				t.Errorf("期望至少 %d 个实例规格，实际获取 %d 个", tc.expectMinimum, len(types))
			}
			
			// 验证数据格式
			for _, it := range types {
				if it.Code == "" {
					t.Error("实例规格 Code 为空")
				}
				if it.CPU <= 0 {
					t.Errorf("实例规格 %s 的 CPU 数量无效: %d", it.Code, it.CPU)
				}
				if it.Memory <= 0 {
					t.Errorf("实例规格 %s 的内存大小无效: %d", it.Code, it.Memory)
				}
			}
			
			t.Logf("区域 %s: 获取 %d 个实例规格", tc.region, len(types))
		})
	}
}

// TestGetInstanceTypes_Integration 测试完整的集成流程
func TestGetInstanceTypes_Integration(t *testing.T) {
	// 测试火山引擎北京区域
	types, err := GetInstanceTypes("volcengine", "cn-beijing")
	
	if err != nil {
		t.Fatalf("获取实例规格失败: %v", err)
	}
	
	if len(types) == 0 {
		t.Fatal("返回的实例规格列表为空")
	}
	
	// 验证缓存是否工作
	// 第二次调用应该从缓存获取
	types2, err := GetInstanceTypes("volcengine", "cn-beijing")
	
	if err != nil {
		t.Fatalf("第二次获取实例规格失败: %v", err)
	}
	
	if len(types2) != len(types) {
		t.Errorf("缓存数据不一致: 第一次 %d 个，第二次 %d 个", len(types), len(types2))
	}
	
	t.Logf("集成测试成功，获取 %d 个实例规格", len(types))
}
