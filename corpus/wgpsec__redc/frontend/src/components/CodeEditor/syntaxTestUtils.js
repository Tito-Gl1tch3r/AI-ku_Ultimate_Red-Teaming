/**
 * Syntax Highlighting Test Utilities
 * Task 8.1: 创建语法高亮测试工具函数
 * 
 * This module provides utility functions and test data for verifying
 * Terraform syntax highlighting in the CodeEditor component.
 * 
 * Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6
 */

/**
 * Sample Terraform code for testing syntax highlighting
 * Covers all major syntax elements that should be highlighted
 */
export const terraformSamples = {
  // Basic resource block with keywords, strings, and braces
  basicResource: `resource "aws_instance" "example" {
  ami           = "ami-0c55b159cbfafe1f0"
  instance_type = "t2.micro"
  
  tags = {
    Name = "ExampleInstance"
  }
}`,

  // Variable declaration with different types
  variables: `variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-west-2"
}

variable "instance_count" {
  description = "Number of instances"
  type        = number
  default     = 3
}`,

  // Output block
  outputs: `output "instance_ip" {
  description = "The public IP of the instance"
  value       = aws_instance.example.public_ip
}`,

  // Module block
  modules: `module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "3.0.0"
  
  name = "my-vpc"
  cidr = "10.0.0.0/16"
}`,

  // Data source
  dataSources: `data "aws_ami" "ubuntu" {
  most_recent = true
  
  filter {
    name   = "name"
    values = ["ubuntu/images/hcl-*"]
  }
}`,

  // Locals block
  locals: `locals {
  common_tags = {
    Environment = "production"
    Project     = "example"
  }
  
  instance_count = 5
}`,

  // Terraform block with provider
  terraformBlock: `terraform {
  required_version = ">= 1.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.0"
    }
  }
}`,

  // Provider configuration
  provider: `provider "aws" {
  region = var.region
  
  default_tags {
    tags = local.common_tags
  }
}`,

  // Comments (single-line and multi-line)
  comments: `# This is a single-line comment
resource "aws_instance" "example" {
  # Another comment
  ami = "ami-12345678"
  
  /*
   * This is a multi-line comment
   * spanning multiple lines
   */
  instance_type = "t2.micro"
}`,

  // Numbers and operators
  numbersAndOperators: `locals {
  count = 10
  price = 99.99
  total = count * price
  
  is_production = true
  is_enabled    = false
  
  result = 5 + 3 - 2 * 4 / 2
}`,

  // Complex nested structures
  complexNested: `resource "aws_security_group" "example" {
  name        = "example-sg"
  description = "Example security group"
  
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  tags = merge(
    local.common_tags,
    {
      Name = "example-sg"
    }
  )
}`,

  // String interpolation
  stringInterpolation: `resource "aws_instance" "example" {
  ami           = data.aws_ami.ubuntu.id
  instance_type = var.instance_type
  
  tags = {
    Name = "\${var.project_name}-instance-\${var.environment}"
  }
  
  user_data = <<-EOF
    #!/bin/bash
    echo "Hello, World!"
    apt-get update
  EOF
}`,
};

/**
 * Expected syntax element types for Terraform
 * These correspond to CodeMirror token types
 */
export const syntaxElementTypes = {
  KEYWORD: 'keyword',           // resource, variable, output, module, data, locals, terraform, provider
  STRING: 'string',             // String literals
  COMMENT: 'comment',           // Single-line and multi-line comments
  NUMBER: 'number',             // Numeric literals
  OPERATOR: 'operator',         // =, +, -, *, /, etc.
  PUNCTUATION: 'punctuation',   // {, }, [, ], (, ), etc.
  PROPERTY: 'property',         // Property names in blocks
  VARIABLE: 'variable',         // Variable references
  BOOLEAN: 'bool',              // true, false
};

/**
 * Terraform keywords that should be highlighted
 * Requirements: 2.1
 */
export const terraformKeywords = [
  'resource',
  'variable',
  'output',
  'module',
  'data',
  'locals',
  'terraform',
  'provider',
  'required_version',
  'required_providers',
  'source',
  'version',
  'default',
  'description',
  'type',
  'string',
  'number',
  'bool',
  'list',
  'map',
  'object',
  'set',
  'tuple',
  'any',
  'for_each',
  'count',
  'depends_on',
  'lifecycle',
  'provisioner',
  'connection',
];

/**
 * Check if a DOM element has a specific syntax highlighting class
 * @param {HTMLElement} element - The DOM element to check
 * @param {string} tokenType - The expected token type (e.g., 'keyword', 'string')
 * @returns {boolean} True if the element has the expected class
 */
export function hasSyntaxClass(element, tokenType) {
  if (!element || !element.className) {
    return false;
  }
  
  // CodeMirror uses classes like 'cm-keyword', 'cm-string', etc.
  const expectedClass = `cm-${tokenType}`;
  return element.classList.contains(expectedClass);
}

/**
 * Find all elements in the editor with a specific syntax class
 * @param {HTMLElement} editorContainer - The editor container element
 * @param {string} tokenType - The token type to search for
 * @returns {HTMLElement[]} Array of elements with the specified class
 */
export function findElementsWithSyntaxClass(editorContainer, tokenType) {
  if (!editorContainer) {
    return [];
  }
  
  const className = `cm-${tokenType}`;
  return Array.from(editorContainer.querySelectorAll(`.${className}`));
}

/**
 * Check if a text content is highlighted with the expected token type
 * @param {HTMLElement} editorContainer - The editor container element
 * @param {string} text - The text to search for
 * @param {string} tokenType - The expected token type
 * @returns {boolean} True if the text is found and has the expected highlighting
 */
export function isTextHighlightedAs(editorContainer, text, tokenType) {
  if (!editorContainer || !text) {
    return false;
  }
  
  const elements = findElementsWithSyntaxClass(editorContainer, tokenType);
  return elements.some(el => el.textContent.includes(text));
}

/**
 * Get all syntax-highlighted elements in the editor
 * @param {HTMLElement} editorContainer - The editor container element
 * @returns {Object} Object mapping token types to arrays of elements
 */
export function getAllSyntaxElements(editorContainer) {
  if (!editorContainer) {
    return {};
  }
  
  const result = {};
  
  // Find all elements with cm- prefix classes
  const allElements = editorContainer.querySelectorAll('[class*="cm-"]');
  
  allElements.forEach(element => {
    element.classList.forEach(className => {
      if (className.startsWith('cm-')) {
        const tokenType = className.substring(3); // Remove 'cm-' prefix
        if (!result[tokenType]) {
          result[tokenType] = [];
        }
        result[tokenType].push(element);
      }
    });
  });
  
  return result;
}

/**
 * Verify that keywords are properly highlighted in the editor
 * @param {HTMLElement} editorContainer - The editor container element
 * @param {string[]} keywords - Array of keywords to check
 * @returns {Object} Object with results: { found: string[], missing: string[] }
 */
export function verifyKeywordHighlighting(editorContainer, keywords = terraformKeywords) {
  const found = [];
  const missing = [];
  
  keywords.forEach(keyword => {
    if (isTextHighlightedAs(editorContainer, keyword, syntaxElementTypes.KEYWORD)) {
      found.push(keyword);
    } else {
      missing.push(keyword);
    }
  });
  
  return { found, missing };
}

/**
 * Verify that strings are properly highlighted in the editor
 * @param {HTMLElement} editorContainer - The editor container element
 * @returns {number} Number of string elements found
 */
export function countStringElements(editorContainer) {
  const stringElements = findElementsWithSyntaxClass(editorContainer, syntaxElementTypes.STRING);
  return stringElements.length;
}

/**
 * Verify that comments are properly highlighted in the editor
 * @param {HTMLElement} editorContainer - The editor container element
 * @returns {number} Number of comment elements found
 */
export function countCommentElements(editorContainer) {
  const commentElements = findElementsWithSyntaxClass(editorContainer, syntaxElementTypes.COMMENT);
  return commentElements.length;
}

/**
 * Verify that numbers are properly highlighted in the editor
 * @param {HTMLElement} editorContainer - The editor container element
 * @returns {number} Number of number elements found
 */
export function countNumberElements(editorContainer) {
  const numberElements = findElementsWithSyntaxClass(editorContainer, syntaxElementTypes.NUMBER);
  return numberElements.length;
}

/**
 * Check if the editor has any syntax highlighting applied
 * @param {HTMLElement} editorContainer - The editor container element
 * @returns {boolean} True if any syntax highlighting classes are found
 */
export function hasSyntaxHighlighting(editorContainer) {
  if (!editorContainer) {
    return false;
  }
  
  // Check if there are any elements with cm- prefix classes (excluding cm-editor, cm-content, etc.)
  const syntaxElements = editorContainer.querySelectorAll('[class*="cm-"][class*="keyword"], [class*="cm-"][class*="string"], [class*="cm-"][class*="comment"]');
  return syntaxElements.length > 0;
}

/**
 * Get a summary of syntax highlighting in the editor
 * @param {HTMLElement} editorContainer - The editor container element
 * @returns {Object} Summary object with counts for each token type
 */
export function getSyntaxHighlightingSummary(editorContainer) {
  const allElements = getAllSyntaxElements(editorContainer);
  
  const summary = {
    total: 0,
    byType: {},
  };
  
  Object.keys(allElements).forEach(tokenType => {
    const count = allElements[tokenType].length;
    summary.byType[tokenType] = count;
    summary.total += count;
  });
  
  return summary;
}

/**
 * Wait for CodeMirror to finish rendering
 * Useful in tests to ensure the editor is fully initialized
 * @param {number} timeout - Maximum time to wait in milliseconds
 * @returns {Promise<void>}
 */
export function waitForEditorRender(timeout = 1000) {
  return new Promise((resolve) => {
    // Give CodeMirror time to render
    setTimeout(resolve, timeout);
  });
}

/**
 * Create a test case for syntax highlighting verification
 * @param {string} name - Test case name
 * @param {string} code - Terraform code to test
 * @param {Object} expectations - Expected highlighting results
 * @returns {Object} Test case object
 */
export function createSyntaxTestCase(name, code, expectations) {
  return {
    name,
    code,
    expectations: {
      hasKeywords: expectations.hasKeywords || false,
      hasStrings: expectations.hasStrings || false,
      hasComments: expectations.hasComments || false,
      hasNumbers: expectations.hasNumbers || false,
      hasOperators: expectations.hasOperators || false,
      hasPunctuation: expectations.hasPunctuation || false,
      minKeywordCount: expectations.minKeywordCount || 0,
      minStringCount: expectations.minStringCount || 0,
      minCommentCount: expectations.minCommentCount || 0,
      minNumberCount: expectations.minNumberCount || 0,
    },
  };
}

/**
 * Verify a test case against the editor
 * @param {HTMLElement} editorContainer - The editor container element
 * @param {Object} testCase - Test case created with createSyntaxTestCase
 * @returns {Object} Verification results
 */
export function verifySyntaxTestCase(editorContainer, testCase) {
  const summary = getSyntaxHighlightingSummary(editorContainer);
  const { expectations } = testCase;
  
  const results = {
    passed: true,
    failures: [],
  };
  
  // Check keyword highlighting
  if (expectations.hasKeywords) {
    const keywordCount = summary.byType[syntaxElementTypes.KEYWORD] || 0;
    if (keywordCount < expectations.minKeywordCount) {
      results.passed = false;
      results.failures.push(`Expected at least ${expectations.minKeywordCount} keywords, found ${keywordCount}`);
    }
  }
  
  // Check string highlighting
  if (expectations.hasStrings) {
    const stringCount = summary.byType[syntaxElementTypes.STRING] || 0;
    if (stringCount < expectations.minStringCount) {
      results.passed = false;
      results.failures.push(`Expected at least ${expectations.minStringCount} strings, found ${stringCount}`);
    }
  }
  
  // Check comment highlighting
  if (expectations.hasComments) {
    const commentCount = summary.byType[syntaxElementTypes.COMMENT] || 0;
    if (commentCount < expectations.minCommentCount) {
      results.passed = false;
      results.failures.push(`Expected at least ${expectations.minCommentCount} comments, found ${commentCount}`);
    }
  }
  
  // Check number highlighting
  if (expectations.hasNumbers) {
    const numberCount = summary.byType[syntaxElementTypes.NUMBER] || 0;
    if (numberCount < expectations.minNumberCount) {
      results.passed = false;
      results.failures.push(`Expected at least ${expectations.minNumberCount} numbers, found ${numberCount}`);
    }
  }
  
  return results;
}
