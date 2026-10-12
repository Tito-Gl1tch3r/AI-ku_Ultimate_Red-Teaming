package cmd

import (
	env "github.com/SpecterOps/BloodHound_CLI/cmd/internal"
	"github.com/stretchr/testify/assert"
	"testing"
)

func TestGraphDriverShortcutCommands(t *testing.T) {
	neo4jCmd.Run(neo4jCmd, nil)
	neo4jSetting := env.GetConfig([]string{"graph_driver"})
	assert.Equal(t, "neo4j", neo4jSetting[0].Val, "`neo4j` command should set graph_driver to neo4j")

	pgCmd.Run(pgCmd, nil)
	pgSetting := env.GetConfig([]string{"graph_driver"})
	assert.Equal(t, "pg", pgSetting[0].Val, "`pg` command should set graph_driver to pg")
}
