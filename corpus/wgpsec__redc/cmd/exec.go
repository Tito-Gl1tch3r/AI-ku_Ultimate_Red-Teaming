package cmd

import (
	"fmt"
	"red-cloud/i18n"
	"red-cloud/mod/gologger"
	"red-cloud/utils/sshutil"
	"strings"

	"github.com/spf13/cobra"
)

var (
	execInteractive bool // 是否启用交互模式
)

// GetInstanceInfoFromTF 预留的 TF 信息获取函数 (Requirement #2)
func GetInstanceInfoFromTF(id string) (*sshutil.SSHConfig, error) {
	c, err := redcProject.GetCase(id)
	if err != nil {
		return nil, fmt.Errorf("%s", i18n.Tf("case_not_found", id, err))
	}
	s, err := c.GetSSHConfig()
	return s, nil

}

var execCmd = &cobra.Command{
	Use:   "exec [id] [command]",
	Short: i18n.T("exec_short"),
	Example: `  redc exec [id] whoami
  redc exec -t [id] bash`,
	//Args: cobra.MinimumNArgs(2), // 需要 ID 和 命令
	Run: func(cmd *cobra.Command, args []string) {
		if len(args) < 2 {
			cmd.Help()
			return
		}
		id := args[0]
		commandStr := strings.Join(args[1:], " ")

		client, err := getSSHClient(id)
		if err != nil {
			if IsJSON() {
				PrintJSONError(err)
				return
			}
			gologger.Error().Msgf("%s", i18n.Tf("exec_connect_failed", err))
			return
		}
		defer client.Close()

		if execInteractive {
			if IsJSON() {
				PrintJSONError(fmt.Errorf("interactive mode not supported with --output json"))
				return
			}
			gologger.Info().Msgf("%s", i18n.T("exec_interactive_starting"))
			err = client.RunInteractiveShell(commandStr)
		} else {
			err = client.RunCommand(commandStr)
		}

		if err != nil {
			if IsJSON() {
				PrintJSONError(err)
				return
			}
			gologger.Error().Msgf("%s", i18n.Tf("exec_error", err))
		}
	},
}

var cpCmd = &cobra.Command{
	Use:   "cp [src] [dest]",
	Short: i18n.T("cp_short"),
	Example: `  redc cp ./tool [id]:/tmp/tool
  redc cp [id]:/var/log/syslog ./local_log`,
	//Args: cobra.ExactArgs(2),
	Run: func(cmd *cobra.Command, args []string) {
		if len(args) < 2 {
			cmd.Help()
			return
		}
		srcArg := args[0]
		destArg := args[1]

		srcID, srcPath, srcRemote := parseCpArg(srcArg)
		destID, destPath, destRemote := parseCpArg(destArg)

		if srcRemote && destRemote {
			if IsJSON() {
				PrintJSONError(fmt.Errorf("remote to remote copy not supported"))
				return
			}
			gologger.Error().Msg(i18n.T("cp_remote_to_remote_not_supported"))
			return
		}
		if !srcRemote && !destRemote {
			if IsJSON() {
				PrintJSONError(fmt.Errorf("use local cp for local to local copy"))
				return
			}
			gologger.Error().Msg(i18n.T("cp_use_local_cp"))
			return
		}

		// Upload
		if !srcRemote && destRemote {
			if !IsJSON() {
				gologger.Info().Msgf("Uploading %s to %s:%s", srcArg, destID, destPath)
			}
			client, err := getSSHClient(destID)
			if err != nil {
				if IsJSON() {
					PrintJSONError(err)
					return
				}
				gologger.Error().Msgf("%s", i18n.Tf("cp_connect_failed", err))
				return
			}
			defer client.Close()

			if err := client.Upload(srcArg, destPath); err != nil {
				if IsJSON() {
					PrintJSONError(err)
					return
				}
				gologger.Error().Msgf("%s", i18n.Tf("cp_upload_failed", err))
			} else {
				if IsJSON() {
					PrintJSON(map[string]string{"action": "upload", "src": srcArg, "dest": destID + ":" + destPath})
				} else {
					gologger.Info().Msg(i18n.T("cp_upload_success"))
				}
			}
		}

		// Download
		if srcRemote && !destRemote {
			if !IsJSON() {
				gologger.Info().Msgf("Downloading %s:%s to %s", srcID, srcPath, destArg)
			}
			client, err := getSSHClient(srcID)
			if err != nil {
				if IsJSON() {
					PrintJSONError(err)
					return
				}
				gologger.Error().Msgf("%s", i18n.Tf("cp_connect_failed", err))
				return
			}
			defer client.Close()

			if err := client.Download(srcPath, destArg); err != nil {
				if IsJSON() {
					PrintJSONError(err)
					return
				}
				gologger.Error().Msgf("%s", i18n.Tf("cp_download_failed", err))
			} else {
				if IsJSON() {
					PrintJSON(map[string]string{"action": "download", "src": srcID + ":" + srcPath, "dest": destArg})
				} else {
					gologger.Info().Msg(i18n.T("cp_download_success"))
				}
			}
		}
	},
}

func init() {
	execCmd.Flags().BoolVarP(&execInteractive, "tty", "t", false, "Allocate a pseudo-TTY (Interactive mode)")
	rootCmd.AddCommand(execCmd)
	rootCmd.AddCommand(cpCmd)
}

// Helper: 获取 SSH Client
func getSSHClient(id string) (*sshutil.Client, error) {
	info, err := GetInstanceInfoFromTF(id)
	if err != nil {
		return nil, err
	}

	return sshutil.NewClient(info)
}

// parseCpArg 解析 cp 参数，判断是本地路径还是远程路径
// 格式 mimic docker: id:/path/to/file
func parseCpArg(arg string) (id string, path string, isRemote bool) {
	if strings.Contains(arg, ":") {
		parts := strings.SplitN(arg, ":", 2)
		return parts[0], parts[1], true
	}
	return "", arg, false
}
