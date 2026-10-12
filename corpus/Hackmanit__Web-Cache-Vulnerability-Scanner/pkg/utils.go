package pkg

import (
	"context"
	"crypto/rand"
	"crypto/tls"
	"fmt"
	"log"
	"math/big"
	"net/http"
	"net/url"
	"os"
	"strconv"
	"strings"
	"time"

	"github.com/fatih/color"
	"github.com/valyala/fasthttp"
	"github.com/valyala/fasthttp/fasthttpproxy"
)

var (
	NoColor = 0
	Red     = 1
	Yellow  = 2
	Green   = 3
	Cyan    = 4
)

var client *fasthttp.Client

func InitClient() {
	var dialer fasthttp.DialFunc
	if Config.UseProxy {
		dialer = fasthttpproxy.FasthttpHTTPDialer(Config.ProxyURL)
	}

	client = &fasthttp.Client{
		Dial:                          dialer,
		DisablePathNormalizing:        true, // needed for path traversal (cache deception)
		DisableHeaderNamesNormalizing: true, // needed for request smuggling and other techniques using non-normalized headers
		ReadTimeout:                   time.Duration(Config.TimeOut) * time.Second,
		WriteTimeout:                  time.Duration(Config.TimeOut) * time.Second,
		TLSConfig:                     &tls.Config{InsecureSkipVerify: true},
		ReadBufferSize:                8 * 1024}
}

func PrintNewLine() {
	Print("\n", NoColor)
}

func PrintLog(msg string) {
	if Config.GenerateLog && Config.Intitialized {
		log.Print(msg)
	}
}

func PrintVerbose(msg string, c int, threshold int) {
	switch c {
	case Red:
		PrintLog("[ERR] " + msg)
		msg = color.RedString("[ERR] ") + msg
	case Yellow:
		PrintLog("[!] " + msg)
		msg = color.YellowString("[!] ") + msg
	case Green:
		PrintLog("[+] " + msg)
		msg = color.GreenString("[+] ") + msg
	case Cyan:
		PrintLog("[*] " + msg)
		msg = color.CyanString("[*] ") + msg
	default:
		PrintLog(msg)
	}

	if Config.Verbosity >= threshold || !Config.Intitialized {
		fmt.Print(msg)
	}
}

func Print(msg string, c int) {
	PrintVerbose(msg, c, 0)
}

func PrintFatal(msg string) {
	Print(msg, Red)
	os.Exit(1)
}

func ReadLocalFile(path string, name string) []string {
	path = strings.TrimPrefix(path, "file:")

	if strings.HasPrefix(strings.ToLower(path), "file:") {
		PrintFatal("Please make sure that path: is lowercase")
	}

	w, err := os.ReadFile(path)
	if err != nil {
		additional := ""
		if name == "header" {
			additional = "Use the flag \"-hw path/to/wordlist\" to specify the path to a header wordlist\n"
		} else if name == "parameter" {
			additional = "Use the flag \"-pw path/to/wordlist\" to specify the path to a parameter wordlist\n"
		}
		PrintFatal("The specified " + name + " file path " + path + " couldn't be found: " + err.Error() + "\n" + additional)
	}

	return strings.Split(string(w), "\n")
}

func setRequest(req *fasthttp.Request, doPost bool, cb string, cookie map[string]string, prependCB bool) {

	cache := Config.Website.Cache
	if cb != "" && cache.CBisParameter {
		var newUrl string
		newUrl, _ = addCachebusterParameter(req.URI().String(), cb, cache.CBName, prependCB)

		newURL, err := url.Parse(newUrl)
		if err != nil {
			msg := "Converting " + newUrl + " to URL:" + err.Error() + "\n"
			Print(msg, Red)
		}
		req.SetRequestURI(newURL.String())
		req.UseHostHeader = true
	}

	setRequestHeaders(req, cb)
	setRequestCookies(req, cb, cookie)

	// Overwrite the content type if specified
	if doPost {
		if Config.ContentType != "" {
			req.Header.SetContentType(Config.ContentType)
		}
	}
}

func responseCookiesToMap(resp *fasthttp.Response, cookieMap map[string]string) map[string]string {
	resp.Header.VisitAllCookie(func(key, value []byte) {
		c := &fasthttp.Cookie{}
		c.ParseBytes(value)
		if err := c.ParseBytes(value); err == nil {
			cookieMap[string(key)] = string(c.Value())
		} else {
			msg := fmt.Sprintf("Error parsing cookie %s: %s\n", string(value), err.Error())
			Print(msg, Red)
		}
	})

	return cookieMap
}

func urlEncodeAll(input string) string {
	encoded := ""
	for i := 0; i < len(input); i++ {
		encoded += fmt.Sprintf("%%%02X", input[i])
	}
	return encoded
}

/* TODO wie bei requestCookies nur die erste occurrence eines headers aufnehmen */
func setRequestHeaders(req *fasthttp.Request, cb string) {
	cache := Config.Website.Cache

	req.Header.Set("User-Agent", useragent)
	for _, h := range Config.Headers {
		h = strings.TrimSuffix(h, "\r")
		h = strings.TrimSpace(h)
		if h == "" {
			continue
		} else if !strings.Contains(h, ":") {
			msg := "Specified header" + h + "doesn't contain a : and will be skipped"
			Print(msg, Yellow)
			continue
		} else {
			hSplitted := strings.SplitN(h, ":", 2)

			// is this header the cachebuster?
			if cb != "" && cache.CBisHeader && strings.EqualFold(hSplitted[0], cache.CBName) {
				req.Header.Set(cache.CBName, cb)
			}

			req.Header.Set(strings.TrimSpace(hSplitted[0]), strings.TrimSpace(hSplitted[1]))
		}
	}
}

func setRequestCookies(req *fasthttp.Request, cb string, cookie map[string]string) {
	cache := Config.Website.Cache

	for k, v := range Config.Website.Cookies {
		if cb != "" && cache.CBisCookie && k == cache.CBName {
			if k == cookie["key"] {
				msg := "Can't test cookie " + k + " for Web Cache Poisoning, as it is used as Cachebuster\n"
				Print(msg, Yellow)
				continue
			}
			k = cb
		} else if k == cookie["key"] {
			v = cookie["value"]
		}
		req.Header.SetCookie(k, v)
	}
}

func addCachebusterParameter(strUrl string, cbvalue string, cb string, prepend bool) (string, string) {
	if cbvalue == "" {
		cbvalue = "cb" + randInt()
	}
	if cb == "" {
		cb = Config.Website.Cache.CBName
	}
	if !strings.Contains(strUrl, "?") {
		strUrl += "?" + cb + "=" + cbvalue
	} else {
		if prepend {
			parts := strings.SplitN(strUrl, "?", 2)
			strUrl = parts[0] + "?" + cb + "=" + cbvalue + Config.QuerySeparator + parts[1]
		} else {
			strUrl += Config.QuerySeparator + cb + "=" + cbvalue
		}
	}

	return strUrl, cbvalue
}

// RandomString generates a random string of the specified length
func RandomString(length int) string {
	const charset = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
	result := make([]byte, length)
	for i := range result {
		n, err := rand.Int(rand.Reader, big.NewInt(int64(len(charset))))
		if err != nil {
			Print(err.Error(), Red)
			return "99999999"
		}
		result[i] = charset[n.Int64()]
	}
	return string(result)
}

func removeParam(rawURL string, paramToRemove string) (string, string, error) {
	// Parse the URL
	parsedURL, err := url.Parse(rawURL)
	if err != nil {
		return "", "", err
	}

	// Get current query parameters
	query := parsedURL.Query()
	ogValue := query.Get(paramToRemove)

	// Check if the parameter exists and remove it
	if _, exists := query[paramToRemove]; exists {
		query.Del(paramToRemove)
		parsedURL.RawQuery = query.Encode()
	}

	return parsedURL.String(), ogValue, nil
}

/* Create a random long integer */
func randInt() string {
	min := int64(100000000000)
	max := int64(999999999999)
	// Range size
	rangeSize := max - min + 1

	n, err := rand.Int(rand.Reader, big.NewInt(rangeSize))
	if err != nil {
		Print(err.Error(), Red)
		return "999999999999"
	}

	result := n.Int64() + min
	return strconv.FormatInt(result, 10)
}

func waitLimiter(identifier string) {
	err := Config.Limiter.Wait(context.Background())
	if err != nil {
		msg := identifier + " rate Wait: " + err.Error()
		Print(msg, Red)
	}
}

func searchBodyHeadersForString(cb string, body string, headers http.Header) bool {
	if strings.Contains(body, cb) {
		return true
	}
	for _, h := range headers {
		for _, v := range h {
			if strings.Contains(v, cb) {
				return true
			}
		}
	}
	return false
}

// check if cache was hit
func checkCacheHit(value string, indicator string) bool {
	if indicator == "" {
		indicator = Config.Website.Cache.Indicator
	}
	if strings.EqualFold("age", indicator) {
		value = strings.TrimSpace(value)
		if value != "0" && value != "" {
			return true
		}
	} else if strings.EqualFold("x-iinfo", indicator) {
		// String anhand von Leerzeichen aufteilen
		parts := strings.Split(value, " ")

		// Prüfen, ob der zweite Part existiert
		if len(parts) > 1 {
			secondPart := parts[1]

			// Sicherstellen, dass der zweite Part mindestens zwei Zeichen lang ist
			if len(secondPart) > 1 {
				secondChar := strings.ToUpper(string(secondPart[1]))
				if secondChar == "C" || secondChar == "V" {
					return true
				}
			}
		}
		// Cache Hit may have 0,>0 or >0,0 as value. Both responses are cached
	} else if strings.EqualFold("x-cache-hits", indicator) {
		for _, x := range strings.Split(indicator, ",") {
			x = strings.TrimSpace(x)
			if x != "0" {
				return true
			}
		}
	} else if strings.EqualFold("x-cc-via", indicator) {
		if strings.Contains(indicator, "[H,") {
			return true
		}
		// Some Headers may have "miss,hit" or "hit,miss" as value. But both are cached responses.
	} else if strings.Contains(strings.ToLower(value), "hit") || strings.Contains(strings.ToLower(value), "cached") {
		return true
	}
	return false
}

// like grep -C
func findOccurrencesWithContext(body, search string, context int) []string {
	var results []string
	inputLen := len(body)
	searchLen := len(search)

	for i := 0; i <= inputLen-searchLen; {
		if body[i:i+searchLen] == search {
			start := i - context
			if start < 0 {
				start = 0
			}
			end := i + searchLen + context
			if end > inputLen {
				end = inputLen
			}
			results = append(results, body[start:end])
			i += searchLen // skip past this match
		} else {
			i++
		}
	}

	return results
}

func headerToMultiMap(h *fasthttp.ResponseHeader) map[string][]string {
	m := make(map[string][]string)
	h.VisitAll(func(key, value []byte) {
		k := string(key)
		v := string(value)
		m[k] = append(m[k], v)
	})
	return m
}

func analyzeCacheIndicator(headers http.Header) (indicators []string) {
	customCacheHeader := strings.ToLower(Config.CacheHeader)
	for key, val := range headers {
		switch strings.ToLower(key) {
		case "cache-control", "pragma", "vary", "expires":
			msg := fmt.Sprintf("%s header was found: %s \n", key, val)
			PrintVerbose(msg, Cyan, 1)
		case "x-cache", "cf-cache-status", "x-drupal-cache", "x-varnish-cache", "akamai-cache-status", "server-timing", "x-iinfo", "x-nc", "x-hs-cf-cache-status", "x-proxy-cache", "x-cache-hits", "x-cache-status", "x-cache-info", "x-rack-cache", "cdn_cache_status", "cache_status", "x-akamai-cache", "x-akamai-cache-remote", "x-cache-remote", "x-litespeed-cache", "x-kinsta-cache", "x-ac", "cache-status", "ki-cf-cache-status", "eo-cache-status", "x-77-cache", "x-cache-lookup", "x-cc-via", customCacheHeader:
			// CacheHeader flag might not be set (=> ""). Continue in this case
			if key == "" {
				continue
			}
			indicators = append(indicators, key)
			msg := fmt.Sprintf("%s header was found: %s \n", key, val)
			PrintVerbose(msg, Cyan, 1)
		case "age":
			// only set it it wasn't set to x-cache or sth. similar beforehand
			indicators = append(indicators, key)
			msg := fmt.Sprintf("%s header was found: %s\n", key, val)
			PrintVerbose(msg, Cyan, 1)
		}
	}
	return indicators
}
