package cmd

import (
	"fmt"
	"red-cloud/i18n"
	"red-cloud/mod/plugin"

	"github.com/spf13/cobra"
)

var pluginCmd = &cobra.Command{
	Use:   "plugin",
	Short: i18n.T("plugin_short"),
	Run: func(cmd *cobra.Command, args []string) {
		cmd.Help()
	},
}

var pluginListCmd = &cobra.Command{
	Use:   "list",
	Short: i18n.T("plugin_list_short"),
	Run: func(cmd *cobra.Command, args []string) {
		pm := plugin.NewPluginManager("")
		if err := pm.LoadAll(); err != nil {
			fmt.Printf("Error: %v\n", err)
			return
		}
		plugins := pm.List()
		if len(plugins) == 0 {
			fmt.Println("No plugins installed.")
			return
		}
		if IsJSON() {
			PrintJSON(plugins)
			return
		}
		for _, p := range plugins {
			status := "enabled"
			if !p.Enabled {
				status = "disabled"
			}
			fmt.Printf("  %s  v%s  [%s]  %s\n", p.Manifest.Name, p.Manifest.Version, status, p.Manifest.Description)
		}
	},
}

var pluginInstallCmd = &cobra.Command{
	Use:   "install <git-url|path>",
	Short: i18n.T("plugin_install_short"),
	Args:  cobra.ExactArgs(1),
	Run: func(cmd *cobra.Command, args []string) {
		pm := plugin.NewPluginManager("")
		name, err := pm.Install(args[0])
		if err != nil {
			fmt.Printf("Error: %v\n", err)
			return
		}
		fmt.Printf("Plugin %s installed successfully.\n", name)
	},
}

var pluginUninstallCmd = &cobra.Command{
	Use:   "uninstall <name>",
	Short: i18n.T("plugin_uninstall_short"),
	Args:  cobra.ExactArgs(1),
	Run: func(cmd *cobra.Command, args []string) {
		pm := plugin.NewPluginManager("")
		if err := pm.Uninstall(args[0]); err != nil {
			fmt.Printf("Error: %v\n", err)
			return
		}
		fmt.Printf("Plugin %s uninstalled.\n", args[0])
	},
}

var pluginEnableCmd = &cobra.Command{
	Use:   "enable <name>",
	Short: i18n.T("plugin_enable_short"),
	Args:  cobra.ExactArgs(1),
	Run: func(cmd *cobra.Command, args []string) {
		pm := plugin.NewPluginManager("")
		if err := pm.Enable(args[0]); err != nil {
			fmt.Printf("Error: %v\n", err)
			return
		}
		fmt.Printf("Plugin %s enabled.\n", args[0])
	},
}

var pluginDisableCmd = &cobra.Command{
	Use:   "disable <name>",
	Short: i18n.T("plugin_disable_short"),
	Args:  cobra.ExactArgs(1),
	Run: func(cmd *cobra.Command, args []string) {
		pm := plugin.NewPluginManager("")
		if err := pm.Disable(args[0]); err != nil {
			fmt.Printf("Error: %v\n", err)
			return
		}
		fmt.Printf("Plugin %s disabled.\n", args[0])
	},
}

var pluginUpdateCmd = &cobra.Command{
	Use:   "update <name>",
	Short: i18n.T("plugin_update_short"),
	Args:  cobra.ExactArgs(1),
	Run: func(cmd *cobra.Command, args []string) {
		pm := plugin.NewPluginManager("")
		msg, err := pm.Update(args[0])
		if err != nil {
			fmt.Printf("Error: %v\n", err)
			return
		}
		fmt.Printf("Plugin %s updated: %s\n", args[0], msg)
	},
}

var pluginInfoCmd = &cobra.Command{
	Use:   "info <name>",
	Short: i18n.T("plugin_info_short"),
	Args:  cobra.ExactArgs(1),
	Run: func(cmd *cobra.Command, args []string) {
		pm := plugin.NewPluginManager("")
		if err := pm.LoadAll(); err != nil {
			fmt.Printf("Error: %v\n", err)
			return
		}
		p, ok := pm.Get(args[0])
		if !ok {
			fmt.Printf("Plugin %s not found.\n", args[0])
			return
		}
		if IsJSON() {
			PrintJSON(p)
			return
		}
		status := "enabled"
		if !p.Enabled {
			status = "disabled"
		}
		fmt.Printf("Name:        %s\n", p.Manifest.Name)
		fmt.Printf("Version:     %s\n", p.Manifest.Version)
		fmt.Printf("Description: %s\n", p.Manifest.Description)
		fmt.Printf("Author:      %s\n", p.Manifest.Author)
		fmt.Printf("Category:    %s\n", p.Manifest.Category)
		fmt.Printf("Status:      %s\n", status)
		fmt.Printf("Directory:   %s\n", p.Dir)
		if p.Manifest.Homepage != "" {
			fmt.Printf("Homepage:    %s\n", p.Manifest.Homepage)
		}
		if len(p.Manifest.Tags) > 0 {
			fmt.Printf("Tags:        %v\n", p.Manifest.Tags)
		}
	},
}

func init() {
	rootCmd.AddCommand(pluginCmd)
	pluginCmd.AddCommand(pluginListCmd)
	pluginCmd.AddCommand(pluginInstallCmd)
	pluginCmd.AddCommand(pluginUninstallCmd)
	pluginCmd.AddCommand(pluginEnableCmd)
	pluginCmd.AddCommand(pluginDisableCmd)
	pluginCmd.AddCommand(pluginUpdateCmd)
	pluginCmd.AddCommand(pluginInfoCmd)
}
