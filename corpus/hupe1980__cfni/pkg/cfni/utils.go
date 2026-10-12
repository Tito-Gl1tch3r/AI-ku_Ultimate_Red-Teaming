package cfni

import (
	"bytes"
	"encoding/hex"
	"fmt"
	"strings"
	"text/template"
)

func executeTemplate(name string, data any) (*bytes.Buffer, error) {
	tpl, err := template.ParseFS(templates, name)
	if err != nil {
		return nil, err
	}

	result := new(bytes.Buffer)
	if err = tpl.Execute(result, data); err != nil {
		return nil, err
	}

	return result, nil
}

func xor(input, key string) (output string) {
	for i := 0; i < len(input); i++ {
		output += string(input[i] ^ key[i%len(key)])
	}

	return output
}

func hexify(input string) string {
	return hex.EncodeToString([]byte(input))
}

func toPythonList(input []string) string {
	input = sliceMap(input, func(s string) string {
		return fmt.Sprintf(`"%s"`, s)
	})

	return fmt.Sprintf("[%s]", strings.Join(input, ", "))
}

func toPythonDict(input map[string]string) string {
	items := []string{}
	for k, v := range input {
		items = append(items, fmt.Sprintf(`"%s": "%s"`, k, v))
	}

	return fmt.Sprintf("{%s}", strings.Join(items, ", "))
}

func sliceMap[T, U any](data []T, f func(T) U) []U {
	res := make([]U, 0, len(data))

	for _, e := range data {
		res = append(res, f(e))
	}

	return res
}
