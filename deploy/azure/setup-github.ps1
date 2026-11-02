<#
.SYNOPSIS
Lets the GitHub workflow (.github/workflows/deploy.yml) deploy to Azure, without
storing any password or key in GitHub. Run once, after provision.ps1; safe to run again.

.DESCRIPTION
Creates an identity, <Name>-github, that only GitHub Actions runs of this repository
on its main branch can sign in as (OpenID Connect). Azure checks this, so it holds
without GitHub's paid branch protection. It may:
  - deploy to the API      (Website Contributor on <Name>-api)
  - read the resource group (Reader)

Prints the three values to add to the repository's Actions variables.

.EXAMPLE
powershell -ExecutionPolicy Bypass -File deploy\azure\setup-github.ps1
#>
param(
    [string]$Name = "list-parser-bot-prod",
    # owner/repository; read from the origin remote when empty
    [string]$Repository
)

. "$PSScriptRoot\common.ps1"

$rg = $Name
$api = "$Name-api"
$identity = "$Name-github"

if (-not $Repository) {
    $origin = (git -C $RepoRoot remote get-url origin).Trim()
    if ($origin -notmatch 'github\.com[:/](.+?)(\.git)?$') { throw "origin isn't a GitHub repository; pass -Repository owner/name" }
    $Repository = $Matches[1]
}

Assert-AzReady
Write-Host "GitHub repository: $Repository (branch: main)"

Invoke-Az provider register --namespace Microsoft.ManagedIdentity --wait -o none

Write-Host "Identity $identity..."
if (-not ((Invoke-Az identity list -g $rg --query "[].name" -o tsv) -contains $identity)) {
    Invoke-Az identity create -g $rg -n $identity -o none
}
$info = Invoke-Az identity show -g $rg -n $identity -o json | Out-String | ConvertFrom-Json

# Only workflow runs of this repository on main can sign in; any other credential
# on the identity (such as an earlier one for a "production" environment) is removed
$subject = "repo:${Repository}:ref:refs/heads/main"
$credentials = Invoke-Az identity federated-credential list -g $rg --identity-name $identity -o json | Out-String | ConvertFrom-Json
if (-not ($credentials | Where-Object { $_.subject -eq $subject })) {
    Invoke-Az identity federated-credential create -g $rg --identity-name $identity -n github-main `
        --issuer "https://token.actions.githubusercontent.com" --subject $subject --audiences "api://AzureADTokenExchange" -o none
}
foreach ($other in $credentials | Where-Object { $_.subject -ne $subject }) {
    Write-Host "  Removing sign-in for $($other.subject)"
    Invoke-Az identity federated-credential delete -g $rg --identity-name $identity -n $other.name --yes -o none
}

Write-Host "Permissions..."
$rgId = (Invoke-Az group show -n $rg --query id -o tsv).Trim()
$apiId = (Invoke-Az webapp show -g $rg -n $api --query id -o tsv).Trim()
Grant-Role $info.principalId "ServicePrincipal" "Reader" $rgId
Grant-Role $info.principalId "ServicePrincipal" "Website Contributor" $apiId

$subscriptionId = (Invoke-Az account show --query id -o tsv).Trim()
Write-Host "`nDone. On GitHub, open $Repository -> Settings -> Secrets and variables -> Actions -> Variables,"
Write-Host "and add these repository variables (they're identifiers, not secrets):`n"
Write-Host "  AZURE_CLIENT_ID        $($info.clientId)"
Write-Host "  AZURE_TENANT_ID        $($info.tenantId)"
Write-Host "  AZURE_SUBSCRIPTION_ID  $subscriptionId"
Write-Host "`nThen, under Secrets (same page, Secrets tab), add DASHBOARD_DISPATCH_TOKEN: a fine-grained personal access"
Write-Host "token with Contents read and write on riccardorestagno/tools-dashboard, so each deploy can start the site's (README.md)."
