[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$RepositoryUrl,

    [string]$Branch = "master",
    [string]$Tag = "v1.1.5",
    [switch]$DryRun
)

$ErrorActionPreference = "Continue"

function Invoke-Git {
    param([Parameter(Mandatory = $true)][string[]]$Arguments)

    & git @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "git command failed: git $($Arguments -join ' ')"
    }
}

function Get-GitOutput {
    param([Parameter(Mandatory = $true)][string[]]$Arguments)

    $output = & git @Arguments 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw "git command failed: git $($Arguments -join ' ')"
    }
    return ($output -join "`n").Trim()
}

function Normalize-RepositoryUrl {
    param([Parameter(Mandatory = $true)][string]$Url)

    $value = $Url.Trim()
    $value = $value.TrimEnd('/')
    if ($value.EndsWith('.git', [StringComparison]::OrdinalIgnoreCase)) {
        $value = $value.Substring(0, $value.Length - 4)
    }
    if ($value -match '^https://github\.com/([^/\s]+)/([^/\s]+)$') {
        return "$($matches[1])/$($matches[2])"
    }
    if ($value -match '^git@github\.com:([^/\s]+)/([^/\s]+)$') {
        return "$($matches[1])/$($matches[2])"
    }
    throw "RepositoryUrl must be an HTTPS or SSH GitHub repository URL."
}

$root = Get-GitOutput @("rev-parse", "--show-toplevel")
$current = [IO.Path]::GetFullPath((Get-Location).Path).TrimEnd('\')
$root = [IO.Path]::GetFullPath($root).TrimEnd('\')
if (-not [StringComparer]::OrdinalIgnoreCase.Equals($root, $current)) {
    throw "Run this script from the repository root: $root"
}

$status = & git status --porcelain 2>$null
if ($LASTEXITCODE -ne 0) {
    throw "Unable to inspect git status."
}
if ($status) {
    throw "Working tree is not clean. Commit or intentionally remove changes before publishing."
}

$head = Get-GitOutput @("rev-parse", "HEAD")
$tagCommit = Get-GitOutput @("rev-list", "-n", "1", $Tag)
if (-not $tagCommit) {
    throw "Required release tag does not exist: $Tag"
}
if ($tagCommit -ne $head) {
    throw "Release tag $Tag does not point to HEAD."
}

$normalizedTarget = Normalize-RepositoryUrl $RepositoryUrl
$existingOrigin = & git remote get-url origin 2>$null
if ($LASTEXITCODE -eq 0 -and $existingOrigin) {
    $normalizedOrigin = Normalize-RepositoryUrl ($existingOrigin -join "`n")
    if ($normalizedOrigin -ne $normalizedTarget) {
        throw "origin already points to a different GitHub repository: $existingOrigin"
    }
    $originAction = "existing"
} elseif ($LASTEXITCODE -ne 0) {
    $originAction = "add"
} else {
    throw "origin exists but has no usable URL."
}

$result = [ordered]@{
    status = "ready"
    dry_run = [bool]$DryRun
    repository = $normalizedTarget
    branch = $Branch
    tag = $Tag
    head = $head
    origin_action = $originAction
    actions = @("verify_clean_worktree", "verify_release_tag")
}

if ($DryRun) {
    if ($originAction -eq "add") {
        $result.actions += "add_origin"
    }
    $result.actions += "push_branch"
    $result.actions += "push_tag"
    $result | ConvertTo-Json -Depth 4
    exit 0
}

if ($originAction -eq "add") {
    Invoke-Git @("remote", "add", "origin", $RepositoryUrl.Trim())
}

Invoke-Git @("push", "--set-upstream", "origin", $Branch)
Invoke-Git @("push", "origin", $Tag)

$result.status = "pushed"
$result.actions += "push_branch"
$result.actions += "push_tag"
$result | ConvertTo-Json -Depth 4
