// mod/plugin/template_funcs_test.go
package plugin

import (
	"bytes"
	"encoding/base64"
	"testing"
	"text/template"
)

func renderTemplate(t *testing.T, tmplStr string, data interface{}) string {
	t.Helper()
	tmpl, err := template.New("test").Funcs(BuiltinFuncs()).Parse(tmplStr)
	if err != nil {
		t.Fatalf("parse: %v", err)
	}
	var buf bytes.Buffer
	if err := tmpl.Execute(&buf, data); err != nil {
		t.Fatalf("exec: %v", err)
	}
	return buf.String()
}

func TestFuncDefault(t *testing.T) {
	got := renderTemplate(t, `{{default "fallback" ""}}`, nil)
	if got != "fallback" {
		t.Errorf("got %q, want %q", got, "fallback")
	}
	got = renderTemplate(t, `{{default "fallback" "real"}}`, nil)
	if got != "real" {
		t.Errorf("got %q, want %q", got, "real")
	}
}

func TestFuncJoin(t *testing.T) {
	data := map[string]interface{}{"IPs": []string{"1.1.1.1", "2.2.2.2"}}
	got := renderTemplate(t, `{{.IPs | join ","}}`, data)
	if got != "1.1.1.1,2.2.2.2" {
		t.Errorf("got %q", got)
	}
}

func TestFuncBase64(t *testing.T) {
	got := renderTemplate(t, `{{"hello" | base64Encode}}`, nil)
	want := base64.StdEncoding.EncodeToString([]byte("hello"))
	if got != want {
		t.Errorf("got %q, want %q", got, want)
	}
}

func TestFuncDict(t *testing.T) {
	got := renderTemplate(t, `{{$d := dict "a" "1" "b" "2"}}{{index $d "a"}}-{{index $d "b"}}`, nil)
	if got != "1-2" {
		t.Errorf("got %q", got)
	}
}

func TestFuncToJSON(t *testing.T) {
	data := map[string]interface{}{"val": map[string]string{"k": "v"}}
	got := renderTemplate(t, `{{.val | toJSON}}`, data)
	if got != `{"k":"v"}` {
		t.Errorf("got %q", got)
	}
}

func TestFuncJsonParse(t *testing.T) {
	got := renderTemplate(t, `{{$m := jsonParse "{\"x\":\"y\"}"}}{{index $m "x"}}`, nil)
	if got != "y" {
		t.Errorf("got %q", got)
	}
}

func TestFuncJsonPath(t *testing.T) {
	data := map[string]interface{}{
		"raw": map[string]interface{}{
			"result": []interface{}{
				map[string]interface{}{"id": "abc123"},
			},
		},
	}
	got := renderTemplate(t, `{{.raw | jsonPath "result.0.id"}}`, data)
	if got != "abc123" {
		t.Errorf("got %q", got)
	}
}

func TestFuncReplace(t *testing.T) {
	got := renderTemplate(t, `{{"a.b.c" | replace "." "-"}}`, nil)
	if got != "a-b-c" {
		t.Errorf("got %q", got)
	}
}

func TestFuncSplit(t *testing.T) {
	got := renderTemplate(t, `{{$s := split "," "a,b,c"}}{{index $s 1}}`, nil)
	if got != "b" {
		t.Errorf("got %q", got)
	}
}

func TestFuncAdd(t *testing.T) {
	got := renderTemplate(t, `{{add 3 4}}`, nil)
	if got != "7" {
		t.Errorf("got %q", got)
	}
}
