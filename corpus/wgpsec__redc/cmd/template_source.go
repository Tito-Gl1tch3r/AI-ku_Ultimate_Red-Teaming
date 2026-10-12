package cmd

import (
	"fmt"
	"os"
	redc "red-cloud/mod"
	"text/tabwriter"

	"github.com/spf13/cobra"
)

var templateSourceCmd = &cobra.Command{
	Use:   "template-source",
	Short: "Manage local template sources",
}

var templateSourceListCmd = &cobra.Command{
	Use:   "list",
	Short: "List configured template sources",
	Args:  cobra.NoArgs,
	RunE: func(cmd *cobra.Command, args []string) error {
		manager, err := redc.LoadConfiguredTemplateSourceManager()
		if err != nil {
			return err
		}
		sources := manager.ListSources()
		if IsJSON() {
			PrintJSON(sources)
			return nil
		}
		w := tabwriter.NewWriter(os.Stdout, 0, 8, 2, ' ', 0)
		fmt.Fprintln(w, "ID\tNAME\tENABLED\tPRIORITY\tTEMPLATES\tPATH\tERROR")
		for _, source := range sources {
			fmt.Fprintf(w, "%s\t%s\t%t\t%d\t%d\t%s\t%s\n",
				source.ID, source.Name, source.Enabled, source.Priority,
				source.TemplateCount, source.Path, source.LastError)
		}
		return w.Flush()
	},
}

var templateSourceAddLocalCmd = &cobra.Command{
	Use:   "add-local <name> <path>",
	Short: "Add a local template directory",
	Args:  cobra.ExactArgs(2),
	RunE: func(cmd *cobra.Command, args []string) error {
		source, err := addLocalTemplateSource(args[0], args[1])
		if err != nil {
			return err
		}
		if IsJSON() {
			PrintJSON(source)
			return nil
		}
		fmt.Printf("Added local template source %s (%s)\n", source.Name, source.ID)
		return nil
	},
}

var templateSourceScanCmd = &cobra.Command{
	Use:   "scan <source-id>",
	Short: "Scan a configured template source",
	Args:  cobra.ExactArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		manager, err := redc.LoadConfiguredTemplateSourceManager()
		if err != nil {
			return err
		}
		templates, scanErr := manager.ScanSource(args[0])
		if saveErr := manager.Save(); scanErr == nil && saveErr != nil {
			return saveErr
		}
		if scanErr != nil {
			return scanErr
		}
		if IsJSON() {
			PrintJSON(templates)
			return nil
		}
		fmt.Printf("Scanned %d templates\n", len(templates))
		return nil
	},
}

var templateSourceRemoveCmd = &cobra.Command{
	Use:   "remove <source-id>",
	Short: "Remove a template source configuration",
	Args:  cobra.ExactArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		manager, err := redc.LoadConfiguredTemplateSourceManager()
		if err != nil {
			return err
		}
		if err := manager.RemoveSource(args[0]); err != nil {
			return err
		}
		if err := manager.Save(); err != nil {
			return err
		}
		if IsJSON() {
			PrintJSON(map[string]string{"source_id": args[0], "status": "removed"})
			return nil
		}
		fmt.Printf("Removed template source %s\n", args[0])
		return nil
	},
}

func addLocalTemplateSource(name, path string) (redc.TemplateSource, error) {
	manager, err := redc.LoadConfiguredTemplateSourceManager()
	if err != nil {
		return redc.TemplateSource{}, err
	}
	source, err := manager.AddLocalSource(name, path)
	if err != nil {
		return redc.TemplateSource{}, err
	}
	if _, err := manager.ScanSource(source.ID); err != nil {
		return redc.TemplateSource{}, err
	}
	if err := manager.Save(); err != nil {
		return redc.TemplateSource{}, err
	}
	for _, configured := range manager.ListSources() {
		if configured.ID == source.ID {
			return configured, nil
		}
	}
	return source, nil
}

func init() {
	templateSourceCmd.AddCommand(
		templateSourceListCmd,
		templateSourceAddLocalCmd,
		templateSourceScanCmd,
		templateSourceRemoveCmd,
	)
	rootCmd.AddCommand(templateSourceCmd)
}
