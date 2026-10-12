package cmd

import (
	"fmt"

	env "github.com/SpecterOps/BloodHound_CLI/cmd/internal"
	"github.com/spf13/cobra"
)

func setGraphDriver(driver string) {
	env.SetConfig("graph_driver", driver)
	// If driver is `pg` or `postgres` or `postgresql`, change string to `PostgreSQL` for user-friendly output
	if driver == "pg" || driver == "postgres" || driver == "postgresql" {
		driver = "PostgreSQL"
	}
	fmt.Printf("[+] Graph database backend set to %s. Bring containers down and up for changes to take effect.\n", driver)
}

var neo4jCmd = &cobra.Command{
	Use:   "neo4j",
	Short: "Set the database backend to Neo4j",
	Long: `Shortcut for "config set graph_driver neo4j" to set the graph database backend to Neo4j.

Bring containers down and up for changes to take effect.

For more information on graph database backends, see the documentation:
https://bloodhound.specterops.io/manage-bloodhound/bh-config#graph_driver`,
	Run: func(cmd *cobra.Command, args []string) {
		if len(args) > 0 {
			fmt.Printf("[-] '%s' does not accept positional arguments\n", cmd.Use)
			return
		}
		setGraphDriver("neo4j")
	},
}

var pgCmd = &cobra.Command{
	Use:     "pg",
	Aliases: []string{"postgres", "postgresql"},
	Short:   "Set the database backend to PostgreSQL",
	Long: `Shortcut for "config set graph_driver pg" to set the graph database backend to PostgreSQL.

Bring containers down and up for changes to take effect.

For more information on graph database backends, see the documentation:
https://bloodhound.specterops.io/manage-bloodhound/bh-config#graph_driver`,
	Run: func(cmd *cobra.Command, args []string) {
		if len(args) > 0 {
			fmt.Printf("[-] '%s' does not accept positional arguments\n", cmd.Use)
			return
		}
		setGraphDriver("pg")
	},
}

func init() {
	rootCmd.AddCommand(neo4jCmd)
	rootCmd.AddCommand(pgCmd)
}
