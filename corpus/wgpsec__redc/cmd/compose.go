package cmd

import (
	"red-cloud/i18n"
	"red-cloud/mod/compose"
	"red-cloud/mod/gologger"

	"github.com/spf13/cobra"
)

var (
	composeFile string
	profiles    []string
)

var composeCmd = &cobra.Command{
	Use:   "compose",
	Short: i18n.T("compose_short"),
}

var upCmd = &cobra.Command{
	Use:   "up",
	Short: i18n.T("compose_up_short"),
	Run: func(cmd *cobra.Command, args []string) {
		opts := compose.ComposeOptions{
			File:     composeFile,
			Profiles: profiles,
			Project:  redcProject,
		}

		if err := compose.RunComposeUp(opts); err != nil {
			if IsJSON() {
				PrintJSONError(err)
				return
			}
			gologger.Fatal().Msgf("%s", i18n.Tf("compose_up_failed", err))
		}

		if IsJSON() {
			PrintJSONMessage("compose up completed")
			return
		}
		gologger.Info().Msg(i18n.T("compose_up_done"))
	},
}

var downCmd = &cobra.Command{
	Use:   "down",
	Short: i18n.T("compose_down_short"),
	Run: func(cmd *cobra.Command, args []string) {
		opts := compose.ComposeOptions{
			File:     composeFile,
			Profiles: profiles,
			Project:  redcProject,
		}

		if err := compose.RunComposeDown(opts); err != nil {
			if IsJSON() {
				PrintJSONError(err)
				return
			}
			gologger.Fatal().Msgf("%s", i18n.Tf("compose_down_failed", err))
		}

		if IsJSON() {
			PrintJSONMessage("compose down completed")
			return
		}
		gologger.Info().Msg(i18n.T("compose_down_done"))
	},
}

var configCmd = &cobra.Command{
	Use:   "config",
	Short: i18n.T("compose_config_short"),
	Long:  i18n.T("compose_config_long"),
	Run: func(cmd *cobra.Command, args []string) {
		opts := compose.ComposeOptions{
			File:     "redc-compose.yaml",
			Profiles: profiles,
			Project:  redcProject,
		}

		if err := compose.InspectConfig(opts); err != nil {
			if IsJSON() {
				PrintJSONError(err)
				return
			}
			gologger.Fatal().Msgf("%s", i18n.Tf("compose_config_failed", err))
		}
	},
}

func init() {
	upCmd.Flags().StringVarP(&composeFile, "file", "f", "redc-compose.yaml", i18n.T("flag_compose_file"))
	upCmd.Flags().StringSliceVarP(&profiles, "profile", "p", []string{}, i18n.T("flag_compose_profile"))

	downCmd.Flags().StringVarP(&composeFile, "file", "f", "redc-compose.yaml", i18n.T("flag_compose_file"))
	downCmd.Flags().StringSliceVarP(&profiles, "profile", "p", []string{}, i18n.T("flag_compose_profile"))

	composeCmd.AddCommand(upCmd)
	composeCmd.AddCommand(downCmd)
	composeCmd.AddCommand(configCmd)
	rootCmd.AddCommand(composeCmd)
}
