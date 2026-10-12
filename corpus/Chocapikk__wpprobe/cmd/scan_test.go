// Copyright (c) 2025 Valentin Lobstein (Chocapikk) <balgogan@protonmail.com>
//
// Permission is hereby granted, free of charge, to any person obtaining a copy of
// this software and associated documentation files (the "Software"), to deal in
// the Software without restriction, including without limitation the rights to
// use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
// the Software, and to permit persons to whom the Software is furnished to do so,
// subject to the following conditions:
//
// The above copyright notice and this permission notice shall be included in all
// copies or substantial portions of the Software.
//
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
// IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
// FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
// COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
// IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
// CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

package cmd

import (
	"errors"
	"testing"
)

func Test_mustBool(t *testing.T) {
	tests := []struct {
		name     string
		value    bool
		err      error
		expected bool
	}{
		{
			name:     "ValidTrue",
			value:    true,
			err:      nil,
			expected: true,
		},
		{
			name:     "ValidFalse",
			value:    false,
			err:      nil,
			expected: false,
		},
		{
			name:     "ErrorFallbackTrue",
			value:    true,
			err:      errors.New("some error"),
			expected: false,
		},
		{
			name:     "ErrorFallbackFalse",
			value:    false,
			err:      errors.New("another error"),
			expected: false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := mustBool(tt.value, tt.err)
			if result != tt.expected {
				t.Errorf("mustBool() = %v, want %v", result, tt.expected)
			}
		})
	}
}

func Test_mustInt(t *testing.T) {
	tests := []struct {
		name     string
		value    int
		err      error
		expected int
	}{
		{
			name:     "ValidInt",
			value:    5,
			err:      nil,
			expected: 5,
		},
		{
			name:     "ValidZero",
			value:    0,
			err:      nil,
			expected: 0,
		},
		{
			name:     "ErrorFallbackPositive",
			value:    100,
			err:      errors.New("invalid int"),
			expected: 10,
		},
		{
			name:     "ErrorFallbackNegative",
			value:    -5,
			err:      errors.New("negative int error"),
			expected: 10,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := mustInt(tt.value, tt.err)
			if result != tt.expected {
				t.Errorf("mustInt() = %v, want %v", result, tt.expected)
			}
		})
	}
}
