/*
Copyright © 2024 github.com/Scayar
ScayOSINT - Next-Generation Email Intelligence Platform
*/
package runner

import (
	"fmt"

	"github.com/Scayar/ScayOSINT/v3/pkg/dns"
	"github.com/Scayar/ScayOSINT/v3/pkg/scrape/googlesearch"
	"github.com/Scayar/ScayOSINT/v3/pkg/services/breachdirectory"
	"github.com/Scayar/ScayOSINT/v3/pkg/services/emailrep"
	"github.com/Scayar/ScayOSINT/v3/pkg/services/haveibeenpwned"
	"github.com/Scayar/ScayOSINT/v3/pkg/services/hunter"
	"github.com/Scayar/ScayOSINT/v3/pkg/services/intelx"
	"github.com/Scayar/ScayOSINT/v3/pkg/services/ipapi"
	"github.com/Scayar/ScayOSINT/v3/pkg/services/psbdmp"
	"github.com/Scayar/ScayOSINT/v3/pkg/social/instagram"
	"github.com/Scayar/ScayOSINT/v3/pkg/social/spotify"
	"github.com/Scayar/ScayOSINT/v3/pkg/social/twitter"
	"github.com/gammazero/workerpool"
)

type Runner struct {
	Email            string
	DnsC             *dns.Dns
	GoogleSearchC    *googlesearch.GoogleSearch
	BreachDirectoryC *breachdirectory.BreachDirectory
	HaveibeenpwnedC  *haveibeenpwned.HaveIBeenPwned
	EmailRepC        *emailrep.Emailrep
	HunterC          *hunter.Hunter
	IntelxC          *intelx.Intelx
	IpApiC           *ipapi.Ipapi
	PsbdmpC          *psbdmp.Psbdmp
	InstagramC       *instagram.Instagram
	SpotifyC         *spotify.Spotify
	TwitterC         *twitter.Twitter
}

func New(email string) *Runner {
	return &Runner{
		Email:            email,
		DnsC:             dns.New(),
		GoogleSearchC:    googlesearch.New(),
		BreachDirectoryC: breachdirectory.New(),
		HaveibeenpwnedC:  haveibeenpwned.New(),
		EmailRepC:        emailrep.New(),
		HunterC:          hunter.New(),
		IntelxC:          intelx.New(),
		IpApiC:           ipapi.New(),
		PsbdmpC:          psbdmp.New(),
		InstagramC:       instagram.New(),
		SpotifyC:         spotify.New(),
		TwitterC:         twitter.New(),
	}
}

func (c *Runner) Start() {
	email := c.Email
	runners := []struct {
		name   string
		runner func(string)
	}{
		{"DNS Lookup", c.DnsC.Resolver},
		{"Google Search", c.GoogleSearchC.Search},
		{"BreachDirectory", c.BreachDirectoryC.Lookup},
		{"HaveIBeenPwned", c.HaveibeenpwnedC.Lookup},
		{"EmailRep", c.EmailRepC.Lookup},
		{"Hunter", c.HunterC.Lookup},
		{"IntelX", c.IntelxC.Search},
		{"IP API", c.IpApiC.GetInfo},
		{"Pastebin", c.PsbdmpC.Search},
		{"Instagram", c.InstagramC.Check},
		{"Spotify", c.SpotifyC.Check},
		{"Twitter", c.TwitterC.Check},
	}

	wp := workerpool.New(12)
	for _, r := range runners {
		r := r
		wp.Submit(func() {
			defer func() {
				if err := recover(); err != nil {
					fmt.Printf("Error in %s: %v\n", r.name, err)
				}
			}()
			r.runner(email)
		})
	}
	wp.StopWait()
}

func (c *Runner) Print() {
	println()

	if c.EmailRepC != nil {
		c.EmailRepC.Print()
	}

	println()
	if c.HunterC != nil {
		c.HunterC.Print()
	}

	println()
	if c.GoogleSearchC != nil {
		c.GoogleSearchC.Print()
	}

	println()
	if c.InstagramC != nil {
		c.InstagramC.Print()
	}
	if c.SpotifyC != nil {
		c.SpotifyC.Print()
	}
	if c.TwitterC != nil {
		c.TwitterC.Print()
	}

	println()
	if c.PsbdmpC != nil {
		c.PsbdmpC.Print()
	}

	println()
	if c.IntelxC != nil {
		c.IntelxC.Print()
	}

	println()
	if c.BreachDirectoryC != nil {
		c.BreachDirectoryC.Print()
	}

	println()
	if c.HaveibeenpwnedC != nil {
		c.HaveibeenpwnedC.Print()
	}

	println()
	if c.IpApiC != nil {
		c.IpApiC.Print()
	}

	println()
	if c.DnsC != nil {
		c.DnsC.Print()
	}
}
