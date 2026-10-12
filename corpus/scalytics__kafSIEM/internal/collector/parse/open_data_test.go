package parse

import (
	"os"
	"strings"
	"testing"
)

func TestParseNVD(t *testing.T) {
	body := []byte(`{
	  "vulnerabilities": [{
	    "cve": {
	      "id": "CVE-2026-1234",
	      "published": "2026-07-01T00:00:00.000",
	      "lastModified": "2026-07-07T12:00:00.000",
	      "vulnStatus": "Analyzed",
	      "descriptions": [{"lang": "en", "value": "Remote code execution in edge routers."}],
	      "metrics": {"cvssMetricV31": [{"cvssData": {"baseScore": 9.8, "vectorString": "AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"}}]},
	      "affected": [{"affectedData": [{"vendor": "ExampleVendor", "product": "Gateway"}]}]
	    }
	  }]
	}`)
	items, err := ParseNVD(body)
	if err != nil {
		t.Fatal(err)
	}
	if len(items) != 1 || items[0].CVEID != "CVE-2026-1234" || items[0].CVSSScore < 9 {
		t.Fatalf("unexpected nvd parse: %#v", items)
	}
}

func TestParseEPSS(t *testing.T) {
	body := []byte(`cve,epss,percentile
CVE-2026-1000,0.91,0.99
CVE-2026-1001,0.10,0.40
`)
	items, err := ParseEPSS(body, 0.35, 10)
	if err != nil {
		t.Fatal(err)
	}
	if len(items) != 1 || items[0].CVEID != "CVE-2026-1000" {
		t.Fatalf("unexpected epss parse: %#v", items)
	}
}

func TestParseURLhausRecent(t *testing.T) {
	body := []byte(`# id,dateadded,url,url_status,last_online,threat,tags,urlhaus_link,reporter
123,2026-07-08 10:00:00,https://evil.test/mal.zip,online,2026-07-08 10:00:00,malware_download,elf,https://urlhaus.abuse.ch/url/123/,abuse
`)
	items, err := ParseURLhausRecent(body, 5)
	if err != nil {
		t.Fatal(err)
	}
	if len(items) != 1 || !strings.Contains(items[0].Title, "evil.test") {
		t.Fatalf("unexpected urlhaus parse: %#v", items)
	}
}

func TestParseUNSanctionsXML(t *testing.T) {
	body, err := os.ReadFile("../../../testdata/un_sanctions_sample.xml")
	if err != nil {
		body = []byte(`<CONSOLIDATED_LIST><ENTITIES><ENTITY>
		  <DATAID>1</DATAID><FIRST_NAME>Islamic State</FIRST_NAME><UN_LIST_TYPE>ISIL</UN_LIST_TYPE>
		  <LISTED_ON>2014-01-01</LISTED_ON><COMMENTS1>Listed terrorist entity</COMMENTS1>
		</ENTITY></ENTITIES></CONSOLIDATED_LIST>`)
	}
	items, err := ParseUNSanctionsXML(body, func(text string) string {
		if strings.Contains(strings.ToLower(text), "islamic state") {
			return "Islamic State"
		}
		return ""
	}, 10)
	if err != nil {
		t.Fatal(err)
	}
	if len(items) == 0 {
		t.Fatal("expected UN sanctions matches")
	}
}

func TestParseOpenSanctionsIndex(t *testing.T) {
	body := []byte(`{"last_change":"2026-07-08T06:58:01","resources":[{"name":"entities.ftm.json","url":"https://data.opensanctions.org/artifacts/sanctions/latest/entities.ftm.json"}]}`)
	index, url, err := ParseOpenSanctionsIndex(body)
	if err != nil {
		t.Fatal(err)
	}
	if index.LastChange == "" || url == "" {
		t.Fatalf("unexpected index parse: %#v %q", index, url)
	}
}

func TestParseOpenSanctionsEntities(t *testing.T) {
	line := `{"id":"NK-test","caption":"Islamic State affiliate","schema":"Organization","datasets":["us_ofac_sdn"],"properties":{"name":["Islamic State affiliate"],"topics":["crime.terror"]}}`
	items, err := ParseOpenSanctionsEntities(strings.NewReader(line+"\n"), func(text string) string {
		if strings.Contains(strings.ToLower(text), "islamic state") {
			return "Islamic State"
		}
		return ""
	}, 5)
	if err != nil {
		t.Fatal(err)
	}
	if len(items) != 1 || items[0].ActorMatch != "Islamic State" {
		t.Fatalf("unexpected opensanctions parse: %#v", items)
	}
}

func TestParseIMBPiracyWarnings(t *testing.T) {
	body := `<html><body>
	<h2>WEST AFRICA (Gulf of Guinea)</h2>
	<p>Vessels are advised to remain vigilant while in these waters due to piracy and armed robbery.</p>
	<h2>RED SEA / GULF OF ADEN</h2>
	<p>Mariners are advised to exercise caution due to Houthi attacks on commercial shipping.</p>
	</body></html>`
	items := ParseIMBPiracyWarnings(body, "https://icc-ccs.org/piracy-and-armed-robbery-prone-areas-and-warnings/", 5)
	if len(items) < 2 {
		t.Fatalf("expected IMB warnings, got %#v", items)
	}
}

func TestParseOFACSDNXML(t *testing.T) {
	body := []byte(`<sdnList><sdnEntry>
	  <uid>99</uid><firstName></firstName><lastName>ISLAMIC STATE OF IRAQ AND THE LEVANT</lastName>
	  <sdnType>Entity</sdnType><programList><program>SDGT</program></programList>
	</sdnEntry></sdnList>`)
	items, err := ParseOFACSDNXML(body, func(text string) string {
		if strings.Contains(strings.ToLower(text), "islamic state") {
			return "Islamic State"
		}
		return ""
	}, 10)
	if err != nil {
		t.Fatal(err)
	}
	if len(items) != 1 || items[0].ActorMatch != "Islamic State" {
		t.Fatalf("unexpected ofac parse: %#v", items)
	}
}
