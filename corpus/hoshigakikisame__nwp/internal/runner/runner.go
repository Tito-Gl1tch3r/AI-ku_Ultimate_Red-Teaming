package runner

import (
	"bytes"
	"fmt"
	"sort"
	"strings"
	"sync"
	"time"

	"github.com/hoshigakikisame/nwp/internal/utils"
	"github.com/miekg/dns"
	"github.com/projectdiscovery/gologger"
)

type runner struct {
	options *Options
}

func New(options *Options) *runner {
	return &runner{options: options}
}

func (r *runner) getFingerPrint(domain string) ([]byte, error) {

	dnsClient := dns.Client{
		Timeout: time.Second,
	}
	msg := dns.Msg{}
	msg.RecursionDesired = true
	msg.SetQuestion(domain+".", dns.TypeANY)
	res, _, err := dnsClient.Exchange(&msg, "8.8.8.8:53")
	if err != nil {
		return nil, fmt.Errorf("DNS query failed for %s: %w", domain, err)
	}

	if res.Rcode != dns.RcodeSuccess {
		return nil, fmt.Errorf("DNS query failed for %s with Rcode: %d", domain, res.Rcode)
	}

	strAnswers := ""
	for _, ans := range res.Answer {
		strRecords := strings.Join(strings.Fields(ans.String())[2:], " ")
		strAnswers += strRecords + "\n"
	}

	strHash := utils.SHA256(strAnswers)

	gologger.Verbose().Msgf("Obtained fingerprint for %s: %x", domain, strHash)

	return strHash, nil
}

func (r *runner) worker(subChan chan string, wg *sync.WaitGroup, commonFP []byte, resultChan chan<- string) {
	defer wg.Done()
	for sub := range subChan {
		subFP, err := r.getFingerPrint(sub)
		if err != nil {
			gologger.Warning().Msgf("Unable to get %s fingerprint, continuing", sub)
			continue
		}

		if !bytes.Equal(subFP, commonFP) {
			gologger.Verbose().Msgf("Found unique subdomain: %s with fingerprint %x", sub, subFP)
			resultChan <- sub
		}
	}
}

func (r *runner) getCommonFingerPrints(wildcard string, limit int) (commonFP []byte, err error) {
	for i := 0; i < limit; i++ {
		sub := utils.RandomString(60) + "." + wildcard
		fp, err := r.getFingerPrint(sub)
		if err != nil {
			gologger.Warning().Msgf("Unable to get %s fingerprint, reason: %s, continuing", sub, err.Error())
			continue
		}

		if commonFP == nil {
			commonFP = fp
			continue
		}

		if !bytes.Equal(fp, commonFP) {
			return nil, fmt.Errorf("inconsistent fingerprints detected for %s", wildcard)
		}
	}

	if commonFP == nil {
		return nil, fmt.Errorf("unable to obtain any fingerprints for %s", wildcard)
	}

	return commonFP, nil
}

func (r *runner) sortSubdomainByDepth(subdomains []string, ascending bool) {
	sort.SliceStable(subdomains, func(i, j int) bool {
		depthI := strings.Count(subdomains[i], ".")
		depthJ := strings.Count(subdomains[j], ".")
		if ascending {
			return depthI < depthJ
		}
		return depthI > depthJ
	})
}

func (r *runner) saveResults(results []string) error {
	if r.options.OutputPath == "" {
		return nil
	}

	var output bytes.Buffer
	for _, res := range results {
		output.WriteString(res + "\n")
	}

	if err := utils.WriteFile(r.options.OutputPath, false, output.Bytes()); err != nil {
		return fmt.Errorf("unable to save results to %s, reason: %w", r.options.OutputPath, err)
	}

	gologger.Info().Msgf("Results saved to %s", r.options.OutputPath)
	return nil
}

func (r *runner) normalizeDomain(domain string) string {
	return strings.TrimSpace(strings.ToLower(domain))
}

func (r *runner) normalizeDomains(domains *[]string) {
	uniqueDomains := make(map[string]struct{})
	for _, domain := range *domains {
		normalized := r.normalizeDomain(domain)
		if utils.IsValidDomain(normalized) {
			uniqueDomains[normalized] = struct{}{}
		}
	}

	*domains = make([]string, 0, len(uniqueDomains))
	for domain := range uniqueDomains {
		*domains = append(*domains, domain)
	}
}

func (r *runner) Run() {
	subGroup := make(map[string][]string)

	gologger.Info().Msgf("Normalize and validate entries")
	r.normalizeDomains(&r.options.Wildcards)
	r.normalizeDomains(&r.options.Subdomains)

	gologger.Info().Msgf("Sorting wildcards by depth")
	r.sortSubdomainByDepth(r.options.Wildcards, false)

	gologger.Info().Msgf("Grouping subdomains")
	remaining := make([]string, 0, len(r.options.Subdomains))

	for _, s := range r.options.Subdomains {

		if !utils.IsValidDomain(s) {
			continue
		}

		matched := false
		for _, w := range r.options.Wildcards {
			suffix := "." + w
			if strings.HasSuffix(s, suffix) {
				subGroup[w] = append(subGroup[w], s)
				gologger.Debug().Msgf("Subdomain %s grouped under wildcard %s", s, w)
				matched = true
				break
			}
		}

		if !matched {
			remaining = append(remaining, s)
		}
	}

	r.options.Subdomains = remaining

	validSubs := make(chan string)
	var wg sync.WaitGroup

	for wildcard, subs := range subGroup {
		gologger.Info().Msgf("Eliminating invalid %s instances..", wildcard)

		if len(subs) == 0 {
			gologger.Warning().Msgf("No subdomains found for wildcard %s, skipping", wildcard)
			continue
		}

		commonFP, err := r.getCommonFingerPrints(wildcard, r.options.CommonFingerPrintsLimit)
		if err != nil {
			gologger.Warning().Msgf("Unable to get common fingerprints for %s, continuing", wildcard)
			continue
		}

		jobs := make(chan string)

		for i := 0; i < r.options.Concurrency; i++ {
			wg.Add(1)
			go r.worker(jobs, &wg, commonFP, validSubs)
		}

		go func(subs []string) {
			for _, sub := range subs {
				jobs <- sub
			}
			close(jobs)
		}(subs)
	}

	go func() {
		wg.Wait()
		close(validSubs)
	}()

	uniqueWildcardSubs := make([]string, 0)

	for sub := range validSubs {
		uniqueWildcardSubs = append(uniqueWildcardSubs, sub)
		fmt.Println(sub)
	}

	if r.options.IncludeNonWildcardMembers {
		gologger.Info().Msgf("Including non-wildcard members in the output")
		uniqueWildcardSubs = append(uniqueWildcardSubs, r.options.Subdomains...)
	}

	gologger.Info().Msgf("Writing %d unique wildcard subdomains", len(uniqueWildcardSubs))
	if r.options.OutputPath != "" {
		if err := r.saveResults(uniqueWildcardSubs); err != nil {
			gologger.Error().Msgf("Error saving results: %s", err)
		}
	}
}
