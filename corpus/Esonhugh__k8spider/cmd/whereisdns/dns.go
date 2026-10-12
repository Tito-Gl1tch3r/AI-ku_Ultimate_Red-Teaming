package whereisdns

import (
	"fmt"

	command "github.com/esonhugh/k8spider/cmd"
	"github.com/esonhugh/k8spider/pkg"
	log "github.com/sirupsen/logrus"
	"github.com/spf13/cobra"
)

func init() {
	command.RootCmd.AddCommand(WhereIsDnsCmd)
}

var WhereIsDnsCmd = &cobra.Command{
	Use: "whereisdns",
	Aliases: []string{
		"dns",
	},
	Short: "this command will help you check where is the dns server in provided CIDR",
	Run: func(cmd *cobra.Command, args []string) {
		ipNets, err := pkg.ParseStringToIPNet(command.Opts.Cidr)
		if err != nil {
			log.Warnf("ParseStringToIPNet failed: %v", err)
			return
		}
		s := false
		for _, ip := range pkg.ParseIPNetToIPs(ipNets) {
			serverAddr := fmt.Sprintf("%s:53", ip.String())
			if checkdns(serverAddr) {
				s = true
			}
			serverAddr = fmt.Sprintf("%s:5353", ip.String())
			if checkdns(serverAddr) {
				s = true
			}
		}
		if s {
			log.Warn("DNS Server Not Found!")
		}
	},
}

func checkdns(serverAddr string) bool {
	dns := pkg.WarpDnsServer(serverAddr)
	if pkg.CheckKubeDNS(dns) {
		log.Infof("Possible cluster DNS Server Found: %s", serverAddr)
		return true
	}
	return false
}
