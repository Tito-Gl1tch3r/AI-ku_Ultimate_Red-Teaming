package main

import (
	"bufio"
	"os"
	"time"

	. "github.com/logrusorgru/aurora/v4"
	log "github.com/projectdiscovery/gologger"
	"github.com/valyala/fasthttp"
)

func GetBody(curl chan string, results chan Results, c *fasthttp.Client) {
	regexfile, _ := os.ReadFile(*regexf)
	req := fasthttp.AcquireRequest()
	resp := fasthttp.AcquireResponse()
	defer fasthttp.ReleaseRequest(req)
	defer fasthttp.ReleaseResponse(resp)

	req_timeout := time.Duration(*timeout) * time.Second

	for url := range curl {

		req.SetRequestURI(url)

		err := c.DoTimeout(req, resp, req_timeout)
		if err != nil {
			log.Error().Msgf("%s : %s", Cyan(url), Red(err))
			wg.Done()
			continue
		}

		html := resp.Body()

		matchRegex(string(html), url, results, regexfile)

		wg.Done()
	}
}

func countLines(filename string) (int, error) {
	file, err := os.Open(filename)
	if err != nil {
		return 0, err
	}
	defer file.Close()

	scanner := bufio.NewScanner(file)
	lineCount := 0

	for scanner.Scan() {
		lineCount++
	}

	if err := scanner.Err(); err != nil {
		return 0, err
	}

	return lineCount, nil
}
