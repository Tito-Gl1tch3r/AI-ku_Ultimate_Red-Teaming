use clap::Parser;
use serde::{Deserialize, Serialize};
use std::collections::{HashMap, HashSet};
use std::fs::File;
use std::io::{BufRead, BufReader};
use std::net::IpAddr;
use std::time::SystemTime;
use tokio::task::JoinSet;

use crate::asn_db::AsnDb;
use crate::cloud_detector::{lookup_arin, ArinResult, CloudDetector, FirewallRule};

#[derive(Parser, Debug)]
#[command(author, version, about = "Parse and analyze collected network connections")]
pub struct ParserOpts {
    /// Input JSONL file from collector
    #[arg(long)]
    pub input: String,

    /// Generate process summary JSON
    #[arg(long)]
    pub process_summary: Option<String>,

    /// Generate cloud provider analysis
    #[arg(long)]
    pub cloud_analysis: Option<String>,

    /// Generate firewall rules (iptables format)
    #[arg(long)]
    pub firewall_rules_iptables: Option<String>,

    /// Generate firewall rules (Windows netsh format)
    #[arg(long)]
    pub firewall_rules_windows: Option<String>,

    /// Generate database export SQL
    #[arg(long)]
    pub database_export: Option<String>,

    /// Whitelist known good processes (comma-separated)
    #[arg(long)]
    pub whitelist_processes: Option<String>,

    /// Minimum connection count to include in reports
    #[arg(long, default_value_t = 1)]
    pub min_connections: usize,

    /// Microsoft Service Tags JSON file for accurate Azure service detection.
    /// Download weekly from: https://www.microsoft.com/en-us/download/details.aspx?id=56519
    #[arg(long)]
    pub ip_ranges_file: Option<String>,

    /// ARIN RDAP lookup for IPs not matched by any known cloud provider
    #[arg(long)]
    pub arin_lookup: bool,

    /// Local ip2asn TSV from iptoasn.com for instant offline ownership lookups.
    /// When provided, --arin-lookup is ignored and no network calls are made.
    ///
    /// Download:
    ///   curl -O https://iptoasn.com/data/ip2asn-v4.tsv.gz && gunzip ip2asn-v4.tsv.gz
    #[arg(long)]
    pub asn_db: Option<String>,

    /// JSON file to persist ARIN lookup results between runs.
    /// IPs already in the cache are never re-queried.
    #[arg(long)]
    pub arin_cache: Option<String>,
}

#[derive(Debug, Deserialize)]
struct ConnectionRecord {
    timestamp: Option<SystemTime>,
    pid: u32,
    process_name: String,
    protocol: String,
    remote_port: Option<u16>,
    remote_ip: String,
    remote_hostname: Option<String>,
    ppid: Option<u32>,
    command_line: Option<String>,
}

#[derive(Debug, Serialize)]
pub struct ProcessAnalysis {
    pub process_name: String,
    pub pid: u32,
    pub ppid: Option<u32>,
    pub command_line: Option<String>,
    pub service_group: Option<String>,
    pub total_connections: usize,
    pub unique_remote_ips: Vec<String>,
    pub unique_domains: Vec<String>,
    pub cloud_providers: HashMap<String, CloudProviderStats>,
    pub protocols: HashMap<String, usize>,
    pub top_ports: Vec<(u16, usize)>,
    pub risk_score: f32,
    pub connection_buckets: Vec<u32>,
    pub bucket_duration_secs: u64,
}

#[derive(Debug, Serialize)]
pub struct CloudProviderStats {
    pub connection_count: usize,
    pub unique_ips: Vec<String>,
    pub unique_domains: Vec<String>,
    pub services: HashMap<String, usize>,
}


/// Combined cloud analysis output: provider summaries + ARIN results for unknowns.
#[derive(Debug, Serialize)]
struct CloudAnalysis {
    providers: std::collections::HashMap<String, crate::cloud_detector::ProviderSummary>,
    /// IPs that didn't match any known provider, with their ARIN registration info.
    arin_results: std::collections::HashMap<String, ArinResult>,
}

pub struct ConnectionParser {
    opts: ParserOpts,
    cloud_detector: CloudDetector,
    whitelist: HashSet<String>,
    asn_db: Option<AsnDb>,
}

impl ConnectionParser {
    pub fn new(opts: ParserOpts) -> Self {
        let whitelist = opts.whitelist_processes
            .as_ref()
            .map(|w| w.split(',').map(|s| s.trim().to_lowercase()).collect())
            .unwrap_or_default();

        let mut cloud_detector = CloudDetector::new();

        if let Some(path) = &opts.ip_ranges_file {
            match cloud_detector.load_service_tags(path) {
                Ok(n) => println!("✓ Loaded {} CIDR ranges from {}", n, path),
                Err(e) => eprintln!("Warning: failed to load IP ranges file: {}", e),
            }
        }

        let asn_db = if let Some(path) = &opts.asn_db {
            match AsnDb::load(path) {
                Ok(db) => {
                    println!("✓ Loaded ASN DB: {} ranges from {}", db.len(), path);
                    Some(db)
                }
                Err(e) => {
                    eprintln!("Warning: failed to load ASN DB: {}", e);
                    None
                }
            }
        } else {
            None
        };

        ConnectionParser {
            opts,
            cloud_detector,
            whitelist,
            asn_db,
        }
    }

    pub async fn parse(&self) -> anyhow::Result<()> {
        let file = File::open(&self.opts.input)?;
        let reader = BufReader::new(file);
        
        let mut connections: Vec<ConnectionRecord> = Vec::new();
        let mut _metadata = None;
        
        for line in reader.lines() {
            let line = line?;
            if line.contains("\"_metadata\"") {
                _metadata = Some(line);
                continue;
            }
            
            if let Ok(record) = serde_json::from_str::<ConnectionRecord>(&line) {
                connections.push(record);
            }
        }
        
        println!("Loaded {} connection records", connections.len());
        
        // Group by process
        let mut process_map: HashMap<(u32, String), Vec<ConnectionRecord>> = HashMap::new();
        for conn in connections {
            let key = (conn.pid, conn.process_name.clone());
            process_map.entry(key).or_default().push(conn);
        }
        
        // Analyze each process
        let mut process_analyses = Vec::new();
        let mut all_cloud_detections = Vec::new();
        let mut all_seen_ips: HashSet<IpAddr> = HashSet::new();
        let mut all_matched_ips: HashSet<IpAddr> = HashSet::new();

        for ((pid, name), conns) in process_map.iter() {
            if conns.len() < self.opts.min_connections {
                continue;
            }

            let mut unique_ips = HashSet::new();
            let mut unique_domains = HashSet::new();
            let mut cloud_providers: HashMap<String, CloudProviderStats> = HashMap::new();
            let mut protocols: HashMap<String, usize> = HashMap::new();
            let mut port_counts: HashMap<u16, usize> = HashMap::new();
            let mut proc_ppid: Option<u32> = None;
            let mut proc_cmd: Option<String> = None;
            let mut timestamps: Vec<SystemTime> = Vec::new();

            for conn in conns {
                if proc_ppid.is_none() { proc_ppid = conn.ppid; }
                if proc_cmd.is_none() { proc_cmd = conn.command_line.clone(); }
                if let Some(ts) = conn.timestamp { timestamps.push(ts); }
                unique_ips.insert(conn.remote_ip.clone());

                if let Some(hostname) = &conn.remote_hostname {
                    unique_domains.insert(hostname.clone());
                }

                *protocols.entry(conn.protocol.clone()).or_insert(0) += 1;

                if let Some(port) = conn.remote_port {
                    *port_counts.entry(port).or_insert(0) += 1;
                }

                // Detect cloud provider
                let ip: IpAddr = conn.remote_ip.parse().unwrap_or_else(|_| "0.0.0.0".parse().unwrap());
                all_seen_ips.insert(ip);
                if let Some(detection) = self.cloud_detector.detect(&ip, conn.remote_hostname.as_deref()) {
                    all_matched_ips.insert(ip);
                    let provider_stats = cloud_providers.entry(detection.provider.name.clone())
                        .or_insert(CloudProviderStats {
                            connection_count: 0,
                            unique_ips: Vec::new(),
                            unique_domains: Vec::new(),
                            services: HashMap::new(),
                        });
                    
                    provider_stats.connection_count += 1;
                    if !provider_stats.unique_ips.contains(&conn.remote_ip) {
                        provider_stats.unique_ips.push(conn.remote_ip.clone());
                    }
                    if let Some(domain) = &conn.remote_hostname {
                        if !provider_stats.unique_domains.contains(domain) {
                            provider_stats.unique_domains.push(domain.clone());
                        }
                    }
                    if let Some(service) = &detection.provider.service {
                        *provider_stats.services.entry(service.clone()).or_insert(0) += 1;
                    }
                    
                    all_cloud_detections.push(detection);
                }
            }
            
            let mut top_ports: Vec<(u16, usize)> = port_counts.into_iter().collect();
            top_ports.sort_by(|a, b| b.1.cmp(&a.1));
            top_ports.truncate(10);

            let service_group = if name.to_lowercase() == "svchost.exe" {
                proc_cmd.as_deref().and_then(parse_service_group)
            } else {
                None
            };

            const BUCKET_SECS: u64 = 60;
            let connection_buckets = build_buckets(&timestamps, BUCKET_SECS);

            let risk_score = self.calculate_risk_score(name, &unique_ips, &cloud_providers);

            process_analyses.push(ProcessAnalysis {
                process_name: name.clone(),
                pid: *pid,
                ppid: proc_ppid,
                command_line: proc_cmd,
                service_group,
                total_connections: conns.len(),
                unique_remote_ips: unique_ips.into_iter().collect(),
                unique_domains: unique_domains.into_iter().collect(),
                cloud_providers,
                protocols,
                top_ports,
                risk_score,
                connection_buckets,
                bucket_duration_secs: BUCKET_SECS,
            });
        }
        
        // Sort by risk score
        process_analyses.sort_by(|a, b| b.risk_score.partial_cmp(&a.risk_score).unwrap());
        
        // Generate outputs
        if let Some(path) = &self.opts.process_summary {
            let json = serde_json::to_string_pretty(&process_analyses)?;
            std::fs::write(path, json)?;
            println!("✓ Written process summary to {}", path);
        }
        
        if let Some(path) = &self.opts.cloud_analysis {
            let providers = self.cloud_detector.get_provider_summary(&all_cloud_detections);
            let mut arin_results: HashMap<String, ArinResult> = HashMap::new();
            let unmatched: Vec<IpAddr> = all_seen_ips.difference(&all_matched_ips).copied().collect();

            if let Some(db) = &self.asn_db {
                // Offline path: instant O(log n) lookup, zero network calls.
                for ip in &unmatched {
                    if let Some(r) = db.lookup(ip) {
                        arin_results.insert(ip.to_string(), ArinResult {
                            handle: format!("AS{}", r.asn),
                            org_name: r.org_name.clone(),
                            cidr: String::new(),
                            country: r.country.clone(),
                        });
                    }
                }
                println!("✓ ASN DB: {} results for {} unmatched IPs", arin_results.len(), unmatched.len());
            } else if self.opts.arin_lookup {
                // Online path: load disk cache, query only misses, persist results.
                let mut cache: HashMap<String, Option<ArinResult>> = self.opts.arin_cache
                    .as_deref()
                    .and_then(|p| std::fs::read_to_string(p).ok())
                    .and_then(|s| serde_json::from_str(&s).ok())
                    .unwrap_or_default();

                let to_query: Vec<IpAddr> = unmatched.iter()
                    .filter(|ip| !cache.contains_key(&ip.to_string()))
                    .copied()
                    .collect();

                if !to_query.is_empty() {
                    println!("ARIN: querying {} uncached IPs...", to_query.len());
                    let mut set = JoinSet::new();
                    for ip in to_query {
                        set.spawn(async move { (ip, lookup_arin(&ip).await) });
                    }
                    while let Some(res) = set.join_next().await {
                        if let Ok((ip, Ok(arin))) = res {
                            cache.insert(ip.to_string(), arin);
                        }
                    }
                    if let Some(cache_path) = &self.opts.arin_cache {
                        let json = serde_json::to_string_pretty(&cache).unwrap_or_default();
                        if let Err(e) = std::fs::write(cache_path, json) {
                            eprintln!("Warning: failed to persist ARIN cache to {}: {}", cache_path, e);
                        }
                    }
                }

                for ip in &unmatched {
                    if let Some(Some(result)) = cache.get(&ip.to_string()) {
                        arin_results.insert(ip.to_string(), result.clone());
                    }
                }
                println!("✓ ARIN lookups complete: {} results", arin_results.len());
            }

            let analysis = CloudAnalysis { providers, arin_results };
            let json = serde_json::to_string_pretty(&analysis)?;
            std::fs::write(path, json)?;
            println!("✓ Written cloud analysis to {}", path);
        }
        
        if let Some(path) = &self.opts.firewall_rules_iptables {
            let rules = self.generate_firewall_rules(&process_analyses, "iptables");
            std::fs::write(path, rules)?;
            println!("✓ Written iptables rules to {}", path);
        }
        
        if let Some(path) = &self.opts.firewall_rules_windows {
            let rules = self.generate_firewall_rules(&process_analyses, "windows");
            std::fs::write(path, rules)?;
            println!("✓ Written Windows firewall rules to {}", path);
        }
        
        if let Some(path) = &self.opts.database_export {
            let sql = self.generate_sql_export(&process_analyses);
            std::fs::write(path, sql)?;
            println!("✓ Written SQL export to {}", path);
        }
        
        Ok(())
    }
    
    fn calculate_risk_score(&self, process_name: &str, ips: &HashSet<String>, providers: &HashMap<String, CloudProviderStats>) -> f32 {
        let mut score: f32 = 0.0;
        
        // Whitelisted processes get low score
        if self.whitelist.contains(&process_name.to_lowercase()) {
            return 0.1;
        }
        
        // Many unique IPs increases risk
        if ips.len() > 20 {
            score += 2.0;
        } else if ips.len() > 10 {
            score += 1.0;
        }
        
        // Unknown cloud providers increase risk
        let known_providers = ["AWS", "Azure", "GCP", "Cloudflare", "GitHub", "Microsoft"];
        for provider in providers.keys() {
            if !known_providers.contains(&provider.as_str()) {
                score += 1.5;
            }
        }
        
        // No cloud provider detected but many connections
        if providers.is_empty() && ips.len() > 5 {
            score += 2.5;
        }
        
        // Suspicious process names
        let suspicious_patterns = ["temp", "tmp", ".exe", "unknown", "python", "node", "java"];
        let name_lower = process_name.to_lowercase();
        for pattern in suspicious_patterns {
            if name_lower.contains(pattern) {
                score += 1.0;
                break;
            }
        }
        
        score.min(10.0)
    }
    
    fn generate_firewall_rules(&self, analyses: &[ProcessAnalysis], format: &str) -> String {
        let mut rules = String::new();
        
        rules.push_str("# Generated firewall rules from network analysis\n");
        rules.push_str(&format!("# Date: {:?}\n\n", SystemTime::now()));
        
        // Allow known cloud providers
        rules.push_str("# === ALLOW: Known Cloud Providers ===\n");
        let known_providers = ["AWS", "Azure", "GCP", "Cloudflare", "GitHub", "Microsoft"];
        
        for analysis in analyses {
            if self.whitelist.contains(&analysis.process_name.to_lowercase()) {
                continue;
            }
            
            for (provider, stats) in &analysis.cloud_providers {
                if known_providers.contains(&provider.as_str()) {
                    for ip in &stats.unique_ips {
                        let rule = FirewallRule {
                            direction: "OUTBOUND".to_string(),
                            action: "ALLOW".to_string(),
                            protocol: "TCP".to_string(),
                            source: "*".to_string(),
                            destination: ip.clone(),
                            port: None,
                            provider: Some(provider.clone()),
                            comment: format!("{} to {}", analysis.process_name, provider),
                        };
                        
                        if format == "iptables" {
                            rules.push_str(&format!("{}\n", rule.to_iptables()));
                        } else {
                            rules.push_str(&format!("{}\n", rule.to_windows_netsh()));
                        }
                    }
                }
            }
        }
        
        rules.push_str("\n# === MONITOR: Suspicious Processes ===\n");
        for analysis in analyses {
            if analysis.risk_score > 5.0 {
                rules.push_str(&format!("# WARNING: {} has risk score {:.1}\n", 
                    analysis.process_name, analysis.risk_score));
                rules.push_str(&format!("# Consider blocking: {:?}\n", 
                    analysis.unique_remote_ips.iter().take(5).collect::<Vec<_>>()));
            }
        }
        
        rules
    }
    
    fn generate_sql_export(&self, analyses: &[ProcessAnalysis]) -> String {
        let mut sql = String::new();

        sql.push_str("-- Network Analysis Database Export\n");
        sql.push_str("-- Create tables\n\n");

        sql.push_str("CREATE TABLE IF NOT EXISTS processes (\n");
        sql.push_str("    id INTEGER PRIMARY KEY,\n");
        sql.push_str("    pid INTEGER,\n");
        sql.push_str("    name TEXT,\n");
        sql.push_str("    total_connections INTEGER,\n");
        sql.push_str("    risk_score REAL,\n");
        sql.push_str("    analysis_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP\n");
        sql.push_str(");\n\n");

        sql.push_str("CREATE TABLE IF NOT EXISTS cloud_connections (\n");
        sql.push_str("    id INTEGER PRIMARY KEY,\n");
        sql.push_str("    process_id INTEGER,\n");
        sql.push_str("    provider TEXT,\n");
        sql.push_str("    service TEXT,\n");
        sql.push_str("    remote_ip TEXT,\n");
        sql.push_str("    remote_domain TEXT,\n");
        sql.push_str("    connection_count INTEGER,\n");
        sql.push_str("    FOREIGN KEY(process_id) REFERENCES processes(id)\n");
        sql.push_str(");\n\n");

        sql.push_str("-- Insert data\n");

        for (idx, analysis) in analyses.iter().enumerate() {
            sql.push_str(&format!(
                "INSERT INTO processes (id, pid, name, total_connections, risk_score) VALUES ({}, {}, '{}', {}, {:.2});\n",
                idx + 1,
                analysis.pid,
                escape_sql(&analysis.process_name),
                analysis.total_connections,
                analysis.risk_score
            ));

            for (provider, stats) in &analysis.cloud_providers {
                for ip in &stats.unique_ips {
                    let empty = String::new();
                    let domain = stats.unique_domains.first().unwrap_or(&empty);
                    let service = stats.services.keys().next().unwrap_or(&empty);
                    sql.push_str(&format!(
                        "INSERT INTO cloud_connections (process_id, provider, service, remote_ip, remote_domain, connection_count) VALUES ({}, '{}', '{}', '{}', '{}', {});\n",
                        idx + 1,
                        escape_sql(provider),
                        escape_sql(service),
                        escape_sql(ip),
                        escape_sql(domain),
                        stats.connection_count
                    ));
                }
            }
        }

        sql
    }
}

/// Escape a string for use in a single-quoted SQL literal by doubling single quotes.
fn escape_sql(s: &str) -> String {
    s.replace('\'', "''")
}

/// Parse the `-k <group>` service group name from an svchost.exe command line.
fn parse_service_group(cmd: &str) -> Option<String> {
    let parts: Vec<&str> = cmd.split_whitespace().collect();
    let pos = parts.iter().position(|&s| s == "-k")?;
    parts.get(pos + 1).map(|s| s.to_string())
}

/// Bucket connection timestamps into fixed-duration intervals starting from the
/// earliest observed timestamp. Returns a Vec where each element is the count
/// of connections that fell within that bucket.
fn build_buckets(timestamps: &[SystemTime], bucket_secs: u64) -> Vec<u32> {
    if timestamps.is_empty() {
        return Vec::new();
    }
    let start = timestamps.iter().copied().min().unwrap();
    let max_offset = timestamps
        .iter()
        .filter_map(|ts| ts.duration_since(start).ok())
        .map(|d| d.as_secs())
        .max()
        .unwrap_or(0);
    let num_buckets = (max_offset / bucket_secs + 1) as usize;
    let mut buckets = vec![0u32; num_buckets];
    for ts in timestamps {
        if let Ok(offset) = ts.duration_since(start) {
            let idx = (offset.as_secs() / bucket_secs) as usize;
            if idx < buckets.len() {
                buckets[idx] += 1;
            }
        }
    }
    buckets
}