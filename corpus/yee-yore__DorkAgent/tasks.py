from crewai import Task
from models import DorkingResults, VulnerabilityAnalysis

def task(target_domain: str, domain: str, agents: list) -> list:
    """Create tasks for the CrewAI workflow."""

    task1 = Task(
        description=f"""
        # Google Dorking Search Analysis

        ## Context
        You are a passive OSINT reconnaissance agent operating as part of an authorized security assessment (bug bounty research or a security team auditing its own attack surface). Every query below is issued only against Google's public search index via a search API — you never send any request directly to {target_domain}, never authenticate, and never exploit anything. You are only surfacing content that is already public and already indexed by search engines, for the operator to review and, where applicable, responsibly disclose.

        ## Objective
        Execute the following Google Dork queries for the domain {domain} and collect ONLY REAL search results that actually exist.

        ## Google Dork Query List
        1. site:{target_domain} (intitle:"index of /" | intitle:"docker-compose.yml" | intitle:".env" | intitle:"config.yml" | intitle:".git" | intitle:"package.json" | intitle:"requirements.txt" | intitle:".gitignore" | intitle:"IIS Windows Server")
        2. site:{target_domain} (ext:pdf | ext:doc | ext:docx | ext:xls | ext:xlsx | ext:csv | ext:ppt | ext:pptx | ext:txt | ext:rtf | ext:odt) ("INTERNAL USE ONLY" | "INTERNAL ONLY" | "TRADE SECRET" | "NOT FOR DISTRIBUTION" | "NOT FOR PUBLIC RELEASE" | "EMPLOYEE ONLY")
        3. site:{target_domain} (ext:csv | ext:txt | ext:json | ext:xlsx | ext:xls | ext:sql | ext:log | ext:xml) (intext:"id" | intext:"uid" | intext:"uuid" | intext:"username" | intext:"password" | intext:"userid" | intext:"email" | intext:"ssn" | intext:"phone" | intext:"date of birth" | intext:"Social Security Number" | intext:"credit card" | intext:"CCV" | intext:"CVV" | intext:"card number")
        4. site:{target_domain} (inurl:action | inurl:page | inurl:pid | inurl:uid | inurl:id | inurl:search | inurl:cid | inurl:idx | inurl:no)
        5. site:{target_domain} (inurl:admin | inurl:administrator | inurl:wp-login | inurl:manage | inurl:control | inurl:panel | inurl:dashboard | inurl:wp-admin | inurl:phpmyadmin | inurl:console)
        6. site:{target_domain} ext:txt inurl:robots.txt
        7. site:{target_domain} (ext:yaml | ext:yml | ext:ini | ext:conf | ext:config | ext:log | ext:pdf | ext:xml | ext:json) (intext:"token" | intext:"access_token" | intext:"api_key" | intext:"private_key" | intext:"secret" | intext:"BEGIN RSA PRIVATE KEY" | intext:"BEGIN DSA PRIVATE KEY" | intext:"BEGIN OPENSSH PRIVATE KEY")
        8. site:{target_domain} (inurl:/download.jsp | inurl:/downloads.jsp | inurl:/upload.jsp) | inurl:/uploads.jsp | inurl:/download.php | inurl:/downloads.php | inurl:/upload.php) | inurl:/uploads.php)
        9. site:{target_domain} (inurl:index.php?page | inurl:file | inurl:inc | inurl:layout | inurl:template | inurl:content | inurl:module | inurl:include= | inurl:require= | inurl:load= | inurl:get= | inurl:show= | inurl:read=)
        10. site:{target_domain} (ext:pdf | ext:doc | ext:docx | ext:ppt | ext:pptx) (intext:"join.slack" | intext:"t.me" | intext:"trello.com/invite" | intext:"notion.so" | intext:"atlassian.net" | intext:"asana.com" | intext:"teams.microsoft.com" | intext:"zoom.us/j" | intext:"bit.ly")
        11. site:{target_domain} (inurl:url= | inurl:continue= | inurl:redirect | inurl:return | inurl:target | inurl:site= | inurl:view= | inurl:path | inurl:returl= | inurl:next= | inurl:fallback= | inurl:u= | inurl:goto= | inurl:link=)
        12. (site:*.s3.amazonaws.com | site:*.s3-external-1.amazonaws.com | site:*.s3.dualstack.us-east-1.amazonaws.com | site:*.s3.ap-south-1.amazonaws.com) "{domain}"
        13. site:{target_domain} inurl:eyJ (inurl:token | inurl:jwt | inurl:access | inurl:auth | inurl:authorization | inurl:secret)
        14. site:{target_domain} inurl:api (inurl:/v1/ | inurl:/v2/ | inurl:/v3/ | inurl:/v4/ | inurl:/v5/ | inurl:/rest)
        15. site:{target_domain} (inurl:/graphql | inurl:/swagger | inurl:swagger-ui | inurl:/rest | inurl:api-docs)
        16. site:{target_domain} inurl:"error" | intitle:"exception" | intitle:"failure" | intitle:"server at" | inurl:exception | "database error" | "SQL syntax" | "undefined index" | "unhandled exception" | "stack trace" | "SQL syntax error" | "mysql_fetch" | "Warning: mysql" | "PostgreSQL query failed" | "Notice: Undefined" | "Warning: include" | "Fatal error" | "Parse error"
        17. site:{target_domain} ext:log | ext:txt | ext:conf | ext:cnf | ext:ini | ext:env | ext:sh | ext:bak | ext:backup | ext:swp | ext:old | ext:~ | ext:git | ext:svn | ext:htpasswd | ext:htaccess | ext:json | ext:sql
        18. site:openbugbounty.org inurl:reports intext:"{domain}"
        19. (site:groups.google.com | site:googleapis.com | site:drive.google.com | site:dropbox.com | site:box.com | site:onedrive.live.com | site:firebaseio.com | site:*.amazonaws.com | site:*.azure.com | site:*.digitaloceanspaces.com | site:pastebin.com | site:paste2.org | site:pastehtml.com | site:slexy.org | site:github.com | site:gitlab.com | site:bitbucket.org) "{domain}"
        20. site:{target_domain} (inurl:dev | inurl:test | inurl:staging | inurl:development | inurl:debug | intext:"phpinfo()" | inurl:phpinfo.php | inurl:info.php | inurl:test.php | inurl:dev.php | inurl:debug.php | intext:"version" | intext:"powered by" | intext:"built with" | intext:"running")
        21. site:{target_domain} (inurl:server | inurl:backup | inurl:config | inurl:setting | inurl:log | inurl:monitor | inurl:metric | inurl:health | inurl:status)
        22. site:{target_domain} (intext:"PAGE NOT FOUND" | intext:"project not found" | intext:"Repository not found"  | intext:"domain does not exist" | intext:"This page could not be found" | intext:"404 Blog is not found" | intext:"No settings were found for this company" | intext:"domain name is invalid")
        23. site:*.{target_domain} -www (inurl:admin | inurl:login | inurl:portal | inurl:dashboard | inurl:jenkins | inurl:gitlab | inurl:bitbucket | inurl:jira | inurl:confluence)
        24. site:{target_domain} (inurl:exec | inurl:shell | inurl:command | inurl:cmd | inurl:system | inurl:eval)
        25. site:{target_domain} (inurl:lang= | inurl:locale= | inurl:country= | intext:"?lang=" | intext:"?language=")
        26. site:{target_domain} inurl:"/.well-known/" (inurl:security.txt | inurl:humans.txt | inurl:apple-app-site-association)
        27. site:{target_domain} (inurl:wp-content/uploads | inurl:wp-config | inurl:wp-admin | inurl:wp-includes) -inurl:wp-content (filetype:sql | filetype:txt | filetype:log)
        28. (cache:{target_domain} | site:web.archive.org "{domain}") (intext:"password" | intext:"admin" | intext:"login" | intext:"internal")
        29. site:crt.sh "{domain}" | site:certificate.transparency.log "{domain}"
        30. (site:linkedin.com | site:twitter.com | site:facebook.com) "{domain}" (intext:"employee" | intext:"work at" | intext:"@{domain}")

        ## Execution Process - YOU MUST FOLLOW THIS
        1. Execute EACH of the 30 queries in sequence - DO NOT SKIP ANY QUERIES
        2. Document results for each query even if it returns nothing
        3. Continue until ALL 30 queries have been executed
        4. Only then compile final results

        ## Search Guidelines
        - Execute each query exactly in the format specified above.
        - If a query returns no results, immediately proceed to the next google dork.
        - ONLY report URLs that you ACTUALLY find in the search results.
        - NEVER fabricate or hallucinate any URLs or search results.
        - If all queries return no results, return empty results list.
        - Search only within the provided domain; do not expand the search scope.

        ## Exclusion Criteria
        - Exclude results containing the following keywords (high false positive likelihood):
          * Common documents: "Advertisement", "Agreement", "Terms", "Policy", "License", "Disclaimer"
          * Support materials: "API Docs", "Forum", "Help", "Community", "Code of Conduct", "Knowledge Base", "Support Center", "Customer Support"
          * Development content: "Developers", "Statement", "Support", "Rules", "Docs", "Developer Portal", "Engineering Blog"
          * Example content: "example", "sample", "demo", "dummy", "placeholder", "mockup"
          * Documents: "Guideline", "Template", "Documentation", "User Manual", "Reference Guide"
          * Corporate communications: "About Us", "Press", "Media", "Careers"

        - Also exclude:
          * Files with naming patterns like:
            - "example_*", "sample_*", "demo_*", "*_sample.*", "*_demo.*"
          * Content that appears non-production:
            - Sequential IDs (user1, user2, user3)
            - Dummy email patterns (test@example.com, admin@localhost, user@test.com)
            - Placeholder usernames (admin, root, temp, organizer)
          * Content with artificial data patterns:
            - Generic sequential identifiers
            - Predictable naming conventions
          * Training materials or documentation examples
          * Onboarding and introductory content

        - Comprehensive URL filtering:
          * Exclude URLs containing subdirectories like:
            - "/help/"
            - "/support/"
            - "/docs/"
            - "/examples/"
            - "/tutorial/"
          * Avoid results from known documentation domains
          * Filter out URLs with explicit non-production indicators
        """,
        expected_output="Provide a comprehensive summary of Google Dorking search results including: total number of queries executed (30), number of queries that returned actual results, total number of unique URLs found, and a detailed list of all discovered URLs with their titles, descriptions, and content snippets. Focus only on real search results that actually exist and exclude any example, demo, or documentation content.",
        agent=agents[0],
        output_pydantic=DorkingResults
    )

    task2 = Task(
        description=f"""
        # Vulnerability and Attack Vector Analysis

        ## Objective
        Analyze the Google Dorking results found by the searcher to identify potential security vulnerabilities or attack vectors.

        ## CRITICAL INSTRUCTIONS
        - ONLY analyze URLs that were ACTUALLY found by the searcher in Task 1.
        - DO NOT invent, fabricate, or hallucinate any vulnerabilities or findings.
        - If no URLs were found by the searcher, report that no vulnerabilities could be identified.
        - DO NOT use example data from this prompt as actual findings.
        - ALWAYS base your analysis SOLELY on real search results.

        ## Filtering Example Data
        - EXCLUDE any files with names containing words like "example", "sample", "demo", "dummy"
        - Do not report vulnerabilities based on example, training files
        - Be skeptical of data that looks too perfect or follows obvious patterns (e.g., sequential IDs, test@example.com)
        - For user data, verify it appears to be actual user information rather than placeholder content
        - If data contains elements like "example_value_based_audience_file" or similar indicators of non-production data, exclude it
        - Pay special attention to file metadata, headers, or comments that might indicate example status

        ## Field Classification Guide
        **IMPORTANT: Understand the difference between discovery_type and category fields:**

        ### Discovery Type Classification:
        - **"Vulnerability"**: Use when finding represents an actual security flaw or weakness
          - Examples: SQL Injection, XSS, exposed credentials, misconfigured services
          - Criteria: Something that can be directly exploited or poses immediate security risk
        
        - **"Attack Vector"**: Use when finding represents a potential attack path or information gathering point
          - Examples: parameter manipulation points, admin panel discovery, directory listings, URL patterns
          - Criteria: Information useful for further reconnaissance or potential attack entry points

        ### Category Field:
        Use one of the 26 predefined categories below (separate from discovery_type)

        ### Examples of Correct Field Usage:
        ```
        URL: /admin/login.php
        - discovery_type: "Attack Vector" (potential entry point)
        - category: "Admin Panel"

        URL: /config.php (containing database passwords)
        - discovery_type: "Vulnerability" (actual security flaw)  
        - category: "Sensitive Data Exposure"

        URL: /api/users?id=123
        - discovery_type: "Attack Vector" (parameter manipulation point)
        - category: "IDOR"
        ```

        ## Analysis Categories
        Analyze findings using one of the following 26 security categories that match the Pydantic model:

        **File and Directory Exposure:**
        - Directory Listing: Exposed directory browsing allowing enumeration of files and folders
        - Configuration Files: Exposed configuration files containing sensitive settings
        - Backup Files: Accessible backup files that may contain sensitive data or code
        - Development Environment: Exposed development/staging environments with debugging info

        **Information Disclosure:**
        - Information Disclosure: General information leakage not fitting other categories
        - Sensitive Data Exposure: Exposed PII, credentials, or confidential business data
        - Token Exposure: Exposed API keys, access tokens, session tokens, or authentication credentials
        - OSINT: Open Source Intelligence gathering revealing organizational information

        **Authentication and Access Control:**
        - Admin Panel: Exposed administrative interfaces or management consoles
        - IDOR: Insecure Direct Object References allowing unauthorized data access

        **Injection Vulnerabilities:**
        - XSS: Cross-Site Scripting vulnerabilities in input fields or output contexts
        - Cross Site Scripting: Alternative classification for XSS findings
        - SQL Injection: Database injection vulnerabilities through user inputs
        - Command Injection: Operating system command injection attack vectors
        - LFI/RFI: Local or Remote File Inclusion vulnerabilities

        **Web Application Security:**
        - CSRF: Cross-Site Request Forgery vulnerabilities
        - Clickjacking: UI redressing attacks through iframe manipulation
        - Open Redirect: Unvalidated redirects leading to malicious sites
        - Server Side Request Forgery: SSRF vulnerabilities allowing internal network access
        - Path Traversal: Directory traversal vulnerabilities accessing unauthorized files

        **File Handling:**
        - API Exposure: Exposed APIs revealing functionality or data
        - File Upload/Download: Insecure file handling mechanisms

        **Infrastructure and Cloud:**
        - Cloud Storage Misconfiguration: Publicly accessible cloud storage buckets or containers
        - Social Engineering: Information useful for social engineering attacks
        - Subdomain Enumeration: Discovery of additional subdomains expanding attack surface

        **CMS-Specific:**
        - WordPress Vulnerabilities: WordPress-specific security issues and misconfigurations

        **General:**
        - Misc: Miscellaneous findings not fitting other specific categories

        ## Severity Assessment Criteria
        - Critical: Direct system access or sensitive data exposure (credentials, tokens, PII)
        - High: Access to important functions/data (source code, configuration files, internal documents)
        - Medium: Vulnerabilities with limited impact (partial information disclosure, potential injection points)
        - Low: Information exposure without a direct attack vector

        """,
        expected_output="Analyze the Google Dorking search results and provide detailed vulnerability and attack vector findings. For each discovered URL, classify it as either a web page or file, identify the discovery type (vulnerability or attack vector), categorize the finding using one of the predefined categories (Directory Listing, IDOR, Admin Panel, Information Disclosure, etc.), assign appropriate severity level, provide detailed description of the security implications, suggest specific testing methods, recommend mitigation strategies, and determine if it's a false positive with reasoning.",
        agent=agents[1],
        output_pydantic=VulnerabilityAnalysis
    )

    task3 = Task(
        description=f"""
        # Enhanced Security Assessment Report Creation

        ## CRITICAL INSTRUCTIONS
        - **FOLLOW USER INSTRUCTIONS**: Strictly adhere to the user instructions provided: {{user_instructions}}
        - ONLY include vulnerabilities and findings that were ACTUALLY identified by the bug hunter in Task 2
        - NEVER fabricate or hallucinate any vulnerabilities, findings, or evidence
        - If the bug hunter found no vulnerabilities, state clearly that no vulnerabilities were found
        - Use ONLY real data from the previous tasks - do not use any example data from this prompt
        - Focus on providing actionable intelligence for manual security testing

        ## Objective
        Create a comprehensive security assessment report for {target_domain} that provides actionable intelligence for attack vector exploitation and information disclosure remediation.

        ## Report Structure
        Create a professional security assessment report with the following sections:
        1. Executive Summary - scope, findings count, risk distribution, key discoveries
        2. Attack Vector Analysis - categorized by vulnerability type with testing recommendations
        3. Information Disclosure Assessment - data sensitivity analysis and remediation steps
        4. Technical Findings - detailed vulnerability descriptions with evidence and impact
        5. Risk Prioritization Matrix - exploitability vs impact ranking for testing order

        ## Formatting Guidelines
        - Use clear section headers and professional markdown formatting
        - Include severity labels: [CRITICAL], [HIGH], [MEDIUM], [LOW], [INFO]  
        - Assign unique finding IDs: AV-001, ID-001, etc.
        - Include actionable commands, URLs, and tool recommendations where relevant
        - Focus on specific manual testing guidance and business impact
        """,
        expected_output=f"""
        **NOTE: Follow the user instructions provided: {{user_instructions}}**

        # Security Assessment Report for {target_domain}

        *Generated by DorkAgent - Attack Vector & Information Disclosure Analysis*

        ---

        ## 1. Executive Summary

        **Target Scope**: {target_domain}

        **Risk Distribution:**
        - [CRITICAL]: <critical_count> findings
        - [HIGH]: <high_count> findings
        - [MEDIUM]: <medium_count> findings
        - [LOW]: <low_count> findings
        - [INFO]: <info_count> findings

        **Key Attack Vectors Discovered:**
        - <primary_attack_vector_1>
        - <primary_attack_vector_2>
        - <primary_attack_vector_3>

        **Information Disclosure Summary:**
        - <information_disclosure_type_1>: <count> instances
        - <information_disclosure_type_2>: <count> instances

        **Overall Risk Rating**: <overall_risk_level>

        ---

        ## 2. Attack Vector Analysis

        <If no attack vectors found: "No exploitable attack vectors were identified during this assessment.">

        ### Parameter Injection Opportunities

        #### AV-001: <Category> - <URL>
        - **Discovery Type**: Attack Vector
        - **Classification**: <Web Page/File>
        - **Category**: <One of 26 Pydantic categories>
        - **Severity**: <Critical/High/Medium/Low/Info>
        - **Description**: <Detailed security implications>
        - **Test Method**: <Specific testing approach>
        - **Mitigation**: <Recommended remediation steps>
        - **False Positive**: <true/false> - <reason if applicable>
        - **Manual Testing**:
          - Tool: <recommended_tool>
          - Command: `<specific_command_or_payload>`

        ### Administrative Interface Exposure

        #### AV-002: <Category> - <URL>
        - **Discovery Type**: Attack Vector
        - **Classification**: <Web Page/File>
        - **Category**: Admin Panel
        - **Severity**: <Critical/High/Medium/Low/Info>
        - **Description**: <Detailed security implications>
        - **Test Method**: <Specific testing approach>
        - **Mitigation**: <Recommended remediation steps>
        - **False Positive**: <true/false> - <reason if applicable>

        ---

        ## 3. Information Disclosure Assessment

        <If no information disclosure found: "No sensitive information exposure was identified.">

        ### Sensitive Data Exposure

        #### ID-001: <Category> - <URL>
        - **Discovery Type**: Vulnerability
        - **Classification**: <Web Page/File>
        - **Category**: <Sensitive Data Exposure/Token Exposure/Configuration Files/etc>
        - **Severity**: <Critical/High/Medium/Low/Info>
        - **Description**: <Detailed security implications>
        - **Test Method**: <How to verify this vulnerability>
        - **Mitigation**: <Specific remediation steps>
        - **False Positive**: <true/false> - <reason if applicable>
        - **Content Preview**: `<sample_content_from_file>`
        - **Accessibility**: <publicly_accessible/authentication_required>

        ### Configuration & Source Code Leakage

        #### ID-002: <Category> - <URL>
        - **Discovery Type**: Vulnerability
        - **Classification**: <Web Page/File>
        - **Category**: <Configuration Files/Backup Files/Information Disclosure>
        - **Severity**: <Critical/High/Medium/Low/Info>
        - **Description**: <Detailed security implications>
        - **Test Method**: <How to verify this vulnerability>
        - **Mitigation**: <Specific remediation steps>
        - **False Positive**: <true/false> - <reason if applicable>
        - **Content Sample**:
          ```
          <actual_code_or_config_snippet>
          ```

        ---

        ## 4. Technical Findings

        ### Detailed Vulnerability Analysis

        For each finding, provide comprehensive technical details:

        #### <Finding_ID>: <Category> - <URL>
        - **Discovery Type**: <Vulnerability/Attack Vector>
        - **Classification**: <Web Page/File>
        - **Category**: <One of 26 categories from Pydantic model>
        - **Severity**: <Critical/High/Medium/Low/Info>
        - **Description**: <Comprehensive explanation of the security issue>
        - **Test Method**: <Step-by-step verification process>
        - **Mitigation**: <Detailed remediation recommendations>
        - **False Positive**: <true/false>
        - **FP Reason**: <If false positive, explain why>
        - **Impact Analysis**: <Potential business and technical impact>
        - **Exploitation Scenario**: <How this could be exploited>

        ---

        ## 5. Risk Prioritization Matrix

        | Finding ID | Category | Discovery Type | Severity | Exploitability | Business Impact | Priority |
        |------------|----------|----------------|----------|----------------|-----------------|----------|
        | AV-001 | <category> | Attack Vector | [CRITICAL] | Easy | High | 1 |
        | ID-001 | <category> | Vulnerability | [HIGH] | N/A | Medium | 2 |
        | AV-002 | <category> | Attack Vector | [MEDIUM] | Medium | Low | 3 |

        ### Testing Priority Recommendations

        #### Immediate Actions (Week 1)
        1. **<Finding_ID>**: <specific_manual_test_with_tools>
        2. **<Finding_ID>**: <specific_manual_test_with_tools>

        #### Secondary Testing (Week 2)
        1. **<Finding_ID>**: <specific_manual_test_with_tools>
        2. **<Finding_ID>**: <specific_manual_test_with_tools>

        ### Testing Tools & Commands
        ```bash
        # For SQL Injection testing
        sqlmap -u "<url_with_parameter>" --dbs --batch

        # For XSS testing
        xsstrike -u "<url_with_parameter>" --crawl

        # For directory brute-forcing
        ffuf -u "<url>/FUZZ" -w /usr/share/wordlists/dirb/common.txt

        # For parameter fuzzing
        ffuf -u "<url>?FUZZ=test" -w /usr/share/wordlists/burp-parameter-names.txt
        ```

        ### Burp Suite Extensions
        - **Param Miner**: For discovering hidden parameters
        - **Autorize**: For testing authorization bypass
        - **Logger++**: For comprehensive request/response logging

        ---

        *This report provides reconnaissance intelligence for authorized security testing only.*
        """,
        agent=agents[2],
    )
    return [task1, task2, task3]

