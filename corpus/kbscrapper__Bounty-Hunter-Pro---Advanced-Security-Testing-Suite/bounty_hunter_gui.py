#!/usr/bin/env python3
"""
Bounty Hunter Pro - Advanced Security Testing GUI Application
Professional vulnerability assessment and bug bounty automation tool
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import json
import time
import webbrowser
from datetime import datetime
import os
import sys

# Import our security modules
try:
    from security_modules import VulnerabilityScanner
except ImportError:
    print("Error: security_modules.py not found. Please ensure it's in the same directory.")
    sys.exit(1)

class BountyHunterGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Bounty Hunter Pro (KBA)- Advanced Security Testing Suite")
        self.root.geometry("1200x800")
        self.root.configure(bg='#1a1a1a')
        
        # Initialize scanner
        self.scanner = VulnerabilityScanner()
        self.current_scan_thread = None
        self.scan_results = None
        
        # Configure styles
        self.setup_styles()
        
        # Create GUI components
        self.create_header()
        self.create_input_section()
        self.create_control_panel()
        self.create_results_section()
        self.create_status_bar()
        
        # Legal disclaimer
        self.show_disclaimer()
    
    def setup_styles(self):
        """Configure custom styles for the application"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure colors
        style.configure('Title.TLabel', 
                       background='#1a1a1a', 
                       foreground='#00ff00', 
                       font=('Consolas', 16, 'bold'))
        
        style.configure('Header.TLabel', 
                       background='#1a1a1a', 
                       foreground='#ffffff', 
                       font=('Consolas', 12, 'bold'))
        
        style.configure('Custom.TButton',
                       background='#333333',
                       foreground='#ffffff',
                       font=('Consolas', 10, 'bold'))
        
        style.configure('Danger.TButton',
                       background='#ff4444',
                       foreground='#ffffff',
                       font=('Consolas', 10, 'bold'))
        
        style.configure('Success.TButton',
                       background='#44ff44',
                       foreground='#000000',
                       font=('Consolas', 10, 'bold'))
    
    def create_header(self):
        """Create the application header"""
        header_frame = tk.Frame(self.root, bg='#1a1a1a', height=80)
        header_frame.pack(fill='x', padx=10, pady=5)
        header_frame.pack_propagate(False)
        
        # Title
        title_label = ttk.Label(header_frame, 
                               text="🎯 BOUNTY HUNTER PRO (KBSCRAPPER)", 
                               style='Title.TLabel')
        title_label.pack(side='left', pady=20)
        
        # Subtitle
        subtitle_label = ttk.Label(header_frame, 
                                  text="Advanced Security Testing & Vulnerability Assessment Suite", 
                                  style='Header.TLabel')
        subtitle_label.pack(side='left', padx=(20, 0), pady=20)
        
        # Version info
        version_label = ttk.Label(header_frame, 
                                 text="v2.0 | Professional Edition", 
                                 background='#1a1a1a', 
                                 foreground='#888888',
                                 font=('Consolas', 8))
        version_label.pack(side='right', pady=20)
    
    def create_input_section(self):
        """Create the URL input section"""
        input_frame = tk.Frame(self.root, bg='#1a1a1a')
        input_frame.pack(fill='x', padx=10, pady=5)
        
        # URL input
        url_label = ttk.Label(input_frame, 
                             text="Target URL:", 
                             background='#1a1a1a', 
                             foreground='#ffffff',
                             font=('Consolas', 10, 'bold'))
        url_label.pack(side='left', padx=(0, 10))
        
        self.url_var = tk.StringVar()
        self.url_entry = tk.Entry(input_frame, 
                                 textvariable=self.url_var,
                                 font=('Consolas', 10),
                                 bg='#333333',
                                 fg='#ffffff',
                                 insertbackground='#ffffff',
                                 width=60)
        self.url_entry.pack(side='left', padx=(0, 10), ipady=5)
        
        # Scan type selection
        scan_label = ttk.Label(input_frame, 
                              text="Scan Type:", 
                              background='#1a1a1a', 
                              foreground='#ffffff',
                              font=('Consolas', 10, 'bold'))
        scan_label.pack(side='left', padx=(20, 10))
        
        self.scan_type_var = tk.StringVar(value="Full Scan")
        scan_combo = ttk.Combobox(input_frame, 
                                 textvariable=self.scan_type_var,
                                 values=["Full Scan", "Quick Scan", "SQL Injection Only", "XSS Only", "Directory Enum Only"],
                                 state="readonly",
                                 font=('Consolas', 9),
                                 width=15)
        scan_combo.pack(side='left')
    
    def create_control_panel(self):
        """Create the control panel with buttons"""
        control_frame = tk.Frame(self.root, bg='#1a1a1a')
        control_frame.pack(fill='x', padx=10, pady=10)
        
        # Start scan button
        self.start_button = tk.Button(control_frame,
                                     text="🚀 START SCAN",
                                     command=self.start_scan,
                                     bg='#00aa00',
                                     fg='#ffffff',
                                     font=('Consolas', 12, 'bold'),
                                     padx=20,
                                     pady=5)
        self.start_button.pack(side='left', padx=(0, 10))
        
        # Stop scan button
        self.stop_button = tk.Button(control_frame,
                                    text="⏹️ STOP SCAN",
                                    command=self.stop_scan,
                                    bg='#aa0000',
                                    fg='#ffffff',
                                    font=('Consolas', 12, 'bold'),
                                    padx=20,
                                    pady=5,
                                    state='disabled')
        self.stop_button.pack(side='left', padx=(0, 10))
        
        # Export results button
        self.export_button = tk.Button(control_frame,
                                      text="💾 EXPORT RESULTS",
                                      command=self.export_results,
                                      bg='#0066aa',
                                      fg='#ffffff',
                                      font=('Consolas', 12, 'bold'),
                                      padx=20,
                                      pady=5,
                                      state='disabled')
        self.export_button.pack(side='left', padx=(0, 10))
        
        # Clear results button
        clear_button = tk.Button(control_frame,
                                text="🗑️ CLEAR",
                                command=self.clear_results,
                                bg='#666666',
                                fg='#ffffff',
                                font=('Consolas', 12, 'bold'),
                                padx=20,
                                pady=5)
        clear_button.pack(side='left', padx=(0, 10))
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(control_frame,
                                           variable=self.progress_var,
                                           maximum=100,
                                           length=200,
                                           mode='indeterminate')
        self.progress_bar.pack(side='right', padx=(10, 0))
        
        # Progress label
        self.progress_label = tk.Label(control_frame,
                                      text="Ready",
                                      bg='#1a1a1a',
                                      fg='#ffffff',
                                      font=('Consolas', 10))
        self.progress_label.pack(side='right', padx=(10, 10))
    
    def create_results_section(self):
        """Create the results display section with tabs"""
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Overview tab
        self.overview_frame = tk.Frame(self.notebook, bg='#2a2a2a')
        self.notebook.add(self.overview_frame, text="📊 Overview")
        
        self.overview_text = scrolledtext.ScrolledText(self.overview_frame,
                                                      bg='#2a2a2a',
                                                      fg='#ffffff',
                                                      font=('Consolas', 10),
                                                      wrap=tk.WORD)
        self.overview_text.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Vulnerabilities tab
        self.vulns_frame = tk.Frame(self.notebook, bg='#2a2a2a')
        self.notebook.add(self.vulns_frame, text="🚨 Vulnerabilities")
        
        # Create treeview for vulnerabilities
        vulns_columns = ('Type', 'Severity', 'Location', 'Evidence')
        self.vulns_tree = ttk.Treeview(self.vulns_frame, columns=vulns_columns, show='headings', height=15)
        
        for col in vulns_columns:
            self.vulns_tree.heading(col, text=col)
            self.vulns_tree.column(col, width=200)
        
        vulns_scrollbar = ttk.Scrollbar(self.vulns_frame, orient='vertical', command=self.vulns_tree.yview)
        self.vulns_tree.configure(yscrollcommand=vulns_scrollbar.set)
        
        self.vulns_tree.pack(side='left', fill='both', expand=True, padx=5, pady=5)
        vulns_scrollbar.pack(side='right', fill='y', pady=5)
        
        # Information tab
        self.info_frame = tk.Frame(self.notebook, bg='#2a2a2a')
        self.notebook.add(self.info_frame, text="ℹ️ Information")
        
        self.info_text = scrolledtext.ScrolledText(self.info_frame,
                                                  bg='#2a2a2a',
                                                  fg='#ffffff',
                                                  font=('Consolas', 10),
                                                  wrap=tk.WORD)
        self.info_text.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Directories tab
        self.dirs_frame = tk.Frame(self.notebook, bg='#2a2a2a')
        self.notebook.add(self.dirs_frame, text="📁 Directories")
        
        dirs_columns = ('Type', 'URL', 'Status', 'Size')
        self.dirs_tree = ttk.Treeview(self.dirs_frame, columns=dirs_columns, show='headings', height=15)
        
        for col in dirs_columns:
            self.dirs_tree.heading(col, text=col)
            self.dirs_tree.column(col, width=200)
        
        dirs_scrollbar = ttk.Scrollbar(self.dirs_frame, orient='vertical', command=self.dirs_tree.yview)
        self.dirs_tree.configure(yscrollcommand=dirs_scrollbar.set)
        
        self.dirs_tree.pack(side='left', fill='both', expand=True, padx=5, pady=5)
        dirs_scrollbar.pack(side='right', fill='y', pady=5)
        
        # Raw data tab
        self.raw_frame = tk.Frame(self.notebook, bg='#2a2a2a')
        self.notebook.add(self.raw_frame, text="📄 Raw Data")
        
        self.raw_text = scrolledtext.ScrolledText(self.raw_frame,
                                                 bg='#2a2a2a',
                                                 fg='#ffffff',
                                                 font=('Consolas', 9),
                                                 wrap=tk.WORD)
        self.raw_text.pack(fill='both', expand=True, padx=5, pady=5)
    
    def create_status_bar(self):
        """Create the status bar"""
        self.status_frame = tk.Frame(self.root, bg='#333333', height=25)
        self.status_frame.pack(fill='x', side='bottom')
        self.status_frame.pack_propagate(False)
        
        self.status_label = tk.Label(self.status_frame,
                                    text="Ready for scanning",
                                    bg='#333333',
                                    fg='#ffffff',
                                    font=('Consolas', 9),
                                    anchor='w')
        self.status_label.pack(side='left', padx=10, pady=2)
        
        # Time label
        self.time_label = tk.Label(self.status_frame,
                                  text="",
                                  bg='#333333',
                                  fg='#ffffff',
                                  font=('Consolas', 9))
        self.time_label.pack(side='right', padx=10, pady=2)
        
        self.update_time()
    
    def update_time(self):
        """Update the time display"""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.time_label.config(text=current_time)
        self.root.after(1000, self.update_time)
    
    def show_disclaimer(self):
        """Show legal disclaimer"""
        disclaimer = """
LEGAL DISCLAIMER

This tool is designed for authorized security testing and educational purposes only.

By using this software, you agree that:
• You will only test systems you own or have explicit permission to test
• You understand the legal implications of security testing
• You will not use this tool for malicious purposes
• You take full responsibility for your actions

Unauthorized access to computer systems is illegal and may result in criminal charges.

Do you agree to these terms and conditions?
        """
        
        result = messagebox.askyesno("Legal Disclaimer", disclaimer)
        if not result:
            self.root.quit()
    
    def start_scan(self):
        """Start the security scan"""
        url = self.url_var.get().strip()
        if not url:
            messagebox.showerror("Error", "Please enter a target URL")
            return
        
        # Confirm scan
        confirm = messagebox.askyesno("Confirm Scan", 
                                     f"Are you authorized to test {url}?\n\nOnly proceed if you have explicit permission.")
        if not confirm:
            return
        
        # Disable start button, enable stop button
        self.start_button.config(state='disabled')
        self.stop_button.config(state='normal')
        
        # Start progress bar
        self.progress_bar.start()
        
        # Clear previous results
        self.clear_results()
        
        # Start scan in separate thread
        self.current_scan_thread = threading.Thread(target=self.run_scan, args=(url,))
        self.current_scan_thread.daemon = True
        self.current_scan_thread.start()
    
    def run_scan(self, url):
        """Run the actual scan"""
        try:
            def progress_callback(message):
                self.root.after(0, lambda: self.update_progress(message))
            
            # Perform the scan
            self.scan_results = self.scanner.full_scan(url, progress_callback)
            
            # Update GUI with results
            self.root.after(0, self.display_results)
            
        except Exception as e:
            self.root.after(0, lambda: self.scan_error(str(e)))
    
    def update_progress(self, message):
        """Update progress display"""
        self.progress_label.config(text=message)
        self.status_label.config(text=f"Scanning: {message}")
    
    def display_results(self):
        """Display scan results in the GUI"""
        if not self.scan_results:
            return
        
        # Overview
        overview = f"""
SCAN RESULTS SUMMARY
{'='*50}

Target URL: {self.scan_results['url']}
Scan Time: {self.scan_results['timestamp']}
Status: {self.scan_results['scan_status']}

VULNERABILITY SUMMARY:
Total Vulnerabilities Found: {len(self.scan_results['vulnerabilities'])}

High Severity: {len([v for v in self.scan_results['vulnerabilities'] if v.get('severity') == 'High'])}
Medium Severity: {len([v for v in self.scan_results['vulnerabilities'] if v.get('severity') == 'Medium'])}
Low Severity: {len([v for v in self.scan_results['vulnerabilities'] if v.get('severity') == 'Low'])}

DISCOVERY SUMMARY:
Directories/Files Found: {len(self.scan_results['directories'])}

{'='*50}
        """
        
        self.overview_text.delete(1.0, tk.END)
        self.overview_text.insert(tk.END, overview)
        
        # Vulnerabilities
        for item in self.vulns_tree.get_children():
            self.vulns_tree.delete(item)
        
        for vuln in self.scan_results['vulnerabilities']:
            self.vulns_tree.insert('', 'end', values=(
                vuln.get('type', 'Unknown'),
                vuln.get('severity', 'Unknown'),
                vuln.get('location', 'Unknown'),
                vuln.get('evidence', 'No evidence')[:100] + '...' if len(vuln.get('evidence', '')) > 100 else vuln.get('evidence', 'No evidence')
            ))
        
        # Information
        info_text = json.dumps(self.scan_results['information'], indent=2)
        self.info_text.delete(1.0, tk.END)
        self.info_text.insert(tk.END, info_text)
        
        # Directories
        for item in self.dirs_tree.get_children():
            self.dirs_tree.delete(item)
        
        for directory in self.scan_results['directories']:
            self.dirs_tree.insert('', 'end', values=(
                directory.get('type', 'Unknown'),
                directory.get('url', 'Unknown'),
                directory.get('status_code', 'Unknown'),
                directory.get('size', 'Unknown')
            ))
        
        # Raw data
        raw_data = json.dumps(self.scan_results, indent=2)
        self.raw_text.delete(1.0, tk.END)
        self.raw_text.insert(tk.END, raw_data)
        
        # Update status
        self.scan_complete()
    
    def scan_complete(self):
        """Handle scan completion"""
        self.progress_bar.stop()
        self.progress_label.config(text="Scan Complete")
        self.status_label.config(text="Scan completed successfully")
        
        self.start_button.config(state='normal')
        self.stop_button.config(state='disabled')
        self.export_button.config(state='normal')
        
        # Show completion message
        vuln_count = len(self.scan_results['vulnerabilities']) if self.scan_results else 0
        messagebox.showinfo("Scan Complete", 
                           f"Security scan completed!\n\nVulnerabilities found: {vuln_count}")
    
    def scan_error(self, error_message):
        """Handle scan errors"""
        self.progress_bar.stop()
        self.progress_label.config(text="Error")
        self.status_label.config(text=f"Scan failed: {error_message}")
        
        self.start_button.config(state='normal')
        self.stop_button.config(state='disabled')
        
        messagebox.showerror("Scan Error", f"An error occurred during scanning:\n\n{error_message}")
    
    def stop_scan(self):
        """Stop the current scan"""
        if self.current_scan_thread and self.current_scan_thread.is_alive():
            # Note: Python threading doesn't support clean termination
            # In a production environment, you'd implement proper cancellation
            messagebox.showinfo("Stop Scan", "Scan will stop after current operation completes.")
        
        self.progress_bar.stop()
        self.progress_label.config(text="Stopping...")
        self.status_label.config(text="Scan stopped by user")
        
        self.start_button.config(state='normal')
        self.stop_button.config(state='disabled')
    
    def export_results(self):
        """Export scan results to file"""
        if not self.scan_results:
            messagebox.showerror("Error", "No scan results to export")
            return
        
        # Ask for file location
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                with open(filename, 'w') as f:
                    if filename.endswith('.json'):
                        json.dump(self.scan_results, f, indent=2)
                    else:
                        # Export as formatted text
                        f.write(f"BOUNTY HUNTER PRO - SCAN RESULTS\n")
                        f.write(f"{'='*50}\n\n")
                        f.write(f"Target: {self.scan_results['url']}\n")
                        f.write(f"Scan Time: {self.scan_results['timestamp']}\n")
                        f.write(f"Status: {self.scan_results['scan_status']}\n\n")
                        
                        f.write(f"VULNERABILITIES FOUND: {len(self.scan_results['vulnerabilities'])}\n")
                        f.write(f"{'-'*30}\n")
                        for vuln in self.scan_results['vulnerabilities']:
                            f.write(f"Type: {vuln.get('type', 'Unknown')}\n")
                            f.write(f"Severity: {vuln.get('severity', 'Unknown')}\n")
                            f.write(f"Location: {vuln.get('location', 'Unknown')}\n")
                            f.write(f"Evidence: {vuln.get('evidence', 'No evidence')}\n")
                            f.write(f"URL: {vuln.get('url', 'Unknown')}\n\n")
                        
                        f.write(f"DIRECTORIES/FILES FOUND: {len(self.scan_results['directories'])}\n")
                        f.write(f"{'-'*30}\n")
                        for directory in self.scan_results['directories']:
                            f.write(f"Type: {directory.get('type', 'Unknown')}\n")
                            f.write(f"URL: {directory.get('url', 'Unknown')}\n")
                            f.write(f"Status: {directory.get('status_code', 'Unknown')}\n\n")
                
                messagebox.showinfo("Export Complete", f"Results exported to {filename}")
                
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to export results:\n{str(e)}")
    
    def clear_results(self):
        """Clear all results"""
        self.overview_text.delete(1.0, tk.END)
        self.info_text.delete(1.0, tk.END)
        self.raw_text.delete(1.0, tk.END)
        
        for item in self.vulns_tree.get_children():
            self.vulns_tree.delete(item)
        
        for item in self.dirs_tree.get_children():
            self.dirs_tree.delete(item)
        
        self.export_button.config(state='disabled')
        self.scan_results = None

def main():
    """Main application entry point"""
    root = tk.Tk()
    app = BountyHunterGUI(root)
    
    # Center the window
    root.update_idletasks()
    x = (root.winfo_screenwidth() // 2) - (root.winfo_width() // 2)
    y = (root.winfo_screenheight() // 2) - (root.winfo_height() // 2)
    root.geometry(f"+{x}+{y}")
    
    root.mainloop()

if __name__ == "__main__":
    main()

