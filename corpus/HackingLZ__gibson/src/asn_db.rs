use serde::Serialize;
use std::net::{IpAddr, Ipv4Addr};

/// A single ASN ownership record.
#[derive(Debug, Clone, Serialize)]
pub struct AsnRecord {
    pub asn: u32,
    /// ISO 3166-1 alpha-2 country code, or None if the registry didn't provide one.
    pub country: Option<String>,
    pub org_name: String,
}

struct AsnRange {
    start: u32,
    end: u32,
    record: AsnRecord,
}

/// In-memory IP → ASN lookup table built from the ip2asn TSV (iptoasn.com).
///
/// Covers all globally-routed IPv4 prefixes (~700 k ranges).
/// Lookups are O(log n) via binary search; the whole file loads in < 1 s.
///
/// **Download (do once, refresh weekly):**
/// ```
/// curl -O https://iptoasn.com/data/ip2asn-v4.tsv.gz
/// gunzip ip2asn-v4.tsv.gz
/// ```
/// Then pass the path with `--asn-db ip2asn-v4.tsv`.
pub struct AsnDb {
    /// Sorted by range start address.
    ranges: Vec<AsnRange>,
}

impl AsnDb {
    /// Load from the decompressed ip2asn TSV file.
    ///
    /// Expected column order (tab-separated):
    /// `start_ip  end_ip  asn  country_code  org_name`
    pub fn load(path: &str) -> anyhow::Result<Self> {
        let content = std::fs::read_to_string(path)?;
        let mut ranges = Vec::with_capacity(800_000);

        for line in content.lines() {
            let mut cols = line.splitn(5, '\t');
            let start_str = match cols.next() {
                Some(s) => s,
                None => continue,
            };
            let end_str = match cols.next() {
                Some(s) => s,
                None => continue,
            };
            let asn_str = match cols.next() {
                Some(s) => s,
                None => continue,
            };
            let country_str = match cols.next() {
                Some(s) => s,
                None => continue,
            };
            let org_str = match cols.next() {
                Some(s) => s,
                None => continue,
            };

            let start: Ipv4Addr = match start_str.parse() {
                Ok(a) => a,
                Err(_) => continue,
            };
            let end: Ipv4Addr = match end_str.parse() {
                Ok(a) => a,
                Err(_) => continue,
            };
            let asn: u32 = match asn_str.parse() {
                Ok(n) => n,
                Err(_) => continue,
            };

            if asn == 0 {
                continue; // unrouted / IANA reserved
            }

            let country = match country_str {
                "None" | "--" | "" => None,
                s => Some(s.to_string()),
            };

            ranges.push(AsnRange {
                start: u32::from(start),
                end: u32::from(end),
                record: AsnRecord {
                    asn,
                    country,
                    org_name: org_str.to_string(),
                },
            });
        }

        ranges.sort_unstable_by_key(|r| r.start);
        Ok(AsnDb { ranges })
    }

    /// Look up the ASN record for an IP address.
    /// Returns `None` for IPv6 (this DB is IPv4-only) and for unrouted ranges.
    pub fn lookup(&self, ip: &IpAddr) -> Option<&AsnRecord> {
        let addr = match ip {
            IpAddr::V4(v4) => u32::from(*v4),
            IpAddr::V6(_) => return None,
        };

        // Find the last range whose start ≤ addr, then check if addr ≤ end.
        let idx = self.ranges.partition_point(|r| r.start <= addr);
        if idx == 0 {
            return None;
        }
        let range = &self.ranges[idx - 1];
        if addr <= range.end {
            Some(&range.record)
        } else {
            None
        }
    }

    pub fn len(&self) -> usize {
        self.ranges.len()
    }

    pub fn is_empty(&self) -> bool {
        self.ranges.is_empty()
    }
}
