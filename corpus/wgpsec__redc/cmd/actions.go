package cmd

import (
	"fmt"
	"os"
	"path/filepath"
	"red-cloud/i18n"
	redc "red-cloud/mod"
	"red-cloud/mod/gologger"
	"red-cloud/mod/plugin"
	"text/tabwriter"

	tfjson "github.com/hashicorp/terraform-json"
	"github.com/spf13/cobra"
)

var changeConfig redc.ChangeCommand

// helper: 通用的执行器
func runAction(actionType string, caseID string) {
	c, err := redcProject.GetCase(caseID)
	if err != nil {
		if IsJSON() {
			PrintJSONError(fmt.Errorf("%s", i18n.Tf("action_case_not_found", caseID, err)))
			return
		}
		gologger.Error().Msgf("%s", i18n.Tf("action_case_not_found", caseID, err))
		return
	}

	redc.RedcLog(fmt.Sprintf("Action %s on %s", actionType, caseID))

	var actionErr error
	switch actionType {
	case "stop":
		actionErr = c.Stop()
	case "start":
		actionErr = c.TfApply()
	case "kill":
		actionErr = c.Kill()
	case "change":
		actionErr = c.Change(changeConfig)
	case "status":
		if IsJSON() {
			runStatusJSON(c)
			return
		}
		actionErr = c.Status()
	case "rm":
		actionErr = c.Remove()
	}

	if actionErr != nil {
		if IsJSON() {
			PrintJSONError(actionErr)
			return
		}
		gologger.Error().Msgf("%s", i18n.Tf("action_failed", actionType, actionErr))
	} else {
		if IsJSON() {
			PrintJSON(map[string]string{
				"action": actionType,
				"case":   c.Name,
				"id":     c.GetId(),
				"state":  string(c.State),
			})
			return
		}
		gologger.Info().Msgf("%s", i18n.Tf("action_success", actionType, c.Name, c.GetId()))
	}
}

// runStatusJSON outputs case status as JSON
func runStatusJSON(c *redc.Case) {
	state, err := redc.TfStatus(c.Path)
	if err != nil {
		PrintJSONError(err)
		return
	}
	PrintJSON(statusJSONData(c, state))
}

func statusJSONData(c *redc.Case, state *tfjson.State) map[string]interface{} {
	result := map[string]interface{}{
		"name":           c.Name,
		"id":             c.Id,
		"state":          string(c.State),
		"plugin_outputs": map[string]string{},
	}
	if outputs := plugin.LoadPluginOutputs(c.Path); outputs != nil {
		result["plugin_outputs"] = outputs
	}
	if state.Values != nil {
		outputs := map[string]interface{}{}
		for k, v := range state.Values.Outputs {
			outputs[k] = v.Value
		}
		result["outputs"] = outputs

		if state.Values.RootModule != nil {
			var resources []map[string]string
			for _, res := range state.Values.RootModule.Resources {
				resources = append(resources, map[string]string{
					"type":    res.Type,
					"address": res.Address,
					"name":    res.Name,
				})
			}
			result["resources"] = resources
		}
	}
	return result
}

// runGlobalStatus shows a global overview: case counts by state, scheduled tasks, plugins
func runGlobalStatus() {
	cases, err := redc.LoadProjectCases(redc.Project)
	if err != nil {
		if IsJSON() {
			PrintJSONError(err)
		} else {
			gologger.Error().Msgf("Failed to load cases: %v", err)
		}
		return
	}

	// Count by state
	counts := map[string]int{
		"running": 0,
		"stopped": 0,
		"error":   0,
		"created": 0,
	}
	for _, c := range cases {
		state := string(c.State)
		if state == "" {
			state = "unknown"
		}
		counts[state]++
	}

	// Scheduled tasks
	pendingTasks := 0
	schedulerDB := filepath.Join(redc.RedcPath, "scheduler.db")
	if scheduler := redc.NewTaskScheduler(redcProject, schedulerDB); scheduler != nil {
		pendingTasks = len(scheduler.ListTasks())
		scheduler.Stop()
	}

	// Plugins
	pluginsDir := filepath.Join(redc.RedcPath, "plugins")
	pm := plugin.NewPluginManager(pluginsDir)
	_ = pm.LoadAll()
	allPlugins := pm.List()
	enabledPlugins := 0
	for _, p := range allPlugins {
		if p.Enabled {
			enabledPlugins++
		}
	}

	if IsJSON() {
		PrintJSON(map[string]interface{}{
			"project":         redc.Project,
			"total_cases":     len(cases),
			"cases_by_state":  counts,
			"pending_tasks":   pendingTasks,
			"total_plugins":   len(allPlugins),
			"enabled_plugins": enabledPlugins,
		})
		return
	}

	// Pretty print
	fmt.Printf("\n  RedC Status — Project: %s\n\n", redc.Project)

	w := tabwriter.NewWriter(os.Stdout, 0, 8, 2, ' ', 0)
	fmt.Fprintf(w, "  %-20s\t%d\n", i18n.T("status_total_cases"), len(cases))
	fmt.Fprintf(w, "  %-20s\t%d\n", "  ● "+i18n.T("status_running"), counts["running"])
	fmt.Fprintf(w, "  %-20s\t%d\n", "  ○ "+i18n.T("status_stopped"), counts["stopped"])
	fmt.Fprintf(w, "  %-20s\t%d\n", "  ✕ "+i18n.T("status_error"), counts["error"])
	fmt.Fprintf(w, "  %-20s\t%d\n", "  ◻ "+i18n.T("status_created"), counts["created"])
	fmt.Fprintf(w, "  %-20s\t%d\n", i18n.T("status_pending_tasks"), pendingTasks)
	fmt.Fprintf(w, "  %-20s\t%d / %d\n", i18n.T("status_plugins"), enabledPlugins, len(allPlugins))
	w.Flush()
	fmt.Println()
}

// 定义各个命令
var stopCmd = &cobra.Command{
	Use:   "stop [id]",
	Short: i18n.T("stop_short"),
	Run: func(cmd *cobra.Command, args []string) {
		runAction("stop", args[0])
	},
}

var statusCmd = &cobra.Command{
	Use:   "status [id]",
	Short: i18n.T("status_short"),
	Run: func(cmd *cobra.Command, args []string) {
		if len(args) == 0 {
			runGlobalStatus()
			return
		}
		runAction("status", args[0])
	},
}

var changeCmd = &cobra.Command{
	Use:   "change [id]",
	Short: i18n.T("change_short"),
	Run: func(cmd *cobra.Command, args []string) {
		runAction("change", args[0])
	},
}

var startCmd = &cobra.Command{
	Use:   "start [id]",
	Short: i18n.T("start_short"),
	Run: func(cmd *cobra.Command, args []string) {
		runAction("start", args[0])
	},
}

var killCmd = &cobra.Command{
	Use:   "kill [id]",
	Short: i18n.T("kill_short"),
	Run: func(cmd *cobra.Command, args []string) {
		runAction("kill", args[0])
	},
}
var rmCmd = &cobra.Command{
	Use:   "rm [id]",
	Short: i18n.T("rm_short"),
	Run: func(cmd *cobra.Command, args []string) {
		runAction("rm", args[0])
	},
}

var listCmd = &cobra.Command{
	Use:   "ps",
	Short: i18n.T("ps_short"),
	Run: func(cmd *cobra.Command, args []string) {
		if IsJSON() {
			cases, err := redc.LoadProjectCases(redc.Project)
			if err != nil {
				PrintJSONError(err)
				return
			}
			PrintJSON(cases)
			return
		}
		redcProject.CaseList()
	},
}

// 注册命令
func init() {
	rootCmd.AddCommand(stopCmd)
	rootCmd.AddCommand(killCmd)
	rootCmd.AddCommand(listCmd)
	rootCmd.AddCommand(statusCmd)
	rootCmd.AddCommand(changeCmd)
	rootCmd.AddCommand(startCmd)
	rootCmd.AddCommand(rmCmd)
	changeCmd.Flags().BoolVar(&changeConfig.IsRemove, "rm", false, i18n.T("flag_change_rm"))
}
