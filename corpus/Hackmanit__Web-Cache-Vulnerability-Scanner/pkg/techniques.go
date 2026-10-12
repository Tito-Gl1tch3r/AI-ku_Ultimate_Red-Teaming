package pkg

import (
	"fmt"
	"io"
	"net/url"
	"slices"
	"strconv"
	"strings"
	"sync"

	"golang.org/x/net/html"
)

var impactfulQueries []string
var unkeyedQueries []string

const NOOGPARAM = "NoOGParameter"

func init() {
}

/* Scan cookies for poisoning */
func ScanCookies() reportResult {
	var repResult reportResult
	repResult.Technique = "Cookies"
	i := 0
	for k, v := range Config.Website.Cookies {
		poison := "p" + randInt()
		msg := fmt.Sprintf("Checking cookie %s (%d/%d)\n", k, i+1, len(Config.Website.Cookies))
		Print(msg, NoColor)
		i++

		rUrl := Config.Website.Url.String()
		cb := "cb" + randInt()
		success := fmt.Sprintf("Cookie %s was successfully poisoned! cachebuster %s: %s poison: %s\n", k, Config.Website.Cache.CBName, cb, poison)
		identifier := k + "=" + v
		msg = fmt.Sprintf("Overwriting %s=%s with %s=%s\n", k, v, k, poison)
		Print(msg, NoColor)

		newCookie := map[string]string{}
		newCookie["key"] = k
		newCookie["value"] = poison

		rp := requestParams{
			repResult:  &repResult,
			headers:    []string{""},
			values:     []string{""},
			name:       k,
			identifier: identifier,
			poison:     poison,
			url:        rUrl,
			cb:         cb,
			success:    success,
			bodyString: "",
			forcePost:  false,
			m:          nil,
			newCookie:  newCookie,
		}
		responseSplittingHeaders, _, _ := issueRequests(rp)

		// check for response splitting, if poison was reflected in a header
		for _, responseSplittingHeader := range responseSplittingHeaders {
			msg := fmt.Sprintf("Checking cookie %s for Response Splitting, because it was reflected in the header %s\n", k, responseSplittingHeader)
			PrintVerbose(msg, Cyan, 1)

			rp.poison += getRespSplit()
			rp.url = rUrl
			rp.cb = "cb" + randInt()
			rp.success = fmt.Sprintf("Cookie %s successfully poisoned the header %s with Response Splitting! cachebuster %s: %s poison: %s\n", k, responseSplittingHeader, Config.Website.Cache.CBName, rp.cb, rp.poison)
			rp.identifier += " response splitting"

			msg = fmt.Sprintf("Overwriting %s=%s with %s=%s\n", k, v, k, rp.poison)
			Print(msg, NoColor)

			issueRequests(rp)
		}
	}
	return repResult
}

func ScanForwardingHeaders() reportResult {
	var repResult reportResult
	repResult.Technique = "Forward/Host Headers"

	// Host header
	header := "Host"

	portInt := 31337
	// Check if port is already contained in default response
	for searchBodyHeadersForString(strconv.Itoa(portInt), Config.Website.Body, Config.Website.Headers) {
		portInt++
	}
	port := strconv.Itoa(portInt)

	values := []string{Config.Website.Url.Host + ":" + port, Config.Website.Url.Host + ":@" + port, Config.Website.Url.Host + " " + port, Config.Website.Url.Host + ".p" + randInt(), "p" + randInt() + "." + Config.Website.Url.Host}
	for _, value := range values {
		PrintVerbose("Port-Number "+strconv.Itoa(portInt)+" was already present in websites response. Adding 1 to it.\n", NoColor, 2)
		ForwardHeadersTemplate(&repResult, []string{header}, []string{value}, header, value, NO_DUPE_HEADER)
	}

	// Duplicate Host header
	headers := []string{"Host", "hOsT"}
	dupes := []int{DUPE_HEADER_BEFORE, DUPE_HEADER_AFTER}
	for _, header := range headers {
		for _, dupe := range dupes {
			poison := "p" + randInt()
			ForwardHeadersTemplate(&repResult, []string{header}, []string{poison}, header, poison, dupe)
		}
	}

	// X-Forwarded Headers
	headers = []string{"X-Forwarded-Host", "X-Forwarded-Scheme"}
	poison := "p" + randInt()
	values = []string{poison, "nothttps"}
	identifier := "X-Forwarded-Host and X-Forwarded-Scheme"
	ForwardHeadersTemplate(&repResult, headers, values, identifier, poison, NO_DUPE_HEADER)

	values = []string{poison, "https"}
	ForwardHeadersTemplate(&repResult, headers, values, identifier, poison, NO_DUPE_HEADER)

	// Forwarded Header
	header = "Forwarded"
	poison = "p" + randInt()
	value := "host=" + poison
	ForwardHeadersTemplate(&repResult, []string{header}, []string{value}, header, poison, NO_DUPE_HEADER)

	// X-Forwarded-Port Header
	header = "X-Forwarded-Port"
	value = port
	ForwardHeadersTemplate(&repResult, []string{header}, []string{value}, header, value, NO_DUPE_HEADER)

	// X-Forwarded-Port Scheme
	header = "X-Forwarded-Scheme"
	values = []string{"http", "https"}
	for _, value := range values {
		ForwardHeadersTemplate(&repResult, []string{header}, []string{value}, header, value, NO_DUPE_HEADER)
	}

	// X-Original-URL Header (https://samcurry.net/abusing-http-path-normalization-and-cache-poisoning-to-steal-rocket-league-accounts)
	header = "X-Original-URL"
	poison = "p" + randInt()
	value = "http:\\\\" + poison + "/foo"
	ForwardHeadersTemplate(&repResult, []string{header}, []string{value}, header, poison, NO_DUPE_HEADER)

	return repResult
}

func ForwardHeadersTemplate(repResult *reportResult, headers []string, values []string, identifier string, poison string, duplicateHeaders int) {
	rUrl := Config.Website.Url.String()
	cb := "cb" + randInt()
	success := fmt.Sprintf("%s was successfully poisoned! cachebuster %s: %s poison: %s\n", headers, Config.Website.Cache.CBName, cb, values)

	rp := requestParams{
		repResult:        repResult,
		headers:          headers,
		values:           values,
		identifier:       identifier,
		poison:           poison,
		url:              rUrl,
		cb:               cb,
		success:          success,
		bodyString:       "",
		forcePost:        false,
		duplicateHeaders: duplicateHeaders,
		m:                nil,
	}
	responseSplittingHeaders, _, _ := issueRequests(rp)

	// check for response splitting, if poison was reflected in a header
	for _, responseSplittingHeader := range responseSplittingHeaders {
		rp.values[0] += getRespSplit()
		msg := fmt.Sprintf("Checking header(s) %s with value(s) %s for Response Splitting, because it was reflected in the header %s\n", rp.headers, rp.values, responseSplittingHeader)
		PrintVerbose(msg, Cyan, 1)

		rp.poison += getRespSplit()
		rp.url = rUrl
		rp.cb = "cb" + randInt()
		rp.success = fmt.Sprintf("%s successfully poisoned the header %s with Response Splitting! cachebuster %s: %s poison: %s\n", headers, responseSplittingHeader, Config.Website.Cache.CBName, rp.cb, rp.values)
		rp.identifier += " response splitting"

		issueRequests(rp)
	}
}

func ScanHTTPRequestSmuggling(proxyURL *url.URL) reportResult {
	var repResult reportResult
	identifier := "HTTP Request Smuggling"
	repResult.Technique = identifier

	path := Config.Website.Url.Path
	if Config.Website.Cache.CBisParameter {
		path, _ = addCachebusterParameter(path, "", Config.Website.Cache.CBName, false)
	}
	if path == "" {
		path = "/"
	}
	headers := GenerateHeaderString()

	PrintVerbose("Trying CLTE Request Smuggling\n", NoColor, 1)
	req := clte(path, headers)
	httpRequestSmuggling(req, &repResult, proxyURL)

	if !repResult.Vulnerable {
		PrintVerbose("Trying TECL Request Smuggling\n", NoColor, 1)
		req = tecl(path, headers)
		httpRequestSmuggling(req, &repResult, proxyURL)
	}

	if !repResult.Vulnerable {
		PrintVerbose("Trying CLCL Request Smuggling\n", NoColor, 1)
		req = clcl(path, headers)
		httpRequestSmuggling(req, &repResult, proxyURL)
	}

	if !repResult.Vulnerable {
		PrintVerbose("Trying CLCL2 Request Smuggling\n", NoColor, 1)
		req = clcl2(path, headers)
		httpRequestSmuggling(req, &repResult, proxyURL)
	}

	return repResult
}

/* Scan headers for poisoning */
func ScanHeaders(headerList []string) reportResult {
	var repResult reportResult
	repResult.Technique = "Headers"
	for _, header := range Config.Headers { // add custom headers to list
		headerVal := strings.Split(header, ":")[0]
		headerList = append(headerList, headerVal)
	}

	threads := Config.Threads
	if Config.Website.Cache.CBisHTTPMethod {
		threads = 1 // No multithreading if HTTP Method is used... Otherwise there will be a lot of false negatives/positives
		PrintVerbose("Can only scan single threaded because a HTTP Method is used as Cachebuster...\n", Yellow, 1)
	}
	sem := make(chan int, threads)
	var wg sync.WaitGroup
	wg.Add(len(headerList))
	var m sync.Mutex

	msg := fmt.Sprintf("Testing %d headers\n", len(headerList))
	PrintVerbose(msg, NoColor, 1)

	for i, header := range headerList {
		header = strings.Trim(header, "\r")
		if header == "" {
			msg := fmt.Sprintf("Skipping empty header (%d/%d)\n", i+1, len(headerList))
			PrintVerbose(msg, NoColor, 2)

			wg.Done()
			continue
		}

		go func(i int, header string) {
			defer wg.Done()
			sem <- 1
			defer func() { <-sem }() // Freigabe der Semaphore, egal was passiert. Dadurch werden Deadlocks verhindert

			msg := fmt.Sprintf("Testing now (%d/%d) %s\n", i+1, len(headerList), header)
			PrintVerbose(msg, NoColor, 2)
			rUrl := Config.Website.Url.String()
			poison := "p" + randInt()
			cb := "cb" + randInt()
			success := fmt.Sprintf("Header %s was successfully poisoned! cachebuster %s: %s poison: %s\n", header, Config.Website.Cache.CBName, cb, poison)
			identifier := fmt.Sprintf("header %s", header)

			rp := requestParams{
				repResult:  &repResult,
				headers:    []string{header},
				values:     []string{poison},
				name:       header,
				identifier: identifier,
				poison:     poison,
				url:        rUrl,
				cb:         cb,
				success:    success,
				bodyString: "",
				forcePost:  false,
				m:          &m,
			}
			responseSplittingHeaders, _, _ := issueRequests(rp)

			// check for response splitting, if poison was reflected in a header
			for _, responseSplittingHeader := range responseSplittingHeaders {
				msg := fmt.Sprintf("Testing now (%d/%d) %s for Response Splitting, because it was reflected in the header %s\n", i+1, len(headerList), header, responseSplittingHeader)
				PrintVerbose(msg, Cyan, 1)

				rp.url = rUrl
				rp.cb = "cb" + randInt()
				rp.poison += getRespSplit()
				rp.success = fmt.Sprintf("Header %s successfully poisoned the header %s with Response Splitting! cachebuster %s: %s poison: %s\n", header, responseSplittingHeader, Config.Website.Cache.CBName, rp.cb, rp.poison)
				rp.identifier += " response splitting"

				issueRequests(rp)
			}
		}(i, header)

	}
	wg.Wait()

	return repResult
}

/* Scan query parameters for poisoning */
func ScanParameters(parameterList []string) reportResult {
	var repResult reportResult
	repResult.Technique = "Parameters"

	parametersToTest := parameterList
	for k := range Config.Website.Queries {
		if !slices.Contains(parameterList, k) { // only add parameters which are not already in the list
			parametersToTest = append(parametersToTest, k) // add custom parameters to list
		}
	}

	threads := Config.Threads
	if Config.Website.Cache.CBisHTTPMethod {
		threads = 1 // No multithreading if HTTP Method is used... Otherwise there will be a lot of false negatives/positives
		PrintVerbose("Can only scan single threaded because a HTTP Method is used as Cachebuster...\n", Yellow, 1)
	}
	sem := make(chan int, threads)
	var wg sync.WaitGroup
	wg.Add(len(parametersToTest))
	var m sync.Mutex

	impactfulQueries = []string{}
	unkeyedQueries = []string{}

	msg := fmt.Sprintf("Testing %d parameters\n", len(parametersToTest))
	PrintVerbose(msg, NoColor, 1)

	for i, parameter := range parametersToTest {
		if parameter == "" {
			msg := fmt.Sprintf("Skipping empty query (%d/%d) %s\n", i+1, len(parametersToTest), parameter)
			PrintVerbose(msg, NoColor, 2)
			wg.Done()
			continue
		}

		go func(i int, parameter string) {
			defer wg.Done()
			sem <- 1
			defer func() { <-sem }() // Freigabe der Semaphore, egal was passiert. Dadurch werden Deadlocks verhindert

			parameter = strings.Trim(parameter, "\r")
			msg := fmt.Sprintf("Testing now Parameter (%d/%d) %s\n", i+1, len(parametersToTest), parameter)
			PrintVerbose(msg, NoColor, 2)

			rUrl := Config.Website.Url.String()
			poison := "p" + randInt()
			cb := "cb" + randInt()
			success := fmt.Sprintf("Query Parameter %s was successfully poisoned! cachebuster %s: %s poison: %s\n", parameter, Config.Website.Cache.CBName, cb, poison)
			identifier := fmt.Sprintf("parameter %s", parameter)

			ogValue := NOOGPARAM
			if strings.Contains(strings.ToLower(rUrl), "?"+parameter+"=") || strings.Contains(strings.ToLower(rUrl), "&"+parameter+"=") { // remove param if it already existed, so that it will be set only one time and that being with the poison value
				rUrl, ogValue, _ = removeParam(rUrl, parameter)
			}

			rp := requestParams{
				repResult:  &repResult,
				headers:    []string{""},
				values:     []string{poison},
				parameters: []string{parameter + "=" + poison},
				name:       parameter,
				identifier: identifier,
				poison:     poison,
				ogParam:    parameter + "=" + ogValue,
				url:        rUrl,
				cb:         cb,
				technique:  "parameter",
				success:    success,
				bodyString: "",
				forcePost:  false,
				m:          &m,
			}
			responseSplittingHeaders, impactful, unkeyed := issueRequests(rp)

			if impactful && !unkeyed {
				impactfulQueries = append(impactfulQueries, parameter)
			} else if unkeyed {
				unkeyedQueries = append(unkeyedQueries, parameter)
			}

			// check for response splitting, if poison was reflected in a header
			for _, responseSplittingHeader := range responseSplittingHeaders {
				msg := fmt.Sprintf("Testing now Parameter (%d/%d) %s for Response Splitting, because it was reflected in the header %s\n", i+1, len(parametersToTest), parameter, responseSplittingHeader)
				PrintVerbose(msg, Cyan, 1)

				rp.poison += getRespSplit()
				rp.parameters = []string{parameter + "=" + rp.poison}
				rp.url = rUrl
				rp.cb = "cb" + randInt()
				rp.success = fmt.Sprintf("Query Parameter %s successfully poisoned the header %s with Response Splitting! cachebuster %s: %s poison: %s\n", parameter, responseSplittingHeader, Config.Website.Cache.CBName, rp.cb, rp.poison)
				rp.identifier += " response splitting"
				issueRequests(rp)
			}
		}(i, parameter)

	}
	wg.Wait()

	return repResult
}

/* Check for fat GET */
func ScanFatGET() reportResult {
	var repResult reportResult
	repResult.Technique = "Fat GET"

	if len(impactfulQueries) == 0 {
		msg := "No impactful query parameters were found beforehand. Run the query parameter scan (maybe with a different wordlist)."
		Print(msg+"\n", Yellow)
		repResult.HasError = true
		repResult.ErrorMessages = append(repResult.ErrorMessages, msg)
		return repResult
	} else {
		msg := fmt.Sprintf("The following parameters were found to be impactful and will be tested for parameter cloaking: %s\n", impactfulQueries)
		Print(msg, Cyan)
	}

	threads := Config.Threads
	if Config.Website.Cache.CBisHTTPMethod {
		threads = 1 // No multithreading if HTTP Method is used... Otherwise there will be a lot of false negatives/positives
		PrintVerbose("Can only scan single threaded because a HTTP Method is used as Cachebuster...\n", Yellow, 1)
	}
	sem := make(chan int, threads)
	var wg sync.WaitGroup
	wg.Add(len(impactfulQueries))
	var m sync.Mutex

	headers := []string{"", "", "X-HTTP-Method-Override", "X-HTTP-Method", "X-Method-Override"}
	values := []string{"", "", "POST", "POST", "POST"}

	for method := 0; method < 5; method++ {
		var identifier string
		forcePost := false
		if method == 0 {
			identifier = "simple Fat GET"
		} else if method == 1 {
			identifier = "POST Fat GET"
			forcePost = true
		} else {
			identifier = fmt.Sprintf("%s Fat GET", headers[method])
		}
		msg := "Testing now " + identifier + "\n"
		Print(msg, NoColor)

		for i, s := range impactfulQueries {
			// Parameter Limit
			if i >= 500 {
				if i == 500 {
					Print("Parameter Limit at 500\n", Red)
				}
				wg.Done()
				continue
			}
			poison := "p" + randInt()

			go func(i int, s string, poison string) {
				defer wg.Done()
				sem <- 1
				defer func() { <-sem }() // Freigabe der Semaphore, egal was passiert. Dadurch werden Deadlocks verhindert

				msg := fmt.Sprintf("(%d/%d) %s\n", i+1, len(impactfulQueries), s)
				PrintVerbose(msg, NoColor, 2)
				rUrl := Config.Website.Url.String()
				cb := "cb" + randInt()
				bodyString := s + "=" + poison
				success := fmt.Sprintf("Query Parameter %s was successfully poisoned via %s! cachebuster %s: %s poison:%s\n", s, identifier, Config.Website.Cache.CBName, cb, poison)

				rp := requestParams{
					repResult:  &repResult,
					headers:    []string{headers[method]},
					values:     []string{values[method]},
					identifier: identifier,
					poison:     poison,
					url:        rUrl,
					cb:         cb,
					success:    success,
					bodyString: bodyString,
					forcePost:  forcePost,
					m:          &m,
				}
				responseSplittingHeaders, _, _ := issueRequests(rp)

				// check for response splitting, if poison was reflected in a header
				for _, responseSplittingHeader := range responseSplittingHeaders {
					msg := fmt.Sprintf("Testing now (%d/%d) %s for Response Splitting, because it was reflected in the header %s\n", i+1, len(impactfulQueries), s, responseSplittingHeader)
					PrintVerbose(msg, Cyan, 1)

					rp.url = rUrl
					rp.cb = "cb" + randInt()
					rp.poison += getRespSplit()
					rp.bodyString += getRespSplit()
					rp.identifier += " response splitting"
					rp.success = fmt.Sprintf("Query Parameter %s successfully poisoned the header %s via %s with Response Splitting! cachebuster %s: %s poison:%s\n", s, responseSplittingHeader, identifier, Config.Website.Cache.CBName, rp.cb, rp.poison)

					issueRequests(rp)
				}
			}(i, s, poison)
		}
		wg.Wait()
		wg.Add(len(impactfulQueries))
	}

	return repResult
}

/* Check for Parameter Cloaking */
func ScanParameterCloaking() reportResult {
	var repResult reportResult
	repResult.Technique = "Parameter Cloaking"

	if len(impactfulQueries) == 0 {
		msg := "No impactful query parameters were found beforehand. Run the query parameter scan (maybe with a different wordlist)."
		Print(msg+"\n", Yellow)
		repResult.HasError = true
		repResult.ErrorMessages = append(repResult.ErrorMessages, msg)
		return repResult
	} else {
		msg := fmt.Sprintf("The following parameters were found to be impactful and will be tested for parameter cloaking: %s\n", impactfulQueries)
		Print(msg, Cyan)
	}

	utm_parameters := []string{"utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term", "gad_campaignid"}
	parameters_to_test := utm_parameters
	for _, k := range unkeyedQueries {
		if !slices.Contains(parameters_to_test, k) { // only add parameters which are not already in the list
			parameters_to_test = append(parameters_to_test, k)
		}
	}

	/***********TODO Check if urlWithCb already contains utm parameter.
				Check if ? or querySeperator is needed
	****************/

	// The first request is made so a cache miss is forced and the following responses will only
	//have a cache hit, if they are unkeyed
	rUrl := Config.Website.Url.String()
	cb := "cb" + randInt()
	rp := requestParams{
		identifier: "first request %s",
		url:        rUrl,
		cb:         cb,
	}
	firstRequest(rp)

	threads := Config.Threads
	if Config.Website.Cache.CBisHTTPMethod {
		threads = 1 // No multithreading if HTTP Method is used... Otherwise there will be a lot of false negatives/positives
		PrintVerbose("Can only scan single threaded because a HTTP Method is used as Cachebuster...\n", Yellow, 1)
	}
	sem := make(chan int, threads)
	var wg sync.WaitGroup
	var m sync.Mutex

	unkeyed_parameters := []string{}
	cache := Config.Website.Cache
	if cache.Indicator == "" || cache.TimeIndicator {
		msg := "hit/miss isn't verbose. Can't check which parameters unkeyed, so all utm_parameters and query parameters will be used\n"
		Print(msg, Yellow)
		unkeyed_parameters = parameters_to_test

	} else {
		//Test which parameters are unkeyed
		wg.Add(len(parameters_to_test))

		for i, s := range parameters_to_test {
			go func(i int, s string) {
				defer wg.Done()
				sem <- 1
				defer func() { <-sem }() // Prevent Deadlocks

				msg := fmt.Sprintf("Testing now for unkeyed parameters (%d/%d) %s\n", i+1, len(parameters_to_test), s)
				PrintVerbose(msg, NoColor, 2)

				identifier := fmt.Sprintf("unkeyed parameter %s", s)
				//TODO: TimeOut behandeln!!!
				rp := requestParams{
					identifier: identifier,
					url:        rUrl,
					cb:         cb,
					parameters: []string{s + "=foobar"}, // parameter with nonsense value
				}
				_, _, _, respHeader, err := firstRequest(rp)
				if err != nil && err.Error() != "stop" { // stop is expected for successful unkeyed parameters,because the first request should be the same as the default/cached request!
					m.Lock()
					repResult.HasError = true
					repResult.ErrorMessages = append(repResult.ErrorMessages, err.Error())
					m.Unlock()
					return
				}
				hit := false
				for _, v := range respHeader[cache.Indicator] {
					indicValue := strings.TrimSpace(strings.ToLower(v))
					hit = hit || checkCacheHit(indicValue, cache.Indicator)
				} // TODO add check for timebased cache indicator! + remove then cache.TimeIndicator from the if above
				if hit {
					m.Lock()
					unkeyed_parameters = append(unkeyed_parameters, s)
					m.Unlock()
				}
			}(i, s)
		}
		wg.Wait()
	}

	if len(unkeyed_parameters) == 0 {
		msg := "No unkeyed parameters could be found. Parameter Cloaking is not possible.\n"
		Print(msg, Yellow)
	} else {
		msg := fmt.Sprintf("The following parameters were found to be unkeyed and will be used for parameter cloaking: %s\n", unkeyed_parameters)
		Print(msg, Cyan)
	}

	cloak := ";"
	if Config.QuerySeparator == ";" {
		cloak = "&"
	}

	if slices.Contains(impactfulQueries, cache.CBName) { // If the cachebuster is impactful, it shall be tested two times. One time appended and one time prepended.
		impactfulQueries = append(impactfulQueries, cache.CBName)
	}

	var cbNameCount int
	var cbNameCountMutex sync.Mutex

	for iu, u := range unkeyed_parameters {

		//its sufficient to only test one unkeyed_parameter as it should behave the same way as the others. However, in the case of no cache indicator, test all parameters
		if iu > 0 && cache.Indicator != "" {
			break
		}
		wg.Add(len(impactfulQueries))

		for is, s := range impactfulQueries {
			// Parameter Limit
			if is >= 500 {
				if is == 500 {
					Print("Parameter Limit at 500\n", Red)
				}
				wg.Done()
				continue
			}

			poison := "p" + randInt()

			go func(iu int, u string, is int, s string, poison string) {
				defer wg.Done()
				sem <- 1
				defer func() { <-sem }() // Freigabe der Semaphore, egal was passiert. Dadurch werden Deadlocks verhindert

				msg := fmt.Sprintf("Testing now Parameter Cloaking (%d/%d) %s%s%s\n", iu+is+1, len(impactfulQueries)*len(unkeyed_parameters), u, cloak, s)
				PrintVerbose(msg, NoColor, 2)
				cb := "cb" + randInt()
				success := fmt.Sprintf("Query Parameter %s was successfully poisoned via Parameter Cloaking using %s! cachebuster %s:%s poison:%s\n", s, u, Config.Website.Cache.CBName, cb, poison)
				identifier := fmt.Sprintf("parameter cloaking %s %s", u, s)

				prependCB := false
				if s == cache.CBName { // shall be true for the second test of the cachebuster and false in all other cases
					cbNameCountMutex.Lock()
					cbNameCount++
					if cbNameCount == 2 {
						prependCB = true
					}
					cbNameCountMutex.Unlock()
				}

				rp := requestParams{
					repResult:  &repResult,
					headers:    []string{""},
					values:     []string{poison},
					parameters: []string{u + "=foobar" + cloak + s + "=" + poison},
					identifier: identifier,
					poison:     poison,
					url:        rUrl,
					cb:         cb,
					prependCB:  prependCB,
					success:    success,
					bodyString: "",
					forcePost:  false,
					m:          &m,
					newCookie:  nil,
				}
				responseSplittingHeaders, _, _ := issueRequests(rp)

				// check for response splitting, if poison was reflected in a header
				for _, responseSplittingHeader := range responseSplittingHeaders {
					msg := fmt.Sprintf("Testing now Parameter Cloaking (%d/%d) %s%s%s for Response Splitting, because it was reflected in the header %s\n", iu+is+1, len(impactfulQueries)*len(unkeyed_parameters), u, cloak, s, responseSplittingHeader)
					PrintVerbose(msg, Cyan, 1)

					rp.url = rUrl
					rp.cb = "cb" + randInt()
					rp.poison += getRespSplit()
					rp.parameters = []string{u + "=foobar" + cloak + s + "=" + rp.poison}
					rp.success = fmt.Sprintf("Query Parameter %s successfully poisoned the header %s with Response Splitting using %s with Parameter Cloaking! cachebuster %s:%s poison:%s\n", s, responseSplittingHeader, u, Config.Website.Cache.CBName, rp.cb, rp.poison)
					rp.identifier += " response splitting"

					issueRequests(rp)
				}
			}(iu, u, is, s, poison)
		}
		wg.Wait()
	}

	return repResult
}

/* Check for Parameter Pollution */
func ScanParameterPollution() reportResult {
	var repResult reportResult
	repResult.Technique = "Parameter Pollution"

	if len(impactfulQueries) == 0 {
		msg := "No impactful query parameters were found beforehand. Run the query parameter scan (maybe with a different wordlist)."
		Print(msg+"\n", Yellow)
		repResult.HasError = true
		repResult.ErrorMessages = append(repResult.ErrorMessages, msg)
		return repResult
	} else {
		msg := fmt.Sprintf("The following parameters were found to be impactful and will be tested for parameter pollution: %s\n", impactfulQueries)
		Print(msg, Cyan)
	}

	threads := Config.Threads
	if Config.Website.Cache.CBisHTTPMethod {
		threads = 1 // No multithreading if HTTP Method is used... Otherwise there will be a lot of false negatives/positives
		PrintVerbose("Can only scan single threaded because a HTTP Method is used as Cachebuster...\n", Yellow, 1)
	}
	sem := make(chan int, threads)
	var wg sync.WaitGroup
	var m sync.Mutex

	if len(impactfulQueries) > 500 { // only test first 500 impactful queries. TODO decrease amount as such a high amount most likely means they are false positives anyways
		shortenedQueries := []string{}
		for i := range 500 {
			shortenedQueries = append(shortenedQueries, impactfulQueries[i])
		}
		impactfulQueries = shortenedQueries
	}
	impactfulQueries = append(impactfulQueries, impactfulQueries...) // we want to test each impactful query parameter 2times. One time with the poison in the first and second with the poison in the second appearance

	wg.Add(len(impactfulQueries))

	for is, s := range impactfulQueries {
		poison := "p" + randInt()
		prependCB := false // shall be true for the second test of the cachebuster

		go func(is int, s string, poison string, secondHalf bool) {
			defer wg.Done()
			sem <- 1
			defer func() { <-sem }() // Freigabe der Semaphore, egal was passiert. Dadurch werden Deadlocks verhindert

			url := Config.Website.Url.String()
			ogValue := "foobar"
			if strings.Contains(strings.ToLower(url), "?"+s+"=") || strings.Contains(strings.ToLower(url), "&"+s+"=") {
				url, ogValue, _ = removeParam(url, s)
			}

			var parameters []string
			if is >= len(impactfulQueries)/2 {
				parameters = []string{s + "=" + poison, s + "=" + ogValue}
			} else {
				parameters = []string{s + "=" + ogValue, s + "=" + poison}
			}

			msg := fmt.Sprintf("Testing now Parameter Pollution (%d/%d) %s\n", is+1, len(impactfulQueries)*2, s)
			PrintVerbose(msg, NoColor, 2)
			cb := "cb" + randInt()
			success := fmt.Sprintf("Query Parameter %s was successfully poisoned via Parameter Pollution! cachebuster %s:%s poison:%s\n", s, Config.Website.Cache.CBName, cb, poison)
			identifier := fmt.Sprintf("parameter Pollution %s", s)

			rp := requestParams{
				repResult:  &repResult,
				headers:    []string{""},
				values:     []string{poison},
				parameters: parameters,
				technique:  "pollution",
				identifier: identifier,
				poison:     poison,
				url:        url,
				cb:         cb,
				ogParam:    s + "=" + ogValue,
				prependCB:  prependCB,
				success:    success,
				bodyString: "",
				forcePost:  false,
				m:          &m,
				newCookie:  nil,
			}
			responseSplittingHeaders, _, _ := issueRequests(rp)

			// check for response splitting, if poison was reflected in a header
			for _, responseSplittingHeader := range responseSplittingHeaders {
				msg := fmt.Sprintf("Testing now Parameter Pollution (%d/%d) %s for Response Splitting, because it was reflected in the header %s\n", is+1, len(impactfulQueries)*2, s, responseSplittingHeader)
				PrintVerbose(msg, Cyan, 1)

				rp.url = url
				rp.cb = "cb" + randInt()
				rp.poison += getRespSplit()

				if is >= len(impactfulQueries) {
					parameters = []string{s + "=" + rp.poison, s + "=foobar"}
				} else {
					parameters = []string{s + "=foobar", s + "=" + rp.poison}
				}

				rp.parameters = parameters
				rp.success = fmt.Sprintf("Query Parameter %s successfully poisoned the header %s with Response Splitting with Parameter Pollution! cachebuster %s:%s poison:%s\n", s, responseSplittingHeader, Config.Website.Cache.CBName, rp.cb, rp.poison)
				rp.identifier += " response splitting"

				issueRequests(rp)
			}
		}(is, s, poison, is >= len(impactfulQueries)/2)
	}
	wg.Wait()

	return repResult
}

/* Check for Parameter Encoding */
func ScanParameterEncoding() reportResult {
	var repResult reportResult
	repResult.Technique = "Parameter Encoding"

	if len(impactfulQueries) == 0 {
		msg := "No impactful query parameters were found beforehand. Run the query parameter scan (maybe with a different wordlist)."
		Print(msg+"\n", Yellow)
		repResult.HasError = true
		repResult.ErrorMessages = append(repResult.ErrorMessages, msg)
		return repResult
	} else {
		msg := fmt.Sprintf("The following parameters were found to be impactful and will be tested for parameter encoding: %s\n", impactfulQueries)
		Print(msg, Cyan)
	}

	threads := Config.Threads
	if Config.Website.Cache.CBisHTTPMethod {
		threads = 1 // No multithreading if HTTP Method is used... Otherwise there will be a lot of false negatives/positives
		PrintVerbose("Can only scan single threaded because a HTTP Method is used as Cachebuster...\n", Yellow, 1)
	}
	sem := make(chan int, threads)
	var wg sync.WaitGroup
	var m sync.Mutex

	if len(impactfulQueries) > 500 { // only test first 500 impactful queries. TODO decrease amount as such a high amount most likely means they are false positives anyways
		shortenedQueries := []string{}
		for i := range 500 {
			shortenedQueries = append(shortenedQueries, impactfulQueries[i])
		}
		impactfulQueries = shortenedQueries
	}
	impactfulQueries = append(impactfulQueries, impactfulQueries...) // we want to test each impactful query parameter 2times. One time with the poison in the first and second with the poison in the second appearance

	wg.Add(len(impactfulQueries))

	for is, s := range impactfulQueries {
		poison := "p" + randInt()
		prependCB := false // shall be true for the second test of the cachebuster

		go func(is int, s string, poison string, secondHalf bool) {
			defer wg.Done()
			sem <- 1
			defer func() { <-sem }() // Freigabe der Semaphore, egal was passiert. Dadurch werden Deadlocks verhindert

			url := Config.Website.Url.String()
			ogValue := "foobar"
			if strings.Contains(strings.ToLower(url), "?"+s+"=") || strings.Contains(strings.ToLower(url), "&"+s+"=") {
				url, ogValue, _ = removeParam(url, s)
			}

			var parameters []string
			if is >= len(impactfulQueries)/2 {
				parameters = []string{urlEncodeAll(s) + "=" + poison, s + "=" + ogValue}
			} else {
				parameters = []string{s + "=" + ogValue, urlEncodeAll(s) + "=" + poison}
			}

			msg := fmt.Sprintf("Testing now Parameter Encoding (%d/%d) %s\n", is+1, len(impactfulQueries)*2, s)
			PrintVerbose(msg, NoColor, 2)
			cb := "cb" + randInt()
			success := fmt.Sprintf("Query Parameter %s was successfully poisoned via Parameter Encoding! cachebuster %s:%s poison:%s\n", s, Config.Website.Cache.CBName, cb, poison)
			identifier := fmt.Sprintf("parameter Encoding %s", s)

			rp := requestParams{
				repResult:  &repResult,
				headers:    []string{""},
				values:     []string{poison},
				parameters: parameters,
				technique:  "encoding",
				identifier: identifier,
				poison:     poison,
				url:        url,
				cb:         cb,
				ogParam:    s + "=" + ogValue,
				prependCB:  prependCB,
				success:    success,
				bodyString: "",
				forcePost:  false,
				m:          &m,
				newCookie:  nil,
			}
			responseSplittingHeaders, _, _ := issueRequests(rp)

			// check for response splitting, if poison was reflected in a header
			for _, responseSplittingHeader := range responseSplittingHeaders {
				msg := fmt.Sprintf("Testing now Parameter Encoding (%d/%d) %s for Response Splitting, because it was reflected in the header %s\n", is+1, len(impactfulQueries)*2, s, responseSplittingHeader)
				PrintVerbose(msg, Cyan, 1)

				rp.url = url
				rp.cb = "cb" + randInt()
				rp.poison += getRespSplit()

				if is >= len(impactfulQueries) {
					parameters = []string{urlEncodeAll(s) + "=" + rp.poison, s + "=foobar"}
				} else {
					parameters = []string{s + "=foobar", urlEncodeAll(s) + "=" + rp.poison}
				}

				rp.parameters = parameters
				rp.success = fmt.Sprintf("Query Parameter %s successfully poisoned the header %s with Response Splitting with Parameter Encoding! cachebuster %s:%s poison:%s\n", s, responseSplittingHeader, Config.Website.Cache.CBName, rp.cb, rp.poison)
				rp.identifier += " response splitting"

				issueRequests(rp)
			}
		}(is, s, poison, is >= len(impactfulQueries)/2)
	}
	wg.Wait()

	return repResult
}

/* Check for different DOS techniques */
func DOS() reportResult {
	var repResult reportResult
	repResult.Technique = "DOS"

	hho(&repResult)

	// HMC (Header Metachar Character)
	headers := []string{"X-Metachar-Header"}
	values := []string{"n\nn", "r\rr", "a\aa", "x00\x00x00", "b\bb", "x1b\x1bx1b", "v\vv", "f\ff", "u0000\u0000u0000"} // TODO put not functional meta chars, due to fasthttp header value restrictions, in the value using \r\n in the header name

	for _, header := range headers {
		headerDOSTemplate(&repResult, values, header, "HMC ", true)
	}

	headers = []string{"X-Meta\nchar-Header", "X-Meta\rchar-Header", "X-Meta\achar-Header", "X-Meta\x00char-Header", "X-Meta\bchar-Header", "X-Meta\x1bchar-Header", "X-Meta\vchar-Header", "X-Meta\fchar-Header", "X-Meta\u0000char-Header"}
	values = []string{"n", "r", "a", "x00", "b", "x1b", "v", "ff", "u0000"}

	for i, header := range headers {
		headerDOSTemplate(&repResult, []string{values[i]}, header, "HMC ", true)
	}

	// HMO (HTTP Method Override)
	values = []string{"GET", "POST", "DELETE", "HEAD", "OPTIONS", "CONNECT", "PATCH", "PUT", "TRACE", "NONSENSE"}
	headers = []string{"X-HTTP-Method-Override", "X-HTTP-Method", "X-Method-Override"}
	for _, header := range headers {
		headerDOSTemplate(&repResult, values, header, "HMO ", true)
	}

	// DOS via not implemented transferEncoding
	values = []string{"asdf"}
	headerDOSTemplate(&repResult, values, "zTRANSFER-ENCODING", "Not supported Transfer-Encoding ", true)

	// DOS via incompatible/outdated browser agent
	values = []string{"Mozilla/5.0 (Windows; U; MSIE 9.0; WIndows NT 9.0; en-US))"}
	headerDOSTemplate(&repResult, values, "User-Agent", "incompatible browser ", true)

	// DOS via blacklisted security scanner user agent // TODO: Also add bots? Or will the IP be blocked too fast
	values = []string{"WebCacheVulnerabilityScanner v" + version, "Fuzz Faster U Fool", "Nuclei - Open-source project (github.com/projectdiscovery/nuclei)", "sqlmap/1.3.11#stable (http://sqlmap.org)", "gobuster/3.1.0", "Wfuzz/2.2", "Mozilla/5.0 (compatible; Nmap Scripting Engine; https://nmap.org/book/nse.html)", "masscan/1.3", "blekkobot"}
	headerDOSTemplate(&repResult, values, "User-Agent", "blacklisted security scanners ", true)

	// DOS via illegal header name
	/* Currently disabled because of net/http throws error because of illegal character TODO: workaround, see https://stackoverflow.com/questions/70678016/how-to-bypass-golangs-http-request-net-http-rfc-compliance
	values = []string{"foobar"}
	headerDOSTemplate(&repResult, values, "Ill\\egal", "illegal header name ", true)
	*/

	// DOS via Max-Forwards (Webserver/Cache returns request)
	values = []string{"0", "1", "2"}
	headerDOSTemplate(&repResult, values, "Max-Forwards", "", true)

	// DOS via waf blocking because of a blacklist word
	// TODO: change header to probably whitelisted header, More Blacklist words?
	values = []string{".burpcollaborator.net", "<script>alert(1)</script>"}
	headerDOSTemplate(&repResult, values, "Any-Header", "blacklist ", true)

	// DOS via Range
	values = []string{"bytes=m10x", "bytes=9-4", "bytes=-1024,0", "bytes=0-,0-,0-,0-"}
	headerDOSTemplate(&repResult, values, "Range", "", true)

	// DOS via X-Forwarded-Protocol
	values = []string{"http", "https", "ssl", "m10x"}
	headerDOSTemplate(&repResult, values, "X-Forwarded-Protocol", "", true)

	// DOS via X-Forwarded-Scheme
	values = []string{"http", "https", "nothttps", "m10x"}
	headerDOSTemplate(&repResult, values, "X-Forwarded-Scheme", "", true)

	// DOS via X-Fordwarded-SSL
	values = []string{"on", "off", "m10x"}
	headerDOSTemplate(&repResult, values, "X-Forwarded-SSL", "", true)

	// DOS via Upgrade
	values = []string{"HTTP/0.9", "Websocket, RTA/x11", "HTTP/2.0, SHTTP/1.3, IRC/6.9", "m10x"}
	headerDOSTemplate(&repResult, values, "Upgrade", "", true)

	// DOS via invalid Content-Type
	values = []string{"m10x"}
	headerDOSTemplate(&repResult, values, "Content-Type", "", true)

	// DOS via middleware prefetch (next.js specific, CVE-2023-46298) TODO check for {} in response
	values = []string{"1"}
	headerDOSTemplate(&repResult, values, "X-Middleware-Prefetch", "", true)

	// DOS via Rsc (next.js specific) TODO check for format in response
	values = []string{"1"}
	headerDOSTemplate(&repResult, values, "Rsc", "", true)

	return repResult
}

/* HTTP Header Oversize */
func hho(repResult *reportResult) {
	repetitions := []int{50, 100, 200} //4k, 8k, 16k

	msg := fmt.Sprintf("Testing now HHO with Size Limits of ~80*%d bytes\n", repetitions)
	PrintVerbose(msg, NoColor, 2)

	threads := Config.Threads
	if Config.Website.Cache.CBisHTTPMethod {
		threads = 1 // No multithreading if HTTP Method is used... Otherwise there will be a lot of false negatives/positives
		PrintVerbose("Can only scan single threaded because a HTTP Method is used as Cachebuster...\n", Yellow, 1)
	}
	sem := make(chan int, threads)
	var wg sync.WaitGroup
	wg.Add(len(repetitions))
	var m sync.Mutex

	for _, repetition := range repetitions {
		go func(repetition int) {
			defer wg.Done()
			sem <- 1
			defer func() { <-sem }() // Freigabe der Semaphore, egal was passiert. Dadurch werden Deadlocks verhindert

			limit := repetition * 8 / 100
			//msg := fmt.Sprintf("Testing now HHO with Size Limit %dk bytes\n", limit)
			//Print(msg, NoColor)

			headers := []string{}
			values := []string{}

			for i := range repetition {
				headername := fmt.Sprintf("X-Oversized-Header-%d", i+1)
				value := "Big-Value-000000000000000000000000000000000000000000000000000000000000000000000000000000"
				headers = append(headers, headername)
				values = append(values, value)
			}

			rUrl := Config.Website.Url.String()
			cb := "cb" + randInt()
			success := fmt.Sprintf("HHO DOS was successfully poisoned! cachebuster %s: %s \n%s\n", Config.Website.Cache.CBName, cb, rUrl)
			identifier := fmt.Sprintf("HHO with limit of %dk bytes", limit)
			rp := requestParams{
				repResult:  repResult,
				headers:    headers,
				values:     values,
				identifier: identifier,
				url:        rUrl,
				cb:         cb,
				success:    success,
				m:          &m,
			}

			_, _, _ = issueRequests(rp)
		}(repetition)
	}

	wg.Wait()
}

func headerDOSTemplate(repResult *reportResult, values []string, header string, msgextra string, httpConform bool) {
	msg := fmt.Sprintf("Testing now %sDOS with header %s and values %s\n", msgextra, header, values)
	PrintVerbose(msg, NoColor, 2)

	threads := Config.Threads
	if Config.Website.Cache.CBisHTTPMethod {
		threads = 1 // No multithreading if HTTP Method is used... Otherwise there will be a lot of false negatives/positives
		PrintVerbose("Can only scan single threaded because a HTTP Method is used as Cachebuster...\n", Yellow, 1)
	}
	sem := make(chan int, threads)
	var wg sync.WaitGroup
	wg.Add(len(values))
	var m sync.Mutex

	for _, value := range values {

		go func(value string, httpConform bool) {
			defer wg.Done()
			sem <- 1
			defer func() { <-sem }() // Freigabe der Semaphore, egal was passiert. Dadurch werden Deadlocks verhindert

			msg := fmt.Sprintf("Testing now %q Header DOS with %q\n", header, value) // %q for raw printing of control characters
			PrintVerbose(msg, NoColor, 2)
			rUrl := Config.Website.Url.String()
			cb := "cb" + randInt()
			success := fmt.Sprintf("%sDOS with header %q was successfully poisoned! cachebuster %s: %s poison: %q\n", msgextra, header, Config.Website.Cache.CBName, cb, value)
			identifier := fmt.Sprintf("%s%q with %q", msgextra, header, value)

			rp := requestParams{
				repResult:  repResult,
				headers:    []string{header},
				values:     []string{value},
				identifier: identifier,
				poison:     "",
				url:        rUrl,
				cb:         cb,
				success:    success,
				bodyString: "",
				forcePost:  false,
				m:          &m,
				newCookie:  nil,
			}
			responseSplittingHeaders, _, _ := issueRequests(rp)

			// check for response splitting, if poison was reflected in a header
			for _, responseSplittingHeader := range responseSplittingHeaders {
				msg := fmt.Sprintf("Testing now %s Header DOS with %s\n for Response Splitting, because it was reflected in the header %s", header, value, responseSplittingHeader)
				PrintVerbose(msg, Cyan, 1)

				rp.values[0] += getRespSplit()
				rp.url = rUrl
				rp.cb = "cb" + randInt()
				rp.success = fmt.Sprintf("%sDOS with header %s successfully poisoned the header %s with Response Splitting! cachebuster %s: %s poison: %s\n", msgextra, header, responseSplittingHeader, Config.Website.Cache.CBName, rp.cb, rp.values[0])
				rp.identifier += getRespSplit() + " with response splitting"

				issueRequests(rp)
			}
		}(value, httpConform)
	}
	wg.Wait()
}

func ScanCSS() reportResult {
	var repResult reportResult
	repResult.Technique = "CSS poisoning"

	webStruct, err := GetWebsite(Config.Website.Url.String(), false, false) // get body without cachebuster. TODO use response w/o cachebuster from recon, so it doesn't have to be fetched again
	if err != nil {
		msg := fmt.Sprintf("Error while fetching css files %s: %s\n", Config.Website.Url.String(), err.Error())
		Print(msg, Red)
		repResult.ErrorMessages = append(repResult.ErrorMessages, msg)
		return repResult
	}
	bodyReader := strings.NewReader(webStruct.Body) // use body without cachebuster, so the css files can be found
	tokenizer := html.NewTokenizer(bodyReader)

	var urls []string

	eof := false
	for !eof {
		tokentype := tokenizer.Next()

		switch tokentype {
		case html.StartTagToken, html.SelfClosingTagToken:

			token := tokenizer.Token()

			if token.Data == "link" {
				for _, a := range token.Attr {
					if a.Key == "href" {
						if !strings.HasSuffix(a.Val, ".css") && !strings.Contains(a.Val, ".css?") {
							break
						}
						tempURL := addDomain(a.Val, Config.Website.Domain)
						if tempURL != "" {
							urls = append(urls, tempURL)
						}
						break
					}
				}
			}
		// When EOF is reached a html.ErrorToken appears
		case html.ErrorToken:
			err := tokenizer.Err()
			if err == io.EOF {
				eof = true
				break
			}
			msg := fmt.Sprintf("error tokenizing HTML: %+v", tokenizer.Err())
			Print(msg, Yellow)
		}
	}

	if len(urls) == 0 {
		msg := "No CSS files were found.\n"
		PrintVerbose(msg, Yellow, 1)

		return repResult
	}
	msg := fmt.Sprintf("Testing the following CSS files for poisoning\n%s\n", urls)
	PrintVerbose(msg, NoColor, 1)

	threads := Config.Threads
	if Config.Website.Cache.CBisHTTPMethod {
		threads = 1 // No multithreading if HTTP Method is used... Otherwise there will be a lot of false negatives/positives
		PrintVerbose("Can only scan single threaded because a HTTP Method is used as Cachebuster...\n", Yellow, 1)
	}
	sem := make(chan int, threads)
	var wg sync.WaitGroup
	wg.Add(len(urls))
	var m sync.Mutex

	for _, url := range urls {

		go func(url string) {
			defer wg.Done()
			sem <- 1
			defer func() { <-sem }() // Freigabe der Semaphore, egal was passiert. Dadurch werden Deadlocks verhindert

			//msg := fmt.Sprintf("Testing now %s Header DOS with %s\n", header, value)
			//Print(msg, NoColor)

			urlWithCb, cb := addCachebusterParameter(url, "", Config.Website.Cache.CBName, false)
			var repCheck reportCheck
			repCheck.URL = url
			repCheck.Identifier = "n/a"

			identifier := url
			rp := requestParams{
				identifier: identifier,
				url:        urlWithCb,
				cb:         "cb" + randInt(),
			}
			body, status, repRequest, _, err := firstRequest(rp)
			if err != nil {
				if err.Error() != "stop" {
					m.Lock()
					repResult.HasError = true
					repResult.ErrorMessages = append(repResult.ErrorMessages, err.Error())
					m.Unlock()
				}
				return
			}
			repCheck.Request = repRequest
			if status != 200 {
				return
			}

			if strings.Contains(string(body), cb) {
				msg = fmt.Sprintf("The following CSS file reflects the url with the cb %s\n%s\n", cb, url)
				Print(msg, Cyan)
			}

			body, _, repRequest, _, err = secondRequest(rp)
			if err != nil {
				if err.Error() != "stop" {
					m.Lock()
					repResult.HasError = true
					repResult.ErrorMessages = append(repResult.ErrorMessages, err.Error())
					m.Unlock()
				}
				return
			}
			repCheck.SecondRequest = &repRequest

			if strings.Contains(string(body), cb) {
				PrintNewLine()
				msg = fmt.Sprintf("A CSS file was successfully poisoned! cachebuster %s: %s\nURL: %s\n", Config.Website.Cache.CBName, cb, url)
				Print(msg, Green)
				Reason := "CSS reflects URL"
				msg = fmt.Sprintf("Reason: %s\n", Reason)
				Print(msg, Green)
				repCheck.Reason = Reason

				m.Lock()
				repResult.Vulnerable = true
				repResult.Checks = append(repResult.Checks, repCheck)
				m.Unlock()
			}
		}(url)

	}
	wg.Wait()

	return repResult
}
