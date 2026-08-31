param(
    [string]$SourceRoot = (Split-Path -Parent $PSScriptRoot),
    [string]$Executable,
    [string]$SidecarExecutable,
    [string]$OutputDirectory,
    [switch]$SkipCompile
)

$ErrorActionPreference = "Stop"
$version = "0.1.0"
$usageFileName = (-join @([char]0x4F7F, [char]0x7528, [char]0x8BF4, [char]0x660E)) + ".txt"
$sourcePath = (Resolve-Path -LiteralPath $SourceRoot).Path

if (-not $OutputDirectory) {
    $OutputDirectory = Join-Path $sourcePath "artifacts"
}
New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
$outputPath = (Resolve-Path -LiteralPath $OutputDirectory).Path
if ([System.StringComparer]::OrdinalIgnoreCase.Equals($sourcePath, $outputPath)) {
    throw "OutputDirectory must not be the source root."
}

if (-not $SkipCompile) {
    Push-Location $sourcePath
    try {
        & (Join-Path $sourcePath "build_backend_exe.bat")
        if ($LASTEXITCODE -ne 0) { throw "Backend sidecar build failed." }
        npm --prefix frontend run build
        if ($LASTEXITCODE -ne 0) { throw "Frontend build failed." }
        $tauri = Join-Path $sourcePath "frontend/node_modules/.bin/tauri.cmd"
        if (-not (Test-Path -LiteralPath $tauri -PathType Leaf)) {
            throw "Tauri CLI is unavailable. Run: npm --prefix frontend install"
        }
        & $tauri build --no-bundle
        if ($LASTEXITCODE -ne 0) { throw "Tauri build failed." }
    }
    finally {
        Pop-Location
    }
}

if (-not $Executable) {
    $Executable = Join-Path $sourcePath "src-tauri/target/release/tts-webui-workbench.exe"
}
$executablePath = (Resolve-Path -LiteralPath $Executable).Path
if (-not $SidecarExecutable) {
    $SidecarExecutable = Join-Path $sourcePath "src-tauri/target/release/backend_sidecar.exe"
}
$sidecarPath = (Resolve-Path -LiteralPath $SidecarExecutable).Path
$staging = Join-Path ([System.IO.Path]::GetTempPath()) ("tts-webui-workbench-release-" + [guid]::NewGuid())
$zipPath = Join-Path $outputPath "tts-webui-workbench-v$version-windows-x64.zip"

try {
    New-Item -ItemType Directory -Path $staging -Force | Out-Null
    foreach ($directory in @("data/audio", "data/db", "data/reference")) {
        New-Item -ItemType Directory -Path (Join-Path $staging $directory) -Force | Out-Null
    }

    Copy-Item -LiteralPath $executablePath -Destination (Join-Path $staging "app.exe")
    Copy-Item -LiteralPath $sidecarPath -Destination (Join-Path $staging "backend_sidecar.exe")
    foreach ($file in @(".env.example", "README.md", "LICENSE", "NOTICE", $usageFileName)) {
        $sourceFile = Join-Path $sourcePath $file
        if (-not (Test-Path -LiteralPath $sourceFile -PathType Leaf)) {
            throw "Required public release file is missing: $file"
        }
        Copy-Item -LiteralPath $sourceFile -Destination (Join-Path $staging $file)
    }

    & (Join-Path $PSScriptRoot "audit_public_release.ps1") -Root $staging

    Add-Type -AssemblyName System.IO.Compression
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    if (Test-Path -LiteralPath $zipPath) { Remove-Item -LiteralPath $zipPath -Force }
    $archive = [System.IO.Compression.ZipFile]::Open($zipPath, [System.IO.Compression.ZipArchiveMode]::Create)
    try {
        foreach ($directory in Get-ChildItem -LiteralPath $staging -Recurse -Directory) {
            $relative = $directory.FullName.Substring($staging.Length).TrimStart([char[]]"\/").Replace("\", "/") + "/"
            $null = $archive.CreateEntry($relative)
        }
        foreach ($file in Get-ChildItem -LiteralPath $staging -Recurse -File) {
            $relative = $file.FullName.Substring($staging.Length).TrimStart([char[]]"\/").Replace("\", "/")
            [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($archive, $file.FullName, $relative) | Out-Null
        }
    }
    finally {
        $archive.Dispose()
    }

    $hash = (Get-FileHash -LiteralPath $zipPath -Algorithm SHA256).Hash.ToLowerInvariant()
    Set-Content -LiteralPath "$zipPath.sha256" -Value "$hash  $([System.IO.Path]::GetFileName($zipPath))" -Encoding ASCII
    Write-Host "Portable release created: $zipPath"
}
finally {
    Remove-Item -LiteralPath $staging -Recurse -Force -ErrorAction SilentlyContinue
}
