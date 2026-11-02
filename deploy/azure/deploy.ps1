<#
.SYNOPSIS
Deploys the committed server/ to the API from your computer.

.DESCRIPTION
The API gets server/ as of the current commit (git archive), so uncommitted
changes, server/.env, server/data and the virtual environment are never sent.
Azure installs requirements.txt during the deploy.

The web app isn't deployed from here: the site belongs to the tools dashboard, which
puts this app's web.zip from its latest GitHub Release in place. Merging into main
publishes one (.github/workflows/deploy.yml).

.EXAMPLE
powershell -ExecutionPolicy Bypass -File deploy\azure\deploy.ps1
#>
param(
    [string]$Name = "list-parser-bot-prod"
)

. "$PSScriptRoot\common.ps1"

$rg = $Name
$api = "$Name-api"

Assert-AzReady
$apiHost = Get-ApiHost $rg $api
$apiUrl = "https://$apiHost"

$commit = (git -C $RepoRoot log -1 --format="%h %s").Trim()
# The release tag on this commit (v1.4.0), or how far past the last one it is (v1.4.0-2-g1a2b3c4)
$version = (git -C $RepoRoot describe --tags --always).Trim()
Write-Host "Deploying $commit ($version)"
if (git -C $RepoRoot status --porcelain -- server) {
    Write-Warning "server/ has uncommitted changes. The API gets only committed code."
}

Write-Host "`nAPI -> $apiUrl"
$zip = Join-Path ([IO.Path]::GetTempPath()) "$api.zip"
try {
    git -C $RepoRoot archive --format=zip -o $zip --add-virtual-file="version.txt:$version" HEAD:server
    if ($LASTEXITCODE -ne 0) { throw "git archive failed" }
    # The CLI's own startup tracking can keep polling long after the site is up; the health check below decides
    Invoke-Az webapp deploy -g $rg -n $api --src-path $zip --type zip --track-status false -o none
}
finally {
    if (Test-Path $zip) { Remove-Item $zip -Force }
}

Write-Host "Waiting for $apiUrl/health ..."
$healthy = $false
for ($try = 1; $try -le 20 -and -not $healthy; $try++) {
    try { Invoke-WebRequest -UseBasicParsing -TimeoutSec 30 "$apiUrl/health" | Out-Null; $healthy = $true }
    catch { Start-Sleep -Seconds 15 }
}
if (-not $healthy) {
    throw "The API didn't start. See its log with: az webapp log tail -g $rg -n $api"
}
Write-Host "API is up."
