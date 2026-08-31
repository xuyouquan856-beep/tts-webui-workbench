$ErrorActionPreference = "Stop"

$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("tts-release-test-" + [guid]::NewGuid())
$source = Join-Path $tempRoot "source"
$output = Join-Path $tempRoot "output"
$extract = Join-Path $tempRoot "extract"
$usageFileName = (-join @([char]0x4F7F, [char]0x7528, [char]0x8BF4, [char]0x660E)) + ".txt"

try {
    New-Item -ItemType Directory -Path $source, $output, $extract -Force | Out-Null
    New-Item -ItemType Directory -Path (Join-Path $source "data/audio"), (Join-Path $source "data/db"), (Join-Path $source "data/reference") -Force | Out-Null

    [System.IO.File]::WriteAllBytes((Join-Path $source "app.exe"), [byte[]](77, 90))
    [System.IO.File]::WriteAllBytes((Join-Path $source "backend_sidecar.exe"), [byte[]](77, 90))
    Set-Content -LiteralPath (Join-Path $source ".env.example") -Value "BOSON_API_KEY=" -Encoding UTF8
    Set-Content -LiteralPath (Join-Path $source "README.md") -Value "Public readme" -Encoding UTF8
    Set-Content -LiteralPath (Join-Path $source "LICENSE") -Value "Apache-2.0" -Encoding UTF8
    Set-Content -LiteralPath (Join-Path $source "NOTICE") -Value "Notices" -Encoding UTF8
    Set-Content -LiteralPath (Join-Path $source $usageFileName) -Value "Usage" -Encoding UTF8

    # These files deliberately exist in the source tree and must never be copied.
    Set-Content -LiteralPath (Join-Path $source ".env") -Value "BOSON_API_KEY=private" -Encoding UTF8
    [System.IO.File]::WriteAllBytes((Join-Path $source "data/audio/private.wav"), [byte[]](1, 2, 3))
    Set-Content -LiteralPath (Join-Path $source "data/db/private.db") -Value "private" -Encoding UTF8

    & (Join-Path $PSScriptRoot "build_portable_release.ps1") `
        -SourceRoot $source `
        -Executable (Join-Path $source "app.exe") `
        -SidecarExecutable (Join-Path $source "backend_sidecar.exe") `
        -OutputDirectory $output `
        -SkipCompile

    $zip = Join-Path $output "tts-webui-workbench-v0.1.0-windows-x64.zip"
    $checksum = "$zip.sha256"
    if (-not (Test-Path -LiteralPath $zip)) { throw "release zip was not created" }
    if (-not (Test-Path -LiteralPath $checksum)) { throw "checksum was not created" }

    Add-Type -AssemblyName System.IO.Compression.FileSystem
    [System.IO.Compression.ZipFile]::ExtractToDirectory($zip, $extract)

    foreach ($required in @("app.exe", "backend_sidecar.exe", ".env.example", "README.md", "LICENSE", "NOTICE", $usageFileName)) {
        if (-not (Test-Path -LiteralPath (Join-Path $extract $required))) {
            throw "required release file is missing: $required"
        }
    }
    foreach ($forbidden in @(".env", "data/audio/private.wav", "data/db/private.db")) {
        if (Test-Path -LiteralPath (Join-Path $extract $forbidden)) {
            throw "private source file leaked: $forbidden"
        }
    }
    foreach ($directory in @("data/audio", "data/db", "data/reference")) {
        if (-not (Test-Path -LiteralPath (Join-Path $extract $directory) -PathType Container)) {
            throw "empty release directory is missing: $directory"
        }
    }

    Write-Host "Release script tests passed."
}
finally {
    Remove-Item -LiteralPath $tempRoot -Recurse -Force -ErrorAction SilentlyContinue
}
