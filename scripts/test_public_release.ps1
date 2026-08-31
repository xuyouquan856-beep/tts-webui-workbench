param(
    [switch]$SkipCompile
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Split-Path -Parent $PSScriptRoot)).Path
$artifacts = Join-Path $root "artifacts"
$python = Join-Path $root "backend/venv/Scripts/python.exe"
$zip = Join-Path $artifacts "tts-webui-workbench-v0.1.0-windows-x64.zip"
$reportPath = Join-Path $artifacts "public-release-report.json"
$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("tts-public-acceptance-" + [guid]::NewGuid())
$extract = Join-Path $tempRoot "release"
$smokeData = Join-Path $tempRoot "smoke-data"
$appData = Join-Path $tempRoot "appdata"
$localAppData = Join-Path $tempRoot "localappdata"
$appProcess = $null

$report = [ordered]@{
    version = "0.1.0"
    status = "running"
    commands = @()
    archive = $null
    portable = $null
    skipped_live_tests = @(
        "Higgs/Boson paid synthesis",
        "user-configured translation providers",
        "user-installed Piper and local HTTP/command engines"
    )
}

function Get-StateFingerprint {
    $candidates = @()
    $envFile = Join-Path $root ".env"
    if (Test-Path -LiteralPath $envFile -PathType Leaf) { $candidates += Get-Item -LiteralPath $envFile }
    $dataRoot = Join-Path $root "data"
    if (Test-Path -LiteralPath $dataRoot -PathType Container) {
        $candidates += Get-ChildItem -LiteralPath $dataRoot -Recurse -File
    }
    $lines = @($candidates | Sort-Object FullName | ForEach-Object {
        $relative = $_.FullName.Substring($root.Length).TrimStart([char[]]"\/").Replace("\", "/")
        "$relative|$((Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash)"
    })
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $bytes = [System.Text.Encoding]::UTF8.GetBytes(($lines -join "`n"))
        $fingerprint = ([System.BitConverter]::ToString($sha.ComputeHash($bytes))).Replace("-", "").ToLowerInvariant()
    }
    finally {
        $sha.Dispose()
    }
    return [ordered]@{ file_count = $candidates.Count; fingerprint = $fingerprint }
}

function Invoke-Gate {
    param([string]$Name, [string]$Command, [scriptblock]$Action)
    $started = Get-Date
    try {
        & $Action
        $code = if ($null -eq $LASTEXITCODE) { 0 } else { $LASTEXITCODE }
    }
    catch {
        $code = 1
        $report.commands += [ordered]@{ name = $Name; command = $Command; exit_code = $code; duration_seconds = [math]::Round(((Get-Date) - $started).TotalSeconds, 2) }
        throw
    }
    $report.commands += [ordered]@{ name = $Name; command = $Command; exit_code = $code; duration_seconds = [math]::Round(((Get-Date) - $started).TotalSeconds, 2) }
    if ($code -ne 0) { throw "$Name failed with exit code $code" }
}

New-Item -ItemType Directory -Path $artifacts, $extract, $smokeData, $appData, $localAppData -Force | Out-Null
$stateBefore = Get-StateFingerprint
$oldPythonPath = $env:PYTHONPATH

try {
    if (-not (Test-Path -LiteralPath $python -PathType Leaf)) { throw "Backend virtual environment is missing." }
    $env:PYTHONPATH = Join-Path $root "backend"

    Invoke-Gate "backend_unit" "python -m unittest discover" {
        & $python -m unittest discover -s (Join-Path $root "backend/tests") -p "test_*_unit.py" -q
    }
    Invoke-Gate "frontend_build" "npm --prefix frontend run build" {
        npm --prefix (Join-Path $root "frontend") run build
    }
    Invoke-Gate "rust_test" "cargo test --manifest-path src-tauri/Cargo.toml" {
        cargo test --manifest-path (Join-Path $root "src-tauri/Cargo.toml")
    }
    Invoke-Gate "dummy_smoke" "python backend/tests/smoke_test.py --data-dir <temp>" {
        & $python (Join-Path $root "backend/tests/smoke_test.py") --data-dir $smokeData
    }
    Invoke-Gate "tracked_source_audit" "audit_public_release.ps1 -GitTree" {
        & (Join-Path $root "scripts/audit_public_release.ps1") -Root $root -GitTree
    }

    $buildArgs = @{ OutputDirectory = $artifacts }
    if ($SkipCompile) {
        $buildArgs.Executable = Join-Path $root "src-tauri/target/release/tts-webui-workbench.exe"
        $buildArgs.SidecarExecutable = Join-Path $root "src-tauri/target/release/backend_sidecar.exe"
        $buildArgs.SkipCompile = $true
    }
    Invoke-Gate "portable_build" "build_portable_release.ps1" {
        & (Join-Path $root "scripts/build_portable_release.ps1") @buildArgs
    }

    if (-not (Test-Path -LiteralPath $zip -PathType Leaf)) { throw "Portable ZIP is missing." }
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    [System.IO.Compression.ZipFile]::ExtractToDirectory($zip, $extract)
    $usageFileName = (-join @([char]0x4F7F, [char]0x7528, [char]0x8BF4, [char]0x660E)) + ".txt"
    $expectedFiles = @(".env.example", "app.exe", "backend_sidecar.exe", "LICENSE", "NOTICE", "README.md", $usageFileName) | Sort-Object
    $actualFiles = @(Get-ChildItem -LiteralPath $extract -Recurse -File | ForEach-Object {
        $_.FullName.Substring($extract.Length).TrimStart([char[]]"\/").Replace("\", "/")
    } | Sort-Object)
    if (($expectedFiles -join "|") -ne ($actualFiles -join "|")) {
        throw "Portable archive file allowlist mismatch."
    }
    foreach ($directory in @("data/audio", "data/db", "data/reference")) {
        if (-not (Test-Path -LiteralPath (Join-Path $extract $directory) -PathType Container)) {
            throw "Portable archive directory is missing: $directory"
        }
    }

    $oldAppData = $env:APPDATA
    $oldLocalAppData = $env:LOCALAPPDATA
    $oldWorkbenchData = $env:TTS_WORKBENCH_DATA_DIR
    try {
        $env:APPDATA = $appData
        $env:LOCALAPPDATA = $localAppData
        $env:TTS_WORKBENCH_DATA_DIR = Join-Path $tempRoot "workbench-data"
        $appProcess = Start-Process -FilePath (Join-Path $extract "app.exe") -WorkingDirectory $extract -WindowStyle Hidden -PassThru
    }
    finally {
        $env:APPDATA = $oldAppData
        $env:LOCALAPPDATA = $oldLocalAppData
        $env:TTS_WORKBENCH_DATA_DIR = $oldWorkbenchData
    }

    $health = $null
    $deadline = (Get-Date).AddSeconds(90)
    while ((Get-Date) -lt $deadline -and $null -eq $health) {
        try { $health = Invoke-RestMethod -Uri "http://127.0.0.1:8765/api/health" -TimeoutSec 2 }
        catch { Start-Sleep -Milliseconds 500 }
    }
    if ($null -eq $health) { throw "Portable backend did not become healthy." }
    $healthJson = $health | ConvertTo-Json -Compress
    if ($health.version -ne "0.1.0" -or $healthJson -match "database_url|[A-Z]:\\") {
        throw "Portable health response is invalid or leaks a path."
    }

    $modelsResponse = Invoke-RestMethod -Uri "http://127.0.0.1:8765/api/models" -TimeoutSec 5
    $models = @($modelsResponse | ForEach-Object { $_ })
    $enabledProviders = @($models | Where-Object { $_.enabled -eq $true } | ForEach-Object { $_.provider_type } | Sort-Object -Unique)
    if (($enabledProviders -join "|") -ne "dummy") {
        throw "Clean portable install enabled unexpected providers: $($enabledProviders -join ',') (model count: $($models.Count))."
    }

    $report.archive = [ordered]@{
        file = [System.IO.Path]::GetFileName($zip)
        sha256 = (Get-FileHash -LiteralPath $zip -Algorithm SHA256).Hash.ToLowerInvariant()
        files = $actualFiles
    }
    $report.portable = [ordered]@{
        health = "passed"
        version = $health.version
        enabled_providers = $enabledProviders
        isolated_app_data = $true
    }

    $stateAfter = Get-StateFingerprint
    if ($stateBefore.file_count -ne $stateAfter.file_count -or $stateBefore.fingerprint -ne $stateAfter.fingerprint) {
        throw "Maintainer environment or data files changed during release verification."
    }
    $report.source_state_unchanged = $true
    $report.status = "passed"
}
catch {
    $report.status = "failed"
    $report.error_type = $_.Exception.GetType().Name
    throw
}
finally {
    if ($null -ne $appProcess) {
        & taskkill /PID $appProcess.Id /T /F 2>$null | Out-Null
    }
    $env:PYTHONPATH = $oldPythonPath
    $report.completed_at = (Get-Date).ToUniversalTime().ToString("o")
    $report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $reportPath -Encoding UTF8
    Remove-Item -LiteralPath $tempRoot -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Host "Public release verification passed. Report: $reportPath"
