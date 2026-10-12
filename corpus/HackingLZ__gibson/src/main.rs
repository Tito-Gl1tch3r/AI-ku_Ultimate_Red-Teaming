use clap::{Parser, Subcommand};
use gibson::collector_v2::{CollectorOpts, SecureCollector};
use gibson::parser::{ConnectionParser, ParserOpts};
use gibson::server::{self, ServerOpts};

#[derive(Parser)]
#[command(author, version, about = "Network connection monitor and analyzer")]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Collect network connections (lightweight agent)
    Collect(CollectorOpts),
    
    /// Parse and analyze collected data
    Parse(ParserOpts),
    
    /// Receive uploads from collectors and run live pattern analysis
    Serve(ServerOpts),

    /// Run both collection and parsing (all-in-one)
    Monitor {
        /// Duration in seconds
        #[arg(long, default_value_t = 300)]
        duration_seconds: u64,
        
        /// Output directory for all reports
        #[arg(long, default_value = "./network_analysis")]
        output_dir: String,
        
        /// Enable all analysis reports
        #[arg(long)]
        full_analysis: bool,
    },
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let cli = Cli::parse();
    
    match cli.command {
        Commands::Serve(opts) => {
            server::run_server(opts).await?;
        }

        Commands::Collect(opts) => {
            let mut collector = SecureCollector::new(opts)?;
            collector.run().await?;
        }
        
        Commands::Parse(opts) => {
            let parser = ConnectionParser::new(opts);
            parser.parse().await?;
        }
        
        Commands::Monitor { duration_seconds, output_dir, full_analysis } => {
            // Create output directory
            std::fs::create_dir_all(&output_dir)?;
            
            // First collect
            println!("=== Phase 1: Collecting network connections ===");
            let connections_file = format!("{}/connections.jsonl", output_dir);
            let collector_opts = CollectorOpts {
                duration_seconds,
                interval_seconds: 5,
                output: connections_file.clone(),
                enable_dns: true,
                verbose: true,
                compress: false,
                encrypt_key: None,
                upload_url: None,
                api_key: None,
                delete_after_upload: false,
                batch_size: 100,
                established_only: false,
                user_agent: None,
            };
            
            let mut collector = SecureCollector::new(collector_opts)?;
            collector.run().await?;
            
            // Then parse
            println!("\n=== Phase 2: Analyzing collected data ===");
            let parser_opts = if full_analysis {
                ParserOpts {
                    input: connections_file,
                    process_summary: Some(format!("{}/process_summary.json", output_dir)),
                    cloud_analysis: Some(format!("{}/cloud_analysis.json", output_dir)),
                    firewall_rules_iptables: Some(format!("{}/firewall_rules.iptables", output_dir)),
                    firewall_rules_windows: Some(format!("{}/firewall_rules.bat", output_dir)),
                    database_export: Some(format!("{}/database_export.sql", output_dir)),
                    whitelist_processes: Some("svchost,System,chrome,firefox,edge".to_string()),
                    min_connections: 1,
                    ip_ranges_file: None,
                    arin_lookup: false,
                    asn_db: None,
                    arin_cache: None,
                }
            } else {
                ParserOpts {
                    input: connections_file,
                    process_summary: Some(format!("{}/process_summary.json", output_dir)),
                    cloud_analysis: Some(format!("{}/cloud_analysis.json", output_dir)),
                    firewall_rules_iptables: None,
                    firewall_rules_windows: None,
                    database_export: None,
                    whitelist_processes: Some("svchost,System,chrome,firefox,edge".to_string()),
                    min_connections: 1,
                    ip_ranges_file: None,
                    arin_lookup: false,
                    asn_db: None,
                    arin_cache: None,
                }
            };

            let parser = ConnectionParser::new(parser_opts);
            parser.parse().await?;
            
            println!("\n=== Analysis Complete ===");
            println!("Results saved to: {}", output_dir);
        }
    }
    
    Ok(())
}