// Rules partially based on https://github.com/gitleaks/gitleaks/blob/master/config/gitleaks.toml

export const secretRules = [
	{
		id: "1password-secret-key",
		description:
			"Uncovered a possible 1Password secret key, potentially compromising access to secrets in vaults.",
		regex:
			/\bA3-[A-Z0-9]{6}-(?:(?:[A-Z0-9]{11})|(?:[A-Z0-9]{6}-[A-Z0-9]{5}))-[A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5}\b/g,
		entropy: 3.8,
		group: 0,
	},
	{
		id: "1password-service-account-token",
		description:
			"Uncovered a possible 1Password service account token, potentially compromising access to secrets in vaults.",
		regex: /\bops_eyJ[a-zA-Z0-9+\/]{250,}={0,3}/g,
		entropy: 4,
		group: 0,
	},
	{
		id: "adafruit-api-key",
		description:
			"Identified a potential Adafruit API Key, which could lead to unauthorized access to Adafruit services and sensitive data exposure.",
		regex:
			/[\w.-]{0,50}?(?:adafruit)(?:[ \t\w.-]{0,20})[\s'"]{0,3}(?:=|>|:{1,3}=|\|\||:|=>|\?=|,)[\x60'"\s=]{0,5}([a-z0-9_-]{32})(?:[\x60'"\s;]|[\n\r]|$)/gi,
		group: 1,
	},
	{
		id: "adobe-client-id",
		description:
			"Detected a pattern that resembles an Adobe OAuth Web Client ID, posing a risk of compromised Adobe integrations and data breaches.",
		regex:
			/[\w.-]{0,50}?(?:adobe)(?:[ \t\w.-]{0,20})[\s'"]{0,3}(?:=|>|:{1,3}=|\|\||:|=>|\?=|,)[\x60'"\s=]{0,5}([a-f0-9]{32})(?:[\x60'"\s;]|[\n\r]|$)/gi,
		entropy: 2,
		group: 1,
	},
	{
		id: "adobe-client-secret",
		description:
			"Discovered a potential Adobe Client Secret, which, if exposed, could allow unauthorized Adobe service access and data manipulation.",
		regex: /\b(p8e-[a-z0-9]{32})(?:[\x60'"\s;]|[\n\r]|$)/gi,
		entropy: 2,
		group: 1,
	},
	{
		id: "age-secret-key",
		description:
			"Discovered a potential Age encryption tool secret key, risking data decryption and unauthorized access to sensitive information.",
		regex: /\bAGE-SECRET-KEY-1[QPZRY9X8GF2TVDW0S3JN54KHCE6MUA7L]{58}\b/g,
		group: 0,
	},
	{
		id: "airtable-api-key",
		description:
			"Uncovered a possible Airtable API Key, potentially compromising database access and leading to data leakage or alteration.",
		regex:
			/[\w.-]{0,50}?(?:airtable)(?:[ \t\w.-]{0,20})[\s'"]{0,3}(?:=|>|:{1,3}=|\|\||:|=>|\?=|,)[\x60'"\s=]{0,5}([a-z0-9]{17})(?:[\x60'"\s;]|[\n\r]|$)/gi,
		group: 1,
	},
	{
		id: "algolia-api-key",
		description:
			"Identified an Algolia API Key, which could result in unauthorized search operations and data exposure on Algolia-managed platforms.",
		regex:
			/[\w.-]{0,50}?(?:algolia)(?:[ \t\w.-]{0,20})[\s'"]{0,3}(?:=|>|:{1,3}=|\|\||:|=>|\?=|,)[\x60'"\s=]{0,5}([a-z0-9]{32})(?:[\x60'"\s;]|[\n\r]|$)/gi,
		group: 1,
	},
	{
		id: "alibaba-access-key-id",
		description:
			"Detected an Alibaba Cloud AccessKey ID, posing a risk of unauthorized cloud resource access and potential data compromise.",
		regex: /\b(LTAI[a-z0-9]{20})\b/gi,
		entropy: 2,
		group: 1,
	},
	{
		id: "alibaba-secret-key",
		description:
			"Discovered a potential Alibaba Cloud Secret Key, potentially allowing unauthorized operations and data access within Alibaba Cloud.",
		regex:
			/[\w.-]{0,50}?(?:alibaba)(?:[ \t\w.-]{0,20})[\s'"]{0,3}(?:=|>|:{1,3}=|\|\||:|=>|\?=|,)[\x60'"\s=]{0,5}([a-z0-9]{30})(?:[\x60'"\s;]|[\n\r]|$)/gi,
		entropy: 2,
		group: 1,
	},
	{
		id: "anthropic-admin-api-key",
		description:
			"Detected an Anthropic Admin API Key, risking unauthorized access to administrative functions and sensitive AI model configurations.",
		regex: /\b(sk-ant-admin01-[a-zA-Z0-9_\-]{93}AA)\b/g,
		group: 1,
	},
	{
		id: "anthropic-api-key",
		description:
			"Identified an Anthropic API Key, which may compromise AI assistant integrations and expose sensitive data to unauthorized access.",
		regex: /\b(sk-ant-api03-[a-zA-Z0-9_\-]{93}AA)\b/g,
		group: 1,
	},
	{
		id: "artifactory-api-key",
		description:
			"Detected an Artifactory api key, posing a risk unauthorized access to the central repository.",
		regex: /\bAKCp[A-Za-z0-9]{69}\b/g,
		entropy: 4.5,
		group: 0,
	},
	{
		id: "artifactory-reference-token",
		description:
			"Detected an Artifactory reference token, posing a risk of impersonation and unauthorized access to the central repository.",
		regex: /\bcmVmd[A-Za-z0-9]{59}\b/g,
		entropy: 4.5,
		group: 0,
	},
	{
		id: "asana-client-id",
		description:
			"Discovered a potential Asana Client ID, risking unauthorized access to Asana projects and sensitive task information.",
		regex:
			/[\w.-]{0,50}?(?:asana)(?:[ \t\w.-]{0,20})[\s'"]{0,3}(?:=|>|:{1,3}=|\|\||:|=>|\?=|,)[\x60'"\s=]{0,5}([0-9]{16})(?:[\x60'"\s;]|[\n\r]|$)/gi,
		group: 1,
	},
	{
		id: "asana-client-secret",
		description:
			"Identified an Asana Client Secret, which could lead to compromised project management integrity and unauthorized access.",
		regex:
			/[\w.-]{0,50}?(?:asana)(?:[ \t\w.-]{0,20})[\s'"]{0,3}(?:=|>|:{1,3}=|\|\||:|=>|\?=|,)[\x60'"\s=]{0,5}([a-z0-9]{32})(?:[\x60'"\s;]|[\n\r]|$)/gi,
		group: 1,
	},
	{
		id: "atlassian-api-token",
		description:
			"Detected an Atlassian API token, posing a threat to project management and collaboration tool security and data confidentiality.",
		regex:
			/[\w.-]{0,50}?(?:atlassian|confluence|jira)(?:[ \t\w.-]{0,20})[\s'"]{0,3}(?:=|>|:{1,3}=|\|\||:|=>|\?=|,)[\x60'"\s=]{0,5}([a-z0-9]{20}[a-f0-9]{4})(?:[\x60'"\s;]|[\n\r]|$)|(\bATATT3[A-Za-z0-9_\-=]{186}\b)/gi,
		entropy: 3.5,
		group: 0,
	},
	{
		id: "authress-service-client-access-key",
		description:
			"Uncovered a possible Authress Service Client Access Key, which may compromise access control services and sensitive data.",
		regex:
			/\b((?:sc|ext|scauth|authress)_[a-zA-Z0-9]{5,30}\.[a-z0-9]{4,6}\.acc[_-][a-z0-9-]{10,32}\.[a-z0-9+\/_=-]{30,120})\b/g,
		entropy: 2,
		group: 1,
	},
	{
		id: "aws-access-token",
		description:
			"Identified a pattern that may indicate AWS credentials, risking unauthorized cloud resource access and data breaches on AWS platforms.",
		regex: /\b((?:A3T[A-Z0-9]|AKIA|ASIA|ABIA|ACCA)[A-Z2-7]{16})\b/g,
		entropy: 3,
		group: 1,
	},
	{
		id: "azure-ad-client-secret",
		description: "Azure AD Client Secret",
		regex:
			/(?:^|['"`\s>=:(,])([a-zA-Z0-9_~.]{3}\dQ~[a-zA-Z0-9_~.-]{31,34})(?:$|['"`\s<),])/g,
		entropy: 3,
		group: 1,
	},
	{
		id: "beamer-api-token",
		description:
			"Detected a Beamer API token, potentially compromising content management and exposing sensitive notifications and updates.",
		regex:
			/[\w.-]{0,50}?(?:beamer)(?:[ \t\w.-]{0,20})[\s'"]{0,3}(?:=|>|:{1,3}=|\|\||:|=>|\?=|,)[\x60'"\s=]{0,5}(b_[a-z0-9=_\-]{44})(?:[\x60'"\s;]|[\n\r]|$)/gi,
		group: 1,
	},
	{
		id: "bitbucket-client-id",
		description:
			"Discovered a potential Bitbucket Client ID, risking unauthorized repository access and potential codebase exposure.",
		regex:
			/[\w.-]{0,50}?(?:bitbucket)(?:[ \t\w.-]{0,20})[\s'"]{0,3}(?:=|>|:{1,3}=|\|\||:|=>|\?=|,)[\x60'"\s=]{0,5}([a-z0-9]{32})(?:[\x60'"\s;]|[\n\r]|$)/gi,
		group: 1,
	},
	{
		id: "bitbucket-client-secret",
		description:
			"Discovered a potential Bitbucket Client Secret, posing a risk of compromised code repositories and unauthorized access.",
		regex:
			/[\w.-]{0,50}?(?:bitbucket)(?:[ \t\w.-]{0,20})[\s'"]{0,3}(?:=|>|:{1,3}=|\|\||:|=>|\?=|,)[\x60'"\s=]{0,5}([a-z0-9=_\-]{64})(?:[\x60'"\s;]|[\n\r]|$)/gi,
		group: 1,
	},
	{
		id: "cisco-meraki-api-key",
		description:
			"Cisco Meraki is a cloud-managed IT solution that provides networking, security, and device management through an easy-to-use interface.",
		regex:
			/[\w.-]{0,50}?(?:meraki)(?:[ \t\w.-]{0,20})[\s'"]{0,3}(?:=|>|:{1,3}=|\|\||:|=>|\?=|,)[\x60'"\s=]{0,5}([0-9a-f]{40})(?:[\x60'"\s;]|[\n\r]|$)/gi,
		entropy: 3,
		group: 1,
	},
	{
		id: "clickhouse-cloud-api-secret-key",
		description:
			"Identified a pattern that may indicate clickhouse cloud API secret key, risking unauthorized clickhouse cloud api access and data breaches on ClickHouse Cloud platforms.",
		regex: /\b(4b1d[A-Za-z0-9]{38})\b/g,
		entropy: 3,
		group: 1,
	},
	{
		id: "clojars-api-token",
		description:
			"Uncovered a possible Clojars API token, risking unauthorized access to Clojure libraries and potential code manipulation.",
		regex: /\bCLOJARS_[a-z0-9]{60}\b/gi,
		entropy: 2,
		group: 0,
	},
	{
		id: "cloudflare-origin-ca-key",
		description:
			"Detected a Cloudflare Origin CA Key, potentially compromising cloud application deployments and operational security.",
		regex: /\b(v1\.0-[a-f0-9]{24}-[a-f0-9]{146})\b/g,
		entropy: 2,
		group: 1,
	},
	{
		id: "databricks-api-token",
		description:
			"Uncovered a Databricks API token, which may compromise big data analytics platforms and sensitive data processing.",
		regex: /\b(dapi[a-f0-9]{32}(?:-\d)?)\b/g,
		entropy: 3,
		group: 1,
	},
	{
		id: "digitalocean-access-token",
		description:
			"Found a DigitalOcean OAuth Access Token, risking unauthorized cloud resource access and data compromise.",
		regex: /\b(doo_v1_[a-f0-9]{64})\b/g,
		entropy: 3,
		group: 1,
	},
	{
		id: "digitalocean-pat",
		description:
			"Discovered a DigitalOcean Personal Access Token, posing a threat to cloud infrastructure security and data privacy.",
		regex: /\b(dop_v1_[a-f0-9]{64})\b/g,
		entropy: 3,
		group: 1,
	},
	{
		id: "digitalocean-refresh-token",
		description:
			"Uncovered a DigitalOcean OAuth Refresh Token, which could allow prolonged unauthorized access and resource manipulation.",
		regex: /\b(dor_v1_[a-f0-9]{64})\b/gi,
		group: 1,
	},
	{
		id: "doppler-api-token",
		description:
			"Discovered a Doppler API token, posing a risk to environment and secrets management security.",
		regex: /\bdp\.pt\.[a-z0-9]{43}\b/gi,
		entropy: 2,
		group: 0,
	},
	{
		id: "dropbox-short-lived-api-token",
		description:
			"Discovered a Dropbox short-lived API token, posing a risk of temporary but potentially harmful data access and manipulation.",
		regex:
			/[\w.-]{0,50}?(?:dropbox)(?:[ \t\w.-]{0,20})[\s'"]{0,3}(?:=|>|:{1,3}=|\|\||:|=>|\?=|,)[\x60'"\s=]{0,5}(sl\.[a-z0-9\-=_]{135})(?:[\x60'"\s;]|[\n\r]|$)/gi,
		group: 1,
	},
	{
		id: "duffel-api-token",
		description:
			"Uncovered a Duffel API token, which may compromise travel platform integrations and sensitive customer data.",
		regex: /\bduffel_(?:test|live)_[a-z0-9_\-=]{43}\b/gi,
		entropy: 2,
		group: 0,
	},
	{
		id: "dynatrace-api-token",
		description:
			"Detected a Dynatrace API token, potentially risking application performance monitoring and data exposure.",
		regex: /\bdt0c01\.[a-z0-9]{24}\.[a-z0-9]{64}\b/gi,
		entropy: 4,
		group: 0,
	},
	{
		id: "easypost-api-token",
		description:
			"Identified an EasyPost API token, which could lead to unauthorized postal and shipment service access and data exposure.",
		regex: /\bEZAK[a-z0-9]{54}\b/gi,
		entropy: 2,
		group: 0,
	},
	{
		id: "easypost-test-api-token",
		description:
			"Detected an EasyPost test API token, risking exposure of test environments and potentially sensitive shipment data.",
		regex: /\bEZTK[a-z0-9]{54}\b/gi,
		entropy: 2,
		group: 0,
	},
	{
		id: "facebook-access-token",
		description:
			"Discovered a Facebook Access Token, posing a risk of unauthorized access to Facebook accounts and personal data exposure.",
		regex: /\b(\d{15,16}(?:\||%)[0-9a-z\-_]{27,40})\b/gi,
		entropy: 3,
		group: 1,
	},
	{
		id: "facebook-page-access-token",
		description:
			"Discovered a Facebook Page Access Token, posing a risk of unauthorized access to Facebook accounts and personal data exposure.",
		regex: /\b(EAA[MC][a-z0-9]{100,})\b/gi,
		entropy: 4,
		group: 1,
	},
	{
		id: "flyio-access-token",
		description: "Uncovered a Fly.io API key",
		regex:
			/\b(fo1_[\w-]{43}|fm1[ar]_[a-zA-Z0-9+\/]{100,}={0,3}|fm2_[a-zA-Z0-9+\/]{100,}={0,3})\b/g,
		entropy: 4,
		group: 1,
	},
	{
		id: "frameio-api-token",
		description:
			"Found a Frame.io API token, potentially compromising video collaboration and project management.",
		regex: /\bfio-u-[a-z0-9\-_=]{64}\b/gi,
		group: 0,
	},
	{
		id: "gcp-api-key",
		description:
			"Uncovered a GCP API key, which could lead to unauthorized access to Google Cloud services and data breaches.",
		regex: /\b(AIza[\w-]{35})\b/g,
		entropy: 4,
		group: 1,
	},
	{
		id: "generic-api-key",
		description:
			"Detected a Generic API Key, potentially exposing access to various services and sensitive operations.",
		regex:
			/[\w.-]{0,50}?(?:access|auth|api|credential|creds|passw(?:or)?d|secret|token)(?:[ \t\w.-]{0,20})[\s'"]{0,3}(?:=|>|:{1,3}=|\|\||:|=>|\?=|,)[\x60'"\s=]{0,5}([\w.=-]{10,150}|[a-z0-9][a-z0-9+\/]{11,}={0,3})(?:[\x60'"\s;&<>,]|[\n\r]|$)/gi,
		entropy: 4.3,
		group: 1,
	},
	{
		id: "github-app-token",
		description:
			"Identified a GitHub App Token, which may compromise GitHub application integrations and source code security.",
		regex: /\b(ghu|ghs)_[0-9a-zA-Z]{36}\b/g,
		entropy: 3,
		group: 0,
	},
	{
		id: "github-fine-grained-pat",
		description:
			"Found a GitHub Fine-Grained Personal Access Token, risking unauthorized repository access and code manipulation.",
		regex: /\bgithub_pat_\w{82}\b/g,
		entropy: 3,
		group: 0,
	},
	{
		id: "github-oauth",
		description:
			"Discovered a GitHub OAuth Access Token, posing a risk of compromised GitHub account integrations and data leaks.",
		regex: /\bgho_[0-9a-zA-Z]{36}\b/g,
		entropy: 3,
		group: 0,
	},
	{
		id: "github-pat",
		description:
			"Uncovered a GitHub Personal Access Token, potentially leading to unauthorized repository access and sensitive content exposure.",
		regex: /\bghp_[0-9a-zA-Z]{36}\b/g,
		entropy: 3,
		group: 0,
	},
	{
		id: "github-refresh-token",
		description:
			"Detected a GitHub Refresh Token, which could allow prolonged unauthorized access to GitHub services.",
		regex: /\bghr_[0-9a-zA-Z]{36}\b/g,
		entropy: 3,
		group: 0,
	},
	{
		id: "gitlab-cicd-job-token",
		description:
			"Identified a GitLab CI/CD Job Token, potential access to projects and some APIs on behalf of a user while the CI job is running.",
		regex: /\bglcbt-[0-9a-zA-Z]{1,5}_[0-9a-zA-Z_-]{20}\b/g,
		entropy: 3,
		group: 0,
	},
	{
		id: "gitlab-deploy-token",
		description:
			"Identified a GitLab Deploy Token, risking access to repositories, packages and containers with write access.",
		regex: /\bgldt-[0-9a-zA-Z_\-]{20}\b/g,
		entropy: 3,
		group: 0,
	},
	{
		id: "gitlab-feature-flag-client-token",
		description:
			"Identified a GitLab feature flag client token, risks exposing user lists and features flags used by an application.",
		regex: /\bglffct-[0-9a-zA-Z_\-]{20}\b/g,
		entropy: 3,
		group: 0,
	},
	{
		id: "gitlab-feed-token",
		description:
			"Identified a GitLab feed token, risking exposure of user data.",
		regex: /\bglft-[0-9a-zA-Z_\-]{20}\b/g,
		entropy: 3,
		group: 0,
	},
	{
		id: "gitlab-incoming-mail-token",
		description:
			"Identified a GitLab incoming mail token, risking manipulation of data sent by mail.",
		regex: /\bglimt-[0-9a-zA-Z_\-]{25}\b/g,
		entropy: 3,
		group: 0,
	},
	{
		id: "gitlab-kubernetes-agent-token",
		description:
			"Identified a GitLab Kubernetes Agent token, risking access to repos and registry of projects connected via agent.",
		regex: /\bglagent-[0-9a-zA-Z_\-]{50}\b/g,
		entropy: 3,
		group: 0,
	},
	{
		id: "gitlab-oauth-app-secret",
		description:
			"Identified a GitLab OIDC Application Secret, risking access to apps using GitLab as authentication provider.",
		regex: /\bgloas-[0-9a-zA-Z_\-]{64}\b/g,
		entropy: 3,
		group: 0,
	},
	{
		id: "gitlab-pat",
		description:
			"Identified a GitLab Personal Access Token, risking unauthorized access to GitLab repositories and codebase exposure.",
		regex: /\bglpat-[\w-]{20}\b/g,
		entropy: 3,
		group: 0,
	},
	{
		id: "gitlab-pat-routable",
		description:
			"Identified a GitLab Personal Access Token (routable), risking unauthorized access to GitLab repositories and codebase exposure.",
		regex: /\bglpat-[0-9a-zA-Z_-]{27,300}\.[0-9a-z]{2}[0-9a-z]{7}\b/g,
		entropy: 4,
		group: 0,
	},
	{
		id: "gitlab-ptt",
		description:
			"Found a GitLab Pipeline Trigger Token, potentially compromising continuous integration workflows and project security.",
		regex: /\bglptt-[0-9a-f]{40}\b/g,
		entropy: 3,
		group: 0,
	},
	{
		id: "gitlab-rrt",
		description:
			"Discovered a GitLab Runner Registration Token, posing a risk to CI/CD pipeline integrity and unauthorized access.",
		regex: /\bGR1348941[\w-]{20}\b/g,
		entropy: 3,
		group: 0,
	},
	{
		id: "gitlab-runner-authentication-token",
		description:
			"Discovered a GitLab Runner Authentication Token, posing a risk to CI/CD pipeline integrity and unauthorized access.",
		regex: /\bglrt-[0-9a-zA-Z_\-]{20}\b/g,
		entropy: 3,
		group: 0,
	},
	{
		id: "gitlab-runner-authentication-token-routable",
		description:
			"Discovered a GitLab Runner Authentication Token (Routable), posing a risk to CI/CD pipeline integrity and unauthorized access.",
		regex: /\bglrt-t\d_[0-9a-zA-Z_\-]{27,300}\.[0-9a-z]{2}[0-9a-z]{7}\b/g,
		entropy: 4,
		group: 0,
	},
	{
		id: "gitlab-scim-token",
		description:
			"Discovered a GitLab SCIM Token, posing a risk to unauthorized access for a organization or instance.",
		regex: /\bglsoat-[0-9a-zA-Z_\-]{20}\b/g,
		entropy: 3,
		group: 0,
	},
	{
		id: "gitlab-session-cookie",
		description:
			"Discovered a GitLab Session Cookie, posing a risk to unauthorized access to a user account.",
		regex: /_gitlab_session=[0-9a-z]{32}/g,
		entropy: 3,
		group: 0,
	},
	{
		id: "grafana-api-key",
		description:
			"Identified a Grafana API key, which could compromise monitoring dashboards and sensitive data analytics.",
		regex: /\b(eyJrIjoi[A-Za-z0-9]{30,400}={0,3})/gi,
		entropy: 3,
		group: 1,
	},
	{
		id: "grafana-cloud-api-token",
		description:
			"Found a Grafana cloud API token, risking unauthorized access to cloud-based monitoring services and data exposure.",
		regex: /\b(glc_[A-Za-z0-9+\/]{32,400}={0,3})\b/gi,
		entropy: 3,
		group: 1,
	},
	{
		id: "grafana-service-account-token",
		description:
			"Discovered a Grafana service account token, posing a risk of compromised monitoring services and data integrity.",
		regex: /\b(glsa_[A-Za-z0-9]{32}_[A-Fa-f0-9]{8})\b/gi,
		entropy: 3,
		group: 1,
	},
	{
		id: "harness-api-key",
		description:
			"Identified a Harness Access Token (PAT or SAT), risking unauthorized access to a Harness account.",
		regex:
			/\b(?:pat|sat)\.[a-zA-Z0-9_-]{22}\.[a-zA-Z0-9]{24}\.[a-zA-Z0-9]{20}\b/g,
		group: 0,
	},
	{
		id: "hashicorp-tf-api-token",
		description:
			"Uncovered a HashiCorp Terraform user/org API token, which may lead to unauthorized infrastructure management and security breaches.",
		regex: /\b[a-zA-Z0-9]{14}\.atlasv1\.[a-z0-9\-_=]{60,70}\b/g,
		entropy: 3.5,
		group: 0,
	},
	{
		id: "heroku-api-key-v2",
		description:
			"Detected a Heroku API Key, potentially compromising cloud application deployments and operational security.",
		regex: /\b(HRKU-AA[0-9a-zA-Z_-]{58})\b/g,
		entropy: 4,
		group: 1,
	},
	{
		id: "huggingface-access-token",
		description:
			"Discovered a Hugging Face Access token, which could lead to unauthorized access to AI models and sensitive data.",
		regex: /\b(hf_[a-z]{34})\b/gi,
		entropy: 2,
		group: 1,
	},
	{
		id: "huggingface-organization-api-token",
		description:
			"Uncovered a Hugging Face Organization API token, potentially compromising AI organization accounts and associated data.",
		regex: /\b(api_org_[a-z]{34})\b/gi,
		entropy: 2,
		group: 1,
	},
	{
		id: "infracost-api-token",
		description:
			"Detected an Infracost API Token, risking unauthorized access to cloud cost estimation tools and financial data.",
		regex: /\b(ico-[a-zA-Z0-9]{32})\b/g,
		entropy: 3,
		group: 1,
	},
	{
		id: "intra42-client-secret",
		description:
			"Found a Intra42 client secret, which could lead to unauthorized access to the 42School API and sensitive data.",
		regex: /\b(s-s4t2(?:ud|af)-[abcdef0123456789]{64})\b/gi,
		entropy: 3,
		group: 1,
	},
	{
		id: "jwt",
		description:
			"Uncovered a JSON Web Token, which may lead to unauthorized access to web applications and sensitive user data.",
		regex:
			/\b(ey[a-zA-Z0-9]{17,}\.ey[a-zA-Z0-9\/\\_-]{17,}\.(?:[a-zA-Z0-9\/\\_-]{10,}={0,2})?)\b/g,
		entropy: 3,
		group: 1,
	},
	{
		id: "linear-api-key",
		description:
			"Detected a Linear API Token, posing a risk to project management tools and sensitive task data.",
		regex: /\blin_api_[a-z0-9]{40}\b/gi,
		entropy: 2,
		group: 0,
	},
	{
		id: "maxmind-license-key",
		description: "Discovered a potential MaxMind license key.",
		regex: /\b([A-Za-z0-9]{6}_[A-Za-z0-9]{29}_mmk)\b/g,
		entropy: 4,
		group: 1,
	},
	{
		id: "microsoft-teams-webhook",
		description:
			"Uncovered a Microsoft Teams Webhook, which could lead to unauthorized access to team collaboration tools and data leaks.",
		regex: /(https:\/\/hooks\.office\.com\/webhookb2\/[a-zA-Z0-9@-]+)/g,
		group: 1,
	},
	{
		id: "notion-api-token",
		description: "Notion API token",
		regex: /\b(ntn_[0-9]{11}[A-Za-z0-9]{32}[A-Za-z0-9]{3})\b/g,
		entropy: 4,
		group: 1,
	},
	{
		id: "npm-access-token",
		description:
			"Uncovered an npm access token, potentially compromising package management and code repository access.",
		regex: /\b(npm_[a-z0-9]{36})\b/gi,
		entropy: 2,
		group: 1,
	},
	{
		id: "octopus-deploy-api-key",
		description:
			"Discovered a potential Octopus Deploy API key, risking application deployments and operational security.",
		regex: /\b(API-[A-Z0-9]{26})\b/g,
		entropy: 3,
		group: 1,
	},
	{
		id: "okta-access-token",
		description:
			"Identified an Okta Access Token, which may compromise identity management services and user authentication data.",
		regex:
			/[\w.-]{0,50}?(?:okta)(?:[ \t\w.-]{0,20})[\s'"]{0,3}(?:=|>|:{1,3}=|\|\||:|=>|\?=|,)[\x60'"\s=]{0,5}(00[\w=\-]{40})(?:[\x60'"\s;]|[\n\r]|$)/gi,
		entropy: 4,
		group: 1,
	},
	{
		id: "openai-api-key",
		description:
			"Found an OpenAI API Key, posing a risk of unauthorized access to AI services and data manipulation.",
		regex:
			/\b(sk-(?:proj|svcacct|admin)-(?:[A-Za-z0-9_-]{74}|[A-Za-z0-9_-]{58})T3BlbkFJ(?:[A-Za-z0-9_-]{74}|[A-Za-z0-9_-]{58})|sk-[a-zA-Z0-9]{20}T3BlbkFJ[a-zA-Z0-9]{20})\b/g,
		entropy: 3,
		group: 1,
	},
	{
		id: "openshift-user-token",
		description:
			"Found an OpenShift user token, potentially compromising an OpenShift/Kubernetes cluster.",
		regex: /\b(sha256~[\w-]{43})\b/g,
		entropy: 3.5,
		group: 1,
	},
	{
		id: "perplexity-api-key",
		description:
			"Detected a Perplexity API key, which could lead to unauthorized access to Perplexity AI services and data exposure.",
		regex: /\b(pplx-[a-zA-Z0-9]{48})\b/g,
		entropy: 4,
		group: 1,
	},
	{
		id: "planetscale-api-token",
		description:
			"Identified a PlanetScale API token, potentially compromising database management and operations.",
		regex: /\b(pscale_tkn_[\w=\.-]{32,64})\b/gi,
		entropy: 3,
		group: 1,
	},
	{
		id: "planetscale-oauth-token",
		description:
			"Found a PlanetScale OAuth token, posing a risk to database access control and sensitive data integrity.",
		regex: /\b(pscale_oauth_[\w=\.-]{32,64})\b/gi,
		entropy: 3,
		group: 1,
	},
	{
		id: "planetscale-password",
		description:
			"Discovered a PlanetScale password, which could lead to unauthorized database operations and data breaches.",
		regex: /\b(pscale_pw_[\w=\.-]{32,64})\b/gi,
		entropy: 3,
		group: 1,
	},
	{
		id: "postman-api-token",
		description:
			"Uncovered a Postman API token, potentially compromising API testing and development workflows.",
		regex: /\b(PMAK-[a-f0-9]{24}\-[a-f0-9]{34})\b/gi,
		entropy: 3,
		group: 1,
	},
	{
		id: "prefect-api-token",
		description:
			"Detected a Prefect API token, risking unauthorized access to workflow management and automation services.",
		regex: /\b(pnu_[a-zA-Z0-9]{36})\b/g,
		entropy: 2,
		group: 1,
	},
	{
		id: "private-key",
		description:
			"Identified a Private Key, which may compromise cryptographic security and sensitive data encryption.",
		regex:
			/-----BEGIN[ A-Z0-9_-]{0,100}PRIVATE KEY(?: BLOCK)?-----[\s\S-]{64,}?KEY(?: BLOCK)?-----/gi,
		group: 0,
	},
	{
		id: "pulumi-api-token",
		description:
			"Found a Pulumi API token, posing a risk to infrastructure as code services and cloud resource management.",
		regex: /\b(pul-[a-f0-9]{40})\b/g,
		entropy: 2,
		group: 1,
	},
	{
		id: "pypi-upload-token",
		description:
			"Discovered a PyPI upload token, potentially compromising Python package distribution and repository integrity.",
		regex: /\bpypi-AgEIcHlwaS5vcmc[\w-]{50,1000}\b/g,
		entropy: 3,
		group: 0,
	},
	{
		id: "readme-api-token",
		description:
			"Detected a Readme API token, risking unauthorized documentation management and content exposure.",
		regex: /\b(rdme_[a-z0-9]{70})\b/g,
		entropy: 2,
		group: 1,
	},
	{
		id: "rubygems-api-token",
		description:
			"Identified a Rubygem API token, potentially compromising Ruby library distribution and package management.",
		regex: /\b(rubygems_[a-f0-9]{48})\b/g,
		entropy: 2,
		group: 1,
	},
	{
		id: "scalingo-api-token",
		description:
			"Found a Scalingo API token, posing a risk to cloud platform services and application deployment security.",
		regex: /\b(tk-us-[\w-]{48})\b/g,
		entropy: 2,
		group: 1,
	},
	{
		id: "sendgrid-api-token",
		description:
			"Detected a SendGrid API token, posing a risk of unauthorized email service operations and data exposure.",
		regex: /\b(SG\.[a-z0-9=_\-\.]{66})\b/gi,
		entropy: 2,
		group: 1,
	},
	{
		id: "sendinblue-api-token",
		description:
			"Identified a Sendinblue API token, which may compromise email marketing services and subscriber data privacy.",
		regex: /\b(xkeysib-[a-f0-9]{64}\-[a-z0-9]{16})\b/gi,
		entropy: 2,
		group: 1,
	},
	{
		id: "sentry-access-token",
		description:
			"Found a Sentry.io Access Token (old format), risking unauthorized access to error tracking services and sensitive application data.",
		regex:
			/[\w.-]{0,50}?(?:sentry)(?:[ \t\w.-]{0,20})[\s'"]{0,3}(?:=|>|:{1,3}=|\|\||:|=>|\?=|,)[\x60'"\s=]{0,5}([a-f0-9]{64})(?:[\x60'"\s;]|[\n\r]|$)/gi,
		entropy: 3,
		group: 1,
	},
	{
		id: "sentry-org-token",
		description:
			"Found a Sentry.io Organization Token, risking unauthorized access to error tracking services and sensitive application data.",
		regex:
			/\bsntrys_eyJpYXQiO[a-zA-Z0-9+\/]{10,200}(?:LCJyZWdpb25fdXJs|InJlZ2lvbl91cmwi|cmVnaW9uX3VybCI6)[a-zA-Z0-9+\/]{10,200}={0,2}_[a-zA-Z0-9+\/]{43}(?:[^a-zA-Z0-9+\/]|$)/g,
		entropy: 4.5,
		group: 0,
	},
	{
		id: "sentry-user-token",
		description:
			"Found a Sentry.io User Token, risking unauthorized access to error tracking services and sensitive application data.",
		regex: /\b(sntryu_[a-f0-9]{64})\b/g,
		entropy: 3.5,
		group: 1,
	},
	{
		id: "settlemint-application-access-token",
		description: "Found a Settlemint Application Access Token.",
		regex: /\b(sm_aat_[a-zA-Z0-9]{16})\b/g,
		entropy: 3,
		group: 1,
	},
	{
		id: "settlemint-personal-access-token",
		description: "Found a Settlemint Personal Access Token.",
		regex: /\b(sm_pat_[a-zA-Z0-9]{16})\b/g,
		entropy: 3,
		group: 1,
	},
	{
		id: "settlemint-service-access-token",
		description: "Found a Settlemint Service Access Token.",
		regex: /\b(sm_sat_[a-zA-Z0-9]{16})\b/g,
		entropy: 3,
		group: 1,
	},
	{
		id: "shippo-api-token",
		description:
			"Discovered a Shippo API token, potentially compromising shipping services and customer order data.",
		regex: /\b(shippo_(?:live|test)_[a-fA-F0-9]{40})\b/g,
		entropy: 2,
		group: 1,
	},
	{
		id: "shopify-access-token",
		description:
			"Uncovered a Shopify access token, which could lead to unauthorized e-commerce platform access and data breaches.",
		regex: /\bshpat_[a-fA-F0-9]{32}\b/g,
		entropy: 2,
		group: 0,
	},
	{
		id: "shopify-custom-access-token",
		description:
			"Detected a Shopify custom access token, potentially compromising custom app integrations and e-commerce data security.",
		regex: /\bshpca_[a-fA-F0-9]{32}\b/g,
		entropy: 2,
		group: 0,
	},
	{
		id: "shopify-private-app-access-token",
		description:
			"Identified a Shopify private app access token, risking unauthorized access to private app data and store operations.",
		regex: /\bshppa_[a-fA-F0-9]{32}\b/g,
		entropy: 2,
		group: 0,
	},
	{
		id: "shopify-shared-secret",
		description:
			"Found a Shopify shared secret, posing a risk to application authentication and e-commerce platform security.",
		regex: /\bshpss_[a-fA-F0-9]{32}\b/g,
		entropy: 2,
		group: 0,
	},
	{
		id: "sidekiq-sensitive-url",
		description:
			"Uncovered a Sidekiq Sensitive URL, potentially exposing internal job queues and sensitive operation details.",
		regex:
			/https?:\/\/([a-f0-9]{8}:[a-f0-9]{8})@(?:gems.contribsys.com|enterprise.contribsys.com)(?:[\/|#|\?|:]|$)/gi,
		group: 1,
	},
	{
		id: "slack-app-token",
		description:
			"Detected a Slack App-level token, risking unauthorized access to Slack applications and workspace data.",
		regex: /\bxapp-\d-[A-Z0-9]+-\d+-[a-z0-9]+\b/gi,
		entropy: 2,
		group: 0,
	},
	{
		id: "slack-bot-token",
		description:
			"Identified a Slack Bot token, which may compromise bot integrations and communication channel security.",
		regex: /\bxoxb-[0-9]{10,13}-[0-9]{10,13}[a-zA-Z0-9-]*/g,
		entropy: 3,
		group: 0,
	},
	{
		id: "slack-config-access-token",
		description:
			"Found a Slack Configuration access token, posing a risk to workspace configuration and sensitive data access.",
		regex: /\bxoxe\.xox[bp]-\d-[A-Z0-9]{163,166}\b/gi,
		entropy: 2,
		group: 0,
	},
	{
		id: "slack-config-refresh-token",
		description:
			"Discovered a Slack Configuration refresh token, potentially allowing prolonged unauthorized access to configuration settings.",
		regex: /\bxoxe-\d-[A-Z0-9]{146}\b/gi,
		entropy: 2,
		group: 0,
	},
	{
		id: "slack-legacy-token",
		description:
			"Detected a Slack Legacy token, risking unauthorized access to older Slack integrations and user data.",
		regex: /\bxox[os]-\d+-\d+-\d+-[a-fA-F\d]+\b/g,
		entropy: 2,
		group: 0,
	},
	{
		id: "slack-webhook-url",
		description:
			"Discovered a Slack Webhook, which could lead to unauthorized message posting and data leakage in Slack channels.",
		regex:
			/https?:\/\/hooks.slack.com\/(?:services|workflows|triggers)\/[A-Za-z0-9+\/]{43,56}/g,
		group: 0,
	},
	{
		id: "sonar-api-token",
		description:
			"Uncovered a Sonar API token, potentially compromising software vulnerability scanning and code security.",
		regex:
			/[\w.-]{0,50}?(?:sonar[_.-]?(login|token))(?:[ \t\w.-]{0,20})[\s'"]{0,3}(?:=|>|:{1,3}=|\|\||:|=>|\?=|,)[\x60'"\s=]{0,5}((?:squ_|sqp_|sqa_)?[a-z0-9=_\-]{40})(?:[\x60'"\s;]|[\n\r]|$)/gi,
		group: 2,
	},
	{
		id: "sourcegraph-access-token",
		description: "Sourcegraph is a code search and navigation engine.",
		regex:
			/\b(sgp_(?:[a-fA-F0-9]{16}|local)_[a-fA-F0-9]{40}|sgp_[a-fA-F0-9]{40})\b/gi,
		entropy: 3,
		group: 1,
	},
	{
		id: "square-access-token",
		description:
			"Detected a Square Access Token, risking unauthorized payment processing and financial transaction exposure.",
		regex: /\b((?:EAAA|sq0atp-)[\w-]{22,60})\b/g,
		entropy: 2,
		group: 1,
	},
	{
		id: "stripe-access-token",
		description:
			"Found a Stripe Access Token, posing a risk to payment processing services and sensitive financial data.",
		regex: /\b((?:sk|rk)_(?:test|live|prod)_[a-zA-Z0-9]{10,99})\b/g,
		entropy: 2,
		group: 1,
	},
	{
		id: "sumologic-access-id",
		description:
			"Discovered a SumoLogic Access ID, potentially compromising log management services and data analytics integrity.",
		regex:
			/[\w.-]{0,50}?(?:sumo)(?:[ \t\w.-]{0,20})[\s'"]{0,3}(?:=|>|:{1,3}=|\|\||:|=>|\?=|,)[\x60'"\s=]{0,5}(su[a-zA-Z0-9]{12})(?:[\x60'"\s;]|[\n\r]|$)/gi,
		entropy: 3,
		group: 1,
	},
	{
		id: "twilio-api-key",
		description:
			"Found a Twilio API Key, posing a risk to communication services and sensitive customer interaction data.",
		regex: /\bSK[0-9a-fA-F]{32}\b/g,
		entropy: 3,
		group: 0,
	},
	{
		id: "typeform-api-token",
		description:
			"Uncovered a Typeform API token, which could lead to unauthorized survey management and data collection.",
		regex: /\b(tfp_[a-z0-9\-_\.=]{59})\b/gi,
		group: 1,
	},
	{
		id: "vault-batch-token",
		description:
			"Detected a Vault Batch Token, risking unauthorized access to secret management services and sensitive data.",
		regex: /\b(hvb\.[\w-]{138,300})\b/g,
		entropy: 4,
		group: 1,
	},
	{
		id: "vault-service-token",
		description:
			"Identified a Vault Service Token, potentially compromising infrastructure security and access to sensitive credentials.",
		regex: /\b((?:hvs\.[\w-]{90,120}|s\.[a-zA-Z0-9]{24}))\b/g,
		entropy: 4.3,
		group: 1,
	},
	{
		id: "azure-secret",
		description: "Azure Secret",
		regex:
			/\b(?:azure|az)[\-_]?(?:key|secret|token)[\-_]?(?:id|key|value)?["'\s:=]+([a-z0-9]{20,})/gi,
		group: 1,
	},
	{
		id: "azure-client-id",
		description: "Azure Client ID",
		// NOTE: This regex combines the original pattern with its keywords to avoid false positives.
		regex:
			/\b(?:AZURE_CLIENT_ID|azureClientId|clientId)["'\s:=]+([0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12})\b/gi,
		group: 1,
	},
	{
		id: "azure-client-secret",
		description: "Azure Client Secret",
		regex:
			/(?:AZURE_CLIENT_SECRET|azureClientSecret|clientSecret)["'\s:=]+([a-zA-Z0-9._\-]{20,})/gi,
		group: 1,
	},
	{
		id: "azure-tenant-id",
		description: "Azure Tenant ID",
		regex:
			/(?:AZURE_TENANT_ID|azureTenantId|tenantId|tenant_id)["'\s:=]+([0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12})/gi,
		group: 1,
	},
	{
		id: "rsa-private-key",
		description: "RSA Private Key",
		regex:
			/-----BEGIN RSA PRIVATE KEY-----[\s\S]*?-----END RSA PRIVATE KEY-----/g,
		group: 0,
	},
	{
		id: "slack-webhook",
		description: "Slack Webhook",
		regex:
			/https:\/\/hooks\.slack\.com\/services\/[A-Z0-9]{9,}\/[A-Z0-9]{9,}\/[a-zA-Z0-9]{24,}/g,
		group: 0,
	},
	{
		id: "pem-certificate",
		description: "PEM Certificate",
		regex: /-----BEGIN CERTIFICATE-----[\s\S]*?-----END CERTIFICATE-----/g,
		group: 0,
	},
	{
		id: "raw-bearer-token",
		description: "Raw Bearer Token",
		regex: /\bBearer\s+([A-Za-z0-9\-._~+\/=]{7,})/gi,
		entropy: 4,
		group: 1,
	},
	{
		id: "raw-basic-auth",
		description: "Raw Basic Auth Token",
		regex: /\bBasic\s+([A-Za-z0-9+\/=]{7,})/gi,
		entropy: 4,
		group: 1,
	},
	{
		id: "raw-aws-auth-header",
		description: "Raw AWS SigV4 Auth Header",
		regex:
			/\bAWS4-HMAC-SHA256\s+Credential=[^,\s]+,\s*SignedHeaders=[^,\s]+,\s*Signature=([a-f0-9]{64})/g,
		group: 1,
	},
	{
		id: "raw-oauth1-header",
		description: "Raw OAuth1 Header Value",
		regex: /\bOAuth\s+oauth_/gi,
		group: 0,
	},
];
