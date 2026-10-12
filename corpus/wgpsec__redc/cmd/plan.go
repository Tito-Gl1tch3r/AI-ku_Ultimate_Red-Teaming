package cmd

import (
	"red-cloud/i18n"
	redc "red-cloud/mod"
	"red-cloud/mod/gologger"
	"strings"

	"github.com/spf13/cobra"
	"github.com/spf13/pflag"
)

var (
	userName     string
	projectName  string
	envVars      map[string]string
	commandToRun string
)

var runCmd = &cobra.Command{
	Use:     "run [template_name]",
	Short:   i18n.T("run_short"),
	Example: "redc run ecs",
	Args:    cobra.MinimumNArgs(1),
	Run: func(cmd *cobra.Command, args []string) {
		templateName := args[0]
		if c, err := planLogic(templateName); err == nil {
			if err := c.TfApply(); err != nil {
				if IsJSON() {
					PrintJSONError(err)
					return
				}
				gologger.Error().Msgf("%s", i18n.Tf("scene_start_failed", err.Error()))
				return
			}
			if IsJSON() {
				PrintJSON(map[string]interface{}{
					"action": "run",
					"name":   c.Name,
					"id":     c.Id,
					"state":  string(c.State),
				})
				return
			}
			if len(args) > 1 {
				commandToRun = strings.Join(args[1:], " ")
			}
		}

	},
}

var planCmd = &cobra.Command{
	Use:     "plan [template_name]",
	Short:   i18n.T("plan_short"),
	Example: "redc plan ecs -u team1 -n operation_alpha",
	Args:    cobra.ExactArgs(1),
	Run: func(cmd *cobra.Command, args []string) {
		templateName := args[0]
		if c, err := planLogic(templateName); err == nil {
			if IsJSON() {
				PrintJSON(map[string]interface{}{
					"action": "plan",
					"name":   c.Name,
					"id":     c.Id,
				})
				return
			}
			gologger.Info().Msgf("%s", i18n.Tf("scene_plan_done", c.Name, c.Id))
		}
	},
}

func planLogic(templateName string) (*redc.Case, error) {

	// 别名处理
	if templateName == "pte" {
		templateName = "pte_arm"
	}
	// 创建 Case
	c, err := redcProject.CaseCreate(templateName, userName, projectName, envVars)
	if err != nil {
		if IsJSON() {
			PrintJSONError(err)
			return nil, err
		}
		gologger.Error().Msgf("%s", i18n.Tf("scene_create_failed", templateName, err.Error()))
		return nil, err
	}
	if !IsJSON() {
		gologger.Info().Msgf("%s", i18n.Tf("scene_create_done", templateName))
	}
	return c, nil
}

func init() {
	rootCmd.AddCommand(planCmd)
	rootCmd.AddCommand(runCmd)
	CRCommonFlagSet := pflag.NewFlagSet("common", pflag.ExitOnError)

	CRCommonFlagSet.StringVarP(&userName, "user", "u", "system", i18n.T("flag_plan_user"))
	CRCommonFlagSet.StringVarP(&projectName, "name", "n", "", i18n.T("flag_plan_name"))
	CRCommonFlagSet.StringToStringVarP(&envVars, "env", "e", nil, i18n.T("flag_plan_env"))
	planCmd.Flags().AddFlagSet(CRCommonFlagSet)
	runCmd.Flags().AddFlagSet(CRCommonFlagSet)
}
