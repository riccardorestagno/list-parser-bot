<#
.SYNOPSIS
Creates the Azure resources for the bot's API on App Service, gives it the tools
dashboard's sign-in key and the bot's Reddit account, and turns its schedule on. Safe
to run again: what exists is kept, and the key is fetched again (run it after the
dashboard's key changes).

.DESCRIPTION
Resources, all in the resource group named -Name:
  <Name>-api    API (App Service, Python 3.14), which sweeps on a schedule; its record of sweeps lives in /home/data
  keep-data     Lock: nobody can delete the resource group or anything in it until it's removed

People use the bot's page at https://www.<Domain>/tools/list-parser-bot/. That site, and
the sign-in in front of it, belong to the tools dashboard (riccardorestagno/tools-dashboard),
which deploys this app's build there. The API keeps its azurewebsites.net address, and
checks each request's sign-in with the dashboard's public key, fetched from -AuthApi:
deploy the dashboard's API before running this. The API runs on the dashboard's App
Service plan (-Plan), which every tool shares, in the same region.

The Reddit account comes from server/.env (LISTBOT_REDDIT_*, see server/.env.example).
A value missing there keeps what the API already has, or is asked for.

.EXAMPLE
powershell -ExecutionPolicy Bypass -File deploy\azure\provision.ps1
#>
param(
    # deploy.yml and ci.yml name these resources too: change them there with it
    [string]$Name = "list-parser-bot-prod",
    [string]$Domain = "riccardorestagno.com",
    # The API and its data stay in Canada
    [string]$Location = "canadacentral",
    # The tools dashboard's API, which signs the tokens this API checks
    [string]$AuthApi = "https://tools-prod-api.azurewebsites.net",
    # The tools dashboard's App Service plan, as resource group/name
    [string]$Plan = "tools-prod/tools-prod-plan"
)

. "$PSScriptRoot\common.ps1"

$rg = $Name
$api = "$Name-api"
$redditKeys = "LISTBOT_REDDIT_CLIENT_ID", "LISTBOT_REDDIT_CLIENT_SECRET", "LISTBOT_REDDIT_USER_AGENT",
    "LISTBOT_REDDIT_USERNAME", "LISTBOT_REDDIT_PASSWORD"

# --- Confirm the subscription --------------------------------------------------

Assert-AzReady
$subscription = (Invoke-Az account show --query name -o tsv).Trim()
Write-Host "Subscription:   $subscription"
Write-Host "Resource group: $rg ($Location)"
$planGroup, $planName = $Plan -split "/", 2
$planId = "$(Invoke-Az resource list -g $planGroup -n $planName --resource-type Microsoft.Web/serverfarms --query "[0].id" -o tsv)".Trim()
if (-not $planId) { throw "The plan $Plan doesn't exist: provision the tools dashboard first" }
Write-Host "Creates: $api on the plan $Plan, the lock keep-data"
if ((Read-Host "Continue? (y/n)") -ne "y") { exit 1 }

# --- Resource group and API -------------------------------------------------------

# A new subscription must turn on each Azure service before its first use
Write-Host "`nTurning on App Service for the subscription..."
Invoke-Az provider register --namespace Microsoft.Web --wait -o none

Write-Host "Resource group..."
Invoke-Az group create -n $rg -l $Location -o none

Write-Host "API web app..."
if (-not ((Invoke-Az webapp list -g $rg --query "[].name" -o tsv) -contains $api)) {
    Invoke-Az webapp create -g $rg -p $planId -n $api --runtime "PYTHON:3.14" -o none
}
Invoke-Az webapp update -g $rg -n $api --https-only true -o none
# One instance, and one uvicorn process on it (no --workers): one schedule, and SQLite takes one writer
Set-OneInstance $planId $rg $api
# Always On keeps the API, and so its schedule, running: without it App Service stops an idle app.
# uvicorn reads FORWARDED_ALLOW_IPS (set below) to see requests came over HTTPS
Invoke-Az webapp config set -g $rg -n $api --always-on true --min-tls-version 1.2 --ftps-state Disabled `
    --startup-file "uvicorn main:app --host 0.0.0.0 --port 8000 --proxy-headers" -o none
Invoke-Az webapp log config -g $rg -n $api --docker-container-logging filesystem -o none
# Deploys sign in with your Azure account; no FTP or deployment passwords
foreach ($policy in "scm", "ftp") {
    Invoke-Az resource update -g $rg --namespace Microsoft.Web --resource-type basicPublishingCredentialsPolicies `
        --parent "sites/$api" -n $policy --set properties.allow=false -o none
}
$apiHost = Get-ApiHost $rg $api

# --- Sign-in key -------------------------------------------------------------------

Write-Host "The tools dashboard's sign-in key, from $AuthApi..."
try {
    $auth = Invoke-RestMethod -Uri "$AuthApi/auth/public-key" -TimeoutSec 60
}
catch {
    throw "Couldn't get $AuthApi/auth/public-key ($($_.Exception.Message)). Deploy the tools dashboard first, then run this again."
}

# --- The bot's Reddit account -------------------------------------------------------

$envFile = Read-EnvFile (Join-Path $RepoRoot "server\.env")
# Names only: the values stay in Azure
$existing = @(Invoke-Az webapp config appsettings list -g $rg -n $api --query "[].name" -o tsv)
$reddit = [ordered]@{}
foreach ($key in $redditKeys) {
    if ($envFile[$key]) {
        $reddit[$key] = $envFile[$key]
    }
    elseif ($existing -notcontains $key) {
        if ($key -match "SECRET|PASSWORD") {
            $secure = Read-Host "$key (not in server\.env)" -AsSecureString
            $value = [Runtime.InteropServices.Marshal]::PtrToStringBSTR([Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure))
        }
        else {
            $value = Read-Host "$key (not in server\.env)"
        }
        if (-not $value) { throw "$key is needed: the bot can't sign in to Reddit without it" }
        $reddit[$key] = $value
    }
}

# --- API settings -------------------------------------------------------------------

Write-Host "API settings..."
$settings = [ordered]@{
    LISTBOT_DATA_DIR               = "/home/data"
    # Sweeps every LISTBOT_SWEEP_MINUTES (90 unless set here), posting to Reddit
    LISTBOT_SCHEDULE_ENABLED       = "true"
    # The browsers that may call it: the site on the domain, with and without www
    LISTBOT_ALLOWED_ORIGINS        = "https://www.$Domain,https://$Domain"
    # Public; written on one line, which settings.py reads back
    LISTBOT_AUTH_PUBLIC_KEY        = ($auth.public_key.Trim() -replace "`r?`n", "\n")
    LISTBOT_AUTH_ISSUER            = $auth.issuer
    LISTBOT_API_DOCS               = "false"
    SCM_DO_BUILD_DURING_DEPLOYMENT = "true"
    FORWARDED_ALLOW_IPS            = "*"
    TZ                             = "America/Toronto"
}
foreach ($key in $reddit.Keys) { $settings[$key] = $reddit[$key] }
# Passed as a file, like every JSON the scripts hand az.cmd; it holds the Reddit password, so it's removed straight after
$settingsFile = [IO.Path]::GetTempFileName()
try {
    [IO.File]::WriteAllText($settingsFile, ($settings | ConvertTo-Json))
    Invoke-Az webapp config appsettings set -g $rg -n $api --settings "@$settingsFile" -o none
}
finally { Remove-Item $settingsFile -Force }

# Last, once everything exists: deleting the API would delete /home/data with it.
# Remove the lock first to delete anything here on purpose
if (-not ((Invoke-Az lock list -g $rg --query "[].name" -o tsv) -contains "keep-data")) {
    Invoke-Az lock create -n keep-data -g $rg --lock-type CanNotDelete `
        --notes "Keeps the record of sweeps. Remove it to delete anything in this group." -o none
}

Write-Host "`nDone."
Write-Host "  API: https://$apiHost (checks sign-ins from $AuthApi, sweeps once it's deployed)"
Write-Host "`nNext:"
Write-Host "  1. Check API_URL in .github/workflows/ci.yml and deploy.yml is https://$apiHost"
Write-Host "  2. Run deploy\azure\setup-github.ps1 so GitHub can deploy, and add the secret DASHBOARD_DISPATCH_TOKEN (README.md)"
Write-Host "  3. Once the first deploy is live, stop the bot running anywhere else, or both will post"
