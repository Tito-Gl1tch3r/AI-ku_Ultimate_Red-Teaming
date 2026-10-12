const SECRET_PATTERNS: Record<string, RegExp> = {
  // REST-like endpoints in strings, e.g., "/api/users", "auth/login"
  api_route: /['"`](\/[a-zA-Z0-9-_\/:.]+)['"`]/g,

  // Fetch / Axios calls with URL paths
  fetch_url: /fetch\(\s*['"`](\/[a-zA-Z0-9-_\/:.?=&]+)['"`]/g,
  axios_url:
    /axios\.(get|post|put|delete|patch)\(\s*['"`](\/[a-zA-Z0-9-_\/:.?=&]+)['"`]/gi,

  // Express-style routes in JS code, e.g., app.get("/login", ...)
  express_route:
    /\.(get|post|put|delete|patch|all)\(\s*['"`](\/[a-zA-Z0-9-_\/:.?=&]*)['"`]/gi,

  // Vue / React Router paths, e.g., path: '/home', component: Home
  router_path: /path\s*:\s*['"`](\/[a-zA-Z0-9-_\/:.?=&]*)['"`]/gi,

  // Generic URL strings in JS (excluding SVG URLs)

  url_string:
    /['"`](https?:\/\/(?!www\.w3\.org)[a-zA-Z0-9\-._~:/?#[\]@!$&'()*+,;=]+)['"`]/g,

  // WebSocket endpoints
  ws_url: /['"`]wss?:\/\/[a-zA-Z0-9\-._~:/?#[\]@!$&'()*+,;=]+['"`]/g,

  // Cloud providers
  aws_access_key_id: /AKIA[0-9A-Z]{16}/g,
  aws_secret_access_key_like:
    /(?<![A-Za-z0-9])(?:aws_secret_access_key|aws_secret|AWS_SECRET)[\s:=]+['"]?[A-Za-z0-9/+=]{40,}['"]?/gi,
  aws_session_token:
    /(?:aws_session_token|x-amz-security-token)[\s:=]+['"]?[A-Za-z0-9/+=]{100,}['"]?/gi,

  // Google / Firebase
  google_api_key: /AIza[0-9A-Za-z\-_]{35}/g,
  gcp_service_account:
    /"type":\s*"service_account"|"private_key":\s*"-----BEGIN PRIVATE KEY-----/g,
  firebase_server_key: /AAAA[0-9A-Za-z\-_]{7,}/g, // weak but catches many Firebase server keys

  // Git host tokens
  github_token: /gh[pousr]_[A-Za-z0-9_]{36,}/g, // ghp_, gho_, ghu_, ghs_, ghr_
  gitlab_token: /glpat-[A-Za-z0-9]{20,}/g,
  bitbucket_app_password: /[a-z0-9]{6,}:[A-Za-z0-9_\-]{40,}/gi, // heuristic

  // Stripe
  stripe_secret: /sk_(live|test)_[0-9a-zA-Z]{24,}/g,
  stripe_publishable: /pk_(live|test)_[0-9a-zA-Z]{24,}/g,

  // Twilio
  twilio_sid: /AC[0-9a-f]{32}/g,
  twilio_auth:
    /(?:TWILIO_AUTH_TOKEN|auth_token)[\s:=]+['"]?[0-9a-f]{32,}['"]?/gi,
  twilio_api_key: /SK[0-9a-f]{32}/g,

  // Slack
  slack_token: /xox[baprs]-[A-Za-z0-9-]{10,}/g, // xoxp, xoxb, xoxa, xoxr, xoxa
  slack_webhook:
    /https?:\/\/hooks\.slack\.com\/services\/[A-Z0-9]{9,}\/[A-Z0-9]{9,}\/[A-Za-z0-9]{24,}/g,

  // SendGrid / Mailgun / Mandrill
  sendgrid: /SG\.[A-Za-z0-9\-_]{20,}/g,
  mailgun_api_key: /key-[0-9a-zA-Z]{32,}/g,
  mandrill_key: /mandrill_key['"]?\s*[:=]\s*['"][0-9a-f]{32,}['"]/gi,

  // Datadog, Sentry, NewRelic, Honeybadger
  datadog_api_key: /[0-9a-f]{32}/g, // be cautious: generic
  sentry_dsn: /https?:\/\/[0-9a-f]{32}@[^\/]+\/\d+/g,
  newrelic_license: /NRAA-[0-9a-f]{24,}/g, // heuristic

  // Database connection strings (common patterns)
  mongodb_uri: /mongodb(?:\+srv)?:\/\/[^:\s]+:[^@\s]+@[^\/\s]+\/?[^\s'"]*/g,
  postgres_uri: /postgres(?:ql)?:\/\/[^:\s]+:[^@\s]+@[^\/\s]+\/?[^\s'"]*/g,
  redis_url: /redis:\/\/(?:[^:\s]+:[^@\s]+@)?[^\/\s:]+(?::\d+)?/g,

  // JWT (already suggested)
  jwt: /eyJ[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+/g,

  // OAuth & generic bearer tokens
  bearer_token_like: /Bearer\s+[A-Za-z0-9\-._~+/]+=*/gi,
  oauth_token_var:
    /(?:oauth|access|refresh|id)?[_-]?(?:token|secret)['"]?\s*[:=]\s*['"][A-Za-z0-9\-_\.]{8,}['"]/gi,

  // Generic tokens and keys (heuristics)
  generic_api_key_assignment:
    /(?:api_key|apikey|apiKey|secret|client_secret|private_key|auth_token|access_token)['"]?\s*[:=]\s*['"][A-Za-z0-9\-_\.\/+]{8,}['"]/gi,
  long_base64: /['"]([A-Za-z0-9+\/]{40,}={0,2})['"]/g, // long base64 strings in quotes

  // Payment / PCI-like
  paypal_braintree_token: /production_[0-9a-z]{16,}/gi,

  // Private key blocks
  rsa_private_key:
    /-----BEGIN (?:RSA )?PRIVATE KEY-----[\s\S]+?-----END (?:RSA )?PRIVATE KEY-----/g,
  ssh_private_key:
    /-----BEGIN OPENSSH PRIVATE KEY-----[\s\S]+?-----END OPENSSH PRIVATE KEY-----/g,
  pgp_private_key:
    /-----BEGIN PGP PRIVATE KEY BLOCK-----[\s\S]+?-----END PGP PRIVATE KEY BLOCK-----/g,

  // Basic auth in URLs
  basic_auth_in_url: /https?:\/\/[^\/\s:@]+:[^\/\s:@]+@[^\/\s]+/g,

  // Common service IDs (heuristics)
  sentry_public_key: /\b[0-9a-f]{32}\b/g,
  //uuid_like: /\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\b/gi,

  telegram_bot_token: /[0-9]{9,}:[A-Za-z0-9_-]{35}/g
}
export { SECRET_PATTERNS }
