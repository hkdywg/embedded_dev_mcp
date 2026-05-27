#Requires -Version 5.1
<#
.SYNOPSIS
    One-click setup for embedded-dev-mcp on Windows.

.DESCRIPTION
    Steps:
      1. Ensure `uv` is installed (auto-install via official script if missing)
      2. Run `uv sync` to create .venv and install dependencies + the project itself
      3. Generate .mcp.json with absolute project path filled in
      4. Verify the server can be imported

    Run from PowerShell:
        .\setup.ps1
    Or double-click setup.bat.

.PARAMETER SkipUvInstall
    Don't try to auto-install uv. Fail if it's missing.

.PARAMETER NoVerify
    Skip the final import-verification step.

.PARAMETER Mirror
    PyPI mirror to use during `uv sync`. Defaults to `default`, which means
    "trust the pyproject.toml [[tool.uv.index]] block" (currently Tsinghua).
    Use `pypi` to force upstream PyPI, or one of the named China mirrors.
#>

[CmdletBinding()]
param(
    [switch]$SkipUvInstall,
    [switch]$NoVerify,
    [ValidateSet('default', 'tsinghua', 'aliyun', 'ustc', 'tencent', 'pypi')]
    [string]$Mirror = 'default'
)

$ErrorActionPreference = 'Stop'
$projectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectDir

function Write-Step($num, $msg) {
    Write-Host ""
    Write-Host "[$num] $msg" -ForegroundColor Cyan
}

function Write-Ok($msg) {
    Write-Host "    OK: $msg" -ForegroundColor Green
}

function Write-Warn($msg) {
    Write-Host "    WARN: $msg" -ForegroundColor Yellow
}

function Test-UvAvailable {
    try {
        $null = & uv --version 2>$null
        return ($LASTEXITCODE -eq 0)
    } catch {
        return $false
    }
}

# ----- 1. Ensure uv is available -----

Write-Step "1/4" "checking for uv"

if (Test-UvAvailable) {
    Write-Ok "uv already installed ($(& uv --version))"
} elseif ($SkipUvInstall) {
    Write-Error "uv not found and -SkipUvInstall passed. Install from https://docs.astral.sh/uv/"
    exit 1
} else {
    Write-Host "    uv not found, installing via https://astral.sh/uv/install.ps1 ..." -ForegroundColor Yellow
    try {
        Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression
    } catch {
        Write-Error "uv installer failed: $_"
        Write-Error "Manual install: https://docs.astral.sh/uv/getting-started/installation/"
        exit 1
    }
    $uvBin = Join-Path $env:USERPROFILE ".local\bin"
    if (Test-Path $uvBin) {
        $env:Path = "$uvBin;$env:Path"
    }
    if (-not (Test-UvAvailable)) {
        Write-Error "uv installation finished but `uv` still isn't on PATH. Open a new terminal and re-run setup.ps1."
        exit 1
    }
    Write-Ok "uv installed ($(& uv --version))"
}

# ----- 2. Sync dependencies into .venv -----

Write-Step "2/4" "running 'uv sync' (creates .venv, installs deps + project)"

$mirrorMap = @{
    'tsinghua' = 'https://pypi.tuna.tsinghua.edu.cn/simple'
    'aliyun'   = 'https://mirrors.aliyun.com/pypi/simple/'
    'ustc'     = 'https://pypi.mirrors.ustc.edu.cn/simple/'
    'tencent'  = 'https://mirrors.cloud.tencent.com/pypi/simple/'
    'pypi'     = 'https://pypi.org/simple'
}
if ($Mirror -ne 'default') {
    $mirrorUrl = $mirrorMap[$Mirror]
    Write-Host "    using mirror: $Mirror ($mirrorUrl)" -ForegroundColor Yellow
    $env:UV_DEFAULT_INDEX = $mirrorUrl
} else {
    Write-Host "    using mirror from pyproject.toml (Tsinghua by default)" -ForegroundColor Yellow
    Write-Host "    if it stalls, retry with: .\setup.ps1 -Mirror aliyun" -ForegroundColor DarkGray
}

& uv sync
if ($LASTEXITCODE -ne 0) {
    Write-Error "uv sync failed (exit $LASTEXITCODE). Try a different mirror: .\setup.ps1 -Mirror aliyun"
    exit 1
}
Write-Ok ".venv ready, dependencies installed"

# ----- 3. Generate .mcp.json from template with absolute path -----

Write-Step "3/4" "generating .mcp.json from template"

$templatePath = Join-Path $projectDir ".mcp.template.json"
$outPath      = Join-Path $projectDir ".mcp.json"

if (-not (Test-Path $templatePath)) {
    Write-Error ".mcp.template.json missing — repo is incomplete"
    exit 1
}

$absForJson = $projectDir.Replace('\', '\\')

$utf8NoBom = [System.Text.UTF8Encoding]::new($false)
$content = [System.IO.File]::ReadAllText($templatePath, $utf8NoBom)
$content = $content.Replace('__ROOT__', $absForJson)

[System.IO.File]::WriteAllText($outPath, $content, $utf8NoBom)
Write-Ok "wrote $outPath"

# ----- 4. Verify import works -----

if (-not $NoVerify) {
    Write-Step "4/4" "verifying import (embedded-dev-mcp)"
    $result = & uv run python -c "from embedded_dev_mcp.server import create_server; print('embedded_dev_mcp import OK')" 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Error "import check failed:`n$result"
        exit 1
    }
    Write-Ok "$result"
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host " embedded-dev-mcp setup complete!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Config file: $outPath"
Write-Host ""
Write-Host " To use with OpenCode / Claude Code:"
Write-Host "   1. Copy server configs from .mcp.json to your MCP settings"
Write-Host "   2. Edit env values:"
Write-Host "      - SSH:  SSH_HOST, SSH_USER, SSH_KEY"
Write-Host "      - ADB:  ADB_SERIAL or ADB_WIFI_HOST"
Write-Host "      - MCU:  PROBE_TYPE, TARGET_CHIP"
Write-Host ""
Write-Host " Supported transports:"
Write-Host "   embedded-dev-ssh       SSH (embedded Linux boards)"
Write-Host "   embedded-dev-adb-usb   ADB USB (Android / RK boards)"
Write-Host "   embedded-dev-adb-wifi  ADB WiFi"
Write-Host "   embedded-dev-mcu       MCU debug (probe-rs + IAR build)"
Write-Host ""
