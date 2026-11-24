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
    [string]$Repository,
    # GitHub's numeric ids for the owner and the repository; asked of the gh CLI when empty.
    # Shown in a failed sign-in's subject: repo:<owner>@<OwnerId>/<repository>@<RepositoryId>:ref:...
    [string]$OwnerId,
    [string]$RepositoryId
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

# Only workflow runs of this repository on main can sign in. GitHub names the repository in
# its sign-in either by name alone (older repositories) or by name and numeric ids (newer
# ones), so both are allowed. Any other credential on the identity (such as an earlier one
# for a "production" environment) is removed
$owner, $repositoryName = $Repository -split "/", 2
if (-not ($OwnerId -and $RepositoryId) -and (Get-Command gh -ErrorAction SilentlyContinue)) {
    $OwnerId = "$(gh api "repos/$Repository" --jq .owner.id)".Trim()
    $RepositoryId = "$(gh api "repos/$Repository" --jq .id)".Trim()
}
$subjects = [ordered]@{ "github-main" = "repo:${Repository}:ref:refs/heads/main" }
if ($OwnerId -match '^\d+$' -and $RepositoryId -match '^\d+$') {
    $subjects["github-main-ids"] = "repo:${owner}@${OwnerId}/${repositoryName}@${RepositoryId}:ref:refs/heads/main"
}
else {
    Write-Warning ("Couldn't get the repository's ids (sign in with: gh auth login, or pass -OwnerId and -RepositoryId). " +
        "If GitHub names it by id, deploys fail with AADSTS700213, whose subject shows both ids.")
}

$credentials = Invoke-Az identity federated-credential list -g $rg --identity-name $identity -o json | Out-String | ConvertFrom-Json
foreach ($entry in $subjects.GetEnumerator()) {
    if (-not ($credentials | Where-Object { $_.subject -eq $entry.Value })) {
        Write-Host "  Allowing $($entry.Value)"
        Invoke-Az identity federated-credential create -g $rg --identity-name $identity -n $entry.Key `
            --issuer "https://token.actions.githubusercontent.com" --subject $entry.Value --audiences "api://AzureADTokenExchange" -o none
    }
}
foreach ($other in $credentials | Where-Object { $subjects.Values -notcontains $_.subject }) {
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
