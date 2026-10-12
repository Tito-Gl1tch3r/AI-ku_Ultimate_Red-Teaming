package pkg

import (
	"net/url"

	"golang.org/x/time/rate"
)

var Config ConfigStruct

type (
	ConfigStruct struct {
		Threads                 int
		ReqRate                 float64
		Verbosity               int
		DoPost                  bool
		ContentType             string
		QuerySeparator          string
		CacheBuster             string
		TimeOut                 int
		DeclineCookies          bool
		Force                   bool
		UseHTTP                 bool
		ReasonTypes             string
		CLDiff                  int
		HMDiff                  int
		SkipTimebased           bool
		SkipWordlistCachebuster bool
		CacheHeader             string
		DisableColor            bool
		DisableStatusLine       bool
		IgnoreStatus            []int

		Recursivity int
		RecInclude  string
		RecExclude  []string
		RecDomains  []string
		RecLimit    int

		Urls       []string
		Cookies    []string
		Headers    []string
		Parameters []string
		Body       string

		OnlyTest string
		SkipTest string

		GeneratePath      string
		GenerateReport    bool
		EscapeJSON        bool
		GenerateCompleted bool
		GenerateLog       bool

		UseProxy bool
		ProxyURL string

		HeaderWordlist    string
		ParameterWordlist string

		Intitialized bool
		Limiter      *rate.Limiter `json:"-"`
		Website      WebsiteStruct `json:"-"`
	}

	WebsiteStruct struct {
		Headers      map[string][]string
		Body         string
		Cookies      map[string]string
		Url          *url.URL
		UrlWOQueries string
		Queries      map[string]string
		StatusCode   int
		Cache        CacheStruct
		Domain       string
	}

	CacheStruct struct {
		CBwasFound     bool
		CBisParameter  bool
		CBisHeader     bool
		CBisCookie     bool
		CBisHTTPMethod bool
		CBName         string

		//HitMissVerbose bool
		//HitMissTime    bool

		NoCache       bool
		Indicator     string
		TimeIndicator bool
	}
)

func init() {
}

func ReadConfigFile() ConfigStruct {
	config := ConfigStruct{
		Threads:           0,
		Recursivity:       0,
		Verbosity:         0,
		DoPost:            false,
		ContentType:       "",
		QuerySeparator:    "",
		CacheBuster:       "",
		TimeOut:           0,
		DeclineCookies:    false,
		Urls:              nil,
		Cookies:           nil,
		Headers:           nil,
		Parameters:        nil,
		Body:              "",
		OnlyTest:          "",
		SkipTest:          "",
		ProxyURL:          "",
		HeaderWordlist:    "",
		ParameterWordlist: "",
		Website: WebsiteStruct{
			Body:         "",
			Cookies:      nil,
			Url:          nil,
			UrlWOQueries: "",
			Queries:      nil,
			StatusCode:   0,
		},
	}

	return config
}
