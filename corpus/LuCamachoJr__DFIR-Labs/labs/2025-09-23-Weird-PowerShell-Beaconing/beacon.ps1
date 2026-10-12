# beacon.ps1 — benign DNS beacon for lab use only
# Generates random subdomains and resolves them on a timer.
# Edit the variables below to match your lab.

$Domain  = "a1b2c3.lab"      # fake lab domain (sinkhole this on your lab DNS)
$Server  = "192.0.2.53"      # your lab DNS server IP (replace)
$Seconds = 65                # interval between queries (seconds)

function New-RandomSubdomain($len=8) {
  $chars = (48..57 + 97..122) | ForEach-Object {[char]$_}
  -join (1..$len | ForEach-Object { $chars | Get-Random })
}

while ($true) {
  $sub = New-RandomSubdomain 8
  try {
    Resolve-DnsName "$sub.$Domain" -Server $Server -Type A -ErrorAction SilentlyContinue | Out-Null
  } catch {}
  Start-Sleep -Seconds $Seconds
}
