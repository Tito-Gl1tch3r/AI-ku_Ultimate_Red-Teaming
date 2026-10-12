from pydantic import BaseModel, Field
from typing import List, Optional, Literal

class SearchResult(BaseModel):
    query_no: int = Field(description="Query number (1-30) that found this URL")
    url: str = Field(description="Found URL")
    title: str = Field(description="Page title")
    description: str = Field(description="Page description")
    snippet: str = Field(description="Content snippet")

class DorkingResults(BaseModel):
    total_queries: int = Field(description="Total number of queries executed")
    queries_with_results: int = Field(description="Number of queries that returned results")
    total_urls_found: int = Field(description="Total number of URLs found")
    search_results: List[SearchResult] = Field(description="List of search results")

class VulnerabilityFinding(BaseModel):
    url: str = Field(description="URL where vulnerability/attack vector was found")
    classification: Literal["Web Page", "File"] = Field(description="Type of resource")
    discovery_type: Literal["Vulnerability", "Attack Vector"] = Field(description="Type of discovery")
    category: Literal[
        "Directory Listing",
        "Information Disclosure",
        "Sensitive Data Exposure",
        "IDOR",
        "Admin Panel",
        "Configuration Files",
        "API Exposure",
        "File Upload/Download",
        "LFI/RFI",
        "Social Engineering",
        "Open Redirect",
        "Cloud Storage Misconfiguration",
        "Token Exposure",
        "XSS",
        "Cross Site Scripting",
        "SQL Injection",
        "Command Injection",
        "CSRF",
        "Clickjacking",
        "Server Side Request Forgery",
        "Path Traversal",
        "Backup Files",
        "Development Environment",
        "WordPress Vulnerabilities",
        "Subdomain Enumeration",
        "OSINT",
        "Misc"
    ] = Field(description="Vulnerability/Attack Vector category based on 30 Google Dork queries")
    severity: Literal["Critical", "High", "Medium", "Low", "Info"] = Field(description="Severity level")
    description: str = Field(description="Detailed explanation of the finding")
    test_method: str = Field(description="How to test/verify this vulnerability/attack vector")
    mitigation: str = Field(description="Recommended mitigation steps")
    false_positive: bool = Field(description="Whether this is a false positive")
    fp_reason: Optional[str] = Field(default=None, description="Reason for false positive if applicable")

class VulnerabilityAnalysis(BaseModel):
    findings: List[VulnerabilityFinding] = Field(description="List of vulnerability/attack vector findings")