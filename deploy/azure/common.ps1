# Shared by the Azure scripts in this folder. Dot-source it: . "$PSScriptRoot\common.ps1"

$ErrorActionPreference = "Stop"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")

# Runs the Azure CLI and stops the script when it fails.
# Arguments must not contain ( ) & | < > ^ unquoted: az.cmd is a batch file and cmd.exe reads them.
function Invoke-Az {
    $out = & az @args
    if ($LASTEXITCODE -ne 0) { throw "az $($args -join ' ') failed (exit code $LASTEXITCODE)" }
    $out
}

function Assert-AzReady {
    if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
        throw "The Azure CLI isn't installed. Install it with: winget install -e --id Microsoft.AzureCLI, then open a new terminal."
    }
    & az account show -o none
    if ($LASTEXITCODE -ne 0) { throw "Sign in first with: az login" }
}

function Grant-Role([string]$ObjectId, [string]$PrincipalType, [string]$Role, [string]$Scope) {
    $existing = Invoke-Az role assignment list --assignee $ObjectId --role $Role --scope $Scope --query "[].id" -o tsv
    if (-not $existing) {
        Invoke-Az role assignment create --assignee-object-id $ObjectId --assignee-principal-type $PrincipalType --role $Role --scope $Scope -o none
    }
}

# Keeps the API on one instance of the shared plan. Each instance runs its own schedule, so two would
# both post; and SQLite lives on /home, a network share every instance mounts, where two writers
# lock each other out or corrupt the file.
# With per-site scaling on the plan, the site is pinned to one instance whatever the plan scales to.
# Without it, the API follows the plan: refuse when the plan can run more than one, warn otherwise.
function Set-OneInstance([string]$PlanId, [string]$ResourceGroup, [string]$App) {
    $plan = (Invoke-Az resource show --ids $PlanId --query "{perSite:properties.perSiteScaling,capacity:sku.capacity}" -o json) -join "`n" | ConvertFrom-Json
    if ($plan.perSite) {
        Invoke-Az webapp update -g $ResourceGroup -n $App --set siteConfig.numberOfWorkers=1 -o none
        return
    }
    # An autoscale setting can sit in any resource group, so look through the whole subscription
    $autoscale = @(Invoke-Az resource list --resource-type Microsoft.Insights/autoscalesettings --query "[].id" -o tsv |
        Where-Object { $_ } | ForEach-Object {
            Invoke-Az resource show --ids $_ --query "[properties.enabled,properties.targetResourceUri]" -o tsv
        } | Where-Object { $_ -match "^true\s+(.+)$" -and $Matches[1].Trim() -eq $PlanId })
    $turnOn = "az resource update --ids $PlanId --set properties.perSiteScaling=true"
    if ($plan.capacity -gt 1 -or $autoscale) {
        throw "The plan runs or can scale to more than one instance, and without per-site scaling $App would too (two schedules would both post). Turn it on with: $turnOn, then run this again."
    }
    Write-Warning "The plan has per-site scaling off: scaling it out would scale $App too, and every instance would post. Turn it on with: $turnOn"
}

function Get-ApiHost([string]$ResourceGroup, [string]$App) {
    (Invoke-Az webapp show -g $ResourceGroup -n $App --query defaultHostName -o tsv).Trim()
}

# Reads KEY=VALUE lines from a .env file, skipping comments.
function Read-EnvFile([string]$Path) {
    $values = @{}
    if (Test-Path $Path) {
        foreach ($line in Get-Content $Path) {
            if ($line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$') {
                $values[$Matches[1]] = $Matches[2].Trim('"', "'")
            }
        }
    }
    $values
}
