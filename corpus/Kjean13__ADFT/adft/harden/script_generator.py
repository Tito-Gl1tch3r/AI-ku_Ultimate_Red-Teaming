"""ADFT — Générateur de scripts PowerShell candidats pour le hardening."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Optional

from adft.core.models import HardeningFinding, HardeningReport


class PowerShellScriptGenerator:
    SCRIPT_HEADER = """#═══════════════════════════════════════════════════════════════
# ADFT — Script PowerShell candidat de remédiation
#
# ⚠️  AVERTISSEMENT
#   - Ce script est un candidat généré par ADFT.
#   - Vérifier, adapter et tester avant exécution.
#   - Exécuter d'abord en pré-production quand c'est possible.
#
# Finding        : {finding_id} — {title}
# Priorité       : {priority}
# Périmètre      : {scope}
# Confiance      : {confidence}
# Catégorie      : {category}
#═══════════════════════════════════════════════════════════════

#Requires -Modules ActiveDirectory
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

"""

    SCRIPT_TEMPLATES: Dict[str, str] = {
        "HARD-001": """
param(
    [string]$SearchBase = "",
    [string]$CsvPath = ""
)

Write-Host "[ADFT] Review of service accounts with SPN" -ForegroundColor Cyan

$properties = @(
    "ServicePrincipalName",
    "msDS-SupportedEncryptionTypes",
    "PasswordLastSet",
    "Enabled"
)

$queryParams = @{
    LDAPFilter = "(servicePrincipalName=*)"
    Properties = $properties
}

if ($SearchBase) {
    $queryParams["SearchBase"] = $SearchBase
    Write-Host "[ADFT] Scoped search base: $SearchBase" -ForegroundColor DarkCyan
}

$svcAccounts = Get-ADUser @queryParams |
    Where-Object { $_.Enabled -eq $true } |
    Select-Object `
        SamAccountName,
        @{Name="SPNCount";Expression={ @($_.ServicePrincipalName).Count }},
        @{Name="EncryptionTypes";Expression={ $_."msDS-SupportedEncryptionTypes" }},
        PasswordLastSet

if (-not $svcAccounts) {
    Write-Host "[ADFT] No enabled service accounts with SPN found." -ForegroundColor Yellow
    return
}

Write-Host "`n[ADFT] Enabled service accounts with SPN" -ForegroundColor Cyan
$svcAccounts | Sort-Object SamAccountName | Format-Table -AutoSize

$weakEnc = $svcAccounts | Where-Object {
    -not $_.EncryptionTypes -or
    (($_.EncryptionTypes -band 24) -eq 0)
}

Write-Host "`n[ADFT] Accounts that may not be AES-only" -ForegroundColor Yellow
if ($weakEnc) {
    $weakEnc | Sort-Object SamAccountName | Format-Table -AutoSize
} else {
    Write-Host "[ADFT] No obvious weak Kerberos encryption configuration detected." -ForegroundColor Green
}

if ($CsvPath) {
    $svcAccounts | Export-Csv -Path $CsvPath -NoTypeInformation -Encoding UTF8
    Write-Host "[ADFT] Exported inventory to $CsvPath" -ForegroundColor Green
}

# Candidate remediation — validate before use
# foreach ($acct in $weakEnc) {
#     Set-ADUser -Identity $acct.SamAccountName -KerberosEncryptionType AES128,AES256
# }
# Consider migrating eligible service accounts to gMSA where possible.
""",
        "HARD-002": """
Write-Host "[ADFT] Recherche des comptes sans pré-authentification Kerberos" -ForegroundColor Cyan
$noPreAuth = Get-ADUser -Filter {DoesNotRequirePreAuth -eq $true} -Properties DoesNotRequirePreAuth,Enabled |
  Where-Object { $_.Enabled -eq $true }
$noPreAuth | Select-Object SamAccountName,Enabled | Format-Table -AutoSize

# --- CANDIDAT DE CORRECTION ---
# foreach ($acct in $noPreAuth) {
#   Set-ADAccountControl -Identity $acct.SamAccountName -DoesNotRequirePreAuth $false
# }
""",
        "HARD-003": """
Write-Host "[ADFT] Vérification du compte KRBTGT" -ForegroundColor Cyan
$krbtgt = Get-ADUser -Identity 'krbtgt' -Properties PasswordLastSet
$krbtgt | Select-Object SamAccountName,PasswordLastSet | Format-Table -AutoSize
Write-Host "[ADFT] Préparer une double rotation KRBTGT selon procédure de crise" -ForegroundColor Yellow
# AUCUNE rotation automatique ici.
# Documenter la séquence, l'intervalle et la validation de réplication avant exécution manuelle.
""",
        "HARD-010": """
param(
    [string[]]$Groups = @(
        "Domain Admins",
        "Enterprise Admins",
        "Schema Admins",
        "Administrators",
        "Account Operators",
        "Backup Operators",
        "Server Operators",
        "Print Operators"
    ),
    [switch]$Recursive,
    [string]$CsvPath = ""
)

Write-Host "[ADFT] Review of privileged groups" -ForegroundColor Cyan

$results = foreach ($g in $Groups) {
    try {
        Write-Host "[ADFT] Reading group: $g" -ForegroundColor DarkCyan

        if ($Recursive) {
            Get-ADGroupMember -Identity $g -Recursive -ErrorAction Stop |
                Select-Object `
                    @{Name="Group";Expression={$g}},
                    Name,
                    SamAccountName,
                    ObjectClass,
                    DistinguishedName
        }
        else {
            Get-ADGroupMember -Identity $g -ErrorAction Stop |
                Select-Object `
                    @{Name="Group";Expression={$g}},
                    Name,
                    SamAccountName,
                    ObjectClass,
                    DistinguishedName
        }
    }
    catch {
        Write-Warning "Unable to read group '$g' : $($_.Exception.Message)"
    }
}

if (-not $results) {
    Write-Host "[ADFT] No privileged group membership data returned." -ForegroundColor Yellow
    return
}

Write-Host "`n[ADFT] Privileged group membership snapshot" -ForegroundColor Cyan
$results |
    Sort-Object Group, ObjectClass, SamAccountName |
    Format-Table Group, Name, SamAccountName, ObjectClass -AutoSize

if ($CsvPath) {
    $results | Export-Csv -Path $CsvPath -NoTypeInformation -Encoding UTF8
    Write-Host "[ADFT] Exported snapshot to $CsvPath" -ForegroundColor Green
}

Write-Host "`n[ADFT] Notes:" -ForegroundColor Yellow
Write-Host " - Use direct membership review by default." -ForegroundColor Yellow
Write-Host " - Use -Recursive only when nested groups must be expanded." -ForegroundColor Yellow
Write-Host " - Review unexpected users, service accounts, and cross-tier memberships." -ForegroundColor Yellow
""",
        "HARD-011": """
param([string[]]$Identity = @())
Write-Host "[ADFT] Contrôle ciblé des identités à risque" -ForegroundColor Cyan
if (-not $Identity -or $Identity.Count -eq 0) {
  Write-Warning "Passez les identités à contrôler avec -Identity user1,user2"
}
foreach ($id in $Identity) {
  Get-ADUser -Identity $id -Properties LastLogonDate,Enabled,PasswordLastSet,MemberOf |
    Select-Object SamAccountName,Enabled,LastLogonDate,PasswordLastSet,MemberOf | Format-List
}
# Réinitialisation éventuelle à mener séparément après qualification IR.
""",
        "HARD-012": """
param(
    [int]$DaysBack = 14,
    [string]$SearchBase = "",
    [string]$CsvPath = ""
)

Write-Host "[ADFT] Review of recently created accounts" -ForegroundColor Cyan

$since = (Get-Date).AddDays(-$DaysBack)
$sinceUtc = $since.ToUniversalTime().ToString("yyyyMMddHHmmss.0Z")
$ldapFilter = "(&(objectCategory=person)(objectClass=user)(whenCreated>=$sinceUtc))"

$properties = @(
    "whenCreated",
    "Enabled",
    "MemberOf"
)

$queryParams = @{
    LDAPFilter = $ldapFilter
    Properties = $properties
}

if ($SearchBase) {
    $queryParams["SearchBase"] = $SearchBase
    Write-Host "[ADFT] Scoped search base: $SearchBase" -ForegroundColor DarkCyan
}

$recentUsers = Get-ADUser @queryParams |
    Select-Object `
        SamAccountName,
        whenCreated,
        Enabled,
        @{Name="GroupCount";Expression={ @($_.MemberOf).Count }}

if (-not $recentUsers) {
    Write-Host "[ADFT] No recently created accounts found in the selected scope." -ForegroundColor Yellow
    return
}

Write-Host "`n[ADFT] Accounts created in the last $DaysBack day(s)" -ForegroundColor Cyan
$recentUsers |
    Sort-Object whenCreated -Descending |
    Format-Table SamAccountName, whenCreated, Enabled, GroupCount -AutoSize

if ($CsvPath) {
    $recentUsers | Export-Csv -Path $CsvPath -NoTypeInformation -Encoding UTF8
    Write-Host "[ADFT] Exported review to $CsvPath" -ForegroundColor Green
}

Write-Host "`n[ADFT] Follow-up actions:" -ForegroundColor Yellow
Write-Host " - Validate owner / business justification" -ForegroundColor Yellow
Write-Host " - Review privileged memberships separately if needed" -ForegroundColor Yellow
Write-Host " - Investigate unexpected creation bursts or naming anomalies" -ForegroundColor Yellow
""",
        "HARD-020": """
Write-Host "[ADFT] Politique de mot de passe / verrouillage" -ForegroundColor Cyan
$policy = Get-ADDefaultDomainPasswordPolicy
$policy | Select-Object LockoutThreshold,LockoutDuration,LockoutObservationWindow,MinPasswordLength,ComplexityEnabled | Format-List
# Ajuster les seuils via GPO ou policy de domaine après validation CAB.
""",
        "HARD-030": """
Write-Host "[ADFT] Contrôle de la surface d'administration latérale" -ForegroundColor Cyan
Get-SmbServerConfiguration | Select-Object EnableSMB1Protocol,EnableSMB2Protocol | Format-List
Get-Service WinRM | Select-Object Status,StartType | Format-Table -AutoSize
Write-Host "[ADFT] Contrôler aussi les ACL de pare-feu et les jump hosts autorisés." -ForegroundColor Yellow
""",
        "HARD-031": """
Write-Host "[ADFT] Inventaire rapide RDP" -ForegroundColor Cyan
Get-ItemProperty -Path 'HKLM:\\System\\CurrentControlSet\\Control\\Terminal Server' -Name fDenyTSConnections | Format-List
Get-NetFirewallRule -DisplayGroup 'Remote Desktop' -ErrorAction SilentlyContinue |
  Select-Object DisplayName,Enabled,Profile,Direction,Action | Format-Table -AutoSize
# Restreindre ensuite les sources et imposer NLA/MFA selon le design d'administration.
""",
        "HARD-032": """
param([string]$ServiceName = '')
Write-Host "[ADFT] Revue des services créés récemment" -ForegroundColor Cyan
Get-WinEvent -FilterHashtable @{LogName='System'; Id=7045; StartTime=(Get-Date).AddDays(-7)} -ErrorAction SilentlyContinue |
  Select-Object TimeCreated, Id, ProviderName, Message | Format-List
if ($ServiceName) {
  Get-Service -Name $ServiceName -ErrorAction SilentlyContinue | Format-List *
}
# Stop-Service / sc.exe delete à exécuter séparément après validation du binaire et du propriétaire.
""",
        "HARD-040": """
Write-Host "[ADFT] Vérification de l'audit avancé" -ForegroundColor Cyan
AuditPol /get /category:*
Write-Host "`n[ADFT] Vérifier la remontée SIEM des événements 4624,4625,4648,4672,4768,4769,4771,4776,5136" -ForegroundColor Yellow
""",
        "HARD-041": """
Write-Host "[ADFT] Checklist d'audit AD post-incident" -ForegroundColor Cyan
@(
  'Tiering administratif',
  'Groupes privilégiés',
  'Comptes inactifs / obsolètes',
  'Délégations',
  'GPO sensibles',
  'Comptes de service et SPN',
  'Journalisation DC'
) | ForEach-Object { " - $_" }
""",
        "HARD-042": """
Write-Host "[ADFT] Contrôle de la résilience des journaux" -ForegroundColor Cyan
wevtutil gl Security
wevtutil gl System
wevtutil gl Application
Write-Host "[ADFT] Vérifier aussi la centralisation distante et les permissions de nettoyage des journaux." -ForegroundColor Yellow
""",
    }

    def enrich_findings(self, report: HardeningReport) -> None:
        for finding in report.findings:
            script = self._generate_script(finding)
            if script:
                finding.powershell_fix = script

    def _metadata_block(self, finding: HardeningFinding) -> str:
        lines = []
        if finding.evidence:
            lines.append('# Preuves observées')
            for item in finding.evidence[:5]:
                lines.append(f'# - {item}')
        if finding.prerequisites:
            lines.append('#')
            lines.append('# Prérequis')
            for item in finding.prerequisites[:5]:
                lines.append(f'# - {item}')
        if finding.validation_steps:
            lines.append('#')
            lines.append('# Vérifications post-action')
            for item in finding.validation_steps[:5]:
                lines.append(f'# - {item}')
        if finding.rollback_steps:
            lines.append('#')
            lines.append('# Rollback / garde-fous')
            for item in finding.rollback_steps[:5]:
                lines.append(f'# - {item}')
        if finding.analyst_notes:
            lines.append('#')
            lines.append(f'# Note analyste: {finding.analyst_notes}')
        return '\n'.join(lines).rstrip() + '\n\n' if lines else ''

    def _generate_script(self, finding: HardeningFinding) -> Optional[str]:
        template = self.SCRIPT_TEMPLATES.get(finding.finding_id)
        if not template:
            return None
        header = self.SCRIPT_HEADER.format(
            finding_id=finding.finding_id,
            title=finding.title,
            priority=finding.priority.upper(),
            scope=finding.candidate_scope,
            confidence=finding.confidence,
            category=finding.category,
        )
        return header + self._metadata_block(finding) + template.lstrip('\n')

    def export_scripts(self, report: HardeningReport, output_dir: str) -> None:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        manifest = {
            'summary': report.summary,
            'coverage': report.script_coverage,
            'scripts': [],
        }
        exported = 0
        for finding in report.sorted_by_priority():
            if not finding.powershell_fix:
                continue
            filename = f"{finding.finding_id}_remediation.ps1"
            filepath = output_path / filename
            filepath.write_text(finding.powershell_fix, encoding='utf-8')
            manifest['scripts'].append({
                'finding_id': finding.finding_id,
                'title': finding.title,
                'priority': finding.priority,
                'confidence': finding.confidence,
                'path': filename,
                'validation_steps': finding.validation_steps,
            })
            exported += 1
            print(f"  [Script] ✓ {filepath}")

        (output_path / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f"\n  {exported} script(s) PowerShell exporté(s) dans {output_dir}")


ScriptGenerator = PowerShellScriptGenerator
