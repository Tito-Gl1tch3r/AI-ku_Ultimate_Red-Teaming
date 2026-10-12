#Requires -RunAsAdministrator

<#
.SYNOPSIS
    Comprehensive log and artifact collection script for security analysts.

.DESCRIPTION
    This script collects various logs, system information, and forensic artifacts
    commonly needed for security incident response and analysis. Creates a timestamped
    ZIP archive with organized folders for different artifact types.

.PARAMETER OutputPath
    Specify custom output path for the ZIP file (default: Desktop)

.PARAMETER CollectionType
    Specify what to collect (default: All):
    All, EventLogs, SystemInfo, NetworkInfo, UserArtifacts, ProcessInfo,
    ExecutionEvidence, PersistenceInfo, BrowserArtifacts, SecurityInfo

.PARAMETER MaxDays
    Collect logs from the last N days (default: 30, 0 = all available)

.PARAMETER IncludeMemoryDump
    Include memory dump files if available (can be very large)

.EXAMPLE
    .\Collect-SecurityLogs.ps1

.EXAMPLE
    .\Collect-SecurityLogs.ps1 -CollectionType EventLogs -MaxDays 7

.EXAMPLE
    .\Collect-SecurityLogs.ps1 -OutputPath "C:\Investigation" -CollectionType PersistenceInfo
#>

[CmdletBinding()]
param(
    [string]$OutputPath,
    [ValidateSet('All', 'EventLogs', 'SystemInfo', 'NetworkInfo', 'UserArtifacts',
                 'ProcessInfo', 'ExecutionEvidence', 'PersistenceInfo', 'BrowserArtifacts', 'SecurityInfo')]
    [string]$CollectionType = 'All',
    [ValidateRange(0, [int]::MaxValue)]
    [int]$MaxDays = 30,
    [switch]$IncludeMemoryDump
)

# ─── Paths and constants ────────────────────────────────────────────────────────
$sourcePath   = "C:\Windows\System32\winevt\Logs"
$desktopPath  = if ($OutputPath) { $OutputPath } else { [Environment]::GetFolderPath("Desktop") }
$timestamp    = Get-Date -Format 'yyyyMMdd_HHmmss'
$zipFileName  = "SecurityArtifacts_$($env:COMPUTERNAME)_$timestamp.zip"
$zipFilePath  = Join-Path -Path $desktopPath -ChildPath $zipFileName
$dateCutoff   = if ($MaxDays -gt 0) { (Get-Date).AddDays(-$MaxDays) } else { $null }

# Priority event logs for security analysis
$priorityEventLogs = @(
    'Security.evtx', 'System.evtx', 'Application.evtx',
    'Windows PowerShell.evtx',
    'Microsoft-Windows-PowerShell%4Operational.evtx',
    'Microsoft-Windows-Sysmon%4Operational.evtx',
    'Microsoft-Windows-TaskScheduler%4Operational.evtx',
    'Microsoft-Windows-TerminalServices-LocalSessionManager%4Operational.evtx',
    'Microsoft-Windows-TerminalServices-RemoteConnectionManager%4Operational.evtx',
    'Microsoft-Windows-WinRM%4Operational.evtx',
    'Microsoft-Windows-Windows Defender%4Operational.evtx',
    'Microsoft-Windows-Windows Firewall With Advanced Security%4Firewall.evtx',
    'Microsoft-Windows-Kernel-Process%4Analytic.evtx',
    'Microsoft-Windows-AppLocker%4EXE and DLL.evtx',
    'Microsoft-Windows-AppLocker%4MSI and Script.evtx',
    'Microsoft-Windows-Bits-Client%4Operational.evtx',
    'Microsoft-Windows-DNS-Client%4Operational.evtx',
    'Microsoft-Windows-Kernel-File%4Analytic.evtx',
    'Microsoft-Windows-SMBClient%4Security.evtx',
    'Microsoft-Windows-SMBServer%4Security.evtx',
    'Microsoft-Windows-NTLM%4Operational.evtx',
    'Microsoft-Windows-Security-Auditing%4Operational.evtx',
    'Microsoft-Windows-CAPI2%4Operational.evtx',
    'Microsoft-Windows-PrintService%4Operational.evtx',
    'Microsoft-Windows-RemoteDesktopServices-RdpCoreTS%4Operational.evtx'
)

# ─── Helper: user profile enumeration ───────────────────────────────────────────
function Get-UserProfilePaths {
    $profiles = Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList\*' -ErrorAction SilentlyContinue |
        Where-Object { $_.ProfileImagePath -like 'C:\Users\*' -and $_.ProfileImagePath -notlike '*\systemprofile' } |
        Select-Object -ExpandProperty ProfileImagePath
    return @($profiles | Where-Object { Test-Path $_ })
}

# ─── Helper: safe file copy (handles locked files via esentutl fallback) ────────
function Copy-LockedFile {
    param([string]$Source, [string]$Destination)

    try {
        Copy-Item -Path $Source -Destination $Destination -Force -ErrorAction Stop
        return $true
    }
    catch {
        try {
            $destFile = if (Test-Path $Destination -PathType Container) {
                Join-Path $Destination (Split-Path $Source -Leaf)
            } else { $Destination }
            esentutl /y $Source /d $destFile /o 2>$null
            return (Test-Path $destFile)
        }
        catch { return $false }
    }
}

# ─── Helper: safe directory creation ────────────────────────────────────────────
function New-DirectorySafe {
    param([string]$Path)
    if (-not (Test-Path $Path)) {
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
    }
}

# ─── Helper: run script-block commands from an ordered hashtable ────────────────
function Invoke-CommandCollection {
    param(
        [string]$ActivityName,
        [System.Collections.Specialized.OrderedDictionary]$Commands,
        [string]$OutputDirectory
    )

    $counter = 0
    foreach ($file in $Commands.Keys) {
        $counter++
        $pct = [math]::Round(($counter / $Commands.Count) * 100, 2)
        Write-Progress -Activity $ActivityName -Status $file -PercentComplete $pct
        try {
            $filePath = Join-Path -Path $OutputDirectory -ChildPath $file
            & $Commands[$file] | Out-File -FilePath $filePath -Encoding UTF8
        }
        catch {
            Write-Warning "Failed to collect $file : $($_.Exception.Message)"
        }
    }
    Write-Progress -Activity $ActivityName -Completed
}

# ─── Helper: SHA-256 hash entry ─────────────────────────────────────────────────
function Get-FileHashEntry {
    param([string]$FilePath)
    try {
        $hash = Get-FileHash -Path $FilePath -Algorithm SHA256 -ErrorAction Stop
        return "$($hash.Hash)  $($hash.Path)"
    }
    catch { return "HASH_ERROR  $FilePath" }
}

# ─── Folder structure ───────────────────────────────────────────────────────────
function New-CollectionStructure {
    param([string]$BasePath)

    $folders = @(
        'EventLogs', 'SystemInfo', 'NetworkInfo', 'ProcessInfo',
        'UserArtifacts', 'RegistryExports', 'SecurityPolicy',
        'ExecutionEvidence', 'PersistenceInfo', 'BrowserArtifacts', 'SecurityInfo'
    )
    foreach ($folder in $folders) {
        New-DirectorySafe (Join-Path $BasePath $folder)
    }
    return $BasePath
}

# ═════════════════════════════════════════════════════════════════════════════════
# COLLECTION FUNCTIONS
# ═════════════════════════════════════════════════════════════════════════════════

# ─── Event Logs ─────────────────────────────────────────────────────────────────
function Collect-EventLogs {
    param([string]$DestinationPath)

    Write-Host "Collecting Event Logs..." -ForegroundColor Green
    $eventLogPath = Join-Path $DestinationPath "EventLogs"

    $allLogs = Get-ChildItem -Path $sourcePath -Filter "*.evtx" -ErrorAction SilentlyContinue
    if ($dateCutoff) {
        $allLogs = $allLogs | Where-Object { $_.LastWriteTime -ge $dateCutoff }
    }

    $priorityLogs = $allLogs | Where-Object { $priorityEventLogs -contains $_.Name }
    $standardLogs = $allLogs | Where-Object { $priorityEventLogs -notcontains $_.Name }

    $priorityPath = Join-Path $eventLogPath "Priority"
    $standardPath = Join-Path $eventLogPath "Standard"
    New-DirectorySafe $priorityPath
    New-DirectorySafe $standardPath

    $totalLogs    = @($priorityLogs).Count + @($standardLogs).Count
    $counter      = 0
    $successCount = 0

    Write-Host "  Copying priority security logs..." -ForegroundColor Cyan
    foreach ($log in $priorityLogs) {
        $counter++
        Write-Progress -Activity "Collecting Event Logs" -Status "Priority: $($log.Name)" -PercentComplete ([math]::Round(($counter / $totalLogs) * 100, 2))
        try { Copy-Item -Path $log.FullName -Destination $priorityPath -ErrorAction Stop; $successCount++ }
        catch { Write-Warning "Failed to copy priority log $($log.Name): $($_.Exception.Message)" }
    }

    Write-Host "  Copying standard event logs..." -ForegroundColor Cyan
    foreach ($log in $standardLogs) {
        $counter++
        Write-Progress -Activity "Collecting Event Logs" -Status "Standard: $($log.Name)" -PercentComplete ([math]::Round(($counter / $totalLogs) * 100, 2))
        try { Copy-Item -Path $log.FullName -Destination $standardPath -ErrorAction Stop; $successCount++ }
        catch { Write-Warning "Failed to copy standard log $($log.Name): $($_.Exception.Message)" }
    }

    Write-Progress -Activity "Collecting Event Logs" -Completed
    Write-Host "  Event logs collected: $successCount of $totalLogs" -ForegroundColor Green
}

# ─── System Information ─────────────────────────────────────────────────────────
function Collect-SystemInfo {
    param([string]$DestinationPath)

    Write-Host "Collecting System Information..." -ForegroundColor Green
    $outDir = Join-Path $DestinationPath "SystemInfo"

    $commands = [ordered]@{
        'SystemInfo.txt'            = { systeminfo }
        'InstalledSoftware.txt'     = { Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*' -ErrorAction SilentlyContinue | Select-Object DisplayName, DisplayVersion, Publisher, InstallDate | Where-Object { $_.DisplayName } | Sort-Object DisplayName }
        'InstalledSoftware_x86.txt' = { Get-ItemProperty 'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*' -ErrorAction SilentlyContinue | Select-Object DisplayName, DisplayVersion, Publisher, InstallDate | Where-Object { $_.DisplayName } | Sort-Object DisplayName }
        'InstalledHotfixes.txt'     = { Get-HotFix | Sort-Object InstalledOn -Descending }
        'EnvironmentVariables.txt'  = { Get-ChildItem Env: | Sort-Object Name }
        'LocalUsers.txt'            = { Get-LocalUser | Select-Object Name, Enabled, LastLogon, PasswordLastSet, PasswordExpires, Description }
        'LocalGroups.txt'           = { Get-LocalGroup }
        'LocalGroupMembers.txt'     = { Get-LocalGroup | ForEach-Object { $g = $_.Name; try { Get-LocalGroupMember $g -ErrorAction Stop | Select-Object @{n='Group';e={$g}}, Name, ObjectClass, PrincipalSource } catch {} } }
        'Shares.txt'                = { Get-SmbShare }
        'StartupPrograms.txt'       = { Get-CimInstance Win32_StartupCommand | Select-Object Name, Command, Location, User }
        'WindowsFeatures.txt'       = { Get-WindowsOptionalFeature -Online -ErrorAction SilentlyContinue | Where-Object State -eq "Enabled" | Select-Object FeatureName, State }
        'TimeZone.txt'              = { Get-TimeZone; w32tm /query /status }
        'SystemUptime.txt'          = { (Get-Date) - (Get-CimInstance Win32_OperatingSystem).LastBootUpTime }
        'Drivers.txt'               = { Get-CimInstance Win32_PnPSignedDriver | Select-Object DeviceName, DriverVersion, Manufacturer, DriverDate, IsSigned, InfName | Sort-Object DeviceName }
        'USBDeviceHistory.txt'      = { Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Enum\USBSTOR\*\*' -ErrorAction SilentlyContinue | Select-Object FriendlyName, HardwareID, ContainerID, Mfg }
        'VolumeShadowCopies.txt'    = { vssadmin list shadows }
        'BITSTransfers.txt'         = { Get-BitsTransfer -AllUsers -ErrorAction SilentlyContinue | Select-Object DisplayName, JobState, TransferType, BytesTotal, BytesTransferred, CreationTime, FileList }
        'PowerShellModules.txt'     = { Get-Module -ListAvailable | Select-Object Name, Version, ModuleType, Path | Sort-Object Name }
        'DiskInfo.txt'              = { Get-CimInstance Win32_DiskDrive | Select-Object Model, SerialNumber, Size, MediaType, InterfaceType; Get-CimInstance Win32_LogicalDisk | Select-Object DeviceID, FileSystem, Size, FreeSpace, VolumeName }
        'WindowsUpdateLog.txt'      = { Get-HotFix | Format-Table -AutoSize; Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\WindowsUpdate\Auto Update\Results\Install' -ErrorAction SilentlyContinue }
        'TPMInfo.txt'               = { Get-Tpm -ErrorAction SilentlyContinue }
        'BitLockerStatus.txt'       = { Get-BitLockerVolume -ErrorAction SilentlyContinue | Select-Object MountPoint, VolumeStatus, ProtectionStatus, EncryptionMethod, KeyProtector }
    }

    Invoke-CommandCollection -ActivityName "Collecting System Information" -Commands $commands -OutputDirectory $outDir
    Write-Host "  System information collected" -ForegroundColor Green
}

# ─── Network Information ────────────────────────────────────────────────────────
function Collect-NetworkInfo {
    param([string]$DestinationPath)

    Write-Host "Collecting Network Information..." -ForegroundColor Green
    $outDir = Join-Path $DestinationPath "NetworkInfo"

    $commands = [ordered]@{
        'NetworkConfig.txt'       = { ipconfig /all }
        'RoutingTable.txt'        = { route print }
        'ARPTable.txt'            = { arp -a }
        'NetstatConnections.txt'  = { netstat -ano }
        'NetstatRoutes.txt'       = { netstat -rn }
        'DNSCache.txt'            = { ipconfig /displaydns }
        'NetworkAdapters.txt'     = { Get-NetAdapter | Select-Object Name, InterfaceDescription, Status, LinkSpeed, MacAddress }
        'FirewallRules.txt'       = { Get-NetFirewallRule | Where-Object Enabled -eq True | Select-Object DisplayName, Direction, Action, Profile }
        'FirewallProfiles.txt'    = { Get-NetFirewallProfile | Select-Object Name, Enabled, DefaultInboundAction, DefaultOutboundAction, LogFileName }
        'WiFiProfiles.txt'        = { netsh wlan show profiles }
        'NetworkShares.txt'       = { net share }
        'ActiveConnections.txt'   = { Get-NetTCPConnection | Where-Object State -eq "Established" | Select-Object LocalAddress, LocalPort, RemoteAddress, RemotePort, OwningProcess }
        'ListeningPorts.txt'      = { Get-NetTCPConnection | Where-Object State -eq "Listen" | Select-Object LocalAddress, LocalPort, OwningProcess, @{n="ProcessName";e={(Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue).ProcessName}} | Sort-Object LocalPort }
        'UDPEndpoints.txt'        = { Get-NetUDPEndpoint | Select-Object LocalAddress, LocalPort, OwningProcess, @{n="ProcessName";e={(Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue).ProcessName}} | Sort-Object LocalPort }
        'HostsFile.txt'           = { Get-Content "C:\Windows\System32\drivers\etc\hosts" -ErrorAction SilentlyContinue }
        'ProxySettings.txt'       = { Get-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -ErrorAction SilentlyContinue | Select-Object ProxyServer, ProxyEnable, AutoConfigURL; netsh winhttp show proxy }
        'DNSClientConfig.txt'     = { Get-DnsClientServerAddress | Select-Object InterfaceAlias, AddressFamily, ServerAddresses }
        'IPSecPolicies.txt'       = { Get-NetIPsecRule -ErrorAction SilentlyContinue | Select-Object DisplayName, Enabled, InboundSecurity, OutboundSecurity }
        'NetworkProfiles.txt'     = { Get-NetConnectionProfile | Select-Object Name, InterfaceAlias, NetworkCategory, IPv4Connectivity, IPv6Connectivity }
        'WLANEventHistory.txt'    = { netsh wlan show all 2>$null }
    }

    Invoke-CommandCollection -ActivityName "Collecting Network Information" -Commands $commands -OutputDirectory $outDir
    Write-Host "  Network information collected" -ForegroundColor Green
}

# ─── Process Information ────────────────────────────────────────────────────────
function Collect-ProcessInfo {
    param([string]$DestinationPath)

    Write-Host "Collecting Process Information..." -ForegroundColor Green
    $outDir = Join-Path $DestinationPath "ProcessInfo"

    $commands = [ordered]@{
        'RunningProcesses.txt' = { Get-Process | Select-Object Name, Id, CPU, WorkingSet, StartTime, Path | Sort-Object CPU -Descending }
        'ProcessTree.txt'      = { Get-CimInstance Win32_Process | Select-Object Name, ProcessId, ParentProcessId, CommandLine, CreationDate | Sort-Object ProcessId }
        'Services.txt'         = { Get-Service | Select-Object Name, Status, StartType, ServiceType | Sort-Object Status, Name }
        'ServiceDetails.txt'   = { Get-CimInstance Win32_Service | Select-Object Name, State, StartMode, PathName, StartName | Sort-Object Name }
        'ScheduledTasks.txt'   = { Get-ScheduledTask | Where-Object State -ne "Disabled" | Select-Object TaskName, State, LastRunTime, NextRunTime, TaskPath }
        'LoadedModules.txt'    = {
            Get-Process | ForEach-Object {
                $proc = $_
                try { $proc.Modules | Select-Object @{n="ProcessName";e={$proc.Name}}, @{n="PID";e={$proc.Id}}, ModuleName, FileName } catch {}
            }
        }
        'NetworkProcesses.txt' = { Get-NetTCPConnection | Select-Object LocalAddress, LocalPort, RemoteAddress, RemotePort, State, OwningProcess, @{n="ProcessName";e={(Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue).ProcessName}} }
        'NamedPipes.txt'       = { Get-ChildItem '\\.\pipe\' -ErrorAction SilentlyContinue | Select-Object Name, Length }
        'HandleCounts.txt'     = { Get-Process | Sort-Object HandleCount -Descending | Select-Object -First 50 Name, Id, HandleCount, WorkingSet, Path }
    }

    Invoke-CommandCollection -ActivityName "Collecting Process Information" -Commands $commands -OutputDirectory $outDir
    Write-Host "  Process information collected" -ForegroundColor Green
}

# ─── User Artifacts (per-user) ──────────────────────────────────────────────────
function Collect-UserArtifacts {
    param([string]$DestinationPath)

    Write-Host "Collecting User Artifacts..." -ForegroundColor Green
    $userArtifactsPath = Join-Path $DestinationPath "UserArtifacts"
    $userProfiles = Get-UserProfilePaths

    foreach ($profilePath in $userProfiles) {
        $userName = Split-Path $profilePath -Leaf
        $userDest = Join-Path $userArtifactsPath $userName
        New-DirectorySafe $userDest

        Write-Host "  Processing user: $userName" -ForegroundColor Cyan

        # ── Per-user registry artifacts via NTUSER.DAT ──
        $ntUserDat = Join-Path $profilePath "NTUSER.DAT"
        $regDest   = Join-Path $userDest "Registry"
        New-DirectorySafe $regDest

        $hiveMounted = $false
        $hiveKey     = "HKU\TempHive_$userName"

        if (Test-Path $ntUserDat) {
            try {
                reg load $hiveKey $ntUserDat 2>$null
                if ($LASTEXITCODE -eq 0) { $hiveMounted = $true }
            } catch {}
        }

        # If user is currently logged in, their hive is already loaded under HKU\<SID>
        $userSID = $null
        if (-not $hiveMounted) {
            try {
                $userSID = (New-Object System.Security.Principal.NTAccount("$env:COMPUTERNAME\$userName")).Translate(
                    [System.Security.Principal.SecurityIdentifier]).Value
            } catch {}
        }

        $regRoot = if ($hiveMounted) { $hiveKey }
                   elseif ($userSID) { "HKU\$userSID" }
                   else { $null }

        if ($regRoot) {
            $userRegExports = @{
                'RunMRU.reg'                = "$regRoot\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\RunMRU"
                'RecentDocs.reg'            = "$regRoot\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\RecentDocs"
                'TypedPaths.reg'            = "$regRoot\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\TypedPaths"
                'TypedURLs.reg'             = "$regRoot\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\TypedURLs"
                'UserAssist.reg'            = "$regRoot\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\UserAssist"
                'WordWheelQuery.reg'        = "$regRoot\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\WordWheelQuery"
                'ComDlg32.reg'              = "$regRoot\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\ComDlg32"
                'Shellbags_BagMRU.reg'      = "$regRoot\SOFTWARE\Microsoft\Windows\Shell\BagMRU"
                'Shellbags_Bags.reg'        = "$regRoot\SOFTWARE\Microsoft\Windows\Shell\Bags"
                'RDP_Servers.reg'           = "$regRoot\SOFTWARE\Microsoft\Terminal Server Client\Servers"
                'RDP_Default.reg'           = "$regRoot\SOFTWARE\Microsoft\Terminal Server Client\Default"
                'MapNetworkDriveMRU.reg'    = "$regRoot\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Map Network Drive MRU"
                'MountPoints2.reg'          = "$regRoot\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\MountPoints2"
                'AppCompatFlags.reg'        = "$regRoot\SOFTWARE\Microsoft\Windows NT\CurrentVersion\AppCompatFlags\Layers"
                'UserRun.reg'               = "$regRoot\SOFTWARE\Microsoft\Windows\CurrentVersion\Run"
                'UserRunOnce.reg'           = "$regRoot\SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce"
            }

            foreach ($file in $userRegExports.Keys) {
                $outFile = Join-Path $regDest $file
                reg export $userRegExports[$file] $outFile /y 2>$null
            }
        }

        if ($hiveMounted) {
            [gc]::Collect()
            reg unload $hiveKey 2>$null
        }

        # ── Recent LNK files ──
        $recentPath = Join-Path $profilePath "AppData\Roaming\Microsoft\Windows\Recent"
        if (Test-Path $recentPath) {
            $lnkDest = Join-Path $userDest "RecentFiles"
            New-DirectorySafe $lnkDest
            $lnkFiles = Get-ChildItem "$recentPath\*.lnk" -ErrorAction SilentlyContinue
            if ($dateCutoff) { $lnkFiles = $lnkFiles | Where-Object { $_.LastWriteTime -ge $dateCutoff } }
            $lnkFiles | Copy-Item -Destination $lnkDest -ErrorAction SilentlyContinue
        }

        # ── Jump Lists ──
        $autoDestPath   = Join-Path $profilePath "AppData\Roaming\Microsoft\Windows\Recent\AutomaticDestinations"
        $customDestPath = Join-Path $profilePath "AppData\Roaming\Microsoft\Windows\Recent\CustomDestinations"
        $jumpDest = Join-Path $userDest "JumpLists"
        New-DirectorySafe $jumpDest

        if (Test-Path $autoDestPath) {
            $autoDest = Join-Path $jumpDest "AutomaticDestinations"
            New-DirectorySafe $autoDest
            Get-ChildItem $autoDestPath -ErrorAction SilentlyContinue | Copy-Item -Destination $autoDest -ErrorAction SilentlyContinue
        }
        if (Test-Path $customDestPath) {
            $custDest = Join-Path $jumpDest "CustomDestinations"
            New-DirectorySafe $custDest
            Get-ChildItem $customDestPath -ErrorAction SilentlyContinue | Copy-Item -Destination $custDest -ErrorAction SilentlyContinue
        }

        # ── PowerShell console history ──
        $psHistoryPath = Join-Path $profilePath "AppData\Roaming\Microsoft\Windows\PowerShell\PSReadLine\ConsoleHost_history.txt"
        if (Test-Path $psHistoryPath) {
            $psDest = Join-Path $userDest "PowerShellHistory"
            New-DirectorySafe $psDest
            Copy-Item $psHistoryPath -Destination $psDest -ErrorAction SilentlyContinue
        }

        # ── Thumbcache ──
        $thumbPath = Join-Path $profilePath "AppData\Local\Microsoft\Windows\Explorer"
        if (Test-Path $thumbPath) {
            $thumbDest = Join-Path $userDest "Thumbcache"
            New-DirectorySafe $thumbDest
            Get-ChildItem "$thumbPath\thumbcache_*.db" -ErrorAction SilentlyContinue |
                Copy-Item -Destination $thumbDest -ErrorAction SilentlyContinue
        }

        # ── Startup folder contents ──
        $startupPath = Join-Path $profilePath "AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup"
        if (Test-Path $startupPath) {
            $startupDest = Join-Path $userDest "StartupFolder"
            New-DirectorySafe $startupDest
            Get-ChildItem $startupPath -ErrorAction SilentlyContinue |
                Copy-Item -Destination $startupDest -ErrorAction SilentlyContinue
        }
    }

    # ── System-level registry exports ──
    $registryPath = Join-Path $DestinationPath "RegistryExports"
    $systemRegExports = @{
        'HKLM_Run.reg'            = 'HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\Run'
        'HKLM_RunOnce.reg'        = 'HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce'
        'HKLM_Services.reg'       = 'HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services'
        'HKLM_Uninstall.reg'      = 'HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall'
        'HKLM_MountedDevices.reg' = 'HKEY_LOCAL_MACHINE\SYSTEM\MountedDevices'
        'HKLM_ProfileList.reg'    = 'HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList'
        'HKLM_USBSTOR.reg'       = 'HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Enum\USBSTOR'
    }

    foreach ($file in $systemRegExports.Keys) {
        $regPath = Join-Path $registryPath $file
        reg export $systemRegExports[$file] $regPath /y 2>$null
    }

    # ── Security policy ──
    $secPolPath = Join-Path $DestinationPath "SecurityPolicy"
    secedit /export /cfg (Join-Path $secPolPath "SecurityPolicy.inf") /quiet 2>$null
    auditpol /get /category:* > (Join-Path $secPolPath "AuditPolicy.txt") 2>$null

    Write-Host "  User artifacts collected for $($userProfiles.Count) profiles" -ForegroundColor Green
}

# ─── Execution Evidence ─────────────────────────────────────────────────────────
function Collect-ExecutionEvidence {
    param([string]$DestinationPath)

    Write-Host "Collecting Execution Evidence..." -ForegroundColor Green
    $execPath = Join-Path $DestinationPath "ExecutionEvidence"

    # Prefetch
    $prefetchDest = Join-Path $execPath "Prefetch"
    New-DirectorySafe $prefetchDest
    $prefetchSource = "C:\Windows\Prefetch"
    if (Test-Path $prefetchSource) {
        $pfFiles = Get-ChildItem "$prefetchSource\*.pf" -ErrorAction SilentlyContinue
        if ($dateCutoff) { $pfFiles = $pfFiles | Where-Object { $_.LastWriteTime -ge $dateCutoff } }
        $pfFiles | Copy-Item -Destination $prefetchDest -ErrorAction SilentlyContinue
        Write-Host "  Prefetch files: $(@($pfFiles).Count)" -ForegroundColor Cyan
    }

    # Amcache.hve
    $amcacheDest = Join-Path $execPath "Amcache"
    New-DirectorySafe $amcacheDest
    $amcacheSrc = "C:\Windows\AppCompat\Programs\Amcache.hve"
    if (Test-Path $amcacheSrc) {
        $copied = Copy-LockedFile -Source $amcacheSrc -Destination $amcacheDest
        # Also grab the transaction logs
        Get-ChildItem "C:\Windows\AppCompat\Programs\Amcache.hve.LOG*" -ErrorAction SilentlyContinue |
            ForEach-Object { Copy-LockedFile -Source $_.FullName -Destination $amcacheDest }
        Write-Host "  Amcache.hve: $(if ($copied) { 'collected' } else { 'locked/unavailable' })" -ForegroundColor Cyan
    }

    # SRUM (System Resource Usage Monitor)
    $srumDest = Join-Path $execPath "SRUM"
    New-DirectorySafe $srumDest
    $srumSrc = "C:\Windows\System32\sru\SRUDB.dat"
    if (Test-Path $srumSrc) {
        $copied = Copy-LockedFile -Source $srumSrc -Destination $srumDest
        Write-Host "  SRUDB.dat: $(if ($copied) { 'collected' } else { 'locked/unavailable' })" -ForegroundColor Cyan
    }

    # BAM / DAM (Background Activity Moderator / Desktop Activity Moderator)
    $bamDest = Join-Path $execPath "BAM"
    New-DirectorySafe $bamDest
    $bamPaths = @(
        'HKLM:\SYSTEM\CurrentControlSet\Services\bam\State\UserSettings',
        'HKLM:\SYSTEM\CurrentControlSet\Services\bam\UserSettings',
        'HKLM:\SYSTEM\CurrentControlSet\Services\dam\State\UserSettings',
        'HKLM:\SYSTEM\CurrentControlSet\Services\dam\UserSettings'
    )
    foreach ($bamPath in $bamPaths) {
        if (Test-Path $bamPath) {
            $bamName = ($bamPath -replace '.*\\', '') + ".txt"
            Get-ChildItem $bamPath -ErrorAction SilentlyContinue |
                ForEach-Object { Get-ItemProperty $_.PSPath -ErrorAction SilentlyContinue } |
                Out-File (Join-Path $bamDest $bamName) -Encoding UTF8
        }
    }

    # AppCompatCache / Shimcache (registry export — binary blob for offline parsing)
    $shimDest = Join-Path $execPath "Shimcache"
    New-DirectorySafe $shimDest
    reg export "HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\Session Manager\AppCompatCache" (Join-Path $shimDest "AppCompatCache.reg") /y 2>$null

    # Windows Error Reporting
    $werDest = Join-Path $execPath "WER"
    New-DirectorySafe $werDest
    $werPaths = @(
        "C:\ProgramData\Microsoft\Windows\WER\ReportArchive",
        "C:\ProgramData\Microsoft\Windows\WER\ReportQueue"
    )
    foreach ($werPath in $werPaths) {
        if (Test-Path $werPath) {
            $werSubDest = Join-Path $werDest (Split-Path $werPath -Leaf)
            New-DirectorySafe $werSubDest
            Get-ChildItem $werPath -Directory -ErrorAction SilentlyContinue | ForEach-Object {
                $reportDest = Join-Path $werSubDest $_.Name
                New-DirectorySafe $reportDest
                Get-ChildItem $_.FullName -File -ErrorAction SilentlyContinue |
                    Copy-Item -Destination $reportDest -ErrorAction SilentlyContinue
            }
        }
    }

    # RecentFileCache.bcf (older Windows)
    $rfcSrc = "C:\Windows\AppCompat\Programs\RecentFileCache.bcf"
    if (Test-Path $rfcSrc) {
        Copy-LockedFile -Source $rfcSrc -Destination $execPath
    }

    Write-Host "  Execution evidence collected" -ForegroundColor Green
}

# ─── Persistence Mechanisms ─────────────────────────────────────────────────────
function Collect-PersistenceInfo {
    param([string]$DestinationPath)

    Write-Host "Collecting Persistence Mechanisms..." -ForegroundColor Green
    $persistPath = Join-Path $DestinationPath "PersistenceInfo"

    # ── Autorun registry keys ──
    $autorunDest = Join-Path $persistPath "AutorunRegistry"
    New-DirectorySafe $autorunDest

    $autorunKeys = @{
        'HKLM_Run.reg'                = 'HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\Run'
        'HKLM_RunOnce.reg'            = 'HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce'
        'HKLM_Run_Wow64.reg'          = 'HKEY_LOCAL_MACHINE\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Run'
        'HKLM_RunOnce_Wow64.reg'      = 'HKEY_LOCAL_MACHINE\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\RunOnce'
        'HKLM_Winlogon.reg'           = 'HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon'
        'HKLM_IFEO.reg'              = 'HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Image File Execution Options'
        'HKLM_AppInit.reg'            = 'HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Windows'
        'HKLM_LSA.reg'                = 'HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\Lsa'
        'HKLM_SessionManager.reg'     = 'HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\Session Manager'
        'HKLM_PrintMonitors.reg'      = 'HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\Print\Monitors'
        'HKLM_SecurityProviders.reg'  = 'HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\SecurityProviders'
        'HKLM_BHO.reg'                = 'HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Browser Helper Objects'
        'HKLM_ShellExtensions.reg'    = 'HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\Shell Extensions\Approved'
        'HKLM_BootExecute.reg'        = 'HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\Session Manager'
        'HKLM_KnownDLLs.reg'          = 'HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\Session Manager\KnownDLLs'
        'HKLM_FontDrivers.reg'        = 'HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Font Drivers'
        'HKLM_Netsh.reg'              = 'HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Netsh'
        'HKLM_ActiveSetup.reg'        = 'HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Active Setup\Installed Components'
    }

    foreach ($file in $autorunKeys.Keys) {
        reg export $autorunKeys[$file] (Join-Path $autorunDest $file) /y 2>$null
    }

    # ── Scheduled Tasks XML ──
    $taskXmlDest = Join-Path $persistPath "ScheduledTasksXML"
    New-DirectorySafe $taskXmlDest
    $taskSource = "C:\Windows\System32\Tasks"
    if (Test-Path $taskSource) {
        Get-ChildItem $taskSource -Recurse -File -ErrorAction SilentlyContinue | ForEach-Object {
            $relPath = $_.FullName.Substring($taskSource.Length + 1)
            $destDir = Join-Path $taskXmlDest (Split-Path $relPath -Parent)
            New-DirectorySafe $destDir
            Copy-Item $_.FullName -Destination (Join-Path $taskXmlDest $relPath) -ErrorAction SilentlyContinue
        }
    }

    # ── Global startup folder ──
    $globalStartup = "C:\ProgramData\Microsoft\Windows\Start Menu\Programs\StartUp"
    if (Test-Path $globalStartup) {
        $startupDest = Join-Path $persistPath "GlobalStartupFolder"
        New-DirectorySafe $startupDest
        Get-ChildItem $globalStartup -ErrorAction SilentlyContinue |
            Copy-Item -Destination $startupDest -ErrorAction SilentlyContinue
    }

    # ── WMI Event Subscriptions ──
    $wmiDest = Join-Path $persistPath "WMISubscriptions"
    New-DirectorySafe $wmiDest
    $wmiCommands = [ordered]@{
        'EventFilters.txt'    = { Get-CimInstance -Namespace root/subscription -ClassName __EventFilter -ErrorAction SilentlyContinue | Select-Object Name, Query, QueryLanguage, EventNamespace }
        'EventConsumers.txt'  = { Get-CimInstance -Namespace root/subscription -ClassName __EventConsumer -ErrorAction SilentlyContinue }
        'FilterToConsumer.txt'= { Get-CimInstance -Namespace root/subscription -ClassName __FilterToConsumerBinding -ErrorAction SilentlyContinue }
    }
    Invoke-CommandCollection -ActivityName "WMI Subscriptions" -Commands $wmiCommands -OutputDirectory $wmiDest

    # ── COM Hijack checks ──
    $comDest = Join-Path $persistPath "COMObjects"
    New-DirectorySafe $comDest
    $comCommands = [ordered]@{
        'InprocServer32_HKCU.txt' = { Get-ChildItem 'HKCU:\SOFTWARE\Classes\CLSID\*\InprocServer32' -ErrorAction SilentlyContinue | ForEach-Object { [PSCustomObject]@{ CLSID = ($_.PSPath -split '\\')[-2]; DLL = (Get-ItemProperty $_.PSPath -ErrorAction SilentlyContinue).'(default)' } } }
        'LocalServer32_HKCU.txt'  = { Get-ChildItem 'HKCU:\SOFTWARE\Classes\CLSID\*\LocalServer32' -ErrorAction SilentlyContinue | ForEach-Object { [PSCustomObject]@{ CLSID = ($_.PSPath -split '\\')[-2]; EXE = (Get-ItemProperty $_.PSPath -ErrorAction SilentlyContinue).'(default)' } } }
    }
    Invoke-CommandCollection -ActivityName "COM Objects" -Commands $comCommands -OutputDirectory $comDest

    # ── Services with unusual paths ──
    $servicesDest = Join-Path $persistPath "Services"
    New-DirectorySafe $servicesDest
    $servCommands = [ordered]@{
        'NonStandardServices.txt' = { Get-CimInstance Win32_Service | Where-Object { $_.PathName -and $_.PathName -notlike '*\Windows\*' -and $_.PathName -notlike '*\Microsoft*' } | Select-Object Name, State, StartMode, PathName, StartName | Sort-Object Name }
        'DriverServices.txt'      = { Get-CimInstance Win32_SystemDriver | Select-Object Name, State, StartMode, PathName | Sort-Object Name }
    }
    Invoke-CommandCollection -ActivityName "Services" -Commands $servCommands -OutputDirectory $servicesDest

    Write-Host "  Persistence mechanisms collected" -ForegroundColor Green
}

# ─── Browser Artifacts ──────────────────────────────────────────────────────────
function Collect-BrowserArtifacts {
    param([string]$DestinationPath)

    Write-Host "Collecting Browser Artifacts..." -ForegroundColor Green
    $browserPath = Join-Path $DestinationPath "BrowserArtifacts"
    $userProfiles = Get-UserProfilePaths

    foreach ($profilePath in $userProfiles) {
        $userName = Split-Path $profilePath -Leaf
        $userBrowserDest = Join-Path $browserPath $userName
        Write-Host "  Processing browser data: $userName" -ForegroundColor Cyan

        # Chrome
        $chromePath = Join-Path $profilePath "AppData\Local\Google\Chrome\User Data\Default"
        if (Test-Path $chromePath) {
            $chromeDest = Join-Path $userBrowserDest "Chrome"
            New-DirectorySafe $chromeDest
            $chromeFiles = @('History', 'Bookmarks', 'Login Data', 'Preferences', 'Web Data',
                            'Favicons', 'Top Sites', 'Shortcuts', 'Network Action Predictor')
            foreach ($cf in $chromeFiles) {
                $cfPath = Join-Path $chromePath $cf
                if (Test-Path $cfPath) { Copy-LockedFile -Source $cfPath -Destination $chromeDest }
            }
            # Additional Chrome profiles
            $chromeUserData = Join-Path $profilePath "AppData\Local\Google\Chrome\User Data"
            Get-ChildItem $chromeUserData -Directory -Filter "Profile *" -ErrorAction SilentlyContinue | ForEach-Object {
                $profDest = Join-Path $userBrowserDest "Chrome_$($_.Name)"
                New-DirectorySafe $profDest
                foreach ($cf in $chromeFiles) {
                    $cfPath = Join-Path $_.FullName $cf
                    if (Test-Path $cfPath) { Copy-LockedFile -Source $cfPath -Destination $profDest }
                }
            }
        }

        # Edge (Chromium-based)
        $edgePath = Join-Path $profilePath "AppData\Local\Microsoft\Edge\User Data\Default"
        if (Test-Path $edgePath) {
            $edgeDest = Join-Path $userBrowserDest "Edge"
            New-DirectorySafe $edgeDest
            $edgeFiles = @('History', 'Bookmarks', 'Login Data', 'Preferences', 'Web Data', 'Favicons', 'Top Sites')
            foreach ($ef in $edgeFiles) {
                $efPath = Join-Path $edgePath $ef
                if (Test-Path $efPath) { Copy-LockedFile -Source $efPath -Destination $edgeDest }
            }
        }

        # Firefox
        $firefoxPath = Join-Path $profilePath "AppData\Roaming\Mozilla\Firefox\Profiles"
        if (Test-Path $firefoxPath) {
            Get-ChildItem $firefoxPath -Directory -ErrorAction SilentlyContinue | ForEach-Object {
                $ffDest = Join-Path $userBrowserDest "Firefox_$($_.Name)"
                New-DirectorySafe $ffDest
                $ffFiles = @('places.sqlite', 'downloads.sqlite', 'formhistory.sqlite',
                            'logins.json', 'cookies.sqlite', 'permissions.sqlite',
                            'extensions.json', 'search.json.mozlz4')
                foreach ($ff in $ffFiles) {
                    $ffPath = Join-Path $_.FullName $ff
                    if (Test-Path $ffPath) { Copy-LockedFile -Source $ffPath -Destination $ffDest }
                }
            }
        }

        # Internet Explorer / Legacy Edge
        $ieHistPath = Join-Path $profilePath "AppData\Local\Microsoft\Windows\WebCache"
        if (Test-Path $ieHistPath) {
            $ieDest = Join-Path $userBrowserDest "IE_WebCache"
            New-DirectorySafe $ieDest
            Get-ChildItem "$ieHistPath\WebCacheV*.dat" -ErrorAction SilentlyContinue |
                ForEach-Object { Copy-LockedFile -Source $_.FullName -Destination $ieDest }
        }
    }

    Write-Host "  Browser artifacts collected for $($userProfiles.Count) profiles" -ForegroundColor Green
}

# ─── Security Artifacts ─────────────────────────────────────────────────────────
function Collect-SecurityInfo {
    param([string]$DestinationPath)

    Write-Host "Collecting Security Artifacts..." -ForegroundColor Green
    $secPath = Join-Path $DestinationPath "SecurityInfo"

    # ── Windows Defender ──
    $defenderDest = Join-Path $secPath "WindowsDefender"
    New-DirectorySafe $defenderDest

    $defenderCommands = [ordered]@{
        'DefenderStatus.txt'     = { Get-MpComputerStatus -ErrorAction SilentlyContinue }
        'DefenderPreferences.txt'= { Get-MpPreference -ErrorAction SilentlyContinue }
        'ThreatHistory.txt'      = { Get-MpThreatDetection -ErrorAction SilentlyContinue | Select-Object ThreatID, DetectionID, ProcessName, DomainUser, ActionSuccess, Resources, InitialDetectionTime }
        'ExclusionPaths.txt'     = { (Get-MpPreference -ErrorAction SilentlyContinue).ExclusionPath }
        'ExclusionProcesses.txt' = { (Get-MpPreference -ErrorAction SilentlyContinue).ExclusionProcess }
        'ExclusionExtensions.txt'= { (Get-MpPreference -ErrorAction SilentlyContinue).ExclusionExtension }
        'ASRRules.txt'           = { (Get-MpPreference -ErrorAction SilentlyContinue).AttackSurfaceReductionRules_Ids }
    }
    Invoke-CommandCollection -ActivityName "Windows Defender" -Commands $defenderCommands -OutputDirectory $defenderDest

    # Defender quarantine folder
    $quarantineSrc = "C:\ProgramData\Microsoft\Windows Defender\Quarantine"
    if (Test-Path $quarantineSrc) {
        $quarantineDest = Join-Path $defenderDest "Quarantine"
        New-DirectorySafe $quarantineDest
        Get-ChildItem $quarantineSrc -Recurse -File -ErrorAction SilentlyContinue |
            Copy-Item -Destination $quarantineDest -ErrorAction SilentlyContinue
    }

    # Defender scan history
    $scanHistSrc = "C:\ProgramData\Microsoft\Windows Defender\Scans\History"
    if (Test-Path $scanHistSrc) {
        $scanHistDest = Join-Path $defenderDest "ScanHistory"
        New-DirectorySafe $scanHistDest
        Get-ChildItem $scanHistSrc -Recurse -File -ErrorAction SilentlyContinue |
            Copy-Item -Destination $scanHistDest -ErrorAction SilentlyContinue
    }

    # ── Certificates ──
    $certDest = Join-Path $secPath "Certificates"
    New-DirectorySafe $certDest
    $certCommands = [ordered]@{
        'RootCerts.txt'           = { Get-ChildItem Cert:\LocalMachine\Root | Select-Object Thumbprint, Subject, NotBefore, NotAfter, Issuer | Sort-Object Subject }
        'PersonalCerts.txt'       = { Get-ChildItem Cert:\LocalMachine\My -ErrorAction SilentlyContinue | Select-Object Thumbprint, Subject, NotBefore, NotAfter, Issuer }
        'UntrustedCerts.txt'      = { Get-ChildItem Cert:\LocalMachine\Disallowed -ErrorAction SilentlyContinue | Select-Object Thumbprint, Subject, NotBefore, NotAfter, Issuer }
        'TrustedPublishers.txt'   = { Get-ChildItem Cert:\LocalMachine\TrustedPublisher -ErrorAction SilentlyContinue | Select-Object Thumbprint, Subject, NotBefore, NotAfter, Issuer }
        'CertUtilStore.txt'       = { certutil -store My 2>$null }
        'CertUtilCATasks.txt'     = { certutil -catasks 2>$null }
    }
    Invoke-CommandCollection -ActivityName "Certificates" -Commands $certCommands -OutputDirectory $certDest

    # ── Group Policy ──
    $gpoDest = Join-Path $secPath "GroupPolicy"
    New-DirectorySafe $gpoDest
    gpresult /z > (Join-Path $gpoDest "GPResult_Verbose.txt") 2>$null
    gpresult /h (Join-Path $gpoDest "GPResult.html") /f 2>$null

    # Copy local GPO files
    $gpoSrc = "C:\Windows\System32\GroupPolicy"
    if (Test-Path $gpoSrc) {
        $gpoFilesDest = Join-Path $gpoDest "LocalGPO"
        New-DirectorySafe $gpoFilesDest
        Get-ChildItem $gpoSrc -Recurse -File -ErrorAction SilentlyContinue |
            Copy-Item -Destination $gpoFilesDest -ErrorAction SilentlyContinue
    }

    # ── Credential / LSA info ──
    $credDest = Join-Path $secPath "Credentials"
    New-DirectorySafe $credDest
    $credCommands = [ordered]@{
        'CredentialManager.txt'  = { cmdkey /list }
        'LSAProtection.txt'     = { Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\Lsa' -ErrorAction SilentlyContinue | Select-Object RunAsPPL, LimitBlankPasswordUse, NoLMHash, RestrictAnonymous, RestrictAnonymousSAM, EveryoneIncludesAnonymous }
        'SAMDomainInfo.txt'     = { Get-ItemProperty 'HKLM:\SAM\SAM\Domains\Account' -ErrorAction SilentlyContinue }
        'LogonSessions.txt'     = { klist sessions 2>$null }
        'CachedLogons.txt'      = { Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon' -ErrorAction SilentlyContinue | Select-Object CachedLogonsCount, DefaultUserName, DefaultDomainName, AutoAdminLogon, ForceAutoLogon }
    }
    Invoke-CommandCollection -ActivityName "Credentials" -Commands $credCommands -OutputDirectory $credDest

    # ── Hosts file (also in NetworkInfo but useful here for quick reference) ──
    $hostsSrc = "C:\Windows\System32\drivers\etc\hosts"
    if (Test-Path $hostsSrc) {
        Copy-Item $hostsSrc -Destination (Join-Path $secPath "hosts.txt") -ErrorAction SilentlyContinue
    }

    # ── Alternate Data Streams on common locations ──
    $adsDest = Join-Path $secPath "AlternateDataStreams.txt"
    $adsResults = @()
    $adsScanPaths = @("C:\Users", "C:\Windows\Temp", "C:\Temp")
    foreach ($adsPath in $adsScanPaths) {
        if (Test-Path $adsPath) {
            $adsResults += Get-ChildItem $adsPath -Recurse -File -ErrorAction SilentlyContinue |
                ForEach-Object { Get-Item $_.FullName -Stream * -ErrorAction SilentlyContinue } |
                Where-Object { $_.Stream -ne ':$DATA' -and $_.Stream -ne 'Zone.Identifier' } |
                Select-Object FileName, Stream, Length
        }
    }
    if ($adsResults) { $adsResults | Out-File $adsDest -Encoding UTF8 }

    # ── Recycle Bin metadata ──
    $recycleDest = Join-Path $secPath "RecycleBin"
    New-DirectorySafe $recycleDest
    $recycleSrc = "C:\`$Recycle.Bin"
    if (Test-Path $recycleSrc) {
        Get-ChildItem $recycleSrc -Recurse -Force -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -like '$I*' } |
            Copy-Item -Destination $recycleDest -ErrorAction SilentlyContinue
    }
    # Also list contents
    $recycleCommands = [ordered]@{
        'RecycleBinContents.txt' = {
            Get-ChildItem "C:\`$Recycle.Bin" -Recurse -Force -ErrorAction SilentlyContinue |
                Select-Object FullName, Length, LastWriteTime, CreationTime
        }
    }
    Invoke-CommandCollection -ActivityName "Recycle Bin" -Commands $recycleCommands -OutputDirectory $recycleDest

    # ── Windows Firewall log ──
    $fwLogPaths = @(
        "C:\Windows\System32\LogFiles\Firewall\pfirewall.log",
        "C:\Windows\System32\LogFiles\Firewall\pfirewall.log.old"
    )
    foreach ($fwLog in $fwLogPaths) {
        if (Test-Path $fwLog) {
            Copy-Item $fwLog -Destination (Join-Path $secPath (Split-Path $fwLog -Leaf)) -ErrorAction SilentlyContinue
        }
    }

    # ── AppLocker policy ──
    $appLockerDest = Join-Path $secPath "AppLocker"
    New-DirectorySafe $appLockerDest
    try { Get-AppLockerPolicy -Effective -Xml -ErrorAction Stop | Out-File (Join-Path $appLockerDest "EffectivePolicy.xml") -Encoding UTF8 } catch {}
    try { Get-AppLockerPolicy -Local -Xml -ErrorAction Stop | Out-File (Join-Path $appLockerDest "LocalPolicy.xml") -Encoding UTF8 } catch {}

    Write-Host "  Security artifacts collected" -ForegroundColor Green
}

# ─── Memory Dumps ───────────────────────────────────────────────────────────────
function Collect-MemoryDump {
    param([string]$DestinationPath)

    Write-Host "Collecting Memory Dump Files..." -ForegroundColor Green
    $dumpDestPath = Join-Path $DestinationPath "MemoryDumps"
    New-DirectorySafe $dumpDestPath

    $dumpPaths = @("C:\Windows\MEMORY.DMP", "C:\Windows\Minidump")
    foreach ($dumpPath in $dumpPaths) {
        if (Test-Path $dumpPath) {
            try {
                if ((Get-Item $dumpPath).PSIsContainer) {
                    $dumpFiles = Get-ChildItem $dumpPath -ErrorAction SilentlyContinue
                    if ($dateCutoff) { $dumpFiles = $dumpFiles | Where-Object { $_.LastWriteTime -ge $dateCutoff } }
                    $dumpFiles | Copy-Item -Destination $dumpDestPath -ErrorAction SilentlyContinue
                } else {
                    $item = Get-Item $dumpPath
                    if (-not $dateCutoff -or $item.LastWriteTime -ge $dateCutoff) {
                        Copy-Item -Path $dumpPath -Destination $dumpDestPath -ErrorAction Stop
                    }
                }
            }
            catch { Write-Warning "Failed to copy dump $dumpPath : $($_.Exception.Message)" }
        }
    }

    $fileCount = (Get-ChildItem $dumpDestPath -File -ErrorAction SilentlyContinue).Count
    Write-Host "  Memory dump files collected: $fileCount" -ForegroundColor Green
}

# ─── Hash Manifest ──────────────────────────────────────────────────────────────
function New-HashManifest {
    param([string]$BasePath)

    Write-Host "Generating integrity hash manifest..." -ForegroundColor Green
    $manifestPath = Join-Path $BasePath "HashManifest_SHA256.txt"
    $files = Get-ChildItem -Path $BasePath -Recurse -File -ErrorAction SilentlyContinue

    $hashEntries = foreach ($file in $files) {
        if ($file.Name -eq "HashManifest_SHA256.txt") { continue }
        Get-FileHashEntry -FilePath $file.FullName
    }
    $hashEntries | Out-File -FilePath $manifestPath -Encoding UTF8
    Write-Host "  Hashed $($hashEntries.Count) files" -ForegroundColor Green
}

# ─── Archive Creation ───────────────────────────────────────────────────────────
function New-SecurityArchive {
    param([string]$SourceFolder, [string]$DestinationZip)

    Write-Host "Creating security archive..." -ForegroundColor Green
    if (Test-Path $DestinationZip) { Remove-Item -Path $DestinationZip -Force }

    Add-Type -AssemblyName System.IO.Compression.FileSystem
    [System.IO.Compression.ZipFile]::CreateFromDirectory($SourceFolder, $DestinationZip)

    $zipInfo = Get-Item -Path $DestinationZip
    $fileSizeMB = [math]::Round($zipInfo.Length / 1MB, 2)
    Write-Host "Archive created successfully!" -ForegroundColor Green
    Write-Host "  Location: $DestinationZip" -ForegroundColor Cyan
    Write-Host "  Size: $fileSizeMB MB" -ForegroundColor Cyan
}

# ═════════════════════════════════════════════════════════════════════════════════
# MAIN EXECUTION
# ═════════════════════════════════════════════════════════════════════════════════
$tempCollectionPath = $null

try {
    $tempCollectionPath = Join-Path $env:TEMP "SecurityCollection_$([System.IO.Path]::GetRandomFileName())"
    New-Item -ItemType Directory -Path $tempCollectionPath -Force | Out-Null
    New-CollectionStructure -BasePath $tempCollectionPath

    Write-Host "Security Artifact Collection Script v3.0" -ForegroundColor Magenta
    Write-Host "=========================================" -ForegroundColor Magenta
    Write-Host "Computer: $env:COMPUTERNAME" -ForegroundColor White
    Write-Host "Collection Type: $CollectionType" -ForegroundColor White
    Write-Host "Output: $zipFilePath" -ForegroundColor White
    Write-Host "Max Days: $(if ($MaxDays -eq 0) { 'All available' } else { $MaxDays })" -ForegroundColor White
    Write-Host "Include Memory Dump: $IncludeMemoryDump" -ForegroundColor White
    Write-Host ""

    switch ($CollectionType) {
        'All' {
            Collect-EventLogs         -DestinationPath $tempCollectionPath
            Collect-SystemInfo        -DestinationPath $tempCollectionPath
            Collect-NetworkInfo       -DestinationPath $tempCollectionPath
            Collect-ProcessInfo       -DestinationPath $tempCollectionPath
            Collect-UserArtifacts     -DestinationPath $tempCollectionPath
            Collect-ExecutionEvidence -DestinationPath $tempCollectionPath
            Collect-PersistenceInfo   -DestinationPath $tempCollectionPath
            Collect-BrowserArtifacts  -DestinationPath $tempCollectionPath
            Collect-SecurityInfo      -DestinationPath $tempCollectionPath
            if ($IncludeMemoryDump) {
                Collect-MemoryDump -DestinationPath $tempCollectionPath
            }
        }
        'EventLogs'         { Collect-EventLogs         -DestinationPath $tempCollectionPath }
        'SystemInfo'        { Collect-SystemInfo        -DestinationPath $tempCollectionPath }
        'NetworkInfo'       { Collect-NetworkInfo       -DestinationPath $tempCollectionPath }
        'ProcessInfo'       { Collect-ProcessInfo       -DestinationPath $tempCollectionPath }
        'UserArtifacts'     { Collect-UserArtifacts     -DestinationPath $tempCollectionPath }
        'ExecutionEvidence' { Collect-ExecutionEvidence -DestinationPath $tempCollectionPath }
        'PersistenceInfo'   { Collect-PersistenceInfo   -DestinationPath $tempCollectionPath }
        'BrowserArtifacts'  { Collect-BrowserArtifacts  -DestinationPath $tempCollectionPath }
        'SecurityInfo'      { Collect-SecurityInfo      -DestinationPath $tempCollectionPath }
    }

    # Generate integrity hashes
    New-HashManifest -BasePath $tempCollectionPath

    # Create collection summary
    $summaryPath = Join-Path $tempCollectionPath "CollectionSummary.txt"
    $folderInfo = Get-ChildItem -Path $tempCollectionPath -Directory | ForEach-Object {
        $fileCount = (Get-ChildItem $_.FullName -Recurse -File -ErrorAction SilentlyContinue).Count
        "- $($_.Name): $fileCount files"
    }

    $summary = @"
Security Artifact Collection Summary
===================================
Computer Name: $env:COMPUTERNAME
Collection Date: $(Get-Date)
Collection Type: $CollectionType
Date Range: $(if ($dateCutoff) { "$dateCutoff to $(Get-Date)" } else { "All available" })
Include Memory Dump: $IncludeMemoryDump
Collector: $env:USERNAME
Script Version: 3.0
PowerShell Version: $($PSVersionTable.PSVersion)
OS Version: $((Get-CimInstance Win32_OperatingSystem).Caption) $((Get-CimInstance Win32_OperatingSystem).Version)

Folders Created:
$($folderInfo -join "`n")

Total Files Collected: $((Get-ChildItem -Path $tempCollectionPath -Recurse -File -ErrorAction SilentlyContinue).Count)

Integrity Verification:
- SHA-256 hashes for all collected files are in HashManifest_SHA256.txt

Collection Categories:
- EventLogs:         Windows event logs (priority + standard)
- SystemInfo:        OS details, software, hotfixes, drivers, USB, BitLocker, TPM
- NetworkInfo:       Adapters, connections, firewall, DNS, proxy, hosts, WLAN
- ProcessInfo:       Processes, services, scheduled tasks, named pipes, modules
- UserArtifacts:     Per-user registry (RunMRU, RecentDocs, TypedPaths, UserAssist,
                     Shellbags, RDP history, WordWheelQuery), LNK files, Jump Lists,
                     PowerShell history, thumbcache, startup folders
- ExecutionEvidence: Prefetch, Amcache, SRUM, BAM/DAM, Shimcache, WER
- PersistenceInfo:   Autorun registry keys, scheduled task XMLs, WMI subscriptions,
                     COM hijacks, startup folders, IFEO, Winlogon, LSA, BHOs
- BrowserArtifacts:  Chrome, Edge, Firefox, IE history/bookmarks/downloads per user
- SecurityInfo:      Defender status/quarantine/exclusions, certificates, GPO results,
                     credential vault, ADS scan, Recycle Bin, firewall logs, AppLocker

For Analysis:
1. Start with Priority event logs (Security.evtx, System.evtx, PowerShell logs)
2. Review ExecutionEvidence for program execution timeline
3. Check PersistenceInfo for unauthorized autorun mechanisms
4. Examine UserArtifacts registry for lateral movement (RDP) and user activity
5. Review BrowserArtifacts for download/browsing indicators
6. Check SecurityInfo for Defender exclusions and ADS anomalies
7. Cross-reference ProcessInfo with NetworkInfo for C2 indicators

This collection was created for security analysis purposes.
"@

    $summary | Out-File -FilePath $summaryPath -Encoding UTF8

    # Create final archive
    New-SecurityArchive -SourceFolder $tempCollectionPath -DestinationZip $zipFilePath

    Write-Host "`nCollection completed successfully!" -ForegroundColor Green
    Write-Host "Archive Location: $zipFilePath" -ForegroundColor Cyan

    Write-Host "`nNext Steps for Analysis:" -ForegroundColor Yellow
    Write-Host "1. Extract the archive to your analysis workstation" -ForegroundColor White
    Write-Host "2. Verify integrity using HashManifest_SHA256.txt" -ForegroundColor White
    Write-Host "3. Start with Priority event logs (Security, System, PowerShell)" -ForegroundColor White
    Write-Host "4. Review ExecutionEvidence (Amcache, Prefetch, SRUM) for timeline" -ForegroundColor White
    Write-Host "5. Check PersistenceInfo for unauthorized autoruns and WMI subs" -ForegroundColor White
    Write-Host "6. Examine UserArtifacts for RunMRU, RDP history, and PowerShell history" -ForegroundColor White
    Write-Host "7. Review BrowserArtifacts for indicators of compromise" -ForegroundColor White
    Write-Host "8. Cross-reference ProcessInfo with NetworkInfo for C2 detection" -ForegroundColor White
}
catch {
    Write-Host "`nERROR: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Stack Trace:" -ForegroundColor Red
    Write-Host $_.ScriptStackTrace -ForegroundColor Red
    exit 1
}
finally {
    if ($tempCollectionPath -and (Test-Path $tempCollectionPath)) {
        try { Remove-Item -Path $tempCollectionPath -Recurse -Force }
        catch { Write-Warning "Could not clean up temporary directory: $tempCollectionPath" }
    }
}
