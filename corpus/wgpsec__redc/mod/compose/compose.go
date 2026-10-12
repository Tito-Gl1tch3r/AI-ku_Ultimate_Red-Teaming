package compose

import (
	"bufio"
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"regexp"
	"strings"

	"red-cloud/i18n"
	"red-cloud/mod/gologger"
	"red-cloud/utils/sshutil"

	"github.com/hashicorp/terraform-exec/tfexec"
)

// RunComposeUp 编排入口
func RunComposeUp(opts ComposeOptions) error {
	_, err := RunComposeUpWithResult(opts)
	return err
}

// ComposeUpResult 编排结果
type ComposeUpResult struct {
	Services []ComposeUpService `json:"services"`
}

// ComposeUpService 单个服务部署结果
type ComposeUpService struct {
	Name     string `json:"name"`
	Template string `json:"template"`
	CaseID   string `json:"case_id"`
	Status   string `json:"status"`
}

// RunComposeUpWithResult 编排入口（返回部署结果）
func RunComposeUpWithResult(opts ComposeOptions) (*ComposeUpResult, error) {
	// 1. 初始化 (调用 Core)
	ctx, err := NewComposeContext(opts)
	if err != nil {
		return nil, err
	}
	if err := VerifyTemplates(ctx); err != nil {
		return nil, err
	}

	ctx.emitLog(i18n.Tf("compose_deploy_total", len(ctx.RuntimeSvcs)))

	// 2. 编排循环
	pendingCount := len(ctx.RuntimeSvcs)
	deployed := 0
	for pendingCount > 0 {
		deployedInThisLoop := 0

		// 使用排序后的 Keys 遍历
		for _, name := range ctx.SortedSvcKeys {
			svc := ctx.RuntimeSvcs[name]

			if svc.IsDeployed {
				continue
			}

			if canDeploy(svc, ctx.RuntimeSvcs) {
				msg := i18n.Tf("compose_deploy_service", svc.Name, svc.Spec.Image)
				gologger.Info().Msgf("%s", msg)
				ctx.emitLog(msg)

				if err := processServiceUp(svc, ctx); err != nil {
					return nil, fmt.Errorf("部署服务 [%s] 失败: %v", svc.Name, err)
				}

				svc.IsDeployed = true
				deployedInThisLoop++
				deployed++
				pendingCount--
				ctx.emitLog(i18n.Tf("compose_deploy_progress", deployed, deployed+pendingCount))
			}
		}

		if deployedInThisLoop == 0 && pendingCount > 0 {
			return nil, fmt.Errorf("编排死锁: 存在循环依赖，或依赖的服务被 Profile 过滤未启动")
		}
	}

	// 3. 执行 Setup
	if len(ctx.ConfigRaw.Setup) > 0 {
		msg := i18n.T("compose_setup_start")
		gologger.Info().Msg(msg)
		ctx.emitLog(msg)
		if err := runSetupTasks(ctx.ConfigRaw.Setup, ctx.RuntimeSvcs, ctx); err != nil {
			return nil, err
		}
	}

	// 4. 收集部署结果
	result := &ComposeUpResult{}
	for _, name := range ctx.SortedSvcKeys {
		svc := ctx.RuntimeSvcs[name]
		s := ComposeUpService{
			Name:     svc.Name,
			Template: svc.Spec.Image,
			Status:   "deployed",
		}
		if svc.CaseRef != nil {
			s.CaseID = svc.CaseRef.Id
		}
		result.Services = append(result.Services, s)
	}

	return result, nil
}

// RunComposeDown 销毁入口
func RunComposeDown(opts ComposeOptions) error {
	ctx, err := NewComposeContext(opts)
	if err != nil {
		return err
	}

	// 状态回填
	pendingCount := 0
	for _, name := range ctx.SortedSvcKeys {
		svc := ctx.RuntimeSvcs[name]
		c, err := ctx.Project.GetCase(svc.Name)
		if err != nil {
			svc.IsDeployed = false
			continue
		}
		svc.CaseRef = c
		svc.IsDeployed = true
		pendingCount++

		if rawOut, err := c.TfOutput(); err == nil {
			svc.Outputs = parseTfOutput(rawOut)
		}
	}

	ctx.emitLog(i18n.Tf("compose_destroy_total", pendingCount))
	destroyed := 0

	// 逆序销毁
	for pendingCount > 0 {
		destroyedInThisLoop := 0
		// 倒序遍历建议
		for i := len(ctx.SortedSvcKeys) - 1; i >= 0; i-- {
			svc := ctx.RuntimeSvcs[ctx.SortedSvcKeys[i]]

			if !svc.IsDeployed {
				continue
		}

		if canDestroy(svc, ctx.RuntimeSvcs) {
			msg := i18n.Tf("compose_destroy_service", svc.Name)
			gologger.Info().Msgf("%s", msg)
			ctx.emitLog(msg)
			if err := svc.CaseRef.TfDestroy(); err != nil {
				errMsg := i18n.Tf("compose_destroy_failed", svc.Name, err)
				gologger.Error().Msgf("%s", errMsg)
				ctx.emitLog(errMsg)
			}

			svc.IsDeployed = false
			destroyedInThisLoop++
			destroyed++
			pendingCount--
			ctx.emitLog(i18n.Tf("compose_destroy_progress", destroyed, destroyed+pendingCount))
		}
	}

		if destroyedInThisLoop == 0 && pendingCount > 0 {
			return fmt.Errorf("销毁死锁: 存在循环依赖")
		}
	}
	return nil
}

// processServiceUp 单个服务部署逻辑
func processServiceUp(svc *RuntimeService, ctx *ComposeContext) error {
	tfVars := make(map[string]string)

	// Configs
	for _, cfgStr := range svc.Spec.Configs {
		parts := strings.SplitN(cfgStr, "=", 2)
		if len(parts) == 2 {
			tfName, cfgKey := parts[0], parts[1]
			if val, ok := ctx.GlobalConfigs[cfgKey]; ok {
				tfVars[tfName] = val
			} else {
				gologger.Error().Msgf("[%s] Config key '%s' not found", svc.Name, cfgKey)
			}
		}
	}

	// Environment
	for _, envStr := range svc.Spec.Environment {
		parts := strings.SplitN(envStr, "=", 2)
		if len(parts) == 2 {
			key, rawVal := parts[0], parts[1]
			vals, err := expandVariable(rawVal, ctx.RuntimeSvcs, svc)
			if err != nil {
				return fmt.Errorf("Environment parse error: %v", err)
			}
			tfVars[key] = strings.Join(vals, ",")
		}
	}

	// Provider Alias
	if pStr, ok := svc.Spec.Provider.(string); ok && pStr != "" && pStr != "default" {
		tfVars["provider_alias"] = pStr
	}

	// TF Apply
	ctx.emitLog(fmt.Sprintf("[%s] Terraform Apply...", svc.Name))
	p := ctx.Project
	c, err := p.GetCase(svc.Name)
	if err != nil {
		c, err = p.CaseCreate(svc.Spec.Image, p.User, svc.Name, tfVars)
		if err != nil {
			return fmt.Errorf("CaseCreate fail: %v", err)
		}
	}
	if err := c.TfApply(); err != nil {
		return fmt.Errorf("Terraform Apply fail: %v", err)
	}
	ctx.emitLog(fmt.Sprintf("[%s] Terraform Apply 完成", svc.Name))
	svc.CaseRef = c

	// Output Cache
	rawOut, err := c.TfOutput()
	if err == nil {
		svc.Outputs = parseTfOutput(rawOut)
	}

	// SSH Actions
	return runSSHActions(svc, ctx)
}

func runSSHActions(svc *RuntimeService, ctx *ComposeContext) error {
	if svc.Spec.Command == "" && len(svc.Spec.Volumes) == 0 && len(svc.Spec.Downloads) == 0 {
		return nil
	}

	sshConf, err := svc.CaseRef.GetSSHConfig()
	if err != nil {
		gologger.Debug().Msgf("[%s] Skipping SSH actions: %v", svc.Name, err)
		return nil
	}

	client, err := sshutil.NewClient(sshConf)
	if err != nil {
		gologger.Error().Msgf("[%s] SSH Connect Fail: %v", svc.Name, err)
		return nil
	}
	defer client.Close()

	logger, _ := ctx.LogMgr.NewServiceLogger(svc.Name)
	// Build a writer that writes to file logger + GUI callback
	var writer io.Writer = os.Stdout
	if logger != nil {
		defer logger.Close()
		if ctx.LogCallback != nil {
			cbWriter := &callbackWriter{prefix: svc.Name, cb: ctx.LogCallback}
			writer = io.MultiWriter(logger, cbWriter)
		} else {
			writer = logger
		}
	} else if ctx.LogCallback != nil {
		writer = &callbackWriter{prefix: svc.Name, cb: ctx.LogCallback}
	}

	// Volumes
	for _, vol := range svc.Spec.Volumes {
		parts := strings.Split(vol, ":")
		if len(parts) == 2 {
			localPath, remotePath := parts[0], parts[1]
			msg := fmt.Sprintf("[%s] Uploading %s -> %s", svc.Name, localPath, remotePath)
			gologger.Info().Msg(msg)
			ctx.emitLog(msg)
			if err := client.Upload(localPath, remotePath); err != nil {
				gologger.Error().Msgf("[%s] Upload failed: %v", svc.Name, err)
			}
		}
	}

	// Command
	if svc.Spec.Command != "" {
		msg := fmt.Sprintf("[%s] Running init command...", svc.Name)
		gologger.Info().Msg(msg)
		ctx.emitLog(msg)
		if err := client.RunCommandWithLogger(svc.Spec.Command, writer); err != nil {
			gologger.Error().Msgf("[%s] Command failed: %v", svc.Name, err)
		}
	}

	// Downloads
	for _, dl := range svc.Spec.Downloads {
		parts := strings.Split(dl, ":")
		if len(parts) == 2 {
			remotePath, localPath := parts[0], parts[1]
			msg := fmt.Sprintf("[%s] Downloading %s -> %s", svc.Name, remotePath, localPath)
			gologger.Info().Msg(msg)
			ctx.emitLog(msg)
			if err := client.Download(remotePath, localPath); err != nil {
				gologger.Error().Msgf("[%s] Download failed: %v", svc.Name, err)
			}
		}
	}
	return nil
}

// callbackWriter is an io.Writer that forwards lines to the GUI log callback
type callbackWriter struct {
	prefix string
	cb     func(string)
}

func (w *callbackWriter) Write(p []byte) (n int, err error) {
	scanner := bufio.NewScanner(bytes.NewReader(p))
	for scanner.Scan() {
		text := scanner.Text()
		if text != "" {
			w.cb(fmt.Sprintf("[%s] %s", w.prefix, text))
		}
	}
	return len(p), nil
}

func runSetupTasks(tasks []SetupTask, svcs map[string]*RuntimeService, ctx *ComposeContext) error {
	gologger.Debug().Msgf("Running Setup Tasks %d...", len(tasks))
	for _, task := range tasks {
		// 1. 查找目标实例 (支持裂变/多实例)
		var targets []*RuntimeService
		for _, s := range svcs {
			if s.RawName == task.Service {
				targets = append(targets, s)
			}
		}
		if len(targets) == 0 {
			gologger.Warning().Msgf("Setup task [%s] skipped: No active instances found for service group '%s'", task.Name, task.Service)
			continue
		}
		msg := fmt.Sprintf("[setup] Task [%s] matched %d instance(s) of '%s'", task.Name, len(targets), task.Service)
		gologger.Info().Msg(msg)
		ctx.emitLog(msg)
		// 2. 遍历所有匹配的实例并执行命令
		for _, targetSvc := range targets {
			cmds, err := expandVariable(task.Command, svcs, targetSvc)
			if err != nil {
				gologger.Error().Msgf("Setup task [%s] var error: %v", task.Name, err)
				continue
			}

			sshConf, err := targetSvc.CaseRef.GetSSHConfig()
			if err != nil {
				gologger.Error().Msgf("Setup task [%s] SSH config error: %v", task.Name, err)
				continue
			}

			err = func() error {
				client, err := sshutil.NewClient(sshConf)
				if err != nil {
					gologger.Error().Msgf("Setup task [%s] SSH connect failed: %v", task.Name, err)
					return fmt.Errorf("SSH connect failed: %v", err)
				}
				defer client.Close()

				logger, _ := ctx.LogMgr.NewServiceLogger("setup")
				if logger != nil {
					logger.ServiceName = "setup"
					defer logger.Close()
				}

				for _, cmd := range cmds {
					cmdMsg := fmt.Sprintf("[setup] Task: %s | Cmd: %s", task.Name, cmd)
					gologger.Info().Msg(cmdMsg)
					ctx.emitLog(cmdMsg)

					// 1. 创建一个 Buffer 来捕获输出 (包括 stdout 和 stderr)
					var outputBuf bytes.Buffer

					// 2. 构造 MultiWriter: 既写入日志文件，又写入 Buffer + GUI
					writers := []io.Writer{&outputBuf}
					if logger != nil {
						writers = append(writers, logger)
					}
					if ctx.LogCallback != nil {
						writers = append(writers, &callbackWriter{prefix: "setup", cb: ctx.LogCallback})
					}
					combinedWriter := io.MultiWriter(writers...)

					// 3. 执行命令
					runErr := client.RunCommandWithLogger(cmd, combinedWriter)

					// 4. 获取结果字符串 (去除首尾空白)
					outputStr := strings.TrimSpace(outputBuf.String())

					task.Outputs = outputStr

					// 6. 错误处理
					if runErr != nil {
						gologger.Error().Msgf("[setup] Task failed: %v | Output: %s", runErr, outputStr)
						return fmt.Errorf("cmd execution failed: %w, output: %s", runErr, outputStr)
					}
				}
				return nil
			}()
			if err != nil {
				// 停止执行后续任务
				//return err
			}
		}
	}
	return nil
}

func expandVariable(raw string, ctx map[string]*RuntimeService, currentSvc *RuntimeService) ([]string, error) {
	re := regexp.MustCompile(`\$\{(.+?)\}`)
	matches := re.FindAllStringSubmatch(raw, -1)

	if len(matches) == 0 {
		return []string{raw}, nil
	}

	fullExpr := matches[0][0]
	innerContent := matches[0][1]
	parts := strings.Split(innerContent, ".")

	if len(parts) != 3 || parts[1] != "outputs" {
		return []string{raw}, nil
	}

	refName, outputKey := parts[0], parts[2]
	var candidates []*RuntimeService

	// 1. 精确
	if s, ok := ctx[refName]; ok {
		candidates = append(candidates, s)
	}

	// 2. 上下文
	if len(candidates) == 0 && currentSvc != nil {
		suffix := strings.TrimPrefix(currentSvc.Name, currentSvc.RawName)
		if suffix != "" {
			guessedName := refName + suffix
			if s, ok := ctx[guessedName]; ok && s.RawName == refName {
				candidates = append(candidates, s)
			}
		}
	}

	// 3. 广播
	if len(candidates) == 0 {
		for _, s := range ctx {
			if s.RawName == refName {
				candidates = append(candidates, s)
			}
		}
	}

	if len(candidates) == 0 {
		return nil, fmt.Errorf("referenced service '%s' not found or not active", refName)
	}

	var results []string
	for _, target := range candidates {
		if !target.IsDeployed {
			return nil, fmt.Errorf("referenced service '%s' is not deployed", target.Name)
		}
		val, ok := target.Outputs[outputKey]
		if !ok {
			return nil, fmt.Errorf("output key '%s' missing in %s", outputKey, target.Name)
		}
		newStr := strings.ReplaceAll(raw, fullExpr, fmt.Sprint(val))
		results = append(results, newStr)
	}
	return results, nil
}

func canDeploy(svc *RuntimeService, all map[string]*RuntimeService) bool {
	for _, depName := range svc.Spec.DependsOn {
		foundAny := false
		for _, rtSvc := range all {
			if rtSvc.RawName == depName {
				foundAny = true
				if !rtSvc.IsDeployed {
					return false
				}
			}
		}
		if !foundAny {
			continue
		}
	}
	return true
}

func canDestroy(target *RuntimeService, all map[string]*RuntimeService) bool {
	for _, other := range all {
		if !other.IsDeployed {
			continue
		}
		for _, dep := range other.Spec.DependsOn {
			if dep == target.RawName {
				return false
			}
		}
	}
	return true
}

func parseTfOutput(outputs map[string]tfexec.OutputMeta) map[string]interface{} {
	res := make(map[string]interface{})
	for k, v := range outputs {
		var val interface{}
		if jsonErr := json.Unmarshal(v.Value, &val); jsonErr != nil {
			res[k] = string(v.Value)
		} else {
			res[k] = val
		}
	}
	return res
}
