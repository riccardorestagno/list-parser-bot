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
