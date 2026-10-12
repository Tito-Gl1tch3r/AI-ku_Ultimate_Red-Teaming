using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using SubdomainScanner.Avalonia.Services;
using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Linq;
using System.Text.RegularExpressions;
using System.Threading;
using System.Threading.Tasks;
using Avalonia;
using Avalonia.Controls;
using Avalonia.Controls.ApplicationLifetimes;
using Avalonia.Platform.Storage;

namespace SubdomainScanner.Avalonia.ViewModels;

public partial class MainWindowViewModel : ViewModelBase
{
    private readonly ScannerService _scannerService;
    private CancellationTokenSource? _cancellationTokenSource;

    // Domain and scan state
    [ObservableProperty]
    private string _domain = "";

    [ObservableProperty]
    private bool _isScanning;

    [ObservableProperty]
    private bool _resolveDns = true;

    [ObservableProperty]
    private int _totalSubdomains;

    [ObservableProperty]
    private int _resolvedHosts;

    [ObservableProperty]
    private string _scanTime = "0s";

    [ObservableProperty]
    private int _activeSources;

    // Data source checkboxes
    [ObservableProperty]
    private bool _enableCrtSh = true;

    [ObservableProperty]
    private bool _enableHackerTarget = true;

    [ObservableProperty]
    private bool _enableWayback = true;

    [ObservableProperty]
    private bool _enableAlienVault = true;

    [ObservableProperty]
    private bool _enableThreatCrowd = true;

    [ObservableProperty]
    private bool _enableCommonCrawl = true;

    // Theme
    [ObservableProperty]
    private bool _isDarkMode = true;

    // Computed properties for UI validation
    public bool IsDomainInvalid => !string.IsNullOrWhiteSpace(Domain) && !IsValidDomain(Domain);

    public bool HasAnySourceSelected => EnableCrtSh || EnableHackerTarget || EnableWayback || 
                                        EnableAlienVault || EnableThreatCrowd || EnableCommonCrawl;

    // Collections
    public ObservableCollection<string> Subdomains { get; } = new();
    public ObservableCollection<string> Logs { get; } = new();

    public MainWindowViewModel()
    {
        _scannerService = new ScannerService(new SimpleHttpClientFactory());
        _scannerService.OnLog += HandleLog;
        _scannerService.OnProgress += HandleProgress;
    }

    [RelayCommand(CanExecute = nameof(CanStartScan))]
    private async Task StartScanAsync()
    {
        if (string.IsNullOrWhiteSpace(Domain))
            return;

        IsScanning = true;
        TotalSubdomains = 0;
        ResolvedHosts = 0;
        ScanTime = "0s";
        Subdomains.Clear();
        Logs.Clear();

        _cancellationTokenSource = new CancellationTokenSource();
        var startTime = DateTime.Now;

        try
        {
            var enabledSources = new List<string>();
            if (EnableCrtSh) enabledSources.Add("crt.sh");
            if (EnableHackerTarget) enabledSources.Add("hackertarget");
            if (EnableWayback) enabledSources.Add("wayback");
            if (EnableAlienVault) enabledSources.Add("alienvault");
            if (EnableThreatCrowd) enabledSources.Add("threatcrowd");
            if (EnableCommonCrawl) enabledSources.Add("commoncrawl");

            ActiveSources = enabledSources.Count;

            var config = new ScanConfiguration(
                Domain.Trim(),
                enabledSources,
                ResolveDns
            );

            var result = await _scannerService.ScanAsync(config, _cancellationTokenSource.Token);

            if (result.IsSuccess)
            {
                TotalSubdomains = result.TotalFound;
                ResolvedHosts = result.ResolvedDomains.Count;

                foreach (var subdomain in result.Subdomains.OrderBy(s => s))
                {
                    Subdomains.Add(subdomain);
                }

                // Notify commands that depend on Subdomains count
                CopySubdomainsCommand.NotifyCanExecuteChanged();
                ExportToTxtCommand.NotifyCanExecuteChanged();

                var elapsed = DateTime.Now - startTime;
                ScanTime = $"{elapsed.TotalSeconds:F1}s";
            }
            else
            {
                AddLog($"❌ Error: {result.ErrorMessage}");
            }
        }
        catch (OperationCanceledException)
        {
            AddLog("⚠️ Scan cancelled");
        }
        catch (Exception ex)
        {
            AddLog($"❌ Error: {ex.Message}");
        }
        finally
        {
            IsScanning = false;
            _cancellationTokenSource?.Dispose();
            _cancellationTokenSource = null;
        }
    }

    private bool CanStartScan() => !IsScanning && !string.IsNullOrWhiteSpace(Domain);

    [RelayCommand(CanExecute = nameof(CanCancelScan))]
    private void CancelScan()
    {
        _cancellationTokenSource?.Cancel();
    }

    private bool CanCancelScan() => IsScanning;

    [RelayCommand(CanExecute = nameof(CanClearResults))]
    private void ClearResults()
    {
        Subdomains.Clear();
        Logs.Clear();
        TotalSubdomains = 0;
        ResolvedHosts = 0;
        ScanTime = "0s";
        ActiveSources = 0;

        // Notify commands that depend on Subdomains count
        CopySubdomainsCommand.NotifyCanExecuteChanged();
        ExportToTxtCommand.NotifyCanExecuteChanged();
    }

    private bool CanClearResults() => !IsScanning && (Subdomains.Count > 0 || Logs.Count > 0);

    [RelayCommand]
    private void ToggleDarkMode()
    {
        IsDarkMode = !IsDarkMode;
    }

    [RelayCommand(CanExecute = nameof(CanCopySubdomains))]
    private async Task CopySubdomainsAsync()
    {
        if (Subdomains.Count == 0)
            return;

        try
        {
            var text = string.Join(Environment.NewLine, Subdomains);
            if (Application.Current?.ApplicationLifetime is IClassicDesktopStyleApplicationLifetime desktop)
            {
                var clipboard = desktop.MainWindow?.Clipboard;
                if (clipboard != null)
                {
                    await clipboard.SetTextAsync(text);
                    AddLog($"✅ Copied {Subdomains.Count} subdomains to clipboard");
                }
            }
        }
        catch (Exception ex)
        {
            AddLog($"❌ Failed to copy: {ex.Message}");
        }
    }

    private bool CanCopySubdomains() => Subdomains.Count > 0;

    [RelayCommand(CanExecute = nameof(CanClearLogs))]
    private void ClearLogs()
    {
        Logs.Clear();
    }

    private bool CanClearLogs() => Logs.Count > 0;

    [RelayCommand]
    private async Task CopySingleSubdomainAsync(string? subdomain)
    {
        if (string.IsNullOrWhiteSpace(subdomain))
            return;

        try
        {
            if (Application.Current?.ApplicationLifetime is IClassicDesktopStyleApplicationLifetime desktop)
            {
                var clipboard = desktop.MainWindow?.Clipboard;
                if (clipboard != null)
                {
                    await clipboard.SetTextAsync(subdomain);
                    AddLog($"✅ Copied: {subdomain}");
                }
            }
        }
        catch (Exception ex)
        {
            AddLog($"❌ Failed to copy: {ex.Message}");
        }
    }

    [RelayCommand]
    private void OpenUrl(string? subdomain)
    {
        if (string.IsNullOrWhiteSpace(subdomain))
            return;

        try
        {
            var url = $"https://{subdomain}";
            System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo
            {
                FileName = url,
                UseShellExecute = true
            });
            AddLog($"🌐 Opened: {url}");
        }
        catch (Exception ex)
        {
            AddLog($"❌ Failed to open URL: {ex.Message}");
        }
    }

    [RelayCommand(CanExecute = nameof(CanExportToTxt))]
    private async Task ExportToTxtAsync()
    {
        if (Subdomains.Count == 0)
            return;

        try
        {
            if (Application.Current?.ApplicationLifetime is IClassicDesktopStyleApplicationLifetime desktop)
            {
                var window = desktop.MainWindow;
                if (window != null)
                {
                    // Use the new StorageProvider API
                    var storageProvider = window.StorageProvider;

                    // Define file type filters
                    var fileTypeFilter = new FilePickerFileType("Text Files")
                    {
                        Patterns = new[] { "*.txt" },
                        MimeTypes = new[] { "text/plain" }
                    };

                    // Configure save options
                    var options = new FilePickerSaveOptions
                    {
                        Title = "Export Subdomains to TXT",
                        SuggestedFileName = $"{Domain}_subdomains_{DateTime.Now:yyyyMMdd_HHmmss}.txt",
                        DefaultExtension = "txt",
                        FileTypeChoices = new[] { fileTypeFilter },
                        ShowOverwritePrompt = true
                    };

                    // Show save dialog
                    var file = await storageProvider.SaveFilePickerAsync(options);

                    if (file != null)
                    {
                        var content = string.Join(Environment.NewLine, Subdomains);

                        // Write to file using stream
                        await using var stream = await file.OpenWriteAsync();
                        await using var writer = new System.IO.StreamWriter(stream);
                        await writer.WriteAsync(content);

                        AddLog($"✅ Exported {Subdomains.Count} subdomains to: {file.Name}");
                    }
                }
            }
        }
        catch (Exception ex)
        {
            AddLog($"❌ Failed to export: {ex.Message}");
        }
    }

    private bool CanExportToTxt() => Subdomains.Count > 0;

    private bool IsValidDomain(string domain)
    {
        if (string.IsNullOrWhiteSpace(domain))
            return false;

        // Remove protocol if present
        domain = domain.Replace("http://", "").Replace("https://", "").Trim();

        // Basic domain validation regex
        var domainRegex = new Regex(@"^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9][a-z0-9-]{0,61}[a-z0-9]$", 
            RegexOptions.IgnoreCase);
        
        return domainRegex.IsMatch(domain);
    }

    private void HandleLog(string message)
    {
        AddLog(message);
    }

    private void HandleProgress(ScanProgress progress)
    {
        // Update UI with progress if needed
    }

    private void AddLog(string message)
    {
        var timestamp = DateTime.Now.ToString("HH:mm:ss");
        Logs.Add($"[{timestamp}] {message}");
    }

    partial void OnDomainChanged(string value)
    {
        StartScanCommand.NotifyCanExecuteChanged();
        OnPropertyChanged(nameof(IsDomainInvalid));
    }

    partial void OnIsScanningChanged(bool value)
    {
        StartScanCommand.NotifyCanExecuteChanged();
        CancelScanCommand.NotifyCanExecuteChanged();
        ClearResultsCommand.NotifyCanExecuteChanged();
    }

    partial void OnEnableCrtShChanged(bool value) => OnPropertyChanged(nameof(HasAnySourceSelected));
    partial void OnEnableHackerTargetChanged(bool value) => OnPropertyChanged(nameof(HasAnySourceSelected));
    partial void OnEnableWaybackChanged(bool value) => OnPropertyChanged(nameof(HasAnySourceSelected));
    partial void OnEnableAlienVaultChanged(bool value) => OnPropertyChanged(nameof(HasAnySourceSelected));
    partial void OnEnableThreatCrowdChanged(bool value) => OnPropertyChanged(nameof(HasAnySourceSelected));
    partial void OnEnableCommonCrawlChanged(bool value) => OnPropertyChanged(nameof(HasAnySourceSelected));
}
