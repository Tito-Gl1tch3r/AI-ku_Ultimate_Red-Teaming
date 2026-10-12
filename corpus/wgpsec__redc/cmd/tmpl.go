package cmd

import (
	"red-cloud/i18n"
	redc "red-cloud/mod"
	"red-cloud/mod/gologger"

	"github.com/spf13/cobra"
)

var tmplCmd = &cobra.Command{
	Use:   "image",
	Short: i18n.T("tmpl_short"),
	Run: func(cmd *cobra.Command, args []string) {
		cmd.Help()
	},
}

// 3. 定义三级命令: ls
var showAll bool // 定义一个变量来接收 flag

var tmplLsCmd = &cobra.Command{
	Use:   "ls",
	Short: i18n.T("tmpl_ls_short"),
	Run: func(cmd *cobra.Command, args []string) {
		if IsJSON() {
			list, err := redc.ListLocalTemplates()
			if err != nil {
				PrintJSONError(err)
				return
			}
			PrintJSON(list)
			return
		}
		redc.ShowLocalTemplates()
	},
}
var tmplRMCmd = &cobra.Command{
	Use:   "rm [case]",
	Short: i18n.T("tmpl_rm_short"),
	Args:  cobra.ExactArgs(1),
	Run: func(cmd *cobra.Command, args []string) {
		id := args[0]
		if err := redc.RemoveTemplate(id); err != nil {
			if IsJSON() {
				PrintJSONError(err)
				return
			}
			gologger.Error().Msgf("remove template failed: %v", err)
			return
		}
		if IsJSON() {
			PrintJSONMessage("template removed: " + id)
		}
	},
}

func init() {
	rootCmd.AddCommand(tmplCmd)
	tmplCmd.AddCommand(tmplLsCmd)
	tmplCmd.AddCommand(tmplRMCmd)
}
