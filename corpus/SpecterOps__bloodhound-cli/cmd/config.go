package cmd

import (
	"fmt"

	env "github.com/SpecterOps/BloodHound_CLI/cmd/internal"
	"github.com/spf13/cobra"
)

// configCmd represents the config command
var configCmd = &cobra.Command{
	Use:   "config",
	Short: "Display or adjust the configuration",
	Long: `Run this command to display the configuration. Use subcommands to
adjust the configuration or retrieve individual values.

Configuration values are documented here:
https://bloodhound.specterops.io/manage-bloodhound/bh-config`,
	Run: configDisplay,
}

func init() {
	rootCmd.AddCommand(configCmd)
}

func configDisplay(cmd *cobra.Command, args []string) {
	fmt.Println("[+] Current configuration:")
	configuration := env.GetConfigAll()
	fmt.Println(string(configuration))
	fmt.Println("\n[+] To adjust a configuration value, use the 'config set' subcommand. For example:")
	fmt.Println("  config set graph_driver neo4j")
	fmt.Println("[+] To retrieve an individual configuration value, use the 'config get' subcommand. For example:")
	fmt.Println("  config get graph_driver")
	fmt.Println("[+] For more information on configuration options, see the documentation:")
	fmt.Println("  https://bloodhound.specterops.io/manage-bloodhound/bh-config")
}
