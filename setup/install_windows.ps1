# One-line install (Windows PowerShell):
#   irm https://github.com/NateYOO/llmwiki-kit/raw/main/setup/install_windows.ps1 | iex
# Existing research folder:
#   $env:LLMWIKI_TARGET="C:\my-thesis"; irm https://github.com/NateYOO/llmwiki-kit/raw/main/setup/install_windows.ps1 | iex
# Downloads the repo ZIP to a temp folder and runs setup_windows.ps1 -Target <folder>. Never overwrites files.
$ErrorActionPreference = "Stop"
$RepoUrl = if ($env:LLMWIKI_REPO_URL) { $env:LLMWIKI_REPO_URL } else { "https://github.com/NateYOO/llmwiki-kit" }
$Branch = if ($env:LLMWIKI_BRANCH) { $env:LLMWIKI_BRANCH } else { "main" }
$Target = if ($env:LLMWIKI_TARGET) { $env:LLMWIKI_TARGET } else { "C:\llmwiki" }
if ($RepoUrl -like "*<*") { throw "REPO_URL placeholder not replaced. Set `$env:LLMWIKI_REPO_URL='https://github.com/<account>/<repo>' first." }
$Tmp = Join-Path ([System.IO.Path]::GetTempPath()) ("llmwiki-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $Tmp | Out-Null
try {
    $Zip = Join-Path $Tmp "kit.zip"
    $ProgressPreference = "SilentlyContinue"
    Invoke-WebRequest -UseBasicParsing -Uri ("{0}/archive/refs/heads/{1}.zip" -f ($RepoUrl.TrimEnd("/") -replace "\.git$", ""), $Branch) -OutFile $Zip
    Expand-Archive -Path $Zip -DestinationPath $Tmp -Force
    $Kit = Get-ChildItem -Path $Tmp -Directory | Select-Object -First 1
    Get-ChildItem -Path $Kit.FullName -Recurse -File | Unblock-File -ErrorAction SilentlyContinue
    $Shell = (Get-Process -Id $PID).Path
    & $Shell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Kit.FullName "setup\setup_windows.ps1") -Target $Target
} finally {
    Remove-Item -Recurse -Force $Tmp -ErrorAction SilentlyContinue
}
