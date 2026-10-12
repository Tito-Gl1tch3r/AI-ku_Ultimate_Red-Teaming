package mod

import (
	"fmt"
	"os"
	"path/filepath"
	"red-cloud/i18n"
	"red-cloud/mod/gologger"
	"red-cloud/pb"
	"strings"
	"text/tabwriter"
	"time"

	bolt "go.etcd.io/bbolt"
	"google.golang.org/protobuf/proto"
)

type ChangeCommand struct {
	IsRemove bool
	Pars     map[string]string
}

func GetProjectCase(projectId string, caseID string, userName string) (*Case, error) {
	pro, err := ProjectParse(projectId, userName) // 注意：这里可能需要处理 global U 或者从配置读取
	if err != nil {
		gologger.Fatal().Msgf("%s", i18n.Tf("project_parse_failed", err))
	}
	c, err := pro.GetCase(caseID)
	if err != nil {
		return nil, fmt.Errorf("%s", i18n.Tf("project_case_not_found", caseID, err))

	}
	return c, nil
}

// NewProjectConfig 创建项目配置文件
func NewProjectConfig(name string, user string) (*RedcProject, error) {
	path := filepath.Join(ProjectPath, name)
	// 创建项目目录
	if err := os.MkdirAll(path, 0755); err != nil {
		return nil, fmt.Errorf("%s", i18n.Tf("project_create_dir_failed", err))
	}
	// 创建项目状态文件
	currentTime := time.Now().Format("2006-01-02 15:04:05")
	project := &RedcProject{
		ProjectName: name,
		ProjectPath: path,
		CreateTime:  currentTime,
		User:        user,
	}

	// 保存到 DB
	if err := project.SaveMeta(); err != nil {
		return nil, fmt.Errorf("%s", i18n.Tf("project_save_db_failed", err))
	}
	gologger.Info().Msg(i18n.T("project_db_created"))
	return project, nil

}

func ProjectParse(name string, user string) (*RedcProject, error) {
	// 尝试直接读取项目
	if p, err := LoadProjectMeta(name); err == nil {
		// 项目鉴权
		if p.User != user && user != "system" {
			return nil, fmt.Errorf("%s", i18n.Tf("project_no_permission", user, name))
		}
		return p, nil
	}
	// 项目不存在，走创建逻辑 (保持不变)
	path := filepath.Join(ProjectPath, name)
	if _, statErr := os.Stat(path); os.IsNotExist(statErr) {
		gologger.Info().Msgf("%s", i18n.Tf("project_creating", name))
		return NewProjectConfig(name, user)
	}
	return NewProjectConfig(name, user)
}

// GetCase 支持通过 ID(精确/模糊) 或 Name(精确) 查找 Case
// 逻辑参考 Docker: 优先精确匹配，其次 ID 前缀匹配。如果 ID 前缀匹配到多个，则报错歧义。
func (p *RedcProject) GetCase(identifier string) (*Case, error) {
	c, err := FindCaseBySearch(p.ProjectName, identifier)
	if err != nil {
		return nil, err
	}

	// 2. 绑定运行时逻辑 (复活对象)
	c.bindHandlers()
	return c, nil
}

// FindCaseBySearch 数据库层面的搜索 (Docker 风格：ID精确 -> Name精确 -> ID前缀)
// 这个函数虽然会遍历，但它不占用内存，因为它边读边丢，只留匹配的那一个
func FindCaseBySearch(projectID, keyword string) (*Case, error) {
	var candidates []*Case

	err := dbExec(func(tx *bolt.Tx) error {
		b := tx.Bucket([]byte(fmt.Sprintf("Cases_%s", projectID)))
		if b == nil {
			return fmt.Errorf("%s", i18n.T("project_no_data"))
		}

		// 1. 尝试直接按 ID 获取 (最快，O(1))
		if data := b.Get([]byte(keyword)); data != nil {
			var p pb.Case
			err := proto.Unmarshal(data, &p)
			if err != nil {
				return fmt.Errorf("%s", i18n.Tf("project_parse_data_failed", err))
			}
			c := caseFromProto(&p)
			c.ProjectID = projectID
			candidates = append(candidates, c)
			return nil // 找到了，直接结束
		}

		// 2. 如果 ID 没找到，进行遍历搜索 (Name 精确匹配 或 ID 前缀匹配)
		// 注意：这里是流式读取，不会把所有数据加载到内存，内存占用极低
		return b.ForEach(func(k, v []byte) error {
			// 优化：先只匹配 ID 前缀 (Key)，不反序列化 Value，速度快
			keyStr := string(k)

			// 匹配 ID 前缀
			matchPrefix := strings.HasPrefix(keyStr, keyword)

			// 如果 ID 前缀不匹配，才不得不反序列化看 Name (稍微慢点，但必须做)
			// 但为了逻辑简单，这里统一反序列化检查
			// 生产环境可以优化为：另建一个 Name->ID 的索引桶

			var p pb.Case
			// 只有当 ID前缀匹配 或者 我们需要检查 Name 时才解析
			// 这里为了简单，我们还是解析一下，但内存是复用的
			if err := proto.Unmarshal(v, &p); err != nil {
				return nil
			}

			// 检查 Name 精确匹配
			if p.Name == keyword {
				c := caseFromProto(&p)
				c.ProjectID = projectID
				candidates = []*Case{c}               // 名字精确匹配优先级最高，清空其他的
				return fmt.Errorf("found_exact_name") // 用特殊 error 提前打断遍历
			}

			if matchPrefix {
				c := caseFromProto(&p)
				c.ProjectID = projectID
				candidates = append(candidates, c)
			}
			return nil
		})
	})

	// 处理特殊中断
	if err != nil && err.Error() == "found_exact_name" {
		return candidates[0], nil
	}
	if err != nil {
		return nil, err
	}

	// 结果判定
	if len(candidates) == 0 {
		return nil, fmt.Errorf("%s", i18n.Tf("project_case_not_found_keyword", keyword))
	}
	if len(candidates) > 1 {
		return nil, fmt.Errorf("%s", i18n.Tf("project_ambiguous_keyword", keyword, len(candidates)))
	}

	return candidates[0], nil
}

// HandleCase 删除指定uid的case
func (p *RedcProject) HandleCase(c *Case) error {
	// 调用 store 直接删除
	if err := c.DBRemove(); err != nil {
		return err
	}
	return nil
}

func (p *RedcProject) AddCase(c *Case) error {
	// 绑定 handler
	c.bindHandlers()
	// 保存到 DB
	if err := c.DBSave(); err != nil {
		return err
	}

	return nil
}

// CaseList 输出项目进程
func (p *RedcProject) CaseList() {
	cases, err := LoadProjectCases(p.ProjectName)
	if err != nil {
		gologger.Error().Msgf("%s", i18n.Tf("project_load_list_failed", err))
		return
	}

	// minwidth=0: 最小单元格宽度
	// tabwidth=8: tab 字符宽度
	// padding=3:  列之间至少保留 3 个空格（比原来的 1 个更清晰）
	// padchar=' ': 填充符
	// flags=0:    默认左对齐 (Docker 风格)，去掉 AlignRight
	w := tabwriter.NewWriter(os.Stdout, 0, 8, 3, ' ', 0)

	// 优化2: 表头全大写，符合 CLI 惯例
	// 并在每一列后明确加上 \t 进行分割
	fmt.Fprintln(w, "Case ID\tTYPE\tNAME\tOPERATOR\tCREATED\tSTATUS")

	for _, c := range cases {

		// ID过长显示前12位
		displayID := c.Id
		if len(c.Id) > 12 {
			displayID = c.Id[:12]
		}
		createTime := parseTime(c.StateTime) // 解析字符串时间
		var displayStatus string
		// 3. 这里使用 c.State 和新的常量
		switch c.State {
		case StateRunning:
			displayStatus = fmt.Sprintf("Up %s", humanDuration(createTime))

		case StateStopped:
			displayStatus = fmt.Sprintf("Exited (0) %s ago", humanDurationShort(createTime))

		case StateError:
			displayStatus = "Error"

		case StateCreated:
			displayStatus = "Created"

		// 如果之前的旧数据没有 State 字段，可能需要一个默认兜底
		case "":
			displayStatus = "Unknown"

		default:
			displayStatus = string(c.State)
		}

		// 使用 Fprintf 配合 \t 格式化输出
		fmt.Fprintf(w, "%s\t%s\t%s\t%s\t%s\t%s\n",
			displayID,
			c.Type,
			c.Name,
			c.Operator,
			c.CreateTime,
			displayStatus,
		)

	}

	// 刷新缓冲区，确保输出
	if err := w.Flush(); err != nil {
		// 假设 gologger 是你的日志库
		// gologger.Fatal().Msgf("表格输出失败: %s", err.Error())
		fmt.Fprintf(os.Stderr, "表格输出失败: %s\n", err.Error())
	}
}

//// SaveProject 保存修改后的项目
//func (p *RedcProject) SaveProject() error {
//
//	return nil
//}

// 简单的时长计算，返回 "2 hours", "5 minutes" 等
func humanDurationShort(t time.Time) string {
	d := time.Since(t)
	if d.Seconds() < 60 {
		return fmt.Sprintf("%.0f seconds", d.Seconds())
	} else if d.Minutes() < 60 {
		return fmt.Sprintf("%.0f minutes", d.Minutes())
	} else if d.Hours() < 24 {
		return fmt.Sprintf("%.0f hours", d.Hours())
	} else {
		return fmt.Sprintf("%.0f days", d.Hours()/24)
	}
}
