package pkg

import (
	"errors"
	"fmt"
	"strings"
	"time"

	"github.com/valyala/fasthttp"
	"github.com/xplorfin/fasthttp2curl"
)

func TestWebCacheDeception() reportResult {
	var repResult reportResult
	repResult.Technique = "Cache Deception"

	// cacheable extensions: class, css, jar, js, jpg, jpeg, gif, ico, png, bmp, pict, csv, doc, docx, xls, xlsx, ps, pdf, pls, ppt, pptx, tif, tiff, ttf, otf, webp, woff, woff2, svg, svgz, eot, eps, ejs, swf, torrent, midi, mid

	appendings := []string{
		"/.css",                                       // Path parameter
		"/nonexistent1.css",                           // Path parameter
		"/../nonexistent2.css",                        // Path traversal
		"/%2e%2e/nonexistent3.css",                    // Encoded path traversal
		"%0Anonexistent4.css",                         // Encoded Newline
		"%00nonexistent5.css",                         // Encoded Null Byte
		"%09nonexistent6.css",                         // Encoded Tab
		"%3Bnonexistent7.css",                         // Encoded Semicolon
		"%23nonexistent8.css",                         // Encoded Pound
		"%3Fname=valnonexistent9.css",                 // Encoded Question Mark
		"%26name=valnonexistent10.css",                // Encoded Ampersand
		";nonexistent11.css",                          // Semicolon
		"?nonexistent12.css",                          // Question Mark
		"&nonexistent13.css",                          // Ampersand
		"%0A%2f%2e%2e%2fresources%2fnonexistent1.css", // Encoded Path Traversal to static directory using Encoded Newline
		"%00%2f%2e%2e%2fresources%2fnonexistent2.css", // Encoded Path Traversal to static directory using Encoded Null Byte
		"%09%2f%2e%2e%2fresources%2fnonexistent3.css", // Encoded Path Traversal to static directory using Encoded Tab
		"%3B%2f%2e%2e%2fresources%2fnonexistent4.css", // Encoded Path Traversal to static directoryEncoded using Semicolon
		"%23%2f%2e%2e%2fresources%2fnonexistent5.css", // Encoded Path Traversal to static directory using Encoded Pound
		"%3F%2f%2e%2e%2fresources%2fnonexistent6.css", // Encoded Path Traversal to static directory using Encoded Question Mark
		"%26%2f%2e%2e%2fresources%2fnonexistent7.css", // Encoded Path Traversal to static directory using Encoded Ampersand
		";%2f%2e%2e%2fresources%2fnonexistent8.css",   // Encoded Path Traversal to static directory using Semicolon
		"?%2f%2e%2e%2fresources%2fnonexistent9.css",   // Encoded Path Traversal to static directoy using Question Mark
		"&%2f%2e%2e%2fresources%2fnonexistent10.css",  // Encoded Path Traversal to static directory using Ampersand
		"%0A%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2frobots.txt", // Encoded Path Traversal to robots.txt using Encoded Newline
		"%00%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2frobots.txt", // Encoded Path Traversal to robots.txt directory using Encoded Null Byte
		"%09%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2frobots.txt", // Encoded Path Traversal to robots.txt directory using Encoded Tab
		"%3B%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2frobots.txt", // Encoded Path Traversal to robots.txt directoryEncoded using Semicolon
		"%23%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2frobots.txt", // Encoded Path Traversal to robots.txt directory using Encoded Pound
		"%3F%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2frobots.txt", // Encoded Path Traversal to robots.txt directory using Encoded Question Mark
		"%26%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2frobots.txt", // Encoded Path Traversal to robots.txt directory using Encoded Ampersand
		";%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2frobots.txt",   // Encoded Path Traversal to robots.txt directory using Semicolon
		"?%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2frobots.txt",   // Encoded Path Traversal to robots.txt directoy using Question Mark
		"&%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2frobots.txt",   // Encoded Path Traversal to robots.txt directory using Ampersand
	}
	// TODO add "Exploiting normalization by the origin server" cache deception which needs to prepend something before the url path

	if Config.Website.StatusCode != 200 || Config.Website.Body == "" {
		msg := "Skipping Web Cache Deception test, as it requires a valid website configuration with a status code of 200 and a non-empty body.\n"
		Print(msg, Yellow)
		repResult.HasError = true
		repResult.ErrorMessages = append(repResult.ErrorMessages, msg)
		return repResult
	}
	PrintVerbose("Testing for Web Cache Deception\n", NoColor, 1)

	// test each appending one after another
	for _, appendStr := range appendings {
		err := webCacheDeceptionTemplate(&repResult, appendStr)
		if err != nil {
			repResult.HasError = true
			repResult.ErrorMessages = append(repResult.ErrorMessages, err.Error())
		}
	}

	return repResult
}

func webCacheDeceptionTemplate(repResult *reportResult, appendStr string) error {
	var msg string
	var repCheck reportCheck
	req := fasthttp.AcquireRequest()
	resp := fasthttp.AcquireResponse()
	defer fasthttp.ReleaseRequest(req)
	defer fasthttp.ReleaseResponse(resp)
	var err error

	rUrl := Config.Website.Url.String()
	// Überprüfen, ob der String genau zwei `//` enthält
	if strings.Count(rUrl, "/") == 2 && !strings.HasPrefix(appendStr, "/") {
		// append `/`, so e.g. https://example%0A does not throw an error when building the request
		rUrl += "/"
	}

	req.Header.SetMethod("GET")
	req.SetRequestURI(rUrl + appendStr)
	setRequest(req, false, "", nil, false)

	err = client.Do(req, resp)
	if err != nil {
		msg = fmt.Sprintf("webCacheDeceptionTemplate: %s: client.Do: %s\n", appendStr, err.Error())
		Print(msg, Red)
		return errors.New(msg)
	}

	waitLimiter("Web Cache Deception")

	if resp.StatusCode() != Config.Website.StatusCode || string(resp.Body()) != Config.Website.Body {
		return nil // no cache deception, as the response is not the same as the original one
	}

	if Config.Website.Cache.NoCache || Config.Website.Cache.Indicator == "age" {
		time.Sleep(1 * time.Second) // wait a second to ensure that age header is not set to 0
	}

	waitLimiter("Web Cache Deception")

	err = client.Do(req, resp)
	if err != nil {
		msg = fmt.Sprintf("webCacheDeceptionTemplate: %s: client.Do: %s\n", appendStr, err.Error())
		Print(msg, Red)
		return errors.New(msg)
	}
	respHeader := headerToMultiMap(&resp.Header)

	// Add the request as curl command to the report
	command, err := fasthttp2curl.GetCurlCommandFastHttp(req)
	if err != nil {
		PrintVerbose("Error: fasthttp2curl: "+err.Error()+"\n", Yellow, 1)
	}

	repCheck.Request.CurlCommand = command.String()
	PrintVerbose("Curl command: "+repCheck.Request.CurlCommand+"\n", NoColor, 2)

	var cacheIndicators []string
	if Config.Website.Cache.Indicator == "" { // check if now a cache indicator exists
		cacheIndicators = analyzeCacheIndicator(respHeader)
	} else {
		cacheIndicators = []string{Config.Website.Cache.Indicator}
	}

	hit := false
	for _, indicator := range cacheIndicators {
		for _, v := range respHeader[indicator] {
			indicValue := strings.TrimSpace(strings.ToLower(v))
			if checkCacheHit(indicValue, Config.Website.Cache.Indicator) {
				hit = true
				Config.Website.Cache.Indicator = indicator
			}
		}
	}

	// check if there's a cache hit and if the body didn't change (otherwise it could be a cached error page, for example)
	if hit && string(resp.Body()) == Config.Website.Body && resp.StatusCode() == Config.Website.StatusCode {
		repResult.Vulnerable = true
		repCheck.Reason = "The response got cached due to Web Cache Deception"
		msg = fmt.Sprintf("%s was successfully decepted! appended: %s\n", rUrl, appendStr)
		Print(msg, Green)
		msg = "Curl: " + repCheck.Request.CurlCommand + "\n\n"
		Print(msg, Green)

		repCheck.Identifier = appendStr
		repCheck.URL = req.URI().String()
		// Dump the request
		repCheck.Request.Request = string(req.String())
		// Dump the response without the body
		resp.SkipBody = true
		repCheck.Request.Response = string(resp.String())

		repResult.Checks = append(repResult.Checks, repCheck)
	} else {
		PrintVerbose("Curl command: "+repCheck.Request.CurlCommand+"\n", NoColor, 2)
	}

	return nil
}
