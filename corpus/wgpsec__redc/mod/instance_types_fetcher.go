package mod

import (
	"fmt"
	"os"
	
	"github.com/aliyun/alibaba-cloud-sdk-go/services/ecs"
	"github.com/volcengine/volcengine-go-sdk/volcengine"
	"github.com/volcengine/volcengine-go-sdk/volcengine/credentials"
	"github.com/volcengine/volcengine-go-sdk/volcengine/session"
	volcengine_ecs "github.com/volcengine/volcengine-go-sdk/service/ecs"
)

// fetchInstanceTypesFromProviderAPI 从云厂商 API 获取实例规格（使用真实 SDK）
// 这个函数会尝试使用配置的凭证调用云厂商 API
// 如果失败（如凭证未配置），则回退到静态数据
func fetchInstanceTypesFromProviderAPI(provider, region string) ([]InstanceType, error) {
	// 优先从配置文件中获取凭证，如果没有则从环境变量获取
	accessKey, secretKey := GetProviderCredentials(provider)
	
	// 如果从配置文件获取失败，尝试从环境变量获取
	if accessKey == "" || secretKey == "" {
		switch provider {
		case "volcengine":
			accessKey = os.Getenv("VOLCENGINE_ACCESS_KEY")
			secretKey = os.Getenv("VOLCENGINE_SECRET_KEY")
		case "alicloud":
			accessKey = os.Getenv("ALICLOUD_ACCESS_KEY")
			secretKey = os.Getenv("ALICLOUD_SECRET_KEY")
		case "tencentcloud":
			accessKey = os.Getenv("TENCENTCLOUD_SECRET_ID")
			secretKey = os.Getenv("TENCENTCLOUD_SECRET_KEY")
		case "aws":
			accessKey = os.Getenv("AWS_ACCESS_KEY_ID")
			secretKey = os.Getenv("AWS_SECRET_ACCESS_KEY")
		case "huaweicloud":
			accessKey = os.Getenv("HUAWEICLOUD_ACCESS_KEY")
			secretKey = os.Getenv("HUAWEICLOUD_SECRET_KEY")
		}
	}
	
	switch provider {
	case "volcengine":
		if accessKey != "" && secretKey != "" {
			// 调用火山引擎 API
			types, err := fetchVolcengineInstanceTypesFromAPI(region, accessKey, secretKey)
			if err == nil {
				return types, nil
			}
			// API 调用失败，记录错误但继续使用静态数据
			fmt.Printf("警告: 调用火山引擎 API 失败: %v，使用静态数据\n", err)
		}
		
	case "alicloud":
		if accessKey != "" && secretKey != "" {
			types, err := fetchAlicloudInstanceTypesFromAPI(region, accessKey, secretKey)
			if err == nil {
				return types, nil
			}
			fmt.Printf("警告: 调用阿里云 API 失败: %v，使用静态数据\n", err)
		}
		
	case "tencentcloud":
		if accessKey != "" && secretKey != "" {
			types, err := fetchTencentcloudInstanceTypesFromAPI(region, accessKey, secretKey)
			if err == nil {
				return types, nil
			}
			fmt.Printf("警告: 调用腾讯云 API 失败: %v，使用静态数据\n", err)
		}
		
	case "aws":
		accessKey = os.Getenv("AWS_ACCESS_KEY_ID")
		secretKey = os.Getenv("AWS_SECRET_ACCESS_KEY")
		
		if accessKey != "" && secretKey != "" {
			types, err := fetchAWSInstanceTypesFromAPI(region, accessKey, secretKey)
			if err == nil {
				return types, nil
			}
			fmt.Printf("警告: 调用 AWS API 失败: %v，使用静态数据\n", err)
		}
		
	case "huaweicloud":
		accessKey = os.Getenv("HUAWEICLOUD_ACCESS_KEY")
		secretKey = os.Getenv("HUAWEICLOUD_SECRET_KEY")
		
		if accessKey != "" && secretKey != "" {
			types, err := fetchHuaweicloudInstanceTypesFromAPI(region, accessKey, secretKey)
			if err == nil {
				return types, nil
			}
			fmt.Printf("警告: 调用华为云 API 失败: %v，使用静态数据\n", err)
		}
	}
	
	// 如果凭证未配置或 API 调用失败，回退到静态数据
	// 直接调用静态函数，避免循环依赖
	switch provider {
	case "volcengine":
		return fetchVolcengineInstanceTypesStatic(region)
	case "alicloud":
		return fetchAlicloudInstanceTypesStatic(region)
	case "tencentcloud":
		return fetchTencentcloudInstanceTypesStatic(region)
	case "aws":
		return fetchAWSInstanceTypesStatic(region)
	case "huaweicloud":
		return fetchHuaweicloudInstanceTypesStatic(region)
	default:
		return nil, fmt.Errorf("不支持的云厂商: %s", provider)
	}
}

// fetchVolcengineInstanceTypesFromAPI 从火山引擎 API 获取实例规格
func fetchVolcengineInstanceTypesFromAPI(region, accessKey, secretKey string) ([]InstanceType, error) {
	// 创建火山引擎配置
	config := volcengine.NewConfig().
		WithRegion(region).
		WithCredentials(credentials.NewStaticCredentials(accessKey, secretKey, ""))
	
	// 创建会话
	sess, err := session.NewSession(config)
	if err != nil {
		return nil, fmt.Errorf("创建火山引擎会话失败: %w", err)
	}
	
	// 创建 ECS 客户端
	client := volcengine_ecs.New(sess)
	
	// 调用 DescribeInstanceTypes API
	input := &volcengine_ecs.DescribeInstanceTypesInput{}
	
	output, err := client.DescribeInstanceTypes(input)
	if err != nil {
		return nil, fmt.Errorf("调用火山引擎 API 失败: %w", err)
	}
	
	if output == nil || output.InstanceTypes == nil || len(output.InstanceTypes) == 0 {
		return nil, fmt.Errorf("未找到任何实例规格")
	}
	
	// 转换为内部格式
	var types []InstanceType
	for _, it := range output.InstanceTypes {
		if it.InstanceTypeId == nil {
			continue
		}
		
		cpu := 0
		memory := 0
		family := ""
		
		// 提取 CPU 核数
		if it.Processor != nil && it.Processor.Cpus != nil {
			cpu = int(*it.Processor.Cpus)
		}
		
		// 提取内存大小（API 返回的单位已经是 MB）
		if it.Memory != nil && it.Memory.Size != nil {
			memory = int(*it.Memory.Size)
		}
		
		// 提取实例族
		if it.InstanceTypeFamily != nil {
			family = *it.InstanceTypeFamily
		}
		
		types = append(types, InstanceType{
			Code:        *it.InstanceTypeId,
			Name:        family,
			CPU:         cpu,
			Memory:      memory,
			Description: fmt.Sprintf("%d核%dGB", cpu, memory/1024),
		})
	}
	
	if len(types) == 0 {
		return nil, fmt.Errorf("未找到任何实例规格")
	}
	
	return types, nil
}

// fetchAlicloudInstanceTypesFromAPI 从阿里云 API 获取实例规格
func fetchAlicloudInstanceTypesFromAPI(region, accessKey, secretKey string) ([]InstanceType, error) {
	// 创建阿里云客户端
	client, err := ecs.NewClientWithAccessKey(region, accessKey, secretKey)
	if err != nil {
		return nil, fmt.Errorf("创建阿里云客户端失败: %w", err)
	}
	
	// 使用 DescribeAvailableResource 查询指定区域的可用实例规格
	request := ecs.CreateDescribeAvailableResourceRequest()
	request.Scheme = "https"
	request.RegionId = region
	request.DestinationResource = "InstanceType"
	
	// 调用 API
	response, err := client.DescribeAvailableResource(request)
	if err != nil {
		return nil, fmt.Errorf("调用阿里云 API 失败: %w", err)
	}
	
	if response == nil || len(response.AvailableZones.AvailableZone) == 0 {
		return nil, fmt.Errorf("未找到任何可用区")
	}
	
	// 使用 map 去重，因为多个可用区可能有相同的实例规格
	instanceTypeMap := make(map[string]bool)
	
	// 遍历所有可用区，收集实例规格信息
	for _, zone := range response.AvailableZones.AvailableZone {
		for _, resource := range zone.AvailableResources.AvailableResource {
			for _, instanceType := range resource.SupportedResources.SupportedResource {
				if instanceType.Status == "Available" {
					// 使用 map 去重
					instanceTypeMap[instanceType.Value] = true
				}
			}
		}
	}
	
	if len(instanceTypeMap) == 0 {
		return nil, fmt.Errorf("该区域未找到可用的实例规格")
	}
	
	fmt.Printf("阿里云区域 %s 找到 %d 个可用实例规格\n", region, len(instanceTypeMap))
	
	// 转换为内部格式
	// 注意：DescribeAvailableResource 返回的数据中已经包含了基本信息
	// 但为了获取详细的 CPU、内存等信息，我们需要调用 DescribeInstanceTypes
	// 由于阿里云 API 不支持按 ID 列表查询，我们只能获取全部然后过滤
	detailRequest := ecs.CreateDescribeInstanceTypesRequest()
	detailRequest.Scheme = "https"
	
	detailResponse, err := client.DescribeInstanceTypes(detailRequest)
	if err != nil {
		return nil, fmt.Errorf("获取实例规格详情失败: %w", err)
	}
	
	// 转换为内部格式，只保留该区域可用的实例规格
	var types []InstanceType
	for _, it := range detailResponse.InstanceTypes.InstanceType {
		// 只保留在可用列表中的实例规格，并且支持 ENI
		if instanceTypeMap[it.InstanceTypeId] && it.EniQuantity > 0 {
			types = append(types, InstanceType{
				Code:        it.InstanceTypeId,
				Name:        it.InstanceTypeFamily,
				CPU:         it.CpuCoreCount,
				Memory:      int(it.MemorySize * 1024), // 阿里云返回的是 GB，转换为 MB
				Description: fmt.Sprintf("%d核%.0fGB", it.CpuCoreCount, it.MemorySize),
			})
		}
	}
	
	if len(types) == 0 {
		return nil, fmt.Errorf("未找到支持 VPC 的实例规格")
	}
	
	fmt.Printf("过滤后返回 %d 个实例规格\n", len(types))
	
	return types, nil
}

// fetchTencentcloudInstanceTypesFromAPI 从腾讯云 API 获取实例规格
func fetchTencentcloudInstanceTypesFromAPI(region, secretId, secretKey string) ([]InstanceType, error) {
	// TODO: 实现腾讯云 SDK 调用
	return nil, fmt.Errorf("腾讯云 SDK 集成尚未实现")
}

// fetchAWSInstanceTypesFromAPI 从 AWS API 获取实例规格
func fetchAWSInstanceTypesFromAPI(region, accessKey, secretKey string) ([]InstanceType, error) {
	// TODO: 实现 AWS SDK 调用
	return nil, fmt.Errorf("AWS SDK 集成尚未实现")
}

// fetchHuaweicloudInstanceTypesFromAPI 从华为云 API 获取实例规格
func fetchHuaweicloudInstanceTypesFromAPI(region, accessKey, secretKey string) ([]InstanceType, error) {
	// TODO: 实现华为云 SDK 调用
	return nil, fmt.Errorf("华为云 SDK 集成尚未实现")
}
