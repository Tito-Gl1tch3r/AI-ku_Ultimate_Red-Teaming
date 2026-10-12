package pkg

import (
	"errors"
	"fmt"
	"net/http"
	"slices"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/valyala/fasthttp"
	"github.com/xplorfin/fasthttp2curl"
)

const (
	RESP_SPLIT_HEADER  = "Web_Cache"
	RESP_SPLIT_VALUE   = "Vulnerability_Scanner"
	NO_DUPE_HEADER     = 0
	DUPE_HEADER_BEFORE = 1
	DUPE_HEADER_AFTER  = 2
)

type requestParams struct {
	repResult        *reportResult
	headers          []string
	values           []string
	parameters       []string
	technique        string
	name             string
	identifier       string
	poison           string
	ogParam          string
	url              string
	cb               string
	success          string
	bodyString       string
	prependCB        bool
	forcePost        bool
	duplicateHeaders int
	newCookie        map[string]string
	m                *sync.Mutex
}

func getRespSplit() string {
	return "\\r\\n" + RESP_SPLIT_HEADER + ": " + RESP_SPLIT_VALUE
}

func getHeaderReflections(header http.Header, headersWithPoison []string) []string {
	var parts []string
	for _, name := range headersWithPoison {
		if val, ok := header[name]; ok {
			// strings.Join if a header has multiple values
			parts = append(parts, fmt.Sprintf("%s: %s", name, strings.Join(val, ",")))
		}
	}
	return parts
}

func checkPoisoningIndicators(repResult *reportResult, repCheck reportCheck, success string, body string, poison string, statusCode1 int, statusCode2 int, sameBodyLength bool, header http.Header, recursive bool) []string {
	headersWithPoison := []string{}
	// Response splitting check
	if strings.Contains(repCheck.Identifier, "response splitting") {
		for x := range header {
			if x == RESP_SPLIT_HEADER && header.Get(x) == RESP_SPLIT_VALUE {
				repCheck.Reason = "HTTP Response Splitting"
				break
			}
		}
		if repCheck.Reason == "" {
			return headersWithPoison // no response splitting header found, return empty slice
		}
		// Other checks
	} else {

		if strings.Contains(Config.ReasonTypes, "header") && header != nil && poison != "" && poison != "http" && poison != "https" && poison != "nothttps" && poison != "1" { // dont check for reflection of http/https/nothttps (used by forwarded headers), 1 (used by DOS) or empty poison
			for x := range header {
				if x == RESP_SPLIT_HEADER && header.Get(x) == RESP_SPLIT_VALUE {
					repCheck.Reason = "HTTP Response Splitting"
				}
				if strings.Contains(header.Get(x), poison) {
					headersWithPoison = append(headersWithPoison, x)
				}
			}
		}

		if repCheck.Reason == "" {
			// check for reflection in body
			if strings.Contains(Config.ReasonTypes, "body") && poison != "" && poison != "http" && poison != "https" && poison != "nothttps" && poison != "1" && strings.Contains(body, poison) { // dont check for reflection of http/https/nothttps (used by forwarded headers), 1 (used by DOS) or empty poison
				if len(headersWithPoison) > 0 {
					repCheck.Reason = fmt.Sprintf("Reflection Body and Header: Response Body contained poison value %s %d times and Response Header(s) %s contained poison value %s", poison, strings.Count(body, poison), strings.Join(headersWithPoison, ", "), poison)
				} else {
					repCheck.Reason = fmt.Sprintf("Reflection Body: Response Body contained poison value %s %d times", poison, strings.Count(body, poison))
				}
				repCheck.Reflections = findOccurrencesWithContext(body, poison, 25)
				repCheck.Reflections = append(repCheck.Reflections, getHeaderReflections(header, headersWithPoison)...)
				// check for reflection in headers
			} else if len(headersWithPoison) > 0 {
				repCheck.Reason = fmt.Sprintf("Reflection Header: Response Header(s) %s contained poison value %s", strings.Join(headersWithPoison, ", "), poison)
				repCheck.Reflections = getHeaderReflections(header, headersWithPoison)
				// check for different status code
			} else if strings.Contains(Config.ReasonTypes, "status") && statusCode1 >= 0 && statusCode1 != Config.Website.StatusCode && statusCode1 == statusCode2 {
				// check if status code should be ignored
				for _, status := range Config.IgnoreStatus {
					if statusCode1 == status || Config.Website.StatusCode == status {
						PrintVerbose("Skipped Status Code "+strconv.Itoa(status)+"\n", Cyan, 1) // TODO is it necessary to check if default status code changed?
						return headersWithPoison
					}
				}

				if !recursive {
					var tmpWebsite WebsiteStruct
					var err error

					// try up to 3 times
					count := 3
					for i := range count {
						Print(fmt.Sprintln("Status Code", statusCode1, "differed from the default", Config.Website.StatusCode, ", sending verification request", i+1, "from up to 3"), Yellow)
						tmpWebsite, err = GetWebsite(Config.Website.Url.String(), true, true)
						if err == nil {
							Print(fmt.Sprintln("The verification request returned the Status Code", tmpWebsite.StatusCode), Yellow)
							break
						}
					}
					if err != nil {
						repResult.HasError = true
						msg := fmt.Sprintf("%s: couldn't verify if status code %d is the new default status code, because the verification encountered the following error %d times: %s", repCheck.URL, statusCode1, count, err.Error())
						repResult.ErrorMessages = append(repResult.ErrorMessages, msg)
					} else {
						Config.Website = tmpWebsite
					}
					return checkPoisoningIndicators(repResult, repCheck, success, body, poison, statusCode1, statusCode2, sameBodyLength, header, true)
				} else {
					repCheck.Reason = fmt.Sprintf("Changed Status Code: Status Code %d differed from %d", statusCode1, Config.Website.StatusCode)
				}
				// check for different body length
			} else if strings.Contains(Config.ReasonTypes, "length") && Config.CLDiff != 0 && success != "" && sameBodyLength && len(body) > 0 && compareLengths(len(body), len(Config.Website.Body), Config.CLDiff) {
				if !recursive {
					var tmpWebsite WebsiteStruct
					var err error

					// try up to 3 times
					count := 3
					for range count {
						tmpWebsite, err = GetWebsite(Config.Website.Url.String(), true, true)
						if err == nil {
							break
						}
					}
					if err != nil {
						repResult.HasError = true
						msg := fmt.Sprintf("%s: couldn't verify if body length %d is the new default body length, because the verification request encountered the following error %d times: %s", repCheck.URL, statusCode1, count, err.Error())
						repResult.ErrorMessages = append(repResult.ErrorMessages, msg)
					} else {
						Config.Website = tmpWebsite
					}
					return checkPoisoningIndicators(repResult, repCheck, success, body, poison, statusCode1, statusCode2, sameBodyLength, header, true)
				} else {
					repCheck.Reason = fmt.Sprintf("Changed Content Length: Length %d differed more than %d bytes from normal length %d", len(body), Config.CLDiff, len(Config.Website.Body))
				}
			} else {
				return headersWithPoison
			}
		}
	}

	PrintNewLine()
	Print(success, Green)
	msg := "URL: " + repCheck.URL + "\n"
	Print(msg, Green)
	msg = "Reason: " + repCheck.Reason + "\n"
	Print(msg, Green)
	if len(repCheck.Reflections) > 0 {
		msg = "Reflections: " + strings.Join(repCheck.Reflections, " ... ") + "\n"
		Print(msg, Green)
	}
	msg = "Curl 1st Request: " + repCheck.Request.CurlCommand + "\n"
	Print(msg, Green)
	msg = "Curl 2nd Request: " + repCheck.SecondRequest.CurlCommand + "\n\n"
	Print(msg, Green)
	repResult.Vulnerable = true
	repResult.Checks = append(repResult.Checks, repCheck)
	return headersWithPoison
}

func compareLengths(len1 int, len2 int, limit int) bool {

	var diff int
	if len1 >= len2 {
		diff = len1 - len2
	} else {
		diff = len2 - len1
	}

	return diff > limit
}

/* Check if the second response makes sense or the continuation shall be stopped. Stop if body, status code and headers are equal to the default response */
func stopContinuation(body []byte, statusCode int, headers map[string][]string) bool {
	if string(body) != Config.Website.Body {
		return false
	} else if statusCode != Config.Website.StatusCode {
		return false
	} else if len(headers) != len(Config.Website.Headers) {
		return false
	}
	for k, v := range headers {
		v2 := Config.Website.Headers[k]

		if !slices.Equal(v, v2) {
			return false
		}
	}
	return true
}

func addParameters(urlStr *string, parameters []string) {
	for _, p := range parameters {
		if p == "" {
			continue
		}
		if !strings.Contains(*urlStr, "?") {
			*urlStr += "?"
		} else {
			*urlStr += Config.QuerySeparator
		}
		*urlStr += p
	}
}

func firstRequest(rp requestParams) (body []byte, respStatusCode int, repRequest reportRequest, respHeaders map[string][]string, err error) {
	req := fasthttp.AcquireRequest()
	resp := fasthttp.AcquireResponse()
	defer fasthttp.ReleaseRequest(req)
	defer fasthttp.ReleaseResponse(resp)
	req.Header.DisableNormalizing()

	var msg string

	if rp.headers == nil {
		rp.headers = []string{""}
	}
	if rp.values == nil {
		rp.values = []string{""}
	}
	if rp.parameters == nil {
		rp.parameters = []string{""}
	}

	if rp.values[0] == "2ndrequest" {
		rp.identifier = fmt.Sprintf("2nd request of %s", rp.identifier)
	} else {
		rp.identifier = fmt.Sprintf("1st request of %s", rp.identifier)
	}

	// check if headers and values have the same length
	if len(rp.headers) != len(rp.values) && rp.values[0] != "2ndrequest" {
		msg = fmt.Sprintf("%s: len(header) %s %d != len(value) %s %d\n", rp.identifier, rp.headers, len(rp.headers), rp.values, len(rp.values))
		Print(msg, Red)
		return body, -1, repRequest, nil, errors.New(msg)
	}

	addParameters(&rp.url, rp.parameters)

	if !rp.forcePost && Config.Website.Cache.CBisHTTPMethod && rp.values[0] != "2ndrequest" {
		req.Header.SetMethod(Config.Website.Cache.CBName)
	} else if Config.DoPost || rp.forcePost {
		if rp.bodyString == "" {
			rp.bodyString = Config.Body
		}
		req.Header.SetMethod("POST")
		req.SetBodyString(rp.bodyString)
	} else {
		req.Header.SetMethod("GET")
		if rp.bodyString != "" {
			req.SetBodyString(rp.bodyString)
		}
	}
	req.SetRequestURI(rp.url)

	setRequest(req, Config.DoPost, rp.cb, rp.newCookie, rp.prependCB)
	repRequest.Request = req.String()

	for i := range rp.headers {
		if rp.headers[i] == "" {
			continue
		}
		if rp.values[0] == "2ndrequest" {
			msg = rp.identifier + "2nd request doesnt allow headers to be set\n"
			Print(msg, Red)
			break
		}
		if strings.EqualFold(rp.headers[i], "Host") {
			switch rp.duplicateHeaders {
			case NO_DUPE_HEADER:
				msg := fmt.Sprintf("Overwriting Host:%s with Host:%s\n", req.Host(), rp.values[i])
				PrintVerbose(msg, NoColor, 2)
				req.Header.SetHost(rp.values[i])
			case DUPE_HEADER_BEFORE:
				req.Header.SetProtocol("HTTP/1.1\r\n" + rp.headers[i] + ": " + rp.values[i])
			case DUPE_HEADER_AFTER:
				req.Header.SetHost(string(req.Host()) + "\r\n" + rp.headers[i] + ": " + rp.values[i])
			}
		} else if rp.headers[i] != "" {
			if h := req.Header.Peek(rp.headers[i]); h != nil {
				if rp.duplicateHeaders != NO_DUPE_HEADER { // TODO differentiate between before and after
					msg := fmt.Sprintf("Overwriting %s:%s with %s:%s\n", rp.headers[i], h, rp.headers[i], rp.values[i])
					PrintVerbose(msg, NoColor, 2)
					req.Header.Set(rp.headers[i], rp.values[i])
				} else {
					req.Header.Add(rp.headers[i], rp.values[i])
				}
			} else {
				req.Header.Set(rp.headers[i], rp.values[i])
			}
		}
	}
	waitLimiter(rp.identifier)

	// Do request
	err = client.Do(req, resp)
	if err != nil {
		msg = fmt.Sprintf("%s: client.Do: %s\n", rp.identifier, err.Error())
		Print(msg, Red)
		return body, -1, repRequest, nil, errors.New(msg)
	}
	body = resp.Body()
	respHeaders = headerToMultiMap(&resp.Header)

	if resp.StatusCode() != Config.Website.StatusCode {
		msg = fmt.Sprintf("Unexpected Status Code %d for %s\n", resp.StatusCode(), rp.identifier)
		Print(msg, Yellow)
	}

	if stopContinuation(body, resp.StatusCode(), respHeaders) {
		msg := "stop"
		return body, resp.StatusCode(), repRequest, respHeaders, errors.New(msg)
	}

	// Add the request as curl command to the report
	command, err := fasthttp2curl.GetCurlCommandFastHttp(req)
	if err != nil {
		PrintVerbose("Error: fasthttp2curl: "+err.Error()+"\n", Yellow, 1)
	}

	repRequest.CurlCommand = command.String()
	PrintVerbose("Curl command: "+repRequest.CurlCommand+"\n", NoColor, 2)

	// Add response without body to report
	resp.SkipBody = true
	repRequest.Response = string(resp.String())

	return body, resp.StatusCode(), repRequest, respHeaders, nil
}

func secondRequest(rpFirst requestParams) ([]byte, int, reportRequest, map[string][]string, error) {
	var parameter []string
	if !strings.Contains(rpFirst.ogParam, NOOGPARAM) { // Only add original parameter if it existed
		parameter = append(parameter, rpFirst.ogParam)
	}

	rp := requestParams{
		parameters: parameter,
		values:     []string{"2ndrequest"},
		identifier: rpFirst.identifier,
		url:        rpFirst.url,
		cb:         rpFirst.cb,
	}

	body, statusCode, repRequest, header, err := firstRequest(rp)

	return body, statusCode, repRequest, header, err
}

/* return values:first bool is needed for responsesplitting, second bool is only needed for ScanParameters */
func issueRequests(rp requestParams) (respsplit []string, impact bool, unkeyed bool) {
	var repCheck reportCheck
	repCheck.Identifier = rp.identifier
	repCheck.URL = rp.url

	body1, statusCode1, repRequest, header1, err := firstRequest(rp)
	if err != nil {
		if err.Error() != "stop" {
			if rp.m != nil {
				rp.m.Lock()
				defer rp.m.Unlock()
			}
			rp.repResult.HasError = true
			rp.repResult.ErrorMessages = append(rp.repResult.ErrorMessages, err.Error())
		}

		return nil, false, false
	}
	repCheck.Request = repRequest

	impactful := firstRequestPoisoningIndicator(rp.identifier, body1, rp.poison, header1, Config.Website.Cache.CBName == rp.name, rp.cb, statusCode1)

	if Config.Website.Cache.NoCache || Config.Website.Cache.Indicator == "age" {
		time.Sleep(1 * time.Second) // wait a second to ensure that age header is not set to 0
	}

	body2, statusCode2, repRequest, respHeader, err := secondRequest(rp)
	if err != nil {
		if err.Error() != "stop" {
			if rp.m != nil {
				rp.m.Lock()
				defer rp.m.Unlock()
			}
			rp.repResult.HasError = true
			rp.repResult.ErrorMessages = append(rp.repResult.ErrorMessages, err.Error())
		}
		return nil, impactful, false
	}
	repCheck.SecondRequest = &repRequest
	sameBodyLength := len(body1) == len(body2)

	// Check for cache hit
	hit := false
	for _, v := range respHeader[Config.Website.Cache.Indicator] {
		indicValue := strings.TrimSpace(strings.ToLower(v))
		hit = hit || checkCacheHit(indicValue, Config.Website.Cache.Indicator)
	}

	// Lock here, to prevent false positives and too many GetWebsite requests
	if rp.m != nil {
		rp.m.Lock()
		defer rp.m.Unlock()
	}
	responseSplittingHeaders := checkPoisoningIndicators(rp.repResult, repCheck, rp.success, string(body2), rp.poison, statusCode1, statusCode2, sameBodyLength, respHeader, false)

	return responseSplittingHeaders, impactful, hit
}

func firstRequestPoisoningIndicator(identifier string, body []byte, poison string, header map[string][]string, identifierIsCB bool, cb string, statusCode int) bool {
	var reason string
	if poison != "" && poison != "http" && poison != "https" && poison != "nothttps" && poison != "1" { // dont check for reflection of http/https/nothttps (used by forwarded headers), 1 (used by DOS) or empty poison
		if strings.Contains(string(body), poison) || (identifierIsCB && strings.Contains(string(body), cb)) { //
			reason = "Response Body contained " + poison
		}
		var reflections []string
		for x := range header {
			for _, v := range header[x] {
				if strings.Contains(v, poison) || (identifierIsCB && strings.Contains(v, cb)) {
					reflections = append(reflections, x)
				}
			}
		}
		if len(reflections) > 0 {
			reason = "Response Header(s) " + strings.Join(reflections, ", ") + " contained " + poison
		}
	}
	if Config.Website.StatusCode != statusCode && reason == "" {
		reason = fmt.Sprintf("Status Code %d differed from %d", statusCode, Config.Website.StatusCode)
	}
	if Config.CLDiff != 0 && reason == "" && len(body) > 0 && compareLengths(len(body), len(Config.Website.Body), Config.CLDiff) {
		reason = fmt.Sprintf("Length %d differed more than %d bytes from normal length %d", len(body), Config.CLDiff, len(Config.Website.Body))
	}

	if reason != "" {
		msg := identifier + ": " + reason + "\n"
		Print(msg, Cyan)
		return true
	} else {
		return false
	}

}
