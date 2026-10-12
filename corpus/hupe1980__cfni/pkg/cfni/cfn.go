package cfni

import (
	"fmt"
	"strings"

	"github.com/hupe1980/cfni/pkg/obfuscator/js"
	"github.com/hupe1980/cfni/pkg/obfuscator/python"
)

type CreateCFNCodeExecutionOptions struct {
	Code            string
	Runtime         string
	LogicalRoleID   string
	LogicalLambdaID string
	LogicalCustomID string
	CustomType      string
	S3AccessKey     *S3AccessKey
	*Filter
}

func (c *CFNI) CreateCFNCodeExecutionHandler(opts *CreateCFNCodeExecutionOptions) ([]byte, error) {
	handler := "index.handler"
	code := createNodeJSInlineFunction(opts.Code)

	if strings.HasPrefix(opts.Runtime, "python") {
		handler = "index.lambda_handler"
		code = createPythonInlineFunction(opts.Code)
	}

	return c.createHandler(&HandlerOptions{
		CFNITemplate: "templates/cfn_code_execution.py",
		CFNIData: &struct {
			Code            string
			Handler         string
			Runtime         string
			LogicalRoleID   string
			LogicalLambdaID string
			LogicalCustomID string
			CustomType      string
		}{
			Code:            toPythonList(code),
			Handler:         handler,
			Runtime:         opts.Runtime,
			LogicalRoleID:   opts.LogicalRoleID,
			LogicalLambdaID: opts.LogicalLambdaID,
			LogicalCustomID: opts.LogicalCustomID,
			CustomType:      opts.CustomType,
		},
		S3Client: s3Client(opts.S3AccessKey),
		Filter:   opts.Filter,
	})
}

func createNodeJSInlineFunction(code string) []string {
	obfuscator := js.New()
	code, _ = obfuscator.Obfuscate(code)

	inlineCode := fmt.Sprintf(`const response = require('cfn-response');
%s

exports.handler = async function(event, context) {
	let responseData = {};
	try {
		responseData = await cfni(event, context);
	} finally {
		await response.send(event, context, response.SUCCESS, responseData, context.logStreamName, true);
	}
}`, code)

	return strings.Split(strings.Replace(inlineCode, `"`, `\"`, -1), "\n")
}

func createPythonInlineFunction(code string) []string {
	obfuscator := python.New()
	code, _ = obfuscator.Obfuscate(code)

	inlineCode := fmt.Sprintf(`import cfnresponse
%s

def lambda_handler(event, context):
	response_data = {}
	try:
		response_data = cfni(event, context)
	finally:
		cfnresponse.send(event, context, cfnresponse.SUCCESS, response_data, context.log_stream_name, True)
`, code)

	return strings.Split(strings.Replace(inlineCode, `"`, `\"`, -1), "\n")
}
