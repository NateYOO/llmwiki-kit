# llmwiki setup for Windows (PowerShell 5.1+ or 7). No Python needed: uv downloads Python 3.12.
#
#   powershell -ExecutionPolicy Bypass -File setup\setup_windows.ps1
#   powershell -ExecutionPolicy Bypass -File setup\setup_windows.ps1 -Target "$HOME\Documents\my-thesis"
#   powershell -ExecutionPolicy Bypass -File setup\setup_windows.ps1 -NoUv      # use existing Python instead of uv
#
# No admin rights needed. Files go only to %USERPROFILE%\.local\bin (uv) and the work folder (.venv).
# (Messages are in English on purpose: Windows PowerShell 5.1 misreads non-ASCII text in scripts.)
param(
    [string]$Target = "",
    [switch]$NoUv,
    [switch]$AppendAgents
)
$ErrorActionPreference = "Stop"
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch { Write-Verbose "console encoding unchanged" }
$env:PYTHONUTF8 = "1"
$PyVer = "3.12"
$Kit = Split-Path -Parent $PSScriptRoot
$OnWindows = ($env:OS -eq "Windows_NT")

function Say($msg) { Write-Host ""; Write-Host "==> $msg" -ForegroundColor Cyan }

function Find-Uv {
    $c = Get-Command uv -ErrorAction SilentlyContinue
    if ($c) { return $c.Source }
    foreach ($p in @("$HOME\.local\bin\uv.exe", "$HOME\.cargo\bin\uv.exe", "$HOME/.local/bin/uv")) {
        if (Test-Path $p) { return $p }
    }
    return $null
}

function Get-VenvPython($dir) {
    $win = Join-Path $dir ".venv\Scripts\python.exe"
    $nix = Join-Path $dir ".venv/bin/python"
    if (Test-Path $win) { return $win }
    if (Test-Path $nix) { return $nix }
    return $null
}

# 1) uv
$Uv = $null
if (-not $NoUv) {
    $Uv = Find-Uv
    if (-not $Uv) {
        Say "Installing uv (https://astral.sh/uv, no admin rights)"
        try {
            if ($OnWindows) {
                $inst = Join-Path ([IO.Path]::GetTempPath()) "llmwiki-uv-install.ps1"
                Invoke-WebRequest -Uri https://astral.sh/uv/install.ps1 -OutFile $inst -UseBasicParsing
                & powershell -NoProfile -ExecutionPolicy Bypass -File $inst
            } else {
                & sh -c "curl -LsSf https://astral.sh/uv/install.sh | sh"
            }
        } catch { Write-Warning "uv install failed: $_" }
        $env:Path = "$HOME\.local\bin;$env:Path"
        $Uv = Find-Uv
    }
    if (-not $Uv) { Write-Warning "uv not available; falling back to an existing Python (-NoUv)."; $NoUv = $true }
}

# 2) Python
if (-not $NoUv) {
    Say "Preparing Python $PyVer with uv (does not touch any system Python)"
    & $Uv python install $PyVer
    if ($LASTEXITCODE -ne 0) { throw "uv python install failed" }
    $Py = (& $Uv python find $PyVer).Trim()
} else {
    $Py = $null
    foreach ($cand in @("py", "python", "python3")) {
        # Judge by actually running it (the Store alias prints nothing / fails; a real
        # Python install manager alias under WindowsApps works and is accepted).
        $c = Get-Command $cand -ErrorAction SilentlyContinue
        if ($c) {
            $args0 = @(); if ($cand -eq "py") { $args0 = @("-3") }
            & $c.Source @args0 -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" 2>$null
            if ($LASTEXITCODE -eq 0) { $Py = (& $c.Source @args0 -c "import sys; print(sys.executable)").Trim(); break }
        }
    }
    if (-not $Py) { throw "Python 3.10+ not found. Re-run without -NoUv, or install Python from https://www.python.org" }
}
Write-Host "Python: $Py"

# 3) optional: copy the kit into an existing research folder (never overwrites)
$Work = $Kit
if ($Target -ne "") {
    Say "Installing kit into $Target (existing files are never overwritten)"
    $env:PYTHONPATH = Join-Path $Kit "tools"
    $initArgs = @("-m", "llmwiki", "init", $Target)
    if ($AppendAgents) { $initArgs += "--append-agents" }
    & $Py @initArgs
    if ($LASTEXITCODE -ne 0) { throw "llmwiki init failed" }
    Remove-Item Env:PYTHONPATH
    $Work = (Resolve-Path $Target).Path
}
Set-Location $Work

# 4) .venv inside the work folder + packages
Say "Creating .venv and installing pymupdf, pyyaml, pyzotero"
$VPy = Get-VenvPython $Work
if (-not $NoUv) {
    if (-not $VPy) { & $Uv venv --python $PyVer .venv; $VPy = Get-VenvPython $Work }
    & $Uv pip install --python $VPy -r (Join-Path "setup" "requirements.txt")
} else {
    if (-not $VPy) { & $Py -m venv .venv; $VPy = Get-VenvPython $Work }
    & $VPy -m pip install --upgrade pip | Out-Null
    & $VPy -m pip install -r (Join-Path "setup" "requirements.txt")
}
if ($LASTEXITCODE -ne 0) { throw "package install failed" }

# 5) doctor
Say "Checking environment (llmwiki doctor)"
$env:PYTHONPATH = Join-Path $Work "tools"
$env:LLMWIKI_ROOT = $Work
& $VPy -m llmwiki doctor
Remove-Item Env:PYTHONPATH; Remove-Item Env:LLMWIKI_ROOT

Write-Host ""
Write-Host "Done: $Work" -ForegroundColor Green
Write-Host "  Next: ChatGPT desktop app -> Codex -> open this folder -> New chat"
Write-Host "  In chat:      `$wiki-ingest   (no words = newest PDF in the Zotero practice collection)"
Write-Host "  In terminal:  .\llmwiki.cmd --help"
