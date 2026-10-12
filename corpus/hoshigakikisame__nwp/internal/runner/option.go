package runner

import (
	"fmt"
	"math/rand"
	"time"

	"github.com/hoshigakikisame/nwp/internal/utils"
	"github.com/projectdiscovery/goflags"
	"github.com/projectdiscovery/gologger"
	"github.com/projectdiscovery/gologger/levels"
)

type Options struct {
	WildcardsPath             string
	SubdomainsPath            string
	Concurrency               int
	IncludeNonWildcardMembers bool
	OutputPath                string
	IsVerbose                 bool
	Quiet                     bool
	CommonFingerPrintsLimit   int

	Wildcards  []string
	Subdomains []string
}

var o *Options

func init() {
	o = &Options{}

	opt := goflags.NewFlagSet()
	opt.SetDescription("NWP Eliminates common wildcard instances and returns unique one")

	// Concurrency
	opt.IntVarP(&o.Concurrency, "concurrency", "c", 3, "Max concurrency")

	// Files
	opt.StringVarP(&o.WildcardsPath, "wildcards", "w", "", "Wildcards file path")
	opt.StringVarP(&o.SubdomainsPath, "subdomains", "s", "", "Subdomains file path")

	// Matchers
	opt.IntVarP(&o.CommonFingerPrintsLimit, "common-fingerprints-limit", "cfl", 7, "Limit for common fingerprints to be generated")

	// Output
	opt.StringVarP(&o.OutputPath, "output", "o", "", "Output file path to save results")
	opt.BoolVarP(&o.IncludeNonWildcardMembers, "include-non-wildcard-members", "inwm", false, "Include non-wildcard members in the output")

	// Misc
	opt.BoolVarP(&o.IsVerbose, "verbose", "v", false, "Enable verbose output")
	opt.BoolVarP(&o.Quiet, "quiet", "q", false, "Enable quiet mode (no logging)")

	_ = opt.Parse()
}

func (o *Options) validate() error {

	if !utils.FileExists(o.WildcardsPath) {
		return fmt.Errorf("wildcards file doesn't exists")
	}

	if !utils.FileExists(o.SubdomainsPath) {
		return fmt.Errorf("subdomains file doesn't exists")
	}

	return nil
}
func Parse() *Options {
	showBanner()

	if err := o.validate(); err != nil {
		gologger.Fatal().Msgf("Unable to parse option, reason: %s", err.Error())
	}

	wildcards, err := utils.ReadFile(o.WildcardsPath)
	if err != nil {
		gologger.Fatal().Msgf("Unable to parse wildcards file, reason: %s", err.Error())
	}
	o.Wildcards = wildcards

	subdomains, err := utils.ReadFile(o.SubdomainsPath)
	if err != nil {
		gologger.Fatal().Msgf("Unable to parse subdomains file, reason: %s", err.Error())
	}
	o.Subdomains = subdomains

	rand.NewSource(time.Now().UnixNano())

	gologger.DefaultLogger.SetMaxLevel(levels.LevelWarning)

	if o.IsVerbose {
		gologger.DefaultLogger.SetMaxLevel(levels.LevelVerbose)
	}

	if o.Quiet {
		gologger.DefaultLogger.SetMaxLevel(levels.LevelSilent)
	}

	return o
}
