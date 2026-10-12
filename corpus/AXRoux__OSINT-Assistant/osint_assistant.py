import requests
import re
import json
import argparse
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Union, Tuple
from urllib.parse import urlparse
from rich.console import Console
from rich.table import Table
from pydantic import BaseModel, Field
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Pydantic models for structured data
class Entity(BaseModel):
    name: str
    type: Optional[str] = None
    confidence: float = 1.0

class Connection(BaseModel):
    from_entity: str = Field(..., alias="from")
    to_entity: str = Field(..., alias="to")
    relationship: str

class Timestamp(BaseModel):
    published: Optional[str] = None
    last_updated: Optional[str] = None

class ContentAnalysis(BaseModel):
    domain: str
    credibility_score: float
    key_entities: List[str]
    sentiment: str
    timestamps: Dict[str, str]
    connections: List[Dict[str, str]]

class SearchResult(BaseModel):
    title: str
    url: str
    snippet: str
    source_type: str
    timestamp: str

class OSINTReport(BaseModel):
    collected_data: List[SearchResult]
    analysis_results: Dict[str, ContentAnalysis]
    timestamp: str
    query_info: Dict[str, Any]

class ApiClient:
    """Handles API communication with AI services"""
    
    def __init__(self, api_key: Optional[str] = None, base_url: str = "https://api.perplexity.ai"):
        self.api_key = api_key
        self.base_url = base_url
        self.console = Console()
        
    def call_api(self, messages: List[Dict[str, str]], model: str = "sonar-pro", 
                 temperature: float = 0.2, max_tokens: int = 2000) -> Optional[str]:
        """Make API call to the AI service"""
        if not self.api_key:
            self.console.print("[yellow]API capabilities not available: No API key provided[/yellow]")
            return None
            
        try:
            data = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            
            headers = {
                "accept": "application/json",
                "content-type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            response = requests.post(
                f"{self.base_url}/chat/completions", 
                headers=headers, 
                json=data
            )
            response.raise_for_status()
            result = response.json()
            
            if "choices" in result and result["choices"] and "message" in result["choices"][0]:
                return result["choices"][0]["message"]["content"]
            else:
                self.console.print("[yellow]Unexpected API response format[/yellow]")
                return None
                
        except Exception as e:
            error_message = str(e)
            if "401" in error_message or "Authorization" in error_message:
                self.console.print("[yellow]Authorization error with API. Check your API key.[/yellow]")
                self.console.print(f"Error details: {error_message}")
                self.api_key = None  # Disable API for future calls
            else:
                self.console.print(f"[red]Error using AI service: {error_message}[/red]")
            return None

class JsonHelper:
    """Helper class for JSON operations"""
    
    @staticmethod
    def extract_json_from_text(text, console: Optional[Console] = None) -> Union[Dict, List, str]:
        """Extract JSON from text that may contain markdown or other non-JSON content."""
        if console is None:
            console = Console()
            
        # Check if the text is already valid JSON
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        
        # Try to extract JSON from markdown code blocks
        for pattern in ["```json", "```"]:
            if pattern in text:
                try:
                    parts = text.split(pattern)
                    if len(parts) > 1:
                        json_content = parts[1].split("```")[0].strip() if pattern == "```json" else parts[1].strip()
                        return json.loads(json_content)
                except (json.JSONDecodeError, IndexError):
                    pass
        
        # Try to match JSON array or object patterns
        for pattern, is_array in [
            (r'\[\s*{[\s\S]*}\s*\]', True),  # Array pattern
            (r'{[\s\S]*}', False)  # Object pattern
        ]:
            matches = re.findall(pattern, text)
            if matches:
                for match in matches:
                    try:
                        return json.loads(match)
                    except json.JSONDecodeError:
                        continue
        
        if console:
            console.print("[yellow]Could not extract valid JSON from text. Using text as-is.[/yellow]")
        return text

class OSINTAssistant:
    """
    A simple OSINT tool that collects and analyzes information from web sources
    based on specific search terms and parameters. Enhanced with AI capabilities.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.console = Console()
        self.collected_data = []
        self.analysis_results = {}
        
        # Get API key from environment if not provided
        if not api_key:
            api_key = os.getenv("PERPLEXITY_API_KEY")
            
        # Initialize API client
        self.api_client = ApiClient(api_key) if api_key else None
        if not api_key:
            self.console.print("[yellow]No API key provided. AI capabilities will be disabled.[/yellow]")
    
    def ask_ai(self, query: str, system_prompt: Optional[str] = None) -> Optional[str]:
        """Use AI to enhance search and analysis capabilities with web search."""
        if not self.api_client:
            self.console.print("[yellow]AI capabilities not available: No API key provided[/yellow]")
            return None
            
        # Default system prompt if none provided
        if not system_prompt:
            system_prompt = """
You are an OSINT (Open Source Intelligence) research assistant. Your task is to gather factual information about the query from the web.

Rules:
1. Search the web for reliable, up-to-date information on the topic.
2. Provide only the final answer based on factual information found online.
3. Be precise, accurate, and comprehensive.
4. Cite sources where possible.
5. Organize information in a structured way.
6. Remain objective and avoid speculation.

Steps:
1. Search for reliable information across multiple sources.
2. Verify facts by cross-referencing sources.
3. Organize facts into a coherent response.
4. Format your response as JSON when requested.
"""
            
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ]
        
        return self.api_client.call_api(messages)
        
    def search_web(self, query: str, num_results: int = 10) -> List[SearchResult]:
        """Search the web for information related to a specific query, enhanced with AI."""
        self.console.print(f"[bold blue]Searching for:[/bold blue] {query}")
        
        # Check if we have AI capabilities
        if not self.api_client:
            self.console.print("[yellow]AI capabilities not available. No results available.[/yellow]")
            self.collected_data = []
            return []
        
        # Make multiple search queries to get the required number of results
        ai_results = []
        max_attempts = min(3, num_results)  # Limit to 3 attempts to avoid excessive API calls
        
        # First query - direct search
        direct_results = self._perform_search(query, num_results)
        if direct_results:
            ai_results.extend(direct_results)
            
        # If we still need more results, try different variations of the query
        if len(ai_results) < num_results and max_attempts > 1:
            variations = [
                f"latest news about {query}",
                f"recent developments regarding {query}",
                f"current information on {query}"
            ]
            
            existing_urls = {result["url"] for result in ai_results}
            
            for i, variation in enumerate(variations):
                if len(ai_results) >= num_results or i >= max_attempts - 1:
                    break
                    
                self.console.print(f"[blue]Searching for additional results with variation: {variation}[/blue]")
                additional_results = self._perform_search(variation, num_results - len(ai_results))
                
                # Add only unique results (checking by URL)
                if additional_results:
                    for result in additional_results:
                        if result["url"] not in existing_urls:
                            ai_results.append(result)
                            existing_urls.add(result["url"])
        
        # Limit results to the requested number
        ai_results = ai_results[:num_results]
        
        # Convert to Pydantic models and store in collected_data
        search_results = self._process_search_results(ai_results)
        
        self.console.print(f"[green]Found {len(search_results)} results[/green]")
        return search_results
    
    def _process_search_results(self, results: List[Dict]) -> List[SearchResult]:
        """Process and validate search results"""
        search_results = []
        self.collected_data = []  # Reset collected data
        
        for result in results:
            try:
                # Ensure each result has all required fields
                if "timestamp" not in result or not result["timestamp"]:
                    result["timestamp"] = datetime.now().strftime("%Y-%m-%d")
                
                search_result = SearchResult(**result)
                search_results.append(search_result)
                # Add to collected data list (as dict for compatibility with existing code)
                self.collected_data.append(result)
            except Exception as e:
                self.console.print(f"[red]Error parsing result: {str(e)}[/red]")
                self.console.print(f"[dim]Result data: {result}[/dim]")
        
        return search_results
        
    def _perform_search(self, query: str, num_results: int) -> List[Dict]:
        """Perform a single search with AI API."""
        system_prompt = f"""
You are an OSINT JSON response generator. Your ONLY job is to return search results in JSON format.

IMPORTANT: Your response MUST be ONLY a valid JSON array with {num_results} search results. 
DO NOT include any explanations, markdown formatting, or text before or after the JSON.

JSON format should be an array of objects with these exact fields:
- "title": The title of the result
- "url": The complete URL of the source
- "snippet": A short excerpt or summary (1-3 sentences)
- "source_type": The type of source (e.g., "News", "Academic", "Government")
- "timestamp": Current date in YYYY-MM-DD format

Example of EXACTLY how your response should look:
[
  {{
    "title": "Example Title",
    "url": "https://example.com/article",
    "snippet": "Brief excerpt from the source.",
    "source_type": "News",
    "timestamp": "2023-04-15"
  }},
  ... more results ...
]

Search for timely, factual information from credible sources. Focus on recent content (last 6 months).
"""
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Return EXACTLY {num_results} search results about '{query}' in ONLY JSON format with no other text."}
            ]
            
            content = self.api_client.call_api(
                messages, 
                temperature=0.1,  # Lower temperature for more reliable formatting
                max_tokens=4000    # Increase token limit to accommodate more results
            )
            
            if not content:
                return self._fallback_search(query, num_results)
                
            # Process the response
            json_content = JsonHelper.extract_json_from_text(content, self.console)
            
            if isinstance(json_content, list):
                self.console.print(f"[green]Successfully retrieved {len(json_content)} results from AI[/green]")
                return json_content
            elif isinstance(json_content, dict):
                # Try to get a list from a field in the dictionary if available
                for field in ["results", "data", "items", "content"]:
                    if field in json_content and isinstance(json_content[field], list):
                        return json_content[field]
                # Fall back to wrapping the dict in a list
                self.console.print("[green]Successfully retrieved 1 result after JSON extraction[/green]")
                return [json_content]
            else:
                self.console.print("[yellow]Could not parse API response as JSON. Trying alternate approach.[/yellow]")
                return self._fallback_search(query, num_results)
                
        except Exception as e:
            self.console.print(f"[yellow]Error in AI search: {str(e)}. Trying fallback approach.[/yellow]")
            return self._fallback_search(query, num_results)
        
    def _fallback_search(self, query: str, num_results: int) -> List[Dict]:
        """Fallback method for search when JSON formatting fails."""
        try:
            results = []
            
            for i in range(min(3, num_results)):
                prompt = f"""
What is a single important, recent result about "{query}"?
Provide only a JSON object with these fields:
- title: The title
- url: The URL
- snippet: A brief excerpt (1-2 sentences)
- source_type: The type of source (News, Academic, etc.)
- timestamp: Today's date
"""
                ai_response = self.ask_ai(prompt, "You must respond with only a single JSON object, nothing else.")
                if ai_response:
                    json_content = JsonHelper.extract_json_from_text(ai_response, self.console)
                    
                    if isinstance(json_content, dict):
                        # Make sure it has required fields
                        required_fields = ["title", "url", "snippet", "source_type"]
                        if all(field in json_content for field in required_fields):
                            # Add timestamp if missing
                            if "timestamp" not in json_content:
                                json_content["timestamp"] = datetime.now().strftime("%Y-%m-%d")
                            # Check if this URL is already in results
                            if not any(result.get("url") == json_content.get("url") for result in results):
                                results.append(json_content)
                
                if len(results) >= num_results:
                    break
                    
            if results:
                self.console.print(f"[green]Retrieved {len(results)} results using fallback approach[/green]")
                return results
                
            # If still no results, fall back to simulated data
            self.console.print("[yellow]No results from AI. Using simulated data.[/yellow]")
            return self._generate_simulated_results(query, num_results)
            
        except Exception as e:
            self.console.print(f"[red]Fallback search failed: {str(e)}[/red]")
            return self._generate_simulated_results(query, num_results)
    
    def analyze_content(self, url: str) -> Optional[ContentAnalysis]:
        """Analyze the content of a specific URL to extract relevant information, enhanced with AI."""
        self.console.print(f"[bold blue]Analyzing content from:[/bold blue] {url}")
        
        # Use AI for content analysis if available
        ai_analysis = None
        if self.api_client:
            system_prompt = """
You are an OSINT content analyzer tasked with analyzing a URL and extracting structured information.

Rules:
1. Search for and analyze the content at the provided URL.
2. Provide a detailed, evidence-based analysis.
3. Format your response as a JSON object with these exact fields:
   - domain: The domain name of the URL (e.g., "example.com")
   - credibility_score: A float from 0.0 to 1.0 indicating source credibility (higher = more credible)
   - key_entities: Array of strings for key people, organizations, or concepts mentioned
   - sentiment: One of "positive", "negative", or "neutral"
   - timestamps: Object with two string fields in YYYY-MM-DD format:
     * "published": When the content was first published
     * "last_updated": When the content was last updated
   - connections: Array of objects showing relationships between entities:
     * "from": The source entity
     * "to": The target entity
     * "relationship": The type of relationship

Return ONLY valid JSON with no additional text or explanation.
"""
            ai_response = self.ask_ai(f"Analyze this URL and extract structured information: {url}", system_prompt)
            
            if ai_response:
                # Extract JSON from the response
                json_content = JsonHelper.extract_json_from_text(ai_response, self.console)
                if isinstance(json_content, dict):
                    ai_analysis = json_content
                    self.console.print("[green]Successfully analyzed content with AI[/green]")
                else:
                    self.console.print("[yellow]Could not parse AI analysis as JSON. Using fallback analysis[/yellow]")
                    if isinstance(json_content, str) and len(json_content) > 50:
                        self.console.print(f"[dim]Response: {json_content[:100]}...[/dim]")
            else:
                self.console.print("[yellow]No response from AI. Using fallback analysis[/yellow]")
        
        # If no AI analysis, use simulated analysis
        if not ai_analysis:
            self.console.print("[yellow]Using simulated content analysis[/yellow]")
            domain = urlparse(url).netloc
            ai_analysis = self._generate_simulated_analysis(url, domain)
        
        # Validate and normalize analysis data
        normalized_analysis = self._normalize_analysis_data(ai_analysis)
            
        # Convert to Pydantic model and store
        try:
            content_analysis = ContentAnalysis(**normalized_analysis)
            self.analysis_results[url] = normalized_analysis  # Store as dict for compatibility
            self.console.print("[green]Analysis complete[/green]")
            return content_analysis
        except Exception as e:
            self.console.print(f"[red]Error in content analysis: {str(e)}[/red]")
            return None
    
    def _generate_simulated_analysis(self, url: str, domain: str) -> Dict[str, Any]:
        """Generate simulated content analysis when AI is not available"""
        return {
            "domain": domain,
            "credibility_score": self._calculate_credibility(domain),
            "key_entities": self._extract_entities(url),
            "sentiment": self._analyze_sentiment(url),
            "timestamps": self._extract_timestamps(url),
            "connections": self._find_connections(url)
        }
                
    def _normalize_analysis_data(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize analysis data to ensure it conforms to the ContentAnalysis model"""
        fixed = analysis.copy()
        
        # Use urlparse to get domain if needed
        if "domain" not in fixed or not isinstance(fixed["domain"], str):
            if self.collected_data:
                fixed["domain"] = urlparse(next(iter(self.collected_data), {}).get("url", "unknown.com")).netloc
            else:
                fixed["domain"] = "unknown.com"
            
        # Normalize credibility_score to a float between 0 and 1
        if "credibility_score" not in fixed or not isinstance(fixed["credibility_score"], (int, float)):
            fixed["credibility_score"] = 0.5
        else:
            fixed["credibility_score"] = max(0.0, min(1.0, float(fixed["credibility_score"])))
            
        # Ensure key_entities is a list of strings
        if "key_entities" not in fixed or not isinstance(fixed["key_entities"], list):
            fixed["key_entities"] = ["Unknown Entity"]
        
        # Normalize sentiment to one of the valid values
        valid_sentiments = ["positive", "negative", "neutral"]
        if "sentiment" not in fixed or fixed["sentiment"] not in valid_sentiments:
            fixed["sentiment"] = "neutral"
            
        # Normalize timestamps to the required format
        fixed["timestamps"] = self._normalize_timestamps(fixed.get("timestamps", {}))
            
        # Normalize connections to the required format
        fixed["connections"] = self._normalize_connections(fixed.get("connections", []))
            
        return fixed
    
    def _normalize_timestamps(self, timestamps: Union[Dict[str, str], None]) -> Dict[str, str]:
        """Normalize timestamps to ensure they are in the correct format"""
        if not timestamps or not isinstance(timestamps, dict):
            return {"published": "N/A", "last_updated": "N/A"}
        
        normalized = {}
        for field in ["published", "last_updated"]:
            if field not in timestamps or not isinstance(timestamps[field], str) or timestamps[field] == "None":
                normalized[field] = "N/A"
            else:
                normalized[field] = timestamps[field]
                
        return normalized
    
    def _normalize_connections(self, connections: Union[List[Dict[str, str]], None]) -> List[Dict[str, str]]:
        """Normalize connections to ensure they are in the correct format"""
        if not connections or not isinstance(connections, list):
            return [{"from": "Entity A", "to": "Entity B", "relationship": "related to"}]
        
        normalized = []
        for conn in connections:
            if isinstance(conn, dict):
                valid_conn = {}
                # Add required fields with defaults if missing
                valid_conn["from"] = conn.get("from", "Entity A") if isinstance(conn.get("from"), str) else "Entity A"
                valid_conn["to"] = conn.get("to", "Entity B") if isinstance(conn.get("to"), str) else "Entity B"
                valid_conn["relationship"] = conn.get("relationship", "related to") if isinstance(conn.get("relationship"), str) else "related to"
                normalized.append(valid_conn)
                
        return normalized if normalized else [{"from": "Entity A", "to": "Entity B", "relationship": "related to"}]
    
    def _calculate_credibility(self, domain: str) -> float:
        """Calculate a basic credibility score for a domain."""
        # This would use heuristics or a database of known sources in a real tool
        credibility_db = {
            "example.com": 0.6,
            "dataresearch.org": 0.8,
            "gov.reports.org": 0.9
        }
        return credibility_db.get(domain, 0.5)  # Default score for unknown domains
    
    def _extract_entities(self, url: str) -> List[str]:
        """Extract key entities mentioned in the content."""
        # Simulated entity extraction
        if "analysis" in url:
            return ["Organization X", "Technology Y", "Process Z"]
        elif "stats" in url:
            return ["Dataset A", "Trend B", "Factor C"]
        else:
            return ["Policy D", "Department E", "Initiative F"]
    
    def _analyze_sentiment(self, url: str) -> str:
        """Analyze the sentiment of the content."""
        # Simulated sentiment analysis
        sentiments = ["positive", "negative", "neutral"]
        return sentiments[hash(url) % 3]
    
    def _extract_timestamps(self, url: str) -> Dict[str, str]:
        """Extract relevant timestamps from the content."""
        # Simulated timestamp extraction
        return {
            "published": (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d"),
            "last_updated": datetime.now().strftime("%Y-%m-%d")
        }
    
    def _find_connections(self, url: str) -> List[Dict[str, str]]:
        """Find connections between entities in the content."""
        # Simulated connection finding
        connections = [
            {"from": "Entity A", "to": "Entity B", "relationship": "funds"},
            {"from": "Entity C", "to": "Entity D", "relationship": "collaborates with"}
        ]
        return connections
    
    def generate_report(self) -> None:
        """Generate a comprehensive report from the collected data."""
        self.console.print("\n[bold yellow]===== OSINT ANALYSIS REPORT =====[/bold yellow]")
        
        # Summary table
        self._generate_summary_table()
        
        # Key findings
        self._generate_key_findings()
        
        # Generate insights using AI or fallback
        self._generate_insights()
        
        # Export options
        self._show_export_options()

    def _generate_summary_table(self) -> None:
        """Generate and display the summary table"""
        table = Table(title="Data Collection Summary")
        table.add_column("Source", style="cyan")
        table.add_column("Type", style="green")
        table.add_column("Credibility", style="yellow")
        
        for item in self.collected_data:
            domain = urlparse(item["url"]).netloc
            credibility = self._calculate_credibility(domain)
            table.add_row(domain, item["source_type"], f"{credibility:.2f}")
        
        self.console.print(table)
    
    def _generate_key_findings(self) -> Dict[str, int]:
        """Generate and display key findings"""
        self.console.print("\n[bold blue]Key Findings:[/bold blue]")
        all_entities = []
        for item in self.collected_data:
            entities = self._extract_entities(item["url"])
            all_entities.extend(entities)
        
        # Find most frequent entities
        entity_counts = {}
        for entity in all_entities:
            entity_counts[entity] = entity_counts.get(entity, 0) + 1
        
        for entity, count in sorted(entity_counts.items(), key=lambda x: x[1], reverse=True):
            self.console.print(f"- [bold]{entity}[/bold] mentioned {count} times")
            
        return entity_counts
    
    def _generate_insights(self) -> None:
        """Generate and display insights"""
        if not self.api_client:
            # Fallback recommendations when AI is not available
            self.console.print("\n[bold blue]Recommendations:[/bold blue]")
            self.console.print("- Further investigate connections between Entity A and Entity C")
            self.console.print("- Monitor developments in Technology Y over the next 30 days")
            self.console.print("- Cross-reference findings with Dataset A for validation")
            return
            
        # Use AI to generate insights
        entity_counts = self._generate_key_findings()
        data_summary = self._prepare_data_summary(entity_counts)
        
        system_prompt = """
You are an OSINT analyst tasked with generating insights from collected intelligence data.

Rules:
1. Analyze the OSINT data summary provided.
2. Generate 3-5 key insights based on the data.
3. Each insight should be specific, actionable, and data-driven.
4. Include a brief conclusion and suggested next steps.
5. Be objective and analytical in your assessment.

Format your response in a structured way with clear section headings.
"""
        
        ai_insights = self.ask_ai(f"Analyze this OSINT data summary and provide insights: {json.dumps(data_summary)}", system_prompt)
        
        if ai_insights:
            self.console.print("\n[bold blue]AI-Generated Insights:[/bold blue]")
            self.console.print(ai_insights)
        else:
            # Fallback recommendations if AI insights not available
            self.console.print("\n[bold blue]Recommendations:[/bold blue]")
            self.console.print("- Further investigate connections between entities")
            self.console.print("- Monitor developments over the next 30 days")
            self.console.print("- Cross-reference findings with additional sources for validation")
    
    def _prepare_data_summary(self, entity_counts: Dict[str, int]) -> Dict[str, Any]:
        """Prepare data summary for AI insights generation"""
        # Extract query info from first item's URL
        query_info = "N/A"
        if self.collected_data and len(self.collected_data) > 0:
            url = self.collected_data[0]["url"]
            query_parts = url.split('/')[-1].replace('-', ' ').replace('_', ' ')
            query_info = query_parts
            
        # Get top entities
        top_entities = [e for e, _ in sorted(entity_counts.items(), key=lambda x: x[1], reverse=True)[:5]]
        
        # Calculate timespan from timestamps
        timespan = self._calculate_timespan()
        
        # Prepare complete data summary
        return {
            "query": query_info,
            "sources": len(self.collected_data),
            "top_entities": top_entities,
            "timespan": timespan,
            "domains": [urlparse(item["url"]).netloc for item in self.collected_data],
            "sentiments": [self.analysis_results[item["url"]]["sentiment"] 
                          for item in self.collected_data 
                          if item["url"] in self.analysis_results]
        }
    
    def _calculate_timespan(self) -> str:
        """Calculate the timespan of data from timestamps"""
        timespan = "Recent"
        dates = []
        
        for url, analysis in self.analysis_results.items():
            if "timestamps" in analysis and "published" in analysis["timestamps"]:
                pub_date = analysis["timestamps"]["published"]
                if pub_date and pub_date != "N/A":
                    dates.append(pub_date)
        
        if dates:
            try:
                min_date = min(dates)
                max_date = max(dates)
                timespan = f"{min_date} to {max_date}"
            except Exception:
                pass
                
        return timespan
    
    def _show_export_options(self) -> None:
        """Display export options"""
        self.console.print("\n[bold blue]Export Options:[/bold blue]")
        self.console.print("1. Export as JSON (Pydantic model_dump_json)")
        self.console.print("2. Export as CSV")
        self.console.print("3. Generate visualization")

    def save_data(self, filename: str = "osint_data.json") -> None:
        """Save the collected data to a file using Pydantic for JSON serialization."""
        # Create a Pydantic model for the full report
        report = OSINTReport(
            collected_data=self.collected_data,
            analysis_results=self.analysis_results,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            query_info={
                "queries_executed": len(self.collected_data)
            }
        )
        
        # Use model_dump_json to properly serialize the data
        with open(filename, 'w') as f:
            f.write(report.model_dump_json(indent=4))
        
        self.console.print(f"[green]Data saved to {filename} using Pydantic serialization[/green]")

    def _generate_simulated_results(self, query: str, count: int) -> List[Dict[str, str]]:
        """Generate simulated search results."""
        simulated_results = []
        domains = ["example.com", "newsportal.org", "research.edu", "dataresearch.org", 
                  "gov.reports.org", "analysis.net", "insights.io", "factfinder.com",
                  "academicjournal.edu", "trustednews.com"]
        source_types = ["Article", "Research", "News", "Blog", "Government", "Academic", "Analysis"]
        title_prefixes = ["Analysis of", "Report on", "Latest on", "Deep Dive into", 
                        "Investigation of", "Overview of", "Update on", "Trends in"]
        
        for i in range(count):
            domain = domains[i % len(domains)]
            source_type = source_types[i % len(source_types)]
            title_prefix = title_prefixes[i % len(title_prefixes)]
            
            result = {
                "title": f"{title_prefix} {query}: Part {i+1}",
                "url": f"https://{domain}/analysis/{query.lower().replace(' ', '-')}-part-{i+1}",
                "snippet": f"This {source_type.lower()} provides insight {i+1} about {query}, revealing important details and context...",
                "source_type": source_type,
                "timestamp": datetime.now().strftime("%Y-%m-%d")
            }
            simulated_results.append(result)
            
        return simulated_results

def main():
    parser = argparse.ArgumentParser(description="OSINT Assistant - A tool for collecting and analyzing open-source intelligence with AI capabilities")
    parser.add_argument("--query", "-q", type=str, help="The search query to investigate")
    parser.add_argument("--results", "-r", type=int, default=10, help="Number of results to collect")
    parser.add_argument("--save", "-s", action="store_true", help="Save the collected data")
    parser.add_argument("--api-key", "-k", type=str, help="Perplexity API key for AI-enhanced capabilities (overrides .env file)")
    parser.add_argument("--json", "-j", action="store_true", help="Output results as JSON")
    
    args = parser.parse_args()
    
    # Initialize with API key if provided
    assistant = OSINTAssistant(api_key=args.api_key)
    
    if args.query:
        search_results = assistant.search_web(args.query, args.results)
        
        # Analyze each result
        for item in assistant.collected_data:
            analysis = assistant.analyze_content(item["url"])
        
        # Generate report or output JSON
        if args.json:
            # Create report object
            report = OSINTReport(
                collected_data=assistant.collected_data,
                analysis_results=assistant.analysis_results,
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                query_info={
                    "query": args.query,
                    "results_requested": args.results,
                    "results_found": len(assistant.collected_data)
                }
            )
            
            # Output as JSON
            print(report.model_dump_json(indent=2))
        else:
            # Generate human-readable report
            assistant.generate_report()
        
        # Save data if requested
        if args.save:
            assistant.save_data()
    else:
        print("Please provide a search query using the --query or -q option")

if __name__ == "__main__":
    main() 