package pkg

import (
	"errors"
	"fmt"
	"io"
	"net/url"
	"path"
	"strings"
	"time"

	"github.com/valyala/fasthttp"
	"golang.org/x/net/html"
)

func cbFoundDifference(times []int64, identifier string) { // TODO: Remove this function as it is only used for statistics
	if len(times)%2 == 0 {
		for i := 0; i < len(times); i += 2 {
			dif := times[i] - times[i+1]
			if dif < int64(Config.HMDiff) {
				msg := fmt.Sprintf("The time difference (%d) was smaller than the threshold (%d)\n", dif, Config.HMDiff)
				PrintVerbose(msg, NoColor, 2)
				return
			}
		}
	} else {
		msg := fmt.Sprintf("%s: len(times) mod 2 != 0\n", identifier)
		Print(msg, Yellow)
	}
}

func cbNotFoundDifference(times []int64, identifier string) {
	if len(times)%2 == 0 {
		for i := 0; i < len(times); i += 2 {
			dif := times[i] - times[i+1]
			if dif >= int64(Config.HMDiff) {
				msg := fmt.Sprintf("The time difference (%d) was equal or higher than the threshold (%d)", dif, Config.HMDiff)
				Print(msg, Yellow)
				return
			}
		}
	} else {
		msg := fmt.Sprintf("%s: len(times) mod 2 != 0", identifier)
		Print(msg, Yellow)
	}
}

/* Check if the parameter "cb" (or any other defined by flag -cb), the headers "accept-encoding, accept, cookie, origin" or any cookie can be used as cachebuster */
func CheckCache(parameterList []string, headerList []string) (CacheStruct, bool, []error) {
	var cache CacheStruct
	var errSlice []error

	// analyze the website headers for cache indicators
	cacheIndicators := analyzeCacheIndicator(Config.Website.Headers)

	alwaysMiss := true
	if len(cacheIndicators) == 0 {
		msg := "No x-cache (or other cache hit/miss header) header was found\nThe time will be measured as cache hit/miss indicator\n"
		Print(msg, Yellow)
	} else {
		for _, cacheIndicator := range cacheIndicators {
			miss, err := checkIfAlwaysMiss(cacheIndicator)
			if err != nil {
				errSlice = append(errSlice, err)
			}
			if !miss {
				alwaysMiss = false
				msg := fmt.Sprintf("The following cache indicator indicated a hit: %s\n", cacheIndicator)
				PrintVerbose(msg, Cyan, 1)
				cache.Indicator = cacheIndicator
			}
		}

		if cache.Indicator == "" && !cache.TimeIndicator {
			msg := "Time measurement as indicator is deactivated, skipping cachebuster tests\n"
			Print(msg, Yellow)
		} else {
			// test for cachebuster, if the cache doesnt always return a miss
			if !alwaysMiss {
				// Check first if a parameter can be used as cachebuster
				if !cache.CBwasFound {
					errs := cachebusterParameter(&cache, nil)
					if len(errs) > 0 {
						errSlice = append(errSlice, errs...)
					}
				}

				// Check second if a header can be used as cachebuster
				if !cache.CBwasFound {
					errs := cachebusterHeader(&cache, nil)
					if len(errs) > 0 {
						errSlice = append(errSlice, errs...)
					}
				}

				// Check third if a cookie can be used as cachebuster
				if !cache.CBwasFound {
					errs := cachebusterCookie(&cache)
					if len(errs) > 0 {
						errSlice = append(errSlice, errs...)
					}
				}

				if Config.SkipWordlistCachebuster {
					msg := "Skipping wordlist cachebuster tests\n"
					PrintVerbose(msg, Yellow, 1)
				} else {
					// Check fourth if a parameter from the wordlist can be used as cachebuster
					if !cache.CBwasFound {
						errs := cachebusterParameter(&cache, parameterList)
						if len(errs) > 0 {
							errSlice = append(errSlice, errs...)
						}
					}

					// Check fivth if a header can be used as cachebuster
					if !cache.CBwasFound {
						errs := cachebusterHeader(&cache, headerList)
						if len(errs) > 0 {
							errSlice = append(errSlice, errs...)
						}
					}
				}

				// Check last if a HTTP Method can be used as cachebuster. Can't do multithreading if HTTP Method is used
				if !cache.CBwasFound {
					errs := cachebusterHTTPMethod(&cache)
					if len(errs) > 0 {
						errSlice = append(errSlice, errs...)
					}
				}
			}
		}

		if cache.Indicator == "" && !cache.TimeIndicator {
			msg := "No cache indicator could be found"
			Print(msg+"\n", Yellow)
			errSlice = append(errSlice, errors.New(strings.ToLower(msg)))
		} else {
			if !cache.CBwasFound {
				msg := "No cachebuster could be found"
				Print(msg+"\n", Yellow)
				errSlice = append(errSlice, errors.New(strings.ToLower(msg)))
			}
		}

		if (!cache.CBwasFound || (cache.Indicator == "" && !cache.TimeIndicator)) && !Config.Force {
			msg := "Use -f/-force to force the test\n"
			Print(msg, Yellow)
		}

	}
	return cache, alwaysMiss, errSlice
}

func checkIfAlwaysMiss(cacheIndicator string) (bool, error) {
	errorString := "checkIfAlwaysMiss"

	req := fasthttp.AcquireRequest()
	resp := fasthttp.AcquireResponse()
	defer fasthttp.ReleaseRequest(req)
	defer fasthttp.ReleaseResponse(resp)
	var err error

	weburl := Config.Website.Url.String()
	if Config.DoPost {
		req.Header.SetMethod("POST")
		req.SetBodyString(Config.Body)
	} else {
		req.Header.SetMethod("GET")
		if Config.Body != "" {
			req.SetBodyString(Config.Body)

		}
	}
	req.SetRequestURI(weburl)

	setRequest(req, Config.DoPost, "", nil, false)

	waitLimiter(errorString)
	err = client.Do(req, resp)
	if err != nil {
		msg := fmt.Sprintf("%s: client.Do: %s", errorString, err.Error())
		Print(msg+"\n", Red)
		return false, errors.New(msg)
	}

	firstUnix := time.Now().Unix()

	if resp.StatusCode() != Config.Website.StatusCode {
		msg := fmt.Sprintf("%s: Unexpected Status Code: %d\n", errorString, resp.StatusCode())
		Print(msg, Yellow)
	}

	setRequest(req, Config.DoPost, "", nil, false)

	waitLimiter(errorString)

	secondUnix := time.Now().Unix()
	timeDiff := secondUnix - firstUnix
	// make sure that there is at least 2 sec difference.
	// So that first req has Age=0 and second req has Age>=2
	if timeDiff <= 1 && strings.EqualFold("age", cacheIndicator) {
		time.Sleep(2 * time.Second)
	}

	err = client.Do(req, resp)
	if err != nil {
		msg := fmt.Sprintf("%s: client.Do: %s", errorString, err.Error())
		Print(msg+"\n", Red)
		return false, errors.New(msg)
	}

	if resp.StatusCode() != Config.Website.StatusCode {
		msg := fmt.Sprintf("%s: Unexpected Status Code: %d\n", errorString, resp.StatusCode())
		Print(msg, Yellow)
	}

	respHeader := headerToMultiMap(&resp.Header)
	hit := false
	for _, v := range respHeader[cacheIndicator] {
		indicValue := strings.TrimSpace(strings.ToLower(v))
		hit = hit || checkCacheHit(indicValue, cacheIndicator)
	}

	if !hit {
		msg := "cache returns always miss"
		Print(msg+"\n", Yellow)
		return true, errors.New(msg)
	}

	return false, nil
}

func cachebusterCookie(cache *CacheStruct) []error {
	var errSlice []error
	for k, _ := range Config.Website.Cookies {
		errorString := "cachebusterCookie " + k
		identifier := "Cookie " + k + " as Cachebuster"

		req := fasthttp.AcquireRequest()
		resp := fasthttp.AcquireResponse()
		defer fasthttp.ReleaseRequest(req)
		defer fasthttp.ReleaseResponse(resp)
		var err error
		var times []int64
		newCookie := map[string]string{}

		if cache.Indicator == "" {
			// No Cache Indicator was found. So time will be used as Indicator

			var cb string
			for ii := range 5 * 2 {
				weburl := Config.Website.Url.String()

				if Config.DoPost {
					req.Header.SetMethod("POST")
					req.SetBodyString(Config.Body)
				} else {
					req.Header.SetMethod("GET")
					if Config.Body != "" {
						req.SetBodyString(Config.Body)

					}
				}
				req.SetRequestURI(weburl)

				if ii%2 == 0 {
					cb = "cb" + randInt()
					newCookie["key"] = k
					newCookie["value"] = cb
				}
				setRequest(req, Config.DoPost, "", newCookie, false)

				waitLimiter(errorString)
				start := time.Now()

				err = client.Do(req, resp)
				if err != nil {
					msg := fmt.Sprintf("%s: client.Do: %s", errorString, err.Error())
					Print(msg+"\n", Red)
					errSlice = append(errSlice, errors.New(msg))
					continue
				}
				elapsed := time.Since(start).Milliseconds()
				times = append(times, elapsed)

				if resp.StatusCode() != Config.Website.StatusCode {
					msg := fmt.Sprintf("%s: Unexpected Status Code: %d\n", errorString, resp.StatusCode())
					Print(msg, Yellow)
				}
			}
			msg := fmt.Sprintf("measured times: %d\n", times)
			PrintVerbose(msg, NoColor, 2)

			skip := false
			for ii := range times {
				// Cache miss has to take 30ms (misshitdif) longer than cache hit
				if ii%2 == 1 && times[ii-1]-times[ii] < int64(Config.HMDiff) {
					msg := fmt.Sprintf("%s was not successful (Cookie)\n", identifier)
					PrintVerbose(msg, NoColor, 2)
					skip = true
					break
				}
			}
			if skip {
				continue
			}
			cache.TimeIndicator = true
			cache.CBwasFound = true
			cache.CBisCookie = true
			cache.CBisHTTPMethod = false
			cache.CBisHeader = false
			cache.CBisParameter = false
			cache.CBName = k

			msg = fmt.Sprintf("%s was successful (Cookie, time was used as indicator)\n", identifier)
			Print(msg, Cyan)

			return errSlice
		} else {
			// A hit miss Indicator was found. Sending 2 requests, each with a new cachebuster, expecting 2 misses
			weburl := Config.Website.Url.String()
			if Config.DoPost {
				req.Header.SetMethod("POST")
				req.SetBodyString(Config.Body)
			} else {
				req.Header.SetMethod("GET")
				if Config.Body != "" {
					req.SetBodyString(Config.Body)

				}
			}
			req.SetRequestURI(weburl)

			cb := "cb" + randInt()
			newCookie["value"] = cb
			setRequest(req, Config.DoPost, "", newCookie, false)

			waitLimiter(errorString)

			start := time.Now()

			err = client.Do(req, resp)
			if err != nil {
				msg := fmt.Sprintf("%s: client.Do: %s", errorString, err.Error())
				Print(msg+"\n", Red)
				errSlice = append(errSlice, errors.New(msg))
				continue
			}

			elapsed := time.Since(start).Milliseconds()
			times = append(times, elapsed)

			firstUnix := time.Now().Unix()

			if resp.StatusCode() != Config.Website.StatusCode {
				msg := fmt.Sprintf("%s: Unexpected Status Code: %d\n", errorString, resp.StatusCode())
				Print(msg, Yellow)
			}

			respHeader := headerToMultiMap(&resp.Header)
			hit := false
			for _, v := range respHeader[cache.Indicator] {
				indicValue := strings.TrimSpace(strings.ToLower(v))
				hit = hit || checkCacheHit(indicValue, cache.Indicator)
			}

			if hit {
				// If there is a hit, the cachebuster didn't work
				msg := fmt.Sprintf("%s was not successful (Cookie)\n", identifier)
				PrintVerbose(msg, NoColor, 2)
				continue
			} else {
				if Config.DoPost {
					req.Header.SetMethod("POST")
					req.SetBodyString(Config.Body)
				} else {
					req.Header.SetMethod("GET")
					if Config.Body != "" {
						req.SetBodyString(Config.Body)

					}
				}
				req.SetRequestURI(weburl)

				cb := "cb" + randInt()
				newCookie["value"] = cb

				setRequest(req, Config.DoPost, "", newCookie, false)

				waitLimiter(errorString)

				secondUnix := time.Now().Unix()
				timeDiff := secondUnix - firstUnix
				// make sure that there is at least 2 sec difference.
				// So that first req has Age=0 and second req has Age>=2
				if timeDiff <= 1 && strings.EqualFold("age", cache.Indicator) {
					time.Sleep(2 * time.Second)
				}

				start := time.Now()
				err = client.Do(req, resp)
				elapsed := time.Since(start).Milliseconds()
				times = append(times, elapsed)
				if err != nil {
					msg := fmt.Sprintf("%s: client.Do: %s", errorString, err.Error())
					Print(msg+"\n", Red)
					errSlice = append(errSlice, errors.New(msg))
					continue
				}

				if resp.StatusCode() != Config.Website.StatusCode {
					msg := fmt.Sprintf("%s: Unexpected Status Code: %d\n", errorString, resp.StatusCode())
					Print(msg, Yellow)
				}

				respHeader := headerToMultiMap(&resp.Header)
				hit := false
				for _, v := range respHeader[cache.Indicator] {
					indicValue := strings.TrimSpace(strings.ToLower(v))
					hit = hit || checkCacheHit(indicValue, cache.Indicator)
				}
				if hit {
					// If there is a hit, the cachebuster didn't work
					msg := fmt.Sprintf("%s was not successful (Cookie)\n", identifier)
					PrintVerbose(msg, NoColor, 2)
					cbNotFoundDifference(times, identifier)
				} else {
					cache.CBwasFound = true
					cache.CBisCookie = true
					cache.CBisHTTPMethod = false
					cache.CBisHeader = false
					cache.CBisParameter = false
					cache.CBName = k

					msg := fmt.Sprintf("%s was successful (Cookie)\n", identifier)
					Print(msg, Cyan)

					cbFoundDifference(times, identifier)

					return errSlice
				}
			}
		}
	}

	return errSlice
}

func cachebusterHeader(cache *CacheStruct, headerList []string) []error {
	headers := []string{}
	values := []string{}
	if len(headerList) > 0 {
		headers = append(headers, headerList...)
	} else {
		headers = append(headers, "Accept-Encoding", "Accept", "Cookie", "Origin")
		values = append(values, "gzip, deflate, ", "*/*, text/", "wcvs_cookie=")
		for _, header := range Config.Headers {
			headers = append(headers, strings.TrimSpace(strings.Split(header, ":")[0])) // Only add headername
		}
	}

	var errSlice []error

	for i, header := range headers {
		errorString := "cachebusterHeader " + header
		identifier := "Header " + header + " as Cachebuster"

		if len(values) < i+1 { // prevent index out of range
			values = append(values, "")
		}

		if header == "" { // skip empty headers
			continue
		}

		req := fasthttp.AcquireRequest()
		resp := fasthttp.AcquireResponse()
		defer fasthttp.ReleaseRequest(req)
		defer fasthttp.ReleaseResponse(resp)
		var err error
		var times []int64

		if cache.Indicator == "" {
			// No Cache Indicator was found. So time will be used as Indicator

			for ii := range 5 * 2 {
				weburl := Config.Website.Url.String()

				if Config.DoPost {
					req.Header.SetMethod("POST")
					req.SetBodyString(Config.Body)
				} else {
					req.Header.SetMethod("GET")
					if Config.Body != "" {
						req.SetBodyString(Config.Body)

					}
				}
				req.SetRequestURI(weburl)

				setRequest(req, Config.DoPost, "", nil, false)
				if ii%2 == 0 {
					cbvalue := values[i] + "cb" + randInt()
					if h := req.Header.Peek(header); h != nil {
						msg := fmt.Sprintf("Overwriting %s:%s with %s:%s\n", header, h, header, cbvalue)
						Print(msg, NoColor)
					}
					req.Header.Set(header, cbvalue)
				}

				waitLimiter(errorString)
				start := time.Now()
				err = client.Do(req, resp)
				elapsed := time.Since(start).Milliseconds()
				times = append(times, elapsed)
				if err != nil {
					msg := fmt.Sprintf("%s: http.DefaultClient.Do: %s", errorString, err.Error())
					Print(msg+"\n", Red)
					errSlice = append(errSlice, errors.New(msg))
					continue
				}

				if resp.StatusCode() != Config.Website.StatusCode {
					msg := fmt.Sprintf("%s: Unexpected Status Code: %d\n", errorString, resp.StatusCode())
					Print(msg, Yellow)
				}
			}
			msg := fmt.Sprintf("measured times: %d\n", times)
			PrintVerbose(msg, NoColor, 2)

			skip := false
			for ii := range times {
				// Cache miss has to take 30ms (misshitdif) longer than cache hit
				if ii%2 == 1 && times[ii-1]-times[ii] < int64(Config.HMDiff) {
					msg := fmt.Sprintf("%s was not successful (Header)\n", identifier)
					PrintVerbose(msg, NoColor, 2)
					skip = true
					break
				}
			}
			if skip {
				continue
			}

			cache.TimeIndicator = true
			cache.CBwasFound = true
			cache.CBisHeader = true
			cache.CBisCookie = false
			cache.CBisHTTPMethod = false
			cache.CBisParameter = false
			cache.CBName = header

			msg = fmt.Sprintf("%s was successful (Header, time was used as indicator)\n", identifier)
			Print(msg, Cyan)

			return errSlice
		} else {
			// A hit miss Indicator was found. Sending 2 requests, each with a new cachebuster, expecting 2 misses
			weburl := Config.Website.Url.String()

			if Config.DoPost {
				req.Header.SetMethod("POST")
				req.SetBodyString(Config.Body)
			} else {
				req.Header.SetMethod("GET")
				if Config.Body != "" {
					req.SetBodyString(Config.Body)

				}
			}
			req.SetRequestURI(weburl)

			setRequest(req, Config.DoPost, "", nil, false)
			cbvalue := values[i] + "cb" + randInt()
			if h := req.Header.Peek(header); h != nil {
				msg := fmt.Sprintf("Overwriting %s:%s with %s:%s\n", header, h, header, cbvalue)
				Print(msg, NoColor)
			}
			req.Header.Set(header, cbvalue)

			waitLimiter(errorString)
			start := time.Now()
			err = client.Do(req, resp)
			elapsed := time.Since(start).Milliseconds()
			times = append(times, elapsed)
			if err != nil {
				msg := fmt.Sprintf("%s: http.DefaultClient.Do: %s", errorString, err.Error())
				Print(msg+"\n", Red)
				errSlice = append(errSlice, errors.New(msg))
				continue
			}

			firstUnix := time.Now().Unix()

			if resp.StatusCode() != Config.Website.StatusCode {
				msg := fmt.Sprintf("%s: Unexpected Status Code: %d\n", errorString, resp.StatusCode())
				Print(msg, Yellow)
			}

			respHeader := headerToMultiMap(&resp.Header)
			hit := false
			for _, v := range respHeader[cache.Indicator] {
				indicValue := strings.TrimSpace(strings.ToLower(v))
				hit = hit || checkCacheHit(indicValue, cache.Indicator)
			}
			if hit {
				// If there is a hit, the cachebuster didn't work
				msg := fmt.Sprintf("%s was not successful (Header)\n", identifier)
				PrintVerbose(msg, NoColor, 2)
				continue
			} else {

				if Config.DoPost {
					req.Header.SetMethod("POST")
					req.SetBodyString(Config.Body)
				} else {
					req.Header.SetMethod("GET")
					if Config.Body != "" {
						req.SetBodyString(Config.Body)

					}
				}
				req.SetRequestURI(weburl)

				setRequest(req, Config.DoPost, "", nil, false)
				cbvalue := values[i] + "cb" + randInt()
				if h := req.Header.Peek(header); h != nil {
					msg := fmt.Sprintf("Overwriting %s:%s with %s:%s\n", header, h, header, cbvalue)
					Print(msg, NoColor)
				}
				req.Header.Set(header, cbvalue)

				waitLimiter(errorString)

				secondUnix := time.Now().Unix()
				timeDiff := secondUnix - firstUnix
				// make sure that there is at least 2 sec difference.
				// So that first req has Age=0 and second req has Age>=2
				if timeDiff <= 1 && strings.EqualFold("age", cache.Indicator) {
					time.Sleep(2 * time.Second)
				}

				start := time.Now()
				err = client.Do(req, resp)
				elapsed := time.Since(start).Milliseconds()
				times = append(times, elapsed)
				if err != nil {
					msg := fmt.Sprintf("%s: http.DefaultClient.Do: %s", errorString, err.Error())
					Print(msg+"\n", Red)
					errSlice = append(errSlice, errors.New(msg))
					continue
				}

				if resp.StatusCode() != Config.Website.StatusCode {
					msg := fmt.Sprintf("%s: Unexpected Status Code: %d\n", errorString, resp.StatusCode())
					Print(msg, Yellow)
				}

				respHeader := headerToMultiMap(&resp.Header)
				hit := false
				for _, v := range respHeader[cache.Indicator] {
					indicValue := strings.TrimSpace(strings.ToLower(v))
					hit = hit || checkCacheHit(indicValue, cache.Indicator)
				}
				if hit {
					// If there is a hit, the cachebuster didn't work
					msg := fmt.Sprintf("%s was not successful (Header)\n", identifier)
					PrintVerbose(msg, NoColor, 2)

					cbNotFoundDifference(times, identifier)
				} else {
					cache.CBwasFound = true
					cache.CBisHeader = true
					cache.CBisCookie = false
					cache.CBisHTTPMethod = false
					cache.CBisParameter = false
					cache.CBName = header

					msg := fmt.Sprintf("%s was successful (Header)\n", identifier)
					Print(msg, Cyan)

					cbFoundDifference(times, identifier)
					return errSlice
				}
			}
		}
	}
	return errSlice
}

func cachebusterParameter(cache *CacheStruct, parameterList []string) []error {
	parameters := []string{}
	values := []string{}

	if len(parameterList) > 0 {
		parameters = parameterList
	} else {
		parameters = append(parameters, Config.CacheBuster)
		values = append(values, "")
		for k, v := range Config.Website.Queries {
			parameters = append(parameters, k)
			values = append(values, v)
		}
	}

	var errSlice []error

	for i, parameter := range parameters {
		errorString := "cachebusterParameter"
		identifier := "Parameter " + parameter + " as Cachebuster"

		if len(values) < i+1 { // prevent index out of range
			values = append(values, "")
		}

		if parameter == "" { // skip empty parameter
			continue
		}

		req := fasthttp.AcquireRequest()
		resp := fasthttp.AcquireResponse()
		defer fasthttp.ReleaseRequest(req)
		defer fasthttp.ReleaseResponse(resp)
		var err error
		var times []int64

		if cache.Indicator == "" {
			// No Cache Indicator was found. So time will be used as Indicator

			var urlCb string
			for ii := range 5 * 2 {
				if ii%2 == 0 {
					urlCb, _ = addCachebusterParameter(Config.Website.Url.String(), values[i], parameter, false)
				}
				if Config.DoPost {
					req.Header.SetMethod("POST")
					req.SetBodyString(Config.Body)
				} else {
					req.Header.SetMethod("GET")
					if Config.Body != "" {
						req.SetBodyString(Config.Body)

					}
				}
				req.SetRequestURI(urlCb)

				setRequest(req, Config.DoPost, "", nil, false)

				waitLimiter(errorString)
				start := time.Now()
				err = client.Do(req, resp)
				elapsed := time.Since(start).Milliseconds()
				times = append(times, elapsed)
				if err != nil {
					msg := fmt.Sprintf("%s: http.DefaultClient.Do: %s", errorString, err.Error())
					Print(msg+"\n", Red)
					errSlice = append(errSlice, errors.New(msg))
					continue
				}

				if resp.StatusCode() != Config.Website.StatusCode {
					msg := fmt.Sprintf("%s: Unexpected Status Code: %d\n", errorString, resp.StatusCode())
					Print(msg, Yellow)
				}
			}
			msg := fmt.Sprintf("measured times: %d\n", times)
			PrintVerbose(msg, NoColor, 2)

			skip := false
			for ii := range times {
				// Cache miss has to take 30ms (misshitdif) longer than cache hit
				if ii%2 == 1 && times[ii-1]-times[ii] < int64(Config.HMDiff) {
					msg := fmt.Sprintf("%s was not successful (Parameter)\n", identifier)
					PrintVerbose(msg, NoColor, 2)
					skip = true
					break
				}
			}
			if skip {
				continue
			}

			cache.TimeIndicator = true
			cache.CBwasFound = true
			cache.CBisParameter = true
			cache.CBisHeader = false
			cache.CBisCookie = false
			cache.CBisHTTPMethod = false
			cache.CBName = parameter

			msg = fmt.Sprintf("%s was successful (Parameter, time was used as indicator)\n", identifier)
			Print(msg, Cyan)
			return errSlice
		} else {
			// A hit miss Indicator was found. Sending 2 requests, each with a new cachebuster, expecting 2 misses
			urlCb, _ := addCachebusterParameter(Config.Website.Url.String(), values[i], parameter, false)

			if Config.DoPost {
				req.Header.SetMethod("POST")
				req.SetBodyString(Config.Body)
			} else {
				req.Header.SetMethod("GET")
				if Config.Body != "" {
					req.SetBodyString(Config.Body)

				}
			}
			req.SetRequestURI(urlCb)

			setRequest(req, Config.DoPost, "", nil, false)
			waitLimiter(errorString)
			start := time.Now()
			err = client.Do(req, resp)
			elapsed := time.Since(start).Milliseconds()
			times = append(times, elapsed)
			if err != nil {
				msg := fmt.Sprintf("%s: http.DefaultClient.Do: %s", errorString, err.Error())
				Print(msg+"\n", Red)
				errSlice = append(errSlice, errors.New(msg))
				continue
			}

			firstUnix := time.Now().Unix()

			if resp.StatusCode() != Config.Website.StatusCode {
				msg := fmt.Sprintf("%s: Unexpected Status Code: %d\n", errorString, resp.StatusCode())
				Print(msg, Yellow)
			}

			respHeader := headerToMultiMap(&resp.Header)
			hit := false
			for _, v := range respHeader[cache.Indicator] {
				indicValue := strings.TrimSpace(strings.ToLower(v))
				hit = hit || checkCacheHit(indicValue, cache.Indicator)
			}
			if hit {
				// If there is a hit, the cachebuster didn't work
				msg := fmt.Sprintf("%s was not successful (Parameter)\n", identifier)
				PrintVerbose(msg, NoColor, 2)
			} else {
				urlCb, _ := addCachebusterParameter(Config.Website.Url.String(), values[i], parameter, false)

				if Config.DoPost {
					req.Header.SetMethod("POST")
					req.SetBodyString(Config.Body)
				} else {
					req.Header.SetMethod("GET")
					if Config.Body != "" {
						req.SetBodyString(Config.Body)

					}
				}
				req.SetRequestURI(urlCb)

				setRequest(req, Config.DoPost, "", nil, false)
				waitLimiter(errorString)

				secondUnix := time.Now().Unix()
				timeDiff := secondUnix - firstUnix
				// make sure that there is at least 2 sec difference.
				// So that first req has Age=0 and second req has Age>=2
				if timeDiff <= 1 && strings.EqualFold("age", cache.Indicator) {
					time.Sleep(2 * time.Second)
				}

				start := time.Now()
				err = client.Do(req, resp)
				elapsed := time.Since(start).Milliseconds()
				times = append(times, elapsed)
				if err != nil {
					msg := fmt.Sprintf("%s: http.DefaultClient.Do: %s", errorString, err.Error())
					Print(msg+"\n", Red)
					errSlice = append(errSlice, errors.New(msg))
					continue
				}

				if resp.StatusCode() != Config.Website.StatusCode {
					msg := fmt.Sprintf("%s: Unexpected Status Code: %d\n", errorString, resp.StatusCode())
					Print(msg, Yellow)
				}

				respHeader := headerToMultiMap(&resp.Header)
				hit := false
				for _, v := range respHeader[cache.Indicator] {
					indicValue := strings.TrimSpace(strings.ToLower(v))
					hit = hit || checkCacheHit(indicValue, cache.Indicator)
				}
				if hit {
					// If there is a hit, the cachebuster didn't work
					msg := fmt.Sprintf("%s was not successful (Parameter)\n", identifier)
					PrintVerbose(msg, NoColor, 2)

					cbNotFoundDifference(times, identifier)
				} else {
					cache.CBwasFound = true
					cache.CBisParameter = true
					cache.CBisHeader = false
					cache.CBisCookie = false
					cache.CBisHTTPMethod = false
					cache.CBName = parameter

					msg := fmt.Sprintf("%s was successful (Parameter)\n", identifier)
					Print(msg, Cyan)

					cbFoundDifference(times, identifier)

					return errSlice
				}
			}
		}
	}

	return errSlice
}

func cachebusterHTTPMethod(cache *CacheStruct) []error {
	http_methods := []string{"PURGE", "FASTLYPURGE"}

	var errSlice []error

	for _, method := range http_methods {
		errorString := "cachebusterHTTPMethod " + method
		identifier := "HTTP Method " + method + " as Cachebuster"

		req := fasthttp.AcquireRequest()
		resp := fasthttp.AcquireResponse()
		defer fasthttp.ReleaseRequest(req)
		defer fasthttp.ReleaseResponse(resp)
		var err error
		var times []int64

		if cache.Indicator == "" {
			// No Cache Indicator was found. So time will be used as Indicator

			skip := false
			for ii := range 5 * 2 {
				weburl := Config.Website.Url.String()
				if ii%2 == 0 {
					req.Header.SetMethod(method)
					if Config.Body != "" {
						req.SetBodyString(Config.Body)
					}
				} else {
					if Config.DoPost {
						req.Header.SetMethod("POST")
						req.SetBodyString(Config.Body)
					} else {
						req.Header.SetMethod("GET")
						if Config.Body != "" {
							req.SetBodyString(Config.Body)

						}
					}

				}
				req.SetRequestURI(weburl)

				setRequest(req, Config.DoPost, "", nil, false)

				waitLimiter(errorString)
				start := time.Now()
				err = client.Do(req, resp)
				elapsed := time.Since(start).Milliseconds()
				times = append(times, elapsed)
				if err != nil {
					msg := fmt.Sprintf("%s: http.DefaultClient.Do: %s", errorString, err.Error())
					Print(msg+"\n", Red)
					errSlice = append(errSlice, errors.New(msg))
					continue
				}

				if resp.StatusCode() != Config.Website.StatusCode {
					msg := fmt.Sprintf("%s: Unexpected Status Code: %d\n", errorString, resp.StatusCode())
					Print(msg, Yellow)
				}
				if resp.StatusCode() >= 400 {
					skip = true
					break
				}
			}
			if skip {
				continue
			}
			msg := fmt.Sprintf("measured times: %d\n", times)
			PrintVerbose(msg, NoColor, 2)

			skip = false
			for ii := range times {
				// Cache miss has to take 30ms (misshitdif) longer than cache hit
				if ii%2 == 1 && times[ii-1]-times[ii] < int64(Config.HMDiff) {
					msg := fmt.Sprintf("%s was not successful (HTTP Method)\n", identifier)
					PrintVerbose(msg, NoColor, 2)
					skip = true
					break
				}
			}
			if skip {
				continue
			}

			cache.TimeIndicator = true
			cache.CBwasFound = true
			cache.CBisHTTPMethod = true
			cache.CBisParameter = false
			cache.CBisHeader = false
			cache.CBisCookie = false
			cache.CBName = method

			msg = fmt.Sprintf("%s was successful (HTTP Method, time was used as indicator)\n", identifier)
			Print(msg, Cyan)

			return errSlice
		} else {
			// A hit miss Indicator was found. Sending 2 requests, each with a new cachebuster, expecting 2 misses
			weburl := Config.Website.Url.String()

			req.Header.SetMethod(method)
			if Config.Body != "" {
				req.SetBodyString(Config.Body)

			}

			req.SetRequestURI(weburl)

			setRequest(req, Config.DoPost, "", nil, false)

			waitLimiter(errorString)
			start := time.Now()
			err = client.Do(req, resp)
			elapsed := time.Since(start).Milliseconds()
			times = append(times, elapsed)
			if err != nil {
				msg := fmt.Sprintf("%s: http.DefaultClient.Do: %s", errorString, err.Error())
				Print(msg+"\n", Red)
				errSlice = append(errSlice, errors.New(msg))
				continue
			}

			firstUnix := time.Now().Unix()

			if resp.StatusCode() != Config.Website.StatusCode {
				msg := fmt.Sprintf("%s: Unexpected Status Code: %d\n", errorString, resp.StatusCode())
				Print(msg, Yellow)
			}
			if resp.StatusCode() >= 400 {
				continue
			}

			respHeader := headerToMultiMap(&resp.Header)
			hit := false
			for _, v := range respHeader[cache.Indicator] {
				indicValue := strings.TrimSpace(strings.ToLower(v))
				hit = hit || checkCacheHit(indicValue, cache.Indicator)
			}
			if hit {
				// If there is a hit, the cachebuster didn't work
				msg := fmt.Sprintf("%s was not successful (HTTP Method)\n", identifier)
				PrintVerbose(msg, NoColor, 2)
			} else {
				req.Header.SetMethod(method)
				if Config.Body != "" {
					req.SetBodyString(Config.Body)

				}

				req.SetRequestURI(weburl)

				setRequest(req, Config.DoPost, "", nil, false)
				waitLimiter(errorString)

				secondUnix := time.Now().Unix()
				timeDiff := secondUnix - firstUnix
				// make sure that there is at least 2 sec difference.
				// So that first req has Age=0 and second req has Age>=2
				if timeDiff <= 1 && strings.EqualFold("age", cache.Indicator) {
					time.Sleep(2 * time.Second)
				}

				start := time.Now()
				err = client.Do(req, resp)
				elapsed := time.Since(start).Milliseconds()
				times = append(times, elapsed)
				if err != nil {
					msg := fmt.Sprintf("%s: http.DefaultClient.Do: %s", errorString, err.Error())
					Print(msg+"\n", Red)
					errSlice = append(errSlice, errors.New(msg))
					continue
				}

				if resp.StatusCode() != Config.Website.StatusCode {
					msg := fmt.Sprintf("%s: Unexpected Status Code: %d\n", errorString, resp.StatusCode())
					Print(msg, Yellow)
				}
				if resp.StatusCode() >= 400 {
					continue
				}

				respHeader := headerToMultiMap(&resp.Header)
				hit := false
				for _, v := range respHeader[cache.Indicator] {
					indicValue := strings.TrimSpace(strings.ToLower(v))
					hit = hit || checkCacheHit(indicValue, cache.Indicator)
				}
				if hit {
					// If there is a hit, the cachebuster didn't work
					msg := fmt.Sprintf("%s was not successful (HTTP Method)\n", identifier)
					PrintVerbose(msg, NoColor, 2)

					cbNotFoundDifference(times, identifier)
				} else {
					cache.CBwasFound = true
					cache.CBisHTTPMethod = true
					cache.CBisParameter = false
					cache.CBisHeader = false
					cache.CBisCookie = false
					cache.CBName = method

					msg := fmt.Sprintf("%s was successful (HTTP Method)\n", identifier)
					Print(msg, Cyan)

					cbFoundDifference(times, identifier)

					return errSlice
				}
			}
		}
	}
	return errSlice
}

/* Simple get request to get the body of a normal response and the cookies */
func GetWebsite(requrl string, setStatusCode bool, cacheBuster bool) (WebsiteStruct, error) {
	errorString := "GetWebsite"

	var web WebsiteStruct
	cache := Config.Website.Cache
	queryParameterMap := make(map[string]string)

	// get domain
	domainParts := strings.SplitN(requrl, "/", 4)
	domain := domainParts[0] + "//" + domainParts[2]

	// splitting url like {https://www.m10x.de/}?{name=max&role=admin}
	urlSlice := strings.SplitN(requrl, "?", 2)

	// splitting queries like {name=max}&{role=admin}
	var parameterSlice []string
	if strings.Contains(requrl, "?") {
		parameterSlice = strings.Split(urlSlice[1], Config.QuerySeparator)
	}

	if len(parameterSlice) > 0 {
		queryParameterMap = setQueryParameterMap(queryParameterMap, parameterSlice)
	}

	if len(Config.Parameters) > 0 {
		queryParameterMap = setQueryParameterMap(queryParameterMap, Config.Parameters)
	}

	requrl = urlSlice[0]
	urlNoQueries := urlSlice[0]

	// adding query parameter
	for key, val := range queryParameterMap {
		if !strings.Contains(requrl, "?") {
			requrl += "?"
		} else {
			requrl += Config.QuerySeparator
		}
		requrl += key + "=" + val
	}

	cb := ""
	if cacheBuster {
		cb = "cb" + randInt()
	}

	req := fasthttp.AcquireRequest()
	resp := fasthttp.AcquireResponse()
	defer fasthttp.ReleaseRequest(req)
	defer fasthttp.ReleaseResponse(resp)
	var err error
	if Config.Website.Cache.CBisHTTPMethod {
		req.Header.SetMethod(Config.Website.Cache.CBName)
	} else if Config.DoPost {
		req.Header.SetMethod("POST")
	} else {
		req.Header.SetMethod("GET")
	}
	if Config.Body != "" {
		req.SetBodyString(Config.Body)
	}
	req.SetRequestURI(requrl)

	setRequest(req, Config.DoPost, cb, nil, false)
	waitLimiter(errorString)

	err = client.Do(req, resp)
	if err != nil {
		msg := fmt.Sprintf("%s: http.DefaultClient.Do: %s", errorString, err.Error()) // Error: context deadline exceeded -> panic; runtime error

		Print(msg+"\n", Red)
		return web, errors.New(msg)
	}

	weburl, err := url.Parse(requrl)
	if err != nil {
		msg := fmt.Sprintf("%s: url.Parse: %s", errorString, err.Error())
		Print(msg+"\n", Red)
		return web, errors.New(msg)
	}

	tempStatusCode := Config.Website.StatusCode
	// Only overwrite statuscode if 1. it wasn't set via flag 2. its the first and only request or the second of two requests
	if setStatusCode && tempStatusCode != resp.StatusCode() {
		tempStatusCode = resp.StatusCode()

		cache = Config.Website.Cache

		msg := fmt.Sprintf("The default status code was set to %d\n", tempStatusCode)
		Print(msg, Cyan)
	}

	// if retrieveCookies is false, only the specified cookies will be used
	// otherwise the by the server given cookies AND the specified cookies will be used
	cookiesWebsite := Config.Website.Cookies
	if !Config.DeclineCookies {
		cookiesWebsite = responseCookiesToMap(resp, cookiesWebsite)
	}

	/*
		weburl.Host:		www.example.com
		weburl.Path:		/
		weburl.Hostname():www.example.com
		weburl.String():	https://www.example.com/?test=12
		domain:			https://www.example.com
		urlNoQueries:		https://www.example.com/
	*/

	web = WebsiteStruct{
		Headers:      headerToMultiMap(&resp.Header),
		Body:         string(resp.Body()),
		Cookies:      cookiesWebsite,
		StatusCode:   tempStatusCode,
		Url:          weburl,
		UrlWOQueries: urlNoQueries,
		Queries:      queryParameterMap,
		Cache:        cache,
		Domain:       domain,
		//make map doesnt work here. is now in main method
		//Added:      make(map[string]bool),
	}

	return web, nil
}

func setQueryParameterMap(queryParameterMap map[string]string, querySlice []string) map[string]string {
	for _, q := range querySlice {
		q = strings.TrimSuffix(q, "\r")
		q = strings.TrimSpace(q)
		if q == "" {
			continue
		} else if !strings.Contains(q, "=") {
			msg := fmt.Sprintf("Specified parameter %s doesn't contain a = and will be skipped\n", q)
			Print(msg, Yellow)
			continue
		} else {
			query := strings.SplitN(q, "=", 2)
			// ok is true, if a query already is set
			val, ok := queryParameterMap[query[0]]
			if ok {
				msg := fmt.Sprintf("Overwriting %s=%s with %s=%s\n", query[0], val, query[0], query[1])
				Print(msg, NoColor)
			}
			queryParameterMap[query[0]] = query[1]
		}
	}

	return queryParameterMap
}

func addDomain(x string, domain string) string {
	if strings.HasPrefix(x, "#") || strings.HasPrefix(x, "mailto:") || strings.HasPrefix(x, "tel:") || strings.HasPrefix(x, "data:") || strings.HasPrefix(x, "javascript:") || (strings.Contains(x, "://") && !strings.HasPrefix(x, "http")) { // we only want http,https,// or relative
		return ""
	}
	x = strings.SplitN(x, "#", 2)[0] // remove everything after # (anchor)
	if strings.HasPrefix(x, "https://"+domain) || strings.HasPrefix(x, "http://"+domain) {
		return x
	} else if strings.HasPrefix(x, "//"+domain) {
		return Config.Website.Url.Scheme + ":" + x // add the scheme to the url
	} else if !strings.HasPrefix(x, "http://") && !strings.HasPrefix(x, "https://") && !strings.HasPrefix(x, "//") {
		if strings.HasPrefix(x, "/") {
			return Config.Website.Domain + x
		} else { // we need to add the basepath to the relative path
			basePath := path.Dir(Config.Website.Url.Path)
			return Config.Website.Domain + strings.TrimSuffix(basePath, "/") + "/" + strings.TrimPrefix(x, "/")
		}
	} else {
		for i, d := range Config.RecDomains {
			if Config.RecDomains[i] == "" {
				continue
			}
			if strings.HasPrefix(x, "https://"+d) || strings.HasPrefix(x, "http://"+d) {
				return x
			}
			if strings.HasPrefix(x, "//"+d) {
				return Config.Website.Url.Scheme + ":" + x // add the scheme to the url
			}
		}

		msg := fmt.Sprintf("%s doesn't have %s as domain\n", x, domain)
		PrintVerbose(msg, NoColor, 2)

		return ""
	}
}

func checkRecInclude(x string, recInclude string) bool {
	for _, inc := range strings.Split(recInclude, " ") {
		// remove spaces and skip if someone used multiple spaces instead of one
		if inc == "" {
			continue
		}
		if strings.Contains(x, inc) {
			return true
		}
	}
	return false
}

func addUrl(urls []string, url string, added map[string]bool, excluded map[string]bool) []string {
	url = addDomain(url, Config.Website.Url.Hostname())

	if url != "" {
		// Check if url isnt added yet and if it satisfies RecInclude (=contains it)
		if excluded[url] {
			msg := fmt.Sprintf("Skipped to add %s to the queue, because it is on the exclude list\n", url)
			PrintVerbose(msg, NoColor, 2)
		} else if added[url] {
			msg := fmt.Sprintf("Skipped to add %s to the queue, because it was already added\n", url)
			PrintVerbose(msg, NoColor, 2)
		} else if Config.RecInclude == "" || checkRecInclude(url, Config.RecInclude) {
			urls = append(urls, url)
			added[url] = true
		} else {
			msg := fmt.Sprintf("Skipped to add %s to the queue, because it doesn't satisfy RecInclude\n", url)
			PrintVerbose(msg, NoColor, 2)
		}
	}

	return urls
}

func CrawlUrls(u string, added map[string]bool, excluded map[string]bool) []string {
	webStruct, err := GetWebsite(u, false, false) // get body without cachebuster. TODO use response w/o cachebuster from recon, so it doesn't have to be fetched again
	if err != nil {
		msg := fmt.Sprintf("Error while crawling %s: %s\n", u, err.Error())
		Print(msg, Red)
		return []string{}
	}
	bodyReader := strings.NewReader(webStruct.Body)
	tokenizer := html.NewTokenizer(bodyReader)

	var urls []string

	eof := false
	for !eof {
		tokentype := tokenizer.Next()

		switch tokentype {
		case html.StartTagToken, html.SelfClosingTagToken:

			token := tokenizer.Token()

			if token.Data == "a" || token.Data == "link" {
				for _, a := range token.Attr {
					if a.Key == "href" {
						//if strings.HasSuffix(a.Val, ".css") && strings.Contains(a.Val, ".css?") { // TODO: Flag to exclude css files from thorough scanning
						//	break
						//}
						urls = addUrl(urls, a.Val, added, excluded)
						break
					}
				}
			} else if token.Data == "script" {
				for _, a := range token.Attr {
					if a.Key == "src" {
						urls = addUrl(urls, a.Val, added, excluded)
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

	// redirect
	if webStruct.Headers["Location"] != nil {
		if h := webStruct.Headers["Location"][0]; h != "" {
			urls = addUrl(urls, h, added, excluded)
		}
	}

	return urls
}
