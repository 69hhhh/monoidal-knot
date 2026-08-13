[CmdletBinding()]
param(
    [ValidateRange(1024, 65535)]
    [int]$Port = 3000,
    [switch]$NoBrowser,
    [switch]$CheckOnly
)

$ErrorActionPreference = "Stop"
$frontendDirectory = $PSScriptRoot
$localUrl = "http://localhost:$Port"
$minimumNodeVersion = [version]"22.13.0"
$mainlandRegistry = "https://registry.npmmirror.com"
$officialRegistry = "https://registry.npmjs.org"

function Write-Step([string]$Message) {
    Write-Host "`n[Knot Atelier] $Message" -ForegroundColor Cyan
}

function Test-KnotAtelierPage([string]$Url) {
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 2
        return $response.StatusCode -eq 200 -and $response.Content -match "Knot Atelier"
    }
    catch {
        return $false
    }
}

Write-Host ""
Write-Host "  Knot Atelier - local knot diagram editor" -ForegroundColor Green
Write-Host "  Project data stays in this browser on this computer." -ForegroundColor DarkGray

$nodeCommand = Get-Command node.exe -ErrorAction SilentlyContinue
$npmCommand = Get-Command npm.cmd -ErrorAction SilentlyContinue
if (-not $nodeCommand -or -not $npmCommand) {
    throw "Node.js was not found. Install Node.js 22 or newer: https://nodejs.org/zh-cn/download"
}

$installedNodeVersionText = (& node.exe -p "process.versions.node").Trim()
$installedNodeVersion = [version]$installedNodeVersionText
if ($installedNodeVersion -lt $minimumNodeVersion) {
    throw "Node.js $installedNodeVersionText is installed, but version 22.13.0 or newer is required."
}
Write-Host "  Node.js $installedNodeVersionText is ready." -ForegroundColor DarkGray

Set-Location -LiteralPath $frontendDirectory
$vinextCommand = Join-Path $frontendDirectory "node_modules\.bin\vinext.cmd"
if (-not (Test-Path -LiteralPath $vinextCommand)) {
    Write-Step "First run: installing dependencies from the mainland mirror..."
    & npm.cmd ci --registry=$mainlandRegistry --no-audit --no-fund
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "The mainland mirror failed. Retrying with the official npm registry."
        & npm.cmd ci --registry=$officialRegistry --no-audit --no-fund
        if ($LASTEXITCODE -ne 0) {
            throw "Dependency installation failed. Check the network connection and run the launcher again."
        }
    }
}

if ($CheckOnly) {
    Write-Host "  Launcher check passed." -ForegroundColor Green
    exit 0
}

if (Test-KnotAtelierPage $localUrl) {
    Write-Host "  Knot Atelier is already running at $localUrl" -ForegroundColor Green
    if (-not $NoBrowser) {
        Start-Process $localUrl
    }
    exit 0
}

$browserWaiter = $null
if (-not $NoBrowser) {
    $waiterScript = @"
`$url = '$localUrl'
for (`$attempt = 0; `$attempt -lt 180; `$attempt += 1) {
    try {
        `$response = Invoke-WebRequest -UseBasicParsing -Uri `$url -TimeoutSec 2
        if (`$response.StatusCode -eq 200 -and `$response.Content -match 'Knot Atelier') {
            Start-Process `$url
            exit 0
        }
    }
    catch {}
    Start-Sleep -Milliseconds 500
}
"@
    $encodedWaiter = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($waiterScript))
    $browserWaiter = Start-Process powershell.exe `
        -ArgumentList "-NoLogo", "-NoProfile", "-EncodedCommand", $encodedWaiter `
        -WindowStyle Hidden `
        -PassThru
}

Write-Step "Starting the editor. The browser will open when it is ready..."
Write-Host "  Address: $localUrl" -ForegroundColor DarkGray
Write-Host "  Keep this window open. Press Ctrl+C to stop Knot Atelier." -ForegroundColor Yellow

try {
    & npm.cmd run dev -- --host 127.0.0.1 --port $Port
    if ($LASTEXITCODE -notin 0, 130, -1073741510) {
        throw "The development server exited with code $LASTEXITCODE."
    }
}
finally {
    if ($browserWaiter -and -not $browserWaiter.HasExited) {
        Stop-Process -Id $browserWaiter.Id -ErrorAction SilentlyContinue
    }
}
