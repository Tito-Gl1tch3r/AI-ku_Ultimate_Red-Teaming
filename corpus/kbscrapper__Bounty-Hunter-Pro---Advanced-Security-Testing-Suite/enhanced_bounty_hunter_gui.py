#!/usr/bin/env python3
"""
Bounty Hunter Pro - Enhanced with Active Exploitation
Professional vulnerability assessment and active penetration testing tool
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

# Import our security and exploitation modules
try:
    from security_modules import VulnerabilityScanner
    from exploitation_modules import AdvancedExploitationEngine
except ImportError as e:
    print(f"Error: Required modules not found. {e}")
    sys.exit(1)

class EnhancedBountyHunterGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Bounty Hunter Pro (KBA)- Advanced Security Testing & Exploitation Suite")
        self.root.geometry("1400x900")
        self.root.configure(bg='#0a0a0a')
        
        # Initialize scanners
        self.scanner = VulnerabilityScanner()
        self.exploiter = AdvancedExploitationEngine()
        self.current_scan_thread = None
        self.current_exploit_thread = None
        self.scan_results = None
        self.exploitation_results = None
        
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
        
        # Configure colors for dark theme
        style.configure('Title.TLabel', 
                       background='#0a0a0a', 
                       foreground='#ff0000', 
                       font=('Consolas', 18, 'bold'))
        
        style.configure('Header.TLabel', 
                       background='#0a0a0a', 
                       foreground='#ffffff', 
                       font=('Consolas', 12, 'bold'))
        
        style.configure('Exploit.TButton',
                       background='#ff0000',
                       foreground='#ffffff',
                       font=('Consolas', 12, 'bold'))
        
        style.configure('Danger.TButton',
                       background='#ff4444',
                       foreground='#ffffff',
                       font=('Consolas', 10, 'bold'))
        
        style.configure('Success.TButton',
                       background='#00ff00',
                       foreground='#000000',
                       font=('Consolas', 10, 'bold'))
    
    def create_header(self):
        """Create the application header"""
        header_frame = tk.Frame(self.root, bg='#0a0a0a', height=100)
        header_frame.pack(fill='x', padx=10, pady=5)
        header_frame.pack_propagate(False)
        
        # Title with hacker aesthetic
        title_label = ttk.Label(header_frame, 
                               text="⚡ BOUNTY HUNTER PRO (KBSCRAPPER)⚡", 
                               style='Title.TLabel')
        title_label.pack(side='left', pady=25)
        
        # Subtitle
        subtitle_label = ttk.Label(header_frame, 
                                  text="Advanced Security Testing & Active Exploitation Suite", 
                                  style='Header.TLabel')
        subtitle_label.pack(side='left', padx=(20, 0), pady=25)
        
        # Version and mode info
        mode_label = ttk.Label(header_frame, 
                              text="EXPLOITATION MODE ENABLED | v3.0 | PROFESSIONAL EDITION", 
                              background='#0a0a0a', 
                              foreground='#ff0000',
                              font=('Consolas', 9, 'bold'))
        mode_label.pack(side='right', pady=25)
    
    def create_input_section(self):
        """Create the URL input section"""
        input_frame = tk.Frame(self.root, bg='#0a0a0a')
        input_frame.pack(fill='x', padx=10, pady=5)
        
        # URL input
        url_label = ttk.Label(input_frame, 
                             text="TARGET URL:", 
                             background='#0a0a0a', 
                             foreground='#ffffff',
                             font=('Consolas', 11, 'bold'))
        url_label.pack(side='left', padx=(0, 10))
        
        self.url_var = tk.StringVar()
        self.url_entry = tk.Entry(input_frame, 
                                 textvariable=self.url_var,
                                 font=('Consolas', 11),
                                 bg='#1a1a1a',
                                 fg='#00ff00',
                                 insertbackground='#00ff00',
                                 width=50)
        self.url_entry.pack(side='left', padx=(0, 15), ipady=6)
        
        # Operation mode selection
        mode_label = ttk.Label(input_frame, 
                              text="MODE:", 
                              background='#0a0a0a', 
                              foreground='#ffffff',
                              font=('Consolas', 11, 'bold'))
        mode_label.pack(side='left', padx=(20, 10))
        
        self.operation_mode_var = tk.StringVar(value="Scan + Exploit")
        mode_combo = ttk.Combobox(input_frame, 
                                 textvariable=self.operation_mode_var,
                                 values=["Scan Only", "Scan + Exploit", "Exploit Only"],
                                 state="readonly",
                                 font=('Consolas', 10),
                                 width=15)
        mode_combo.pack(side='left')
        
        # Exploitation intensity
        intensity_label = ttk.Label(input_frame, 
                                   text="INTENSITY:", 
                                   background='#0a0a0a', 
                                   foreground='#ffffff',
                                   font=('Consolas', 11, 'bold'))
        intensity_label.pack(side='left', padx=(20, 10))
        
        self.intensity_var = tk.StringVar(value="Aggressive")
        intensity_combo = ttk.Combobox(input_frame, 
                                      textvariable=self.intensity_var,
                                      values=["Passive", "Normal", "Aggressive", "Maximum"],
                                      state="readonly",
                                      font=('Consolas', 10),
                                      width=12)
        intensity_combo.pack(side='left')
    
    def create_control_panel(self):
        """Create the control panel with buttons"""
        control_frame = tk.Frame(self.root, bg='#0a0a0a')
        control_frame.pack(fill='x', padx=10, pady=15)
        
        # Start scan button
        self.start_button = tk.Button(control_frame,
                                     text="🚀 START OPERATION",
                                     command=self.start_operation,
                                     bg='#00aa00',
                                     fg='#ffffff',
                                     font=('Consolas', 14, 'bold'),
                                     padx=25,
                                     pady=8)
        self.start_button.pack(side='left', padx=(0, 15))
        
        # Exploit button (separate)
        self.exploit_button = tk.Button(control_frame,
                                       text="💥 EXPLOIT VULNS",
                                       command=self.start_exploitation,
                                       bg='#ff0000',
                                       fg='#ffffff',
                                       font=('Consolas', 14, 'bold'),
                                       padx=25,
                                       pady=8,
                                       state='disabled')
        self.exploit_button.pack(side='left', padx=(0, 15))
        
        # Stop button
        self.stop_button = tk.Button(control_frame,
                                    text="⏹️ STOP",
                                    command=self.stop_operation,
                                    bg='#aa0000',
                                    fg='#ffffff',
                                    font=('Consolas', 14, 'bold'),
                                    padx=25,
                                    pady=8,
                                    state='disabled')
        self.stop_button.pack(side='left', padx=(0, 15))
        
        # Export results button
        self.export_button = tk.Button(control_frame,
                                      text="💾 EXPORT",
                                      command=self.export_results,
                                      bg='#0066aa',
                                      fg='#ffffff',
                                      font=('Consolas', 14, 'bold'),
                                      padx=25,
                                      pady=8,
                                      state='disabled')
        self.export_button.pack(side='left', padx=(0, 15))
        
        # Clear button
        clear_button = tk.Button(control_frame,
                                text="🗑️ CLEAR",
                                command=self.clear_results,
                                bg='#666666',
                                fg='#ffffff',
                                font=('Consolas', 14, 'bold'),
                                padx=25,
                                pady=8)
        clear_button.pack(side='left', padx=(0, 15))
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(control_frame,
                                           variable=self.progress_var,
                                           maximum=100,
                                           length=250,
                                           mode='indeterminate')
        self.progress_bar.pack(side='right', padx=(15, 0))
        
        # Progress label
        self.progress_label = tk.Label(control_frame,
                                      text="Ready for operation",
                                      bg='#0a0a0a',
                                      fg='#00ff00',
                                      font=('Consolas', 11, 'bold'))
        self.progress_label.pack(side='right', padx=(15, 15))
    
    def create_results_section(self):
        """Create the results display section with enhanced tabs"""
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Overview tab
        self.overview_frame = tk.Frame(self.notebook, bg='#1a1a1a')
        self.notebook.add(self.overview_frame, text="📊 OVERVIEW")
        
        self.overview_text = scrolledtext.ScrolledText(self.overview_frame,
                                                      bg='#1a1a1a',
                                                      fg='#00ff00',
                                                      font=('Consolas', 10),
                                                      wrap=tk.WORD)
        self.overview_text.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Vulnerabilities tab
        self.vulns_frame = tk.Frame(self.notebook, bg='#1a1a1a')
        self.notebook.add(self.vulns_frame, text="🚨 VULNERABILITIES")
        
        vulns_columns = ('Type', 'Severity', 'Location', 'Status', 'Evidence')
        self.vulns_tree = ttk.Treeview(self.vulns_frame, columns=vulns_columns, show='headings', height=15)
        
        for col in vulns_columns:
            self.vulns_tree.heading(col, text=col)
            self.vulns_tree.column(col, width=180)
        
        vulns_scrollbar = ttk.Scrollbar(self.vulns_frame, orient='vertical', command=self.vulns_tree.yview)
        self.vulns_tree.configure(yscrollcommand=vulns_scrollbar.set)
        
        self.vulns_tree.pack(side='left', fill='both', expand=True, padx=5, pady=5)
        vulns_scrollbar.pack(side='right', fill='y', pady=5)
        
        # Exploitation Results tab
        self.exploits_frame = tk.Frame(self.notebook, bg='#1a1a1a')
        self.notebook.add(self.exploits_frame, text="💥 EXPLOITATIONS")
        
        exploits_columns = ('Type', 'Target', 'Status', 'Impact', 'Data')
        self.exploits_tree = ttk.Treeview(self.exploits_frame, columns=exploits_columns, show='headings', height=15)
        
        for col in exploits_columns:
            self.exploits_tree.heading(col, text=col)
            self.exploits_tree.column(col, width=180)
        
        exploits_scrollbar = ttk.Scrollbar(self.exploits_frame, orient='vertical', command=self.exploits_tree.yview)
        self.exploits_tree.configure(yscrollcommand=exploits_scrollbar.set)
        
        self.exploits_tree.pack(side='left', fill='both', expand=True, padx=5, pady=5)
        exploits_scrollbar.pack(side='right', fill='y', pady=5)
        
        # Shells tab
        self.shells_frame = tk.Frame(self.notebook, bg='#1a1a1a')
        self.notebook.add(self.shells_frame, text="🐚 SHELLS")
        
        self.shells_text = scrolledtext.ScrolledText(self.shells_frame,
                                                    bg='#1a1a1a',
                                                    fg='#ff0000',
                                                    font=('Consolas', 10),
                                                    wrap=tk.WORD)
        self.shells_text.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Information tab
        self.info_frame = tk.Frame(self.notebook, bg='#1a1a1a')
        self.notebook.add(self.info_frame, text="ℹ️ INTELLIGENCE")
        
        self.info_text = scrolledtext.ScrolledText(self.info_frame,
                                                  bg='#1a1a1a',
                                                  fg='#ffffff',
                                                  font=('Consolas', 10),
                                                  wrap=tk.WORD)
        self.info_text.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Raw data tab
        self.raw_frame = tk.Frame(self.notebook, bg='#1a1a1a')
        self.notebook.add(self.raw_frame, text="📄 RAW DATA")
        
        self.raw_text = scrolledtext.ScrolledText(self.raw_frame,
                                                 bg='#1a1a1a',
                                                 fg='#888888',
                                                 font=('Consolas', 9),
                                                 wrap=tk.WORD)
        self.raw_text.pack(fill='both', expand=True, padx=5, pady=5)
    
    def create_status_bar(self):
        """Create the status bar"""
        self.status_frame = tk.Frame(self.root, bg='#ff0000', height=30)
        self.status_frame.pack(fill='x', side='bottom')
        self.status_frame.pack_propagate(False)
        
        self.status_label = tk.Label(self.status_frame,
                                    text="EXPLOITATION MODE ACTIVE - Ready for authorized penetration testing",
                                    bg='#ff0000',
                                    fg='#ffffff',
                                    font=('Consolas', 10, 'bold'),
                                    anchor='w')
        self.status_label.pack(side='left', padx=15, pady=5)
        
        # Time label
        self.time_label = tk.Label(self.status_frame,
                                  text="",
                                  bg='#ff0000',
                                  fg='#ffffff',
                                  font=('Consolas', 10, 'bold'))
        self.time_label.pack(side='right', padx=15, pady=5)
        
        self.update_time()
    
    def update_time(self):
        """Update the time display"""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.time_label.config(text=current_time)
        self.root.after(1000, self.update_time)
    
    def show_disclaimer(self):
        """Show enhanced legal disclaimer"""
        disclaimer = """
⚠️ CRITICAL LEGAL DISCLAIMER - EXPLOITATION MODE ⚠️

This tool includes ACTIVE EXPLOITATION capabilities that can:
• Execute code on target systems
• Extract sensitive data
• Modify system configurations
• Establish persistent access

LEGAL REQUIREMENTS:
• You MUST have explicit written authorization
• You MUST be the system owner OR have legal permission
• Unauthorized access is a CRIMINAL OFFENSE
• You are FULLY RESPONSIBLE for all actions

ETHICAL OBLIGATIONS:
• Only test authorized systems
• Follow responsible disclosure
• Respect scope limitations
• Document all activities

By proceeding, you confirm:
✓ You have proper authorization
✓ You understand the legal risks
✓ You will use this tool ethically
✓ You accept full responsibility

Do you have proper authorization and agree to these terms?
        """
        
        result = messagebox.askyesno("⚠️ EXPLOITATION MODE DISCLAIMER ⚠️", disclaimer)
        if not result:
            self.root.quit()
    
    def start_operation(self):
        """Start the security operation"""
        url = self.url_var.get().strip()
        if not url:
            messagebox.showerror("Error", "Please enter a target URL")
            return
        
        mode = self.operation_mode_var.get()
        
        # Enhanced confirmation
        confirm_msg = f"""
CONFIRM OPERATION

Target: {url}
Mode: {mode}
Intensity: {self.intensity_var.get()}

⚠️ WARNING: This will perform active security testing.
Only proceed if you have explicit authorization.

Are you authorized to test this target?
        """
        
        confirm = messagebox.askyesno("⚠️ CONFIRM OPERATION ⚠️", confirm_msg)
        if not confirm:
            return
        
        # Update UI state
        self.start_button.config(state='disabled')
        self.stop_button.config(state='normal')
        self.progress_bar.start()
        self.clear_results()
        
        # Start operation in separate thread
        if mode in ["Scan Only", "Scan + Exploit"]:
            self.current_scan_thread = threading.Thread(target=self.run_scan, args=(url, mode))
            self.current_scan_thread.daemon = True
            self.current_scan_thread.start()
        elif mode == "Exploit Only":
            if self.scan_results:
                self.start_exploitation()
            else:
                messagebox.showerror("Error", "No scan results available for exploitation")
                self.operation_complete()
    
    def run_scan(self, url, mode):
        """Run the vulnerability scan"""
        try:
            def progress_callback(message):
                self.root.after(0, lambda: self.update_progress(f"SCANNING: {message}"))
            
            # Perform the scan
            self.scan_results = self.scanner.full_scan(url, progress_callback)
            
            # Update GUI with scan results
            self.root.after(0, self.display_scan_results)
            
            # If mode includes exploitation, start it automatically
            if mode == "Scan + Exploit" and self.scan_results.get('vulnerabilities'):
                self.root.after(1000, self.start_exploitation)  # Small delay
            else:
                self.root.after(0, self.operation_complete)
            
        except Exception as e:
            self.root.after(0, lambda: self.operation_error(str(e)))
    
    def start_exploitation(self):
        """Start the exploitation phase"""
        if not self.scan_results:
            messagebox.showerror("Error", "No scan results available for exploitation")
            return
        
        vulnerabilities = self.scan_results.get('vulnerabilities', [])
        if not vulnerabilities:
            messagebox.showinfo("No Exploits", "No exploitable vulnerabilities found")
            self.operation_complete()
            return
        
        # Final confirmation for exploitation
        exploit_confirm = messagebox.askyesno(
            "⚠️ CONFIRM EXPLOITATION ⚠️",
            f"Found {len(vulnerabilities)} vulnerabilities.\n\n"
            "This will attempt ACTIVE EXPLOITATION.\n"
            "Are you sure you want to proceed?"
        )
        
        if not exploit_confirm:
            self.operation_complete()
            return
        
        self.exploit_button.config(state='disabled')
        
        # Start exploitation in separate thread
        self.current_exploit_thread = threading.Thread(target=self.run_exploitation)
        self.current_exploit_thread.daemon = True
        self.current_exploit_thread.start()
    
    def run_exploitation(self):
        """Run the exploitation phase"""
        try:
            def progress_callback(message):
                self.root.after(0, lambda: self.update_progress(f"EXPLOITING: {message}"))
            
            # Perform exploitation
            self.exploitation_results = self.exploiter.exploit_vulnerabilities(
                self.scan_results, progress_callback
            )
            
            # Update GUI with exploitation results
            self.root.after(0, self.display_exploitation_results)
            self.root.after(0, self.operation_complete)
            
        except Exception as e:
            self.root.after(0, lambda: self.operation_error(str(e)))
    
    def update_progress(self, message):
        """Update progress display"""
        self.progress_label.config(text=message)
        self.status_label.config(text=message)
    
    def display_scan_results(self):
        """Display scan results in the GUI"""
        if not self.scan_results:
            return
        
        # Overview
        overview = f"""
SECURITY ASSESSMENT RESULTS
{'='*60}

Target URL: {self.scan_results['url']}
Scan Time: {self.scan_results['timestamp']}
Status: {self.scan_results['scan_status']}

VULNERABILITY SUMMARY:
Total Vulnerabilities: {len(self.scan_results['vulnerabilities'])}

High Severity: {len([v for v in self.scan_results['vulnerabilities'] if v.get('severity') == 'High'])}
Medium Severity: {len([v for v in self.scan_results['vulnerabilities'] if v.get('severity') == 'Medium'])}
Low Severity: {len([v for v in self.scan_results['vulnerabilities'] if v.get('severity') == 'Low'])}

DISCOVERY SUMMARY:
Directories/Files Found: {len(self.scan_results['directories'])}

EXPLOITATION STATUS: {'READY' if self.scan_results['vulnerabilities'] else 'NO TARGETS'}
{'='*60}
        """
        
        self.overview_text.delete(1.0, tk.END)
        self.overview_text.insert(tk.END, overview)
        
        # Vulnerabilities
        for item in self.vulns_tree.get_children():
            self.vulns_tree.delete(item)
        
        for vuln in self.scan_results['vulnerabilities']:
            status = "EXPLOITABLE" if vuln.get('severity') in ['High', 'Critical'] else "DETECTED"
            self.vulns_tree.insert('', 'end', values=(
                vuln.get('type', 'Unknown'),
                vuln.get('severity', 'Unknown'),
                vuln.get('location', 'Unknown'),
                status,
                vuln.get('evidence', 'No evidence')[:100] + '...' if len(vuln.get('evidence', '')) > 100 else vuln.get('evidence', 'No evidence')
            ))
        
        # Information
        info_text = json.dumps(self.scan_results['information'], indent=2)
        self.info_text.delete(1.0, tk.END)
        self.info_text.insert(tk.END, info_text)
        
        # Raw data
        raw_data = json.dumps(self.scan_results, indent=2)
        self.raw_text.delete(1.0, tk.END)
        self.raw_text.insert(tk.END, raw_data)
        
        # Enable exploit button if vulnerabilities found
        if self.scan_results.get('vulnerabilities'):
            self.exploit_button.config(state='normal')
    
    def display_exploitation_results(self):
        """Display exploitation results"""
        if not self.exploitation_results:
            return
        
        # Update overview with exploitation summary
        exploitation_summary = f"""

EXPLOITATION RESULTS
{'='*60}

Exploitation Time: {self.exploitation_results['timestamp']}
Status: {self.exploitation_results['status']}

EXPLOITATION SUMMARY:
Total Exploitations: {len(self.exploitation_results['exploitations'])}
Shells Obtained: {len(self.exploitation_results['shells_obtained'])}
Privilege Escalations: {len(self.exploitation_results['privilege_escalations'])}

COMPROMISED SYSTEMS:
{chr(10).join(self.exploitation_results['shells_obtained']) if self.exploitation_results['shells_obtained'] else 'None'}

{'='*60}
        """
        
        self.overview_text.insert(tk.END, exploitation_summary)
        
        # Exploitation results
        for item in self.exploits_tree.get_children():
            self.exploits_tree.delete(item)
        
        for exploit in self.exploitation_results['exploitations']:
            self.exploits_tree.insert('', 'end', values=(
                exploit.get('type', 'Unknown'),
                exploit.get('url', 'Unknown')[:50] + '...' if len(exploit.get('url', '')) > 50 else exploit.get('url', 'Unknown'),
                'SUCCESS',
                exploit.get('impact', 'Unknown'),
                str(exploit.get('extracted_data', ''))[:100] + '...' if len(str(exploit.get('extracted_data', ''))) > 100 else str(exploit.get('extracted_data', ''))
            ))
        
        # Shells information
        shells_info = f"""
OBTAINED SHELLS AND ACCESS
{'='*40}

Total Shells: {len(self.exploitation_results['shells_obtained'])}

Shell URLs:
{chr(10).join(f"• {shell}" for shell in self.exploitation_results['shells_obtained'])}

Privilege Escalation Attempts:
{chr(10).join(f"• {pe.get('technique', 'Unknown')}: {pe.get('potential_vectors', [])}" for pe in self.exploitation_results['privilege_escalations'])}

⚠️ WARNING: These are active compromises. Use responsibly and document all activities.
        """
        
        self.shells_text.delete(1.0, tk.END)
        self.shells_text.insert(tk.END, shells_info)
        
        # Update raw data with exploitation results
        combined_data = {
            'scan_results': self.scan_results,
            'exploitation_results': self.exploitation_results
        }
        
        self.raw_text.delete(1.0, tk.END)
        self.raw_text.insert(tk.END, json.dumps(combined_data, indent=2))
    
    def operation_complete(self):
        """Handle operation completion"""
        self.progress_bar.stop()
        self.progress_label.config(text="Operation Complete")
        self.status_label.config(text="Operation completed - Review results")
        
        self.start_button.config(state='normal')
        self.stop_button.config(state='disabled')
        self.export_button.config(state='normal')
        
        # Show completion message
        vuln_count = len(self.scan_results['vulnerabilities']) if self.scan_results else 0
        exploit_count = len(self.exploitation_results['exploitations']) if self.exploitation_results else 0
        shell_count = len(self.exploitation_results['shells_obtained']) if self.exploitation_results else 0
        
        completion_msg = f"""
OPERATION COMPLETED

Vulnerabilities Found: {vuln_count}
Successful Exploitations: {exploit_count}
Shells Obtained: {shell_count}

{'⚠️ ACTIVE COMPROMISES DETECTED' if shell_count > 0 else 'Assessment completed'}
        """
        
        messagebox.showinfo("Operation Complete", completion_msg)
    
    def operation_error(self, error_message):
        """Handle operation errors"""
        self.progress_bar.stop()
        self.progress_label.config(text="Error")
        self.status_label.config(text=f"Operation failed: {error_message}")
        
        self.start_button.config(state='normal')
        self.stop_button.config(state='disabled')
        
        messagebox.showerror("Operation Error", f"An error occurred:\n\n{error_message}")
    
    def stop_operation(self):
        """Stop the current operation"""
        self.progress_bar.stop()
        self.progress_label.config(text="Stopping...")
        self.status_label.config(text="Operation stopped by user")
        
        self.start_button.config(state='normal')
        self.stop_button.config(state='disabled')
        
        messagebox.showinfo("Operation Stopped", "Operation has been stopped.")
    
    def export_results(self):
        """Export comprehensive results"""
        if not self.scan_results and not self.exploitation_results:
            messagebox.showerror("Error", "No results to export")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                export_data = {
                    'scan_results': self.scan_results,
                    'exploitation_results': self.exploitation_results,
                    'export_timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                
                with open(filename, 'w') as f:
                    if filename.endswith('.json'):
                        json.dump(export_data, f, indent=2)
                    else:
                        # Export as formatted text
                        f.write("BOUNTY HUNTER PRO - COMPREHENSIVE RESULTS\n")
                        f.write("="*60 + "\n\n")
                        
                        if self.scan_results:
                            f.write(f"SCAN RESULTS\n")
                            f.write("-"*30 + "\n")
                            f.write(f"Target: {self.scan_results['url']}\n")
                            f.write(f"Vulnerabilities: {len(self.scan_results['vulnerabilities'])}\n\n")
                        
                        if self.exploitation_results:
                            f.write(f"EXPLOITATION RESULTS\n")
                            f.write("-"*30 + "\n")
                            f.write(f"Exploitations: {len(self.exploitation_results['exploitations'])}\n")
                            f.write(f"Shells: {len(self.exploitation_results['shells_obtained'])}\n")
                            f.write(f"Shell URLs:\n")
                            for shell in self.exploitation_results['shells_obtained']:
                                f.write(f"  • {shell}\n")
                
                messagebox.showinfo("Export Complete", f"Results exported to {filename}")
                
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to export results:\n{str(e)}")
    
    def clear_results(self):
        """Clear all results"""
        self.overview_text.delete(1.0, tk.END)
        self.info_text.delete(1.0, tk.END)
        self.raw_text.delete(1.0, tk.END)
        self.shells_text.delete(1.0, tk.END)
        
        for item in self.vulns_tree.get_children():
            self.vulns_tree.delete(item)
        
        for item in self.exploits_tree.get_children():
            self.exploits_tree.delete(item)
        
        self.export_button.config(state='disabled')
        self.exploit_button.config(state='disabled')
        self.scan_results = None
        self.exploitation_results = None

def main():
    """Main application entry point"""
    root = tk.Tk()
    app = EnhancedBountyHunterGUI(root)
    
    # Center the window
    root.update_idletasks()
    x = (root.winfo_screenwidth() // 2) - (root.winfo_width() // 2)
    y = (root.winfo_screenheight() // 2) - (root.winfo_height() // 2)
    root.geometry(f"+{x}+{y}")
    
    root.mainloop()

if __name__ == "__main__":
    main()

