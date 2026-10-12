use axum::{
    extract::{Path, State},
    http::{HeaderMap, StatusCode},
    routing::{get, post},
    Json, Router,
};
use clap::Parser;
use serde::Serialize;
use std::collections::{HashMap, HashSet};
use std::net::IpAddr;
use std::sync::{Arc, Mutex};
use std::time::SystemTime;

use crate::asn_db::AsnDb;
use crate::cloud_detector::{lookup_arin, ArinResult, CloudDetector};
use crate::collector_v2::{ConnectionRecord, UploadBatch};

// ─── CLI ─────────────────────────────────────────────────────────────────────

#[derive(Parser, Debug)]
#[command(about = "Receive and analyze data from multiple collectors")]
pub struct ServerOpts {
    /// Address to listen on
    #[arg(long, default_value = "0.0.0.0:8080")]
    pub bind: String,

    /// Required API key (sent by collectors as X-API-Key header)
    #[arg(long)]
    pub api_key: Option<String>,

    /// Microsoft Service Tags JSON for accurate Azure detection
    #[arg(long)]
    pub ip_ranges_file: Option<String>,

    /// JSON file for persisting ARIN lookup results across restarts.
    /// IPs already in the file are never re-queried.
    #[arg(long)]
    pub arin_cache: Option<String>,

    /// Local ip2asn TSV database from iptoasn.com for instant offline lookups.
    /// When provided, ARIN is never queried.
    ///
    /// Download:
    ///   curl -O https://iptoasn.com/data/ip2asn-v4.tsv.gz && gunzip ip2asn-v4.tsv.gz
    #[arg(long)]
    pub asn_db: Option<String>,
}

// ─── session storage ──────────────────────────────────────────────────────────

struct Session {
    id: String,
    hostname: String,
    first_seen_unix: u64,
    last_seen_unix: u64,
    records: Vec<ConnectionRecord>,
}

impl Session {
    fn new(hostname: String, records: Vec<ConnectionRecord>) -> Self {
        let now = unix_now();
        Session {
            id: format!("{}-{}", hostname, now),
            hostname,
            first_seen_unix: now,
            last_seen_unix: now,
            records,
        }
    }
}

fn unix_now() -> u64 {
    SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs()
}

// ─── shared state ─────────────────────────────────────────────────────────────

#[derive(Clone)]
struct AppState {
    // Keyed by hostname so batches from the same machine accumulate.
    sessions: Arc<Mutex<HashMap<String, Session>>>,
    cloud_detector: Arc<CloudDetector>,
    api_key: Option<String>,
    // IP string -> ARIN result (None = looked up, no record found).
    // Persisted to --arin-cache file so cold restarts don't re-query known IPs.
    arin_cache: Arc<Mutex<HashMap<String, Option<ArinResult>>>>,
    arin_cache_path: Option<String>,
    // When present, used instead of ARIN for all unknown IP lookups.
    asn_db: Option<Arc<AsnDb>>,
}

// ─── API types ────────────────────────────────────────────────────────────────

#[derive(Serialize)]
struct HealthResponse {
    status: &'static str,
    machines: usize,
    total_records: usize,
}

#[derive(Serialize)]
struct UploadResponse {
    session_id: String,
    records_accepted: usize,
    total_for_machine: usize,
}

#[derive(Serialize)]
pub struct SessionSummary {
    id: String,
    hostname: String,
    first_seen_unix: u64,
    last_seen_unix: u64,
    record_count: usize,
}

// ─── pattern report types ─────────────────────────────────────────────────────

/// Full analysis for one machine.
#[derive(Serialize)]
pub struct SessionAnalysis {
    pub session: SessionSummary,
    pub patterns: PatternReport,
    /// ARIN registration info for IPs not matched by any known cloud provider.
    pub arin_results: HashMap<String, ArinResult>,
}

#[derive(Serialize)]
pub struct PatternReport {
    /// Processes/IPs with suspiciously regular inter-connection timing.
    pub beaconing_candidates: Vec<BeaconingCandidate>,
    /// Hostnames whose left-most label has high Shannon entropy (possible DGA).
    pub high_entropy_hosts: Vec<HighEntropyHost>,
    /// Connections to non-standard destination ports.
    pub port_anomalies: Vec<PortAnomaly>,
    /// Processes with many connections to IPs not matched by any known cloud provider.
    pub high_freq_noncloud: Vec<HighFreqTalker>,
}

#[derive(Serialize)]
pub struct BeaconingCandidate {
    pub process: String,
    pub remote_ip: String,
    pub remote_host: Option<String>,
    /// Number of distinct appearances after deduplicating poll-adjacent timestamps.
    pub distinct_appearances: usize,
    /// Mean time between re-establishments (seconds).
    pub interval_mean_secs: f64,
    pub interval_stddev_secs: f64,
    /// Coefficient of variation (stddev/mean). Low = regular = suspicious.
    pub jitter_ratio: f64,
    pub is_known_cloud: bool,
    /// 0–10.  ≥ 5 warrants investigation.
    pub suspicion_score: f64,
}

#[derive(Serialize)]
pub struct HighEntropyHost {
    pub hostname: String,
    pub process: String,
    /// Shannon entropy of the leftmost DNS label (bits per character).
    pub entropy_bits_per_char: f64,
    pub connection_count: usize,
}

#[derive(Serialize)]
pub struct PortAnomaly {
    pub port: u16,
    pub process: String,
    pub remote_ip: String,
    pub remote_host: Option<String>,
    pub connection_count: usize,
}

#[derive(Serialize)]
pub struct HighFreqTalker {
    pub process: String,
    pub remote_ip: String,
    pub remote_host: Option<String>,
    pub connection_count: usize,
}

/// Cross-machine analysis combining all sessions.
#[derive(Serialize)]
pub struct CrossMachineReport {
    /// IPs observed on more than one machine — could indicate shared C2 or CDN.
    pub shared_ips: Vec<SharedIp>,
    /// Per-machine pattern summaries.
    pub by_machine: Vec<MachineSummary>,
    /// ARIN info for every unmatched IP seen across all machines.
    pub arin_results: HashMap<String, ArinResult>,
}

#[derive(Serialize)]
pub struct SharedIp {
    pub remote_ip: String,
    pub remote_host: Option<String>,
    pub seen_on: Vec<String>,
    pub total_connections: usize,
    pub is_known_cloud: bool,
}

#[derive(Serialize)]
pub struct MachineSummary {
    pub hostname: String,
    pub record_count: usize,
    pub beacon_count: usize,
    pub high_entropy_count: usize,
    pub noncloud_freq_count: usize,
}

// ─── server entry point ───────────────────────────────────────────────────────

pub async fn run_server(opts: ServerOpts) -> anyhow::Result<()> {
    let mut cloud_detector = CloudDetector::new();
    if let Some(path) = &opts.ip_ranges_file {
        match cloud_detector.load_service_tags(path) {
            Ok(n) => println!("✓ Loaded {} CIDR ranges from {}", n, path),
            Err(e) => eprintln!("Warning: failed to load IP ranges: {}", e),
        }
    }

    // Load persisted ARIN cache from disk if available.
    let arin_cache_initial: HashMap<String, Option<ArinResult>> =
        if let Some(path) = &opts.arin_cache {
            match std::fs::read_to_string(path) {
                Ok(json) => serde_json::from_str(&json).unwrap_or_default(),
                Err(_) => HashMap::new(),
            }
        } else {
            HashMap::new()
        };
    if !arin_cache_initial.is_empty() {
        println!(
            "✓ Loaded {} cached ARIN entries from {:?}",
            arin_cache_initial.len(),
            opts.arin_cache
        );
    }

    let asn_db = if let Some(path) = &opts.asn_db {
        match AsnDb::load(path) {
            Ok(db) => {
                println!("✓ Loaded {} ASN ranges from {} (offline lookups enabled)", db.len(), path);
                Some(Arc::new(db))
            }
            Err(e) => {
                eprintln!("Warning: failed to load ASN DB '{}': {}", path, e);
                None
            }
        }
    } else {
        None
    };

    let state = AppState {
        sessions: Arc::new(Mutex::new(HashMap::new())),
        cloud_detector: Arc::new(cloud_detector),
        api_key: opts.api_key.clone(),
        arin_cache: Arc::new(Mutex::new(arin_cache_initial)),
        arin_cache_path: opts.arin_cache.clone(),
        asn_db,
    };

    let app = Router::new()
        .route("/health", get(handle_health))
        .route("/upload", post(handle_upload))
        .route("/api/sessions", get(handle_list_sessions))
        .route("/api/sessions/:hostname", get(handle_get_session))
        .route("/api/patterns", get(handle_cross_machine))
        .with_state(state);

    let addr: std::net::SocketAddr = opts
        .bind
        .parse()
        .map_err(|e| anyhow::anyhow!("Invalid bind address '{}': {}", opts.bind, e))?;

    println!("Analysis server listening on http://{}", addr);
    println!("  POST /upload          — receive data from collectors");
    println!("  GET  /api/sessions    — list machines");
    println!("  GET  /api/sessions/:h — patterns for one machine");
    println!("  GET  /api/patterns    — cross-machine analysis");
    if opts.api_key.is_some() {
        println!("✓ API key authentication enabled");
    } else {
        println!("⚠  No API key — all uploads accepted");
    }

    let listener = tokio::net::TcpListener::bind(addr).await?;
    axum::serve(listener, app).await?;
    Ok(())
}

// ─── handlers ─────────────────────────────────────────────────────────────────

async fn handle_health(State(state): State<AppState>) -> Json<HealthResponse> {
    let sessions = state.sessions.lock().unwrap();
    let total_records: usize = sessions.values().map(|s| s.records.len()).sum();
    Json(HealthResponse {
        status: "ok",
        machines: sessions.len(),
        total_records,
    })
}

/// Returns `Err(UNAUTHORIZED)` if the state has an API key and the request
/// does not present a matching `X-API-Key` header.  When no key is configured
/// every request is allowed through.
fn check_api_key(state: &AppState, headers: &HeaderMap) -> Result<(), StatusCode> {
    if let Some(expected) = &state.api_key {
        let provided = headers
            .get("x-api-key")
            .and_then(|v| v.to_str().ok())
            .unwrap_or("");
        if provided != expected {
            return Err(StatusCode::UNAUTHORIZED);
        }
    }
    Ok(())
}

async fn handle_upload(
    State(state): State<AppState>,
    body: String,
) -> Result<Json<UploadResponse>, StatusCode> {
    // Upload is intentionally unauthenticated — agents are anonymous.
    let batch: UploadBatch =
        serde_json::from_str(&body).map_err(|_| StatusCode::BAD_REQUEST)?;

    let hostname = batch.hostname.clone();
    let incoming_count = batch.records.len();
    let session_id;
    let total_for_machine;

    {
        let mut sessions = state.sessions.lock().unwrap();
        let session = sessions
            .entry(hostname.clone())
            .or_insert_with(|| Session::new(hostname.clone(), Vec::new()));

        session.records.extend(batch.records);
        session.last_seen_unix = unix_now();
        session_id = session.id.clone();
        total_for_machine = session.records.len();
    }

    println!(
        "[upload] {} — +{} records ({} total)",
        hostname, incoming_count, total_for_machine
    );

    Ok(Json(UploadResponse {
        session_id,
        records_accepted: incoming_count,
        total_for_machine,
    }))
}

async fn handle_list_sessions(
    State(state): State<AppState>,
    headers: HeaderMap,
) -> Result<Json<Vec<SessionSummary>>, StatusCode> {
    check_api_key(&state, &headers)?;
    let sessions = state.sessions.lock().unwrap();
    let mut list: Vec<SessionSummary> = sessions
        .values()
        .map(|s| SessionSummary {
            id: s.id.clone(),
            hostname: s.hostname.clone(),
            first_seen_unix: s.first_seen_unix,
            last_seen_unix: s.last_seen_unix,
            record_count: s.records.len(),
        })
        .collect();
    list.sort_by_key(|s| s.first_seen_unix);
    Ok(Json(list))
}

async fn handle_get_session(
    State(state): State<AppState>,
    headers: HeaderMap,
    Path(hostname): Path<String>,
) -> Result<Json<SessionAnalysis>, StatusCode> {
    check_api_key(&state, &headers)?;
    // Hold the session lock only long enough to clone what we need,
    // then release it before doing any async work.
    let (summary, patterns, unmatched) = {
        let sessions = state.sessions.lock().unwrap();
        let session = sessions.get(&hostname).ok_or(StatusCode::NOT_FOUND)?;
        let patterns = analyze_patterns(&session.records, &state.cloud_detector);
        let unmatched = collect_unmatched_ips(&session.records, &state.cloud_detector);
        let summary = SessionSummary {
            id: session.id.clone(),
            hostname: session.hostname.clone(),
            first_seen_unix: session.first_seen_unix,
            last_seen_unix: session.last_seen_unix,
            record_count: session.records.len(),
        };
        (summary, patterns, unmatched)
    };

    let arin_results = resolve_ip_ownership(
        &unmatched,
        state.asn_db.as_deref(),
        &state.arin_cache,
        state.arin_cache_path.as_deref(),
    )
    .await;

    Ok(Json(SessionAnalysis {
        session: summary,
        patterns,
        arin_results,
    }))
}

async fn handle_cross_machine(
    State(state): State<AppState>,
    headers: HeaderMap,
) -> Result<Json<CrossMachineReport>, StatusCode> {
    check_api_key(&state, &headers)?;
    // Collect everything we need while holding the lock, then drop it.
    let (shared_ips, by_machine, all_unmatched) = {
        let sessions = state.sessions.lock().unwrap();

        let mut ip_to_machines: HashMap<String, HashSet<String>> = HashMap::new();
        let mut ip_to_host: HashMap<String, Option<String>> = HashMap::new();
        let mut ip_conn_count: HashMap<String, usize> = HashMap::new();

        for session in sessions.values() {
            for r in &session.records {
                ip_to_machines
                    .entry(r.remote_ip.clone())
                    .or_default()
                    .insert(session.hostname.clone());
                ip_to_host
                    .entry(r.remote_ip.clone())
                    .or_insert_with(|| r.remote_hostname.clone());
                *ip_conn_count.entry(r.remote_ip.clone()).or_insert(0) += 1;
            }
        }

        let mut shared_ips: Vec<SharedIp> = ip_to_machines
            .into_iter()
            .filter(|(_, machines)| machines.len() > 1)
            .map(|(ip, machines)| {
                let parsed: Option<IpAddr> = ip.parse().ok();
                let is_known_cloud = parsed
                    .and_then(|a| {
                        let host = ip_to_host.get(&ip).and_then(|h| h.as_deref());
                        state.cloud_detector.detect(&a, host)
                    })
                    .is_some();
                SharedIp {
                    remote_host: ip_to_host.get(&ip).and_then(|h| h.clone()),
                    seen_on: machines.into_iter().collect(),
                    total_connections: *ip_conn_count.get(&ip).unwrap_or(&0),
                    is_known_cloud,
                    remote_ip: ip,
                }
            })
            .collect();

        shared_ips.sort_by(|a, b| {
            b.is_known_cloud
                .cmp(&a.is_known_cloud)
                .reverse()
                .then(b.total_connections.cmp(&a.total_connections))
        });

        let by_machine: Vec<MachineSummary> = sessions
            .values()
            .map(|s| {
                let p = analyze_patterns(&s.records, &state.cloud_detector);
                MachineSummary {
                    hostname: s.hostname.clone(),
                    record_count: s.records.len(),
                    beacon_count: p.beaconing_candidates.len(),
                    high_entropy_count: p.high_entropy_hosts.len(),
                    noncloud_freq_count: p.high_freq_noncloud.len(),
                }
            })
            .collect();

        // Aggregate unmatched IPs across all sessions.
        let all_unmatched: Vec<IpAddr> = sessions
            .values()
            .flat_map(|s| collect_unmatched_ips(&s.records, &state.cloud_detector))
            .collect::<HashSet<_>>()
            .into_iter()
            .collect();

        (shared_ips, by_machine, all_unmatched)
    };

    let arin_results = resolve_ip_ownership(
        &all_unmatched,
        state.asn_db.as_deref(),
        &state.arin_cache,
        state.arin_cache_path.as_deref(),
    )
    .await;

    Ok(Json(CrossMachineReport {
        shared_ips,
        by_machine,
        arin_results,
    }))
}

// ─── ARIN helpers ─────────────────────────────────────────────────────────────

/// Return every public IP in `records` that the cloud detector does not recognise.
fn collect_unmatched_ips(records: &[ConnectionRecord], detector: &CloudDetector) -> Vec<IpAddr> {
    let mut seen: HashSet<IpAddr> = HashSet::new();
    let mut matched: HashSet<IpAddr> = HashSet::new();

    for r in records {
        let ip: IpAddr = match r.remote_ip.parse() {
            Ok(a) => a,
            Err(_) => continue,
        };
        if ip.is_loopback() || ip.is_unspecified() {
            continue;
        }
        if let IpAddr::V4(v4) = ip {
            if v4.is_private() || v4.is_link_local() {
                continue;
            }
        }
        seen.insert(ip);
        if detector.detect(&ip, r.remote_hostname.as_deref()).is_some() {
            matched.insert(ip);
        }
    }

    seen.difference(&matched).copied().collect()
}

/// Resolve ownership for a slice of IPs.
///
/// Priority:
///   1. Local ASN DB (instant, offline) — when `--asn-db` is provided.
///   2. In-memory + file-backed ARIN cache — for IPs not yet seen.
///   3. Live ARIN RDAP query — only for cache misses when no local DB is present.
async fn resolve_ip_ownership(
    ips: &[IpAddr],
    asn_db: Option<&AsnDb>,
    cache: &Arc<Mutex<HashMap<String, Option<ArinResult>>>>,
    cache_path: Option<&str>,
) -> HashMap<String, ArinResult> {
    if let Some(db) = asn_db {
        // Local DB path: instant O(log n) lookup, zero network calls.
        return ips
            .iter()
            .filter_map(|ip| {
                db.lookup(ip).map(|r| {
                    (
                        ip.to_string(),
                        ArinResult {
                            handle: format!("AS{}", r.asn),
                            org_name: r.org_name.clone(),
                            cidr: String::new(),
                            country: r.country.clone(),
                        },
                    )
                })
            })
            .collect();
    }

    // ARIN path: check cache first, query only misses.
    let to_lookup: Vec<IpAddr> = {
        let guard = cache.lock().unwrap();
        ips.iter()
            .filter(|ip| !guard.contains_key(&ip.to_string()))
            .copied()
            .collect()
    };

    if !to_lookup.is_empty() {
        println!("ARIN: querying {} uncached IPs...", to_lookup.len());

        let mut set = tokio::task::JoinSet::new();
        for ip in to_lookup {
            set.spawn(async move { (ip, lookup_arin(&ip).await) });
        }

        let mut updates: Vec<(String, Option<ArinResult>)> = Vec::new();
        while let Some(result) = set.join_next().await {
            if let Ok((ip, Ok(arin))) = result {
                updates.push((ip.to_string(), arin));
            }
        }

        println!("ARIN: {} responses received", updates.len());

        let mut guard = cache.lock().unwrap();
        for (ip_str, arin) in updates {
            guard.insert(ip_str, arin);
        }

        if let Some(path) = cache_path {
            let json = serde_json::to_string_pretty(&*guard).unwrap_or_default();
            if let Err(e) = std::fs::write(path, json) {
                eprintln!("Warning: failed to persist ARIN cache to {}: {}", path, e);
            }
        }
    }

    let guard = cache.lock().unwrap();
    ips.iter()
        .filter_map(|ip| {
            guard
                .get(&ip.to_string())
                .and_then(|r| r.as_ref())
                .map(|r| (ip.to_string(), r.clone()))
        })
        .collect()
}

// ─── pattern analysis ─────────────────────────────────────────────────────────

fn analyze_patterns(records: &[ConnectionRecord], detector: &CloudDetector) -> PatternReport {
    PatternReport {
        beaconing_candidates: detect_beaconing(records, detector),
        high_entropy_hosts: detect_high_entropy_hosts(records),
        port_anomalies: detect_port_anomalies(records),
        high_freq_noncloud: detect_high_freq_noncloud(records, detector),
    }
}

/// Detect processes that re-connect to the same IP at suspiciously regular intervals.
///
/// Algorithm:
///   1. Group records by (process, remote_ip).
///   2. Sort timestamps and collapse poll-adjacent duplicates (gap < 6 s) so
///      a persistent TCP connection that appears every poll doesn't look like beaconing.
///   3. Compute inter-arrival gaps between distinct appearances.
///      Only gaps > 15 s are kept — smaller gaps are just consecutive polls.
///   4. If there are ≥ 3 such gaps, compute mean, stddev, and CV (stddev/mean).
///      CV < 0.4 → regular timing → beacon candidate.
fn detect_beaconing(
    records: &[ConnectionRecord],
    detector: &CloudDetector,
) -> Vec<BeaconingCandidate> {
    // (process, remote_ip) -> (sorted timestamps, first seen hostname)
    let mut groups: HashMap<(String, String), (Vec<f64>, Option<String>)> = HashMap::new();

    for r in records {
        let ts = r
            .timestamp
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap_or_default()
            .as_secs_f64();
        let key = (r.process_name.clone(), r.remote_ip.clone());
        let entry = groups
            .entry(key)
            .or_insert_with(|| (Vec::new(), r.remote_hostname.clone()));
        entry.0.push(ts);
        if entry.1.is_none() {
            entry.1 = r.remote_hostname.clone();
        }
    }

    let mut candidates = Vec::new();

    for ((process, ip), (mut times, remote_host)) in groups {
        times.sort_by(|a, b| a.partial_cmp(b).unwrap());

        // Collapse poll-adjacent timestamps: keep only the first of each "burst"
        // where the gap to the previous kept timestamp is ≤ 6 s.
        let mut distinct: Vec<f64> = Vec::new();
        for t in times {
            if distinct.last().is_none_or(|&last| t - last > 6.0) {
                distinct.push(t);
            }
        }

        if distinct.len() < 5 {
            continue;
        }

        // Inter-arrival gaps — only the ones large enough to indicate a deliberate
        // re-connection rather than just consecutive polls.
        let gaps: Vec<f64> = distinct
            .windows(2)
            .map(|w| w[1] - w[0])
            .filter(|&g| g > 15.0)
            .collect();

        if gaps.len() < 3 {
            continue;
        }

        let mean = gaps.iter().sum::<f64>() / gaps.len() as f64;
        let variance =
            gaps.iter().map(|g| (g - mean).powi(2)).sum::<f64>() / gaps.len() as f64;
        let stddev = variance.sqrt();
        let jitter_ratio = if mean > 0.0 { stddev / mean } else { 1.0 };

        if jitter_ratio > 0.4 {
            continue;
        }

        let ip_addr: IpAddr = match ip.parse() {
            Ok(a) => a,
            Err(_) => continue,
        };
        let is_known_cloud = detector.detect(&ip_addr, remote_host.as_deref()).is_some();

        // Suspicion score 0–10:
        //   Base = how regular the timing is (1 = perfectly regular, 0 = barely qualifies)
        //   Cloud factor = known CDN/provider reduces score (still worth showing)
        //   Count factor = more gaps = more confident
        let base = 1.0 - (jitter_ratio / 0.4);
        let cloud_factor = if is_known_cloud { 0.35 } else { 1.0 };
        let count_factor = ((gaps.len() as f64 - 3.0) / 7.0).clamp(0.0, 1.0);
        let suspicion_score =
            ((base * cloud_factor * (0.5 + 0.5 * count_factor)) * 10.0).round() / 10.0;

        candidates.push(BeaconingCandidate {
            process,
            remote_ip: ip,
            remote_host,
            distinct_appearances: distinct.len(),
            interval_mean_secs: (mean * 10.0).round() / 10.0,
            interval_stddev_secs: (stddev * 10.0).round() / 10.0,
            jitter_ratio: (jitter_ratio * 1000.0).round() / 1000.0,
            is_known_cloud,
            suspicion_score,
        });
    }

    candidates.sort_by(|a, b| b.suspicion_score.partial_cmp(&a.suspicion_score).unwrap());
    candidates.truncate(20);
    candidates
}

fn shannon_entropy(s: &str) -> f64 {
    if s.is_empty() {
        return 0.0;
    }
    let mut freq: HashMap<char, usize> = HashMap::new();
    for c in s.chars() {
        *freq.entry(c).or_insert(0) += 1;
    }
    let len = s.len() as f64;
    freq.values().fold(0.0, |acc, &count| {
        let p = count as f64 / len;
        acc - p * p.log2()
    })
}

// Known-clean domain suffixes — we skip entropy checks for these.
const CLEAN_SUFFIXES: &[&str] = &[
    ".microsoft.com",
    ".windows.com",
    ".windowsupdate.com",
    ".msftconnecttest.com",
    ".azure.com",
    ".windows.net",
    ".office.com",
    ".live.com",
    ".amazonaws.com",
    ".cloudfront.net",
    ".akamaiedge.net",
    ".akamaihd.net",
    ".cloudflare.com",
    ".github.com",
    ".githubusercontent.com",
    ".google.com",
    ".googleapis.com",
    ".gstatic.com",
];

/// Flag hostnames whose leftmost DNS label has high Shannon entropy.
/// High entropy labels suggest algorithmically-generated names (DGA).
fn detect_high_entropy_hosts(records: &[ConnectionRecord]) -> Vec<HighEntropyHost> {
    // hostname -> (process, count)
    let mut seen: HashMap<String, (String, usize)> = HashMap::new();

    for r in records {
        let hostname = match &r.remote_hostname {
            Some(h) if h.len() > 8 && h.contains('.') => h.clone(),
            _ => continue,
        };
        if hostname.parse::<IpAddr>().is_ok() {
            continue; // bare IP, not a hostname
        }
        if CLEAN_SUFFIXES.iter().any(|s| hostname.ends_with(s)) {
            continue;
        }
        let entry = seen
            .entry(hostname)
            .or_insert((r.process_name.clone(), 0));
        entry.1 += 1;
    }

    let mut findings: Vec<HighEntropyHost> = seen
        .into_iter()
        .filter_map(|(hostname, (process, count))| {
            let label = hostname.split('.').next().unwrap_or(&hostname);
            if label.len() < 8 {
                return None;
            }
            let entropy = shannon_entropy(label);
            if entropy < 3.5 {
                return None;
            }
            Some(HighEntropyHost {
                hostname,
                process,
                entropy_bits_per_char: (entropy * 100.0).round() / 100.0,
                connection_count: count,
            })
        })
        .collect();

    findings.sort_by(|a, b| {
        b.entropy_bits_per_char
            .partial_cmp(&a.entropy_bits_per_char)
            .unwrap()
    });
    findings.truncate(20);
    findings
}

const STANDARD_PORTS: &[u16] = &[
    80, 443, 8080, 8443, 8888, 53, 25, 587, 465, 993, 995, 143, 21, 22, 23, 3389, 5985,
    5986,
];

/// Flag connections to destination ports outside the well-known set.
fn detect_port_anomalies(records: &[ConnectionRecord]) -> Vec<PortAnomaly> {
    // (port, process, remote_ip) -> (count, remote_host)
    let mut groups: HashMap<(u16, String, String), (usize, Option<String>)> =
        HashMap::new();

    for r in records {
        let port = match r.remote_port {
            Some(p) if !STANDARD_PORTS.contains(&p) && p > 0 => p,
            _ => continue,
        };
        let key = (port, r.process_name.clone(), r.remote_ip.clone());
        let entry = groups
            .entry(key)
            .or_insert((0, r.remote_hostname.clone()));
        entry.0 += 1;
    }

    let mut findings: Vec<PortAnomaly> = groups
        .into_iter()
        .map(|((port, process, ip), (count, host))| PortAnomaly {
            port,
            process,
            remote_ip: ip,
            remote_host: host,
            connection_count: count,
        })
        .collect();

    findings.sort_by(|a, b| b.connection_count.cmp(&a.connection_count));
    findings.truncate(25);
    findings
}

/// Flag processes with many connections to IPs not matched by any cloud provider.
/// Legitimate software almost always talks to known infrastructure;
/// unknown high-count destinations warrant a closer look.
fn detect_high_freq_noncloud(
    records: &[ConnectionRecord],
    detector: &CloudDetector,
) -> Vec<HighFreqTalker> {
    // (process, remote_ip) -> (count, remote_host)
    let mut groups: HashMap<(String, String), (usize, Option<String>)> = HashMap::new();

    for r in records {
        let ip: IpAddr = match r.remote_ip.parse() {
            Ok(a) => a,
            Err(_) => continue,
        };
        if detector.detect(&ip, r.remote_hostname.as_deref()).is_some() {
            continue; // known cloud provider — expected
        }
        if ip.is_private() {
            continue; // skip RFC 1918 / internal
        }
        let key = (r.process_name.clone(), r.remote_ip.clone());
        let entry = groups
            .entry(key)
            .or_insert((0, r.remote_hostname.clone()));
        entry.0 += 1;
    }

    let mut findings: Vec<HighFreqTalker> = groups
        .into_iter()
        .filter(|(_, (count, _))| *count >= 5)
        .map(|((process, ip), (count, host))| HighFreqTalker {
            process,
            remote_ip: ip,
            remote_host: host,
            connection_count: count,
        })
        .collect();

    findings.sort_by(|a, b| b.connection_count.cmp(&a.connection_count));
    findings.truncate(25);
    findings
}

// ─── IpAddr::is_private helper (stable in 1.75+) ─────────────────────────────

trait IsPrivate {
    fn is_private(&self) -> bool;
}

impl IsPrivate for IpAddr {
    fn is_private(&self) -> bool {
        match self {
            IpAddr::V4(a) => a.is_private() || a.is_link_local(),
            IpAddr::V6(a) => a.is_loopback(),
        }
    }
}
