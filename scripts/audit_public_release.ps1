param(
    [Parameter(Mandatory = $true)]
    [string]$Root,
    [switch]$GitTree
)

$ErrorActionPreference = "Stop"
$rootPath = (Resolve-Path -LiteralPath $Root).Path
$violations = [System.Collections.Generic.List[string]]::new()
$forbiddenExtensions = @(
    ".db", ".sqlite", ".sqlite3",
    ".wav", ".mp3", ".flac", ".ogg", ".m4a", ".aac",
    ".pth", ".pt", ".onnx", ".ckpt", ".safetensors"
)
$textExtensions = @(
    ".md", ".txt", ".json", ".js", ".ts", ".tsx", ".css", ".html",
    ".toml", ".yaml", ".yml", ".example", ".py", ".ps1", ".bat", ".rs"
)
$contentPatterns = @(
    "(?i)[A-Z]:\\Users\\",
    "(?i)/home/[^/\s]+/",
    "(?i)(sk-|ghp_|github_pat_|hf_)[A-Za-z0-9_-]{12,}"
)

if ($GitTree) {
    $files = @(
        & git -C $rootPath -c core.quotepath=false ls-files --cached --others --exclude-standard | ForEach-Object {
            $candidate = Join-Path $rootPath $_
            if (Test-Path -LiteralPath $candidate -PathType Leaf) { Get-Item -LiteralPath $candidate }
        }
    )
}
else {
    $files = @(Get-ChildItem -LiteralPath $rootPath -Recurse -File)
}

foreach ($file in $files) {
    $relative = $file.FullName.Substring($rootPath.Length).TrimStart([char[]]"\/").Replace("\", "/")
    $lower = $relative.ToLowerInvariant()

    if ($lower -eq ".env" -or $forbiddenExtensions -contains $file.Extension.ToLowerInvariant()) {
        $violations.Add($relative)
        continue
    }
    if (($lower -match "^data/(audio|reference)/.+" -or $lower -match "^data/db/.+") -and $file.Name -ne ".gitkeep") {
        $violations.Add($relative)
        continue
    }

    if ($lower -ne "scripts/audit_public_release.ps1" -and ($textExtensions -contains $file.Extension.ToLowerInvariant() -or $file.Name -in @("LICENSE", "NOTICE")) -and $file.Length -le 2MB) {
        $content = Get-Content -LiteralPath $file.FullName -Raw -ErrorAction Stop
        foreach ($pattern in $contentPatterns) {
            if ($content -match $pattern) {
                $violations.Add($relative)
                break
            }
        }
    }
}

if ($violations.Count -gt 0) {
    $paths = ($violations | Sort-Object -Unique) -join ", "
    throw "Public release audit failed. Remove private or forbidden files: $paths"
}

Write-Host "Public release audit passed."
