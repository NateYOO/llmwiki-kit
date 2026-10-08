<#
  LLM 위키 스타터 키트 - Windows 원프롬프트 설치 (bootstrap)
  이 스크립트는 Codex 앱 에이전트가 INSTALL_FOR_AGENT.md 절차대로 실행한다. 학생은 [승인]만 누른다.

  실행(고정):  powershell -NoProfile -ExecutionPolicy Bypass -File <이 파일> -RepoUrl <저장소 주소>
  점검만:      ... -CheckOnly
  하는 일 (8단계, 다시 실행해도 안전 / 기존 파일은 절대 덮어쓰지 않음):
    0 폴더 점검(비어 있음 · OneDrive/문서/바탕화면 자체가 아님)  1 winget 확인  2 Git(선택, 사용자 범위)
    3 uv + Python 3.12 (관리자 권한 없음)  4 키트 받기(git clone 또는 ZIP) + 병합  5 .venv + 패키지
    6 UTF-8 설정  7 git init(Git이 있을 때)  8 doctor + 한 줄 요약
  오류 코드: E00 폴더 / E01 인터넷 / E02 Git(치명 아님) / E03 uv / E04 Python / E05 키트 받기·복사 / E06 패키지 / E07 doctor
  PowerShell 5.1과 7 모두 지원. 시스템 설정(실행 정책 등)은 영구 변경하지 않는다.
#>
[CmdletBinding()]
param(
    [string]$RepoUrl = "",
    [string]$Branch = "main",
    [string]$Target = "",
    [string]$KitSource = "",
    [switch]$CheckOnly,
    [switch]$SkipGit,
    [switch]$NoUv,
    [switch]$AllowNonEmpty
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'   # PS 5.1 Invoke-WebRequest 속도 저하 방지
try { [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false) } catch { $null = $_ }
$OutputEncoding = New-Object System.Text.UTF8Encoding($false)
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
try { [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12 } catch { $null = $_ }

$OnWindows = ($env:OS -eq 'Windows_NT')
$TotalSteps = 8
$Script:LogFile = $null

function Write-Line([string]$Text) {
    Write-Host $Text
    if ($Script:LogFile) { try { Add-Content -LiteralPath $Script:LogFile -Value $Text -Encoding UTF8 } catch { $null = $_ } }
}
function Write-Step([int]$N, [string]$Text) {
    Write-Line ""
    Write-Line ("[{0}/{1}] {2}   ({3})" -f $N, $TotalSteps, $Text, (Get-Date -Format 'HH:mm:ss'))
}
function Exit-WithError([string]$Code, [string]$Message, [string]$Hint) {
    Write-Line ""
    Write-Line "[$Code] $Message"
    if ($Hint) { Write-Line "  해결: $Hint" }
    Write-Line "설치 중단 ❌ / 오류 코드 $Code"
    $num = 0
    [void][int]::TryParse($Code.Substring(1), [ref]$num)
    exit (10 + $num)
}
function Invoke-Native([string]$Exe, [string[]]$Arguments) {
    # 네이티브 명령의 stderr를 오류로 취급하지 않고(PS 5.1), 줄 단위로 바로 보여 준 뒤 종료 코드를 돌려준다.
    $old = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        & $Exe @Arguments 2>&1 | ForEach-Object { Write-Line ("    " + "$_") }
        $code = $LASTEXITCODE
    } catch {
        Write-Line ("    " + $_.Exception.Message)
        $code = 9009
    } finally {
        $ErrorActionPreference = $old
    }
    if ($null -eq $code) { $code = 0 }
    return [int]$code
}
function Sync-SessionPath {
    # 설치 프로그램이 바꾼 PATH는 이미 떠 있는 셸에 반영되지 않으므로 레지스트리 값을 다시 읽는다.
    if (-not $OnWindows) { return }
    $machine = [Environment]::GetEnvironmentVariable('Path', 'Machine')
    $user = [Environment]::GetEnvironmentVariable('Path', 'User')
    $extra = @("$env:USERPROFILE\.local\bin", "$env:LOCALAPPDATA\Programs\Git\cmd", "$env:ProgramFiles\Git\cmd", "$env:LOCALAPPDATA\Microsoft\WinGet\Links")
    $env:Path = (@($machine, $user) + $extra | Where-Object { $_ }) -join ';'
}
function Find-FirstFile([string[]]$Candidates) {
    foreach ($c in $Candidates) { if ($c -and (Test-Path -LiteralPath $c -PathType Leaf)) { return $c } }
    return $null
}
function Find-Git {
    $cands = @()
    if ($OnWindows) { $cands += @("$env:LOCALAPPDATA\Programs\Git\cmd\git.exe", "$env:ProgramFiles\Git\cmd\git.exe") }
    $f = Find-FirstFile $cands
    if ($f) { return $f }
    $cmd = Get-Command git -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($cmd) { return $cmd.Source }
    return $null
}
function Find-Uv {
    $cands = @()
    if ($OnWindows) { $cands += @("$env:USERPROFILE\.local\bin\uv.exe", "$env:LOCALAPPDATA\Microsoft\WinGet\Links\uv.exe", "$env:USERPROFILE\.cargo\bin\uv.exe") }
    else { $cands += @("$HOME/.local/bin/uv", "/usr/local/bin/uv") }
    $f = Find-FirstFile $cands
    if ($f) { return $f }
    $cmd = Get-Command uv -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($cmd) { return $cmd.Source }
    return $null
}
function Test-PythonExe([string]$Exe) {
    # 경로가 아니라 실제 실행 결과로 판정한다(Store 별칭은 실행해도 버전을 출력하지 못함).
    if (-not $Exe) { return $false }
    $old = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $out = & $Exe -c "import sys; print('%d.%d' % sys.version_info[:2])" 2>$null
        $ok = ($LASTEXITCODE -eq 0) -and ("$out" -match '^3\.(1[0-9]|[2-9][0-9])')
    } catch { $ok = $false } finally { $ErrorActionPreference = $old }
    return $ok
}
function Invoke-Download([string]$Url, [string]$OutFile) {
    for ($i = 1; $i -le 2; $i++) {
        try {
            Invoke-WebRequest -Uri $Url -OutFile $OutFile -UseBasicParsing
            return $true
        } catch {
            Write-Line ("    다운로드 실패({0}/2): {1}" -f $i, $_.Exception.Message)
            Start-Sleep -Seconds 2
        }
    }
    return $false
}
function Copy-KitFile([string]$Src, [string]$Dst) {
    # 키트 → 작업 폴더 병합. 이미 있는 파일은 절대 덮어쓰지 않는다.
    #   AGENTS.md / README.md / .gitignore 가 이미 있고 내용이 다르면 *.llmwiki.* 이름으로 옆에 둔다.
    $Src = (Resolve-Path -LiteralPath $Src).ProviderPath.TrimEnd('\', '/')
    $special = @{ 'AGENTS.md' = 'AGENTS.llmwiki.md'; 'README.md' = 'README.llmwiki.md'; '.gitignore' = '.gitignore.llmwiki' }
    $copied = 0; $skipped = 0; $alt = @()
    $files = Get-ChildItem -LiteralPath $Src -Recurse -Force -File
    foreach ($f in $files) {
        $rel = $f.FullName.Substring($Src.Length).TrimStart('\', '/')
        if ($rel -match '^(\.git|\.venv)([\\/]|$)' -or $rel -match '__pycache__') { continue }
        $dest = Join-Path $Dst $rel
        if (Test-Path -LiteralPath $dest) {
            if ($special.ContainsKey($rel)) {
                $same = $false
                try { $same = ((Get-FileHash -LiteralPath $dest).Hash -eq (Get-FileHash -LiteralPath $f.FullName).Hash) } catch { $null = $_ }
                if (-not $same) {
                    $altPath = Join-Path $Dst $special[$rel]
                    if (-not (Test-Path -LiteralPath $altPath)) { Copy-Item -LiteralPath $f.FullName -Destination $altPath; $alt += $special[$rel] }
                }
            }
            $skipped++
            continue
        }
        $dir = Split-Path -Parent $dest
        if (-not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
        Copy-Item -LiteralPath $f.FullName -Destination $dest
        $copied++
    }
    return @{ Copied = $copied; Skipped = $skipped; Alt = $alt }
}

# ------------------------------------------------------------------ 0. 폴더 점검
if (-not $Target) { $Target = (Get-Location).ProviderPath }
$Target = [IO.Path]::GetFullPath($Target).TrimEnd('\', '/')
if ($Target.Length -lt 3) { $Target = $Target + [IO.Path]::DirectorySeparatorChar }
Write-Line "LLM 위키 스타터 키트 설치 (Windows bootstrap) - 예상 5~10분, 다운로드 약 60MB"
Write-Step 0 "폴더 점검"
$who = ''
try { $who = [Security.Principal.WindowsIdentity]::GetCurrent().Name } catch { $who = [Environment]::UserName }
Write-Line "  작업 폴더   : $Target"
Write-Line "  실행 사용자 : $who"
Write-Line ("  사용자 폴더 : {0}" -f $(if ($env:USERPROFILE) { $env:USERPROFILE } else { $HOME }))
Write-Line ("  PowerShell  : {0}" -f $PSVersionTable.PSVersion)
if (-not (Test-Path -LiteralPath $Target -PathType Container)) { Exit-WithError -Code 'E00' -Message "작업 폴더가 없습니다: $Target" -Hint "Codex 앱에서 빈 폴더(권장: C:\llmwiki)를 열고 다시 시작하세요." }
$docs = [Environment]::GetFolderPath('MyDocuments'); $desk = [Environment]::GetFolderPath('Desktop')
$homeDir = $(if ($env:USERPROFILE) { $env:USERPROFILE } else { $HOME })
$special = @($docs, $desk, $homeDir) | Where-Object { $_ } | ForEach-Object { $_.TrimEnd('\', '/') }
if ($Target -match 'OneDrive') {
    Exit-WithError -Code 'E00' -Message "OneDrive 안의 폴더입니다(동기화가 .venv 수천 개 파일을 올리고, 파일 잠금으로 설치가 깨질 수 있음)." -Hint "탐색기에서 C:\llmwiki 폴더를 새로 만들고, Codex 앱에서 그 폴더를 연 뒤 같은 문장을 다시 보내세요."
}
if ($special -contains $Target -or $Target -match '^[A-Za-z]:\\?$') {
    Exit-WithError -Code 'E00' -Message "문서/바탕 화면/사용자 폴더(또는 드라이브 최상위) 자체를 열었습니다." -Hint "C:\llmwiki 같은 새 빈 폴더를 만들어 Codex 앱에서 열고 다시 시작하세요."
}
$ignore = @('desktop.ini', 'Thumbs.db', '.DS_Store', '.git', '.llmwiki-install.log', '.codex')
$entries = @(Get-ChildItem -LiteralPath $Target -Force | Where-Object { $ignore -notcontains $_.Name })
$kitHere = (Test-Path -LiteralPath (Join-Path $Target 'tools\llmwiki\cli.py')) -and (Test-Path -LiteralPath (Join-Path $Target 'AGENTS.md'))
if ($entries.Count -gt 0 -and -not $kitHere -and -not $AllowNonEmpty) {
    $names = ($entries | Select-Object -First 8 | ForEach-Object { $_.Name }) -join ', '
    Exit-WithError -Code 'E00' -Message "폴더가 비어 있지 않습니다: $names" -Hint "새 빈 폴더(권장: C:\llmwiki)를 열어 다시 시작하세요. 기존 연구 폴더에 넣으려면 README의 'llmwiki init' 방법을 쓰세요."
}
if ($kitHere) { Write-Line "  이미 키트가 있는 폴더 → 이어서 설치(기존 파일 보존)" } else { Write-Line "  빈 폴더 확인" }
if ($homeDir -match '[^\x00-\x7F]') { Write-Line "  참고: 사용자 폴더 이름에 한글이 있습니다. uv·Python은 지원하지만, 문제가 생기면 오류 코드를 알려 주세요." }
if ($CheckOnly) { Write-Line ""; Write-Line "CHECK OK - 설치를 진행해도 됩니다."; exit 0 }
# 점검을 통과한 뒤에만 폴더에 기록을 남긴다(점검 실패·CheckOnly 때는 학생 폴더에 아무것도 만들지 않음)
$Script:LogFile = Join-Path $Target '.llmwiki-install.log'
Write-Line ("--- 설치 시작 {0} ---" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'))

# ------------------------------------------------------------------ 1. winget
Write-Step 1 "winget 확인"
Sync-SessionPath
$winget = Get-Command winget -ErrorAction SilentlyContinue | Select-Object -First 1
if ($winget) { Write-Line "  winget 있음: $($winget.Source)" } else { Write-Line "  winget 없음 → Git 설치는 건너뛰고 ZIP으로 받습니다(문제 없음)." }
$wingetCommon = @('--accept-source-agreements', '--accept-package-agreements', '--disable-interactivity', '--silent', '-e', '--source', 'winget')

# ------------------------------------------------------------------ 2. Git (선택)
Write-Step 2 "Git (선택 - 없어도 설치는 계속됩니다)"
$git = Find-Git
if ($git) { Write-Line "  Git 있음: $git" }
elseif ($SkipGit -or -not $OnWindows) { Write-Line "  Git 건너뜀" }
elseif ($winget) {
    Write-Line "  winget으로 Git 설치(사용자 범위 시도, 1~3분)"
    $rc = Invoke-Native $winget.Source (@('install', '--id', 'Git.Git', '--scope', 'user') + $wingetCommon)
    Sync-SessionPath; $git = Find-Git
    if (-not $git) {
        Write-Line "  사용자 범위 설치가 안 되어 일반 설치를 시도합니다(Windows 확인 창이 뜨면 [예]). rc=$rc"
        $rc = Invoke-Native $winget.Source (@('install', '--id', 'Git.Git') + $wingetCommon)
        Sync-SessionPath; $git = Find-Git
    }
    if ($git) { Write-Line "  Git 설치됨: $git" } else { Write-Line "  [E02] Git 설치 실패(rc=$rc) - 치명 아님, ZIP으로 계속합니다." }
} else { Write-Line "  winget이 없어 Git은 건너뜁니다." }

# ------------------------------------------------------------------ 3. uv + Python
Write-Step 3 "Python 3.12 준비 (uv, 관리자 권한 없음, 1~2분)"
$uv = $null; $basePy = $null
if (-not $NoUv) {
    $uv = Find-Uv
    if (-not $uv -and $OnWindows) {
        Write-Line "  uv 설치(astral.sh 공식 설치 스크립트, 사용자 폴더에 설치)"
        $uvInstaller = Join-Path ([IO.Path]::GetTempPath()) 'llmwiki-uv-install.ps1'
        if (Invoke-Download 'https://astral.sh/uv/install.ps1' $uvInstaller) {
            $null = Invoke-Native 'powershell' @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $uvInstaller)
        }
        Sync-SessionPath; $uv = Find-Uv
        if (-not $uv -and $winget) {
            Write-Line "  설치 스크립트 실패 → winget으로 uv 설치"
            $null = Invoke-Native $winget.Source (@('install', '--id', 'astral-sh.uv', '--scope', 'user') + $wingetCommon)
            Sync-SessionPath; $uv = Find-Uv
        }
    }
    if ($uv) {
        Write-Line "  uv: $uv"
        $rc = Invoke-Native $uv @('python', 'install', '3.12')
        if ($rc -ne 0) { $rc = Invoke-Native $uv @('python', 'install', '3.12') }
        $old = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
        $found = & $uv python find 3.12 2>$null
        $ErrorActionPreference = $old
        if (Test-PythonExe "$found") { $basePy = "$found".Trim() }
    } else {
        Write-Line "  [E03] uv를 설치하지 못했습니다 → winget Python으로 대신 시도"
    }
}
if (-not $basePy) {
    $cands = @()
    if ($OnWindows) {
        $cands += @("$env:LOCALAPPDATA\Programs\Python\Python312\python.exe", "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe")
        if (-not (Find-FirstFile $cands) -and $winget) {
            Write-Line "  winget으로 Python 3.12 설치(사용자 범위)"
            $null = Invoke-Native $winget.Source (@('install', '--id', 'Python.Python.3.12', '--scope', 'user') + $wingetCommon)
        }
        $cands += @('py')
    } else { $cands += @('python3') }
    foreach ($c in $cands) {
        if ($c -eq 'py') {
            $old = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
            $p = & py -3 -c "import sys; print(sys.executable)" 2>$null
            $ErrorActionPreference = $old
            if ($LASTEXITCODE -eq 0 -and (Test-PythonExe "$p")) { $basePy = "$p".Trim(); break }
        } elseif ((Test-Path -LiteralPath $c) -or (Get-Command $c -ErrorAction SilentlyContinue)) {
            if (Test-PythonExe $c) { $basePy = $c; break }
        }
    }
}
if (-not $basePy -and -not $uv) { Exit-WithError -Code 'E04' -Message "Python 3.10 이상을 준비하지 못했습니다." -Hint "인터넷 연결을 확인하고 같은 문장을 다시 보내세요. 두 번째도 같으면 이 화면을 강사에게 보여 주세요." }
if ($basePy) { Write-Line "  Python: $basePy" }

# ------------------------------------------------------------------ 4. 키트 받기 + 병합
Write-Step 4 "키트 받기 + 작업 폴더에 복사 (기존 파일은 건드리지 않음)"
$tmpRoot = Join-Path ([IO.Path]::GetTempPath()) ("llmwiki-kit-" + [guid]::NewGuid().ToString('N').Substring(0, 8))
$kit = $null
if ($KitSource) { $kit = $KitSource; Write-Line "  로컬 키트 사용: $kit" }
elseif ($kitHere -and (Test-Path -LiteralPath (Join-Path $Target 'setup\requirements.txt'))) { Write-Line "  이미 키트가 있음 → 받기 생략" }
else {
    if (-not $RepoUrl -or $RepoUrl -match '<') { Exit-WithError -Code 'E05' -Message "저장소 주소(-RepoUrl)가 없습니다." -Hint "INSTALL_FOR_AGENT.md 1단계의 명령에 학생이 준 주소를 그대로 넣으세요." }
    $RepoUrl = $RepoUrl.Trim().TrimEnd('/')
    if ($RepoUrl.EndsWith('.git')) { $RepoUrl = $RepoUrl.Substring(0, $RepoUrl.Length - 4) }
    New-Item -ItemType Directory -Path $tmpRoot -Force | Out-Null
    if ($git) {
        Write-Line "  git clone $RepoUrl"
        $rc = Invoke-Native $git @('clone', '--depth', '1', '--branch', $Branch, "$RepoUrl.git", (Join-Path $tmpRoot 'kit'))
        if ($rc -eq 0) { $kit = Join-Path $tmpRoot 'kit' } else { Write-Line "  git clone 실패(rc=$rc) → ZIP으로 받기" }
    }
    if (-not $kit) {
        $zipUrl = "$RepoUrl/archive/refs/heads/$Branch.zip"
        $zip = Join-Path $tmpRoot 'kit.zip'
        Write-Line "  ZIP 받기: $zipUrl"
        if (-not (Invoke-Download $zipUrl $zip)) { Exit-WithError -Code 'E01' -Message "키트 ZIP을 받지 못했습니다." -Hint "인터넷 연결과 저장소 주소를 확인하세요: $zipUrl" }
        try { Unblock-File -LiteralPath $zip -ErrorAction SilentlyContinue } catch { $null = $_ }
        Expand-Archive -LiteralPath $zip -DestinationPath (Join-Path $tmpRoot 'x') -Force
        $kit = (Get-ChildItem -LiteralPath (Join-Path $tmpRoot 'x') -Directory | Select-Object -First 1).FullName
    }
}
if ($kit) {
    if (-not (Test-Path -LiteralPath (Join-Path $kit 'tools/llmwiki/cli.py'))) { Exit-WithError -Code 'E05' -Message "받은 파일에 키트(tools/llmwiki)가 없습니다: $kit" -Hint "저장소 주소가 맞는지 확인하세요." }
    try { $res = Copy-KitFile $kit $Target }
    catch [System.UnauthorizedAccessException] { Exit-WithError -Code 'E05' -Message "폴더에 쓸 권한이 없습니다: $($_.Exception.Message)" -Hint "Windows 보안 → 바이러스 및 위협 방지 → 랜섬웨어 방지 → '제어된 폴더 액세스'가 켜져 있으면 C:\llmwiki 처럼 보호되지 않는 폴더를 쓰세요." }
    catch { Exit-WithError -Code 'E05' -Message "파일 복사 실패: $($_.Exception.Message)" -Hint "백신이 막았을 수 있습니다. C:\llmwiki 폴더에서 다시 시도하세요." }
    Write-Line ("  복사 {0}개 · 이미 있어서 건너뜀 {1}개" -f $res.Copied, $res.Skipped)
    foreach ($a in $res.Alt) { Write-Line "  기존 파일과 달라서 옆에 둠: $a (합칠지는 사람이 결정)" }
}
foreach ($need in @('AGENTS.md', 'tools\llmwiki\cli.py', 'setup\requirements.txt', '.agents\skills\wiki-ingest\SKILL.md')) {
    if (-not (Test-Path -LiteralPath (Join-Path $Target $need))) { Exit-WithError -Code 'E05' -Message "필수 파일이 없습니다: $need" -Hint "같은 문장을 다시 보내 주세요(이미 받은 파일은 보존됩니다)." }
}

# ------------------------------------------------------------------ 5. .venv + 패키지
Write-Step 5 "가상환경(.venv) + 패키지 설치 (pymupdf · pyyaml · pyzotero, 1~3분)"
$venvDir = Join-Path $Target '.venv'
$venvPy = $(if ($OnWindows) { Join-Path $venvDir 'Scripts\python.exe' } else { Join-Path $venvDir 'bin/python' })
$req = Join-Path $Target 'setup\requirements.txt'
if (-not $OnWindows) { $req = Join-Path $Target 'setup/requirements.txt' }
if (Test-PythonExe $venvPy) { Write-Line "  기존 .venv 재사용: $venvPy" }
else {
    if (Test-Path -LiteralPath $venvDir) { Write-Line "  망가진 .venv를 다시 만듭니다"; Remove-Item -LiteralPath $venvDir -Recurse -Force }
    if ($uv) { $rc = Invoke-Native $uv @('venv', $venvDir, '--python', $(if ($basePy) { $basePy } else { '3.12' })) }
    else { $rc = Invoke-Native $basePy @('-m', 'venv', $venvDir) }
    if (-not (Test-PythonExe $venvPy)) { Exit-WithError -Code 'E04' -Message "가상환경을 만들지 못했습니다(rc=$rc)." -Hint "같은 문장을 다시 보내 주세요. 두 번째도 같으면 강사에게 화면을 보여 주세요." }
}
if ($uv) {
    $rc = Invoke-Native $uv @('pip', 'install', '--python', $venvPy, '-r', $req)
    if ($rc -ne 0) { Write-Line "  한 번 더 시도"; $rc = Invoke-Native $uv @('pip', 'install', '--python', $venvPy, '-r', $req) }
} else {
    $rc = Invoke-Native $venvPy @('-m', 'pip', 'install', '--disable-pip-version-check', '-r', $req)
    if ($rc -ne 0) { Write-Line "  한 번 더 시도"; $rc = Invoke-Native $venvPy @('-m', 'pip', 'install', '--disable-pip-version-check', '-r', $req) }
}
if ($rc -ne 0) { Exit-WithError -Code 'E06' -Message "패키지 설치 실패(rc=$rc)." -Hint "인터넷 연결을 확인하고 같은 문장을 다시 보내세요." }

# ------------------------------------------------------------------ 6. UTF-8
Write-Step 6 "한글 출력 설정 (PYTHONUTF8=1)"
if ($OnWindows) {
    if ([Environment]::GetEnvironmentVariable('PYTHONUTF8', 'User') -ne '1') {
        [Environment]::SetEnvironmentVariable('PYTHONUTF8', '1', 'User')
        Write-Line "  사용자 환경 변수 PYTHONUTF8=1 설정 (llmwiki.cmd도 매번 설정함)"
    } else { Write-Line "  이미 설정됨" }
} else { Write-Line "  (Windows 아님 - 건너뜀)" }

# ------------------------------------------------------------------ 7. git init
Write-Step 7 "버전 관리 폴더로 만들기 (git init, Git이 있을 때만)"
if ($git -and -not (Test-Path -LiteralPath (Join-Path $Target '.git'))) {
    $null = Invoke-Native $git @('-C', $Target, 'init', '-q')
    Write-Line "  git init 완료 (Codex가 이 폴더를 프로젝트 루트로 인식하기 쉬워짐)"
} elseif ($git) { Write-Line "  이미 git 저장소" } else { Write-Line "  Git 없음 - 건너뜀(없어도 됨)" }

# ------------------------------------------------------------------ 8. doctor
Write-Step 8 "환경 점검 (llmwiki doctor)"
$env:PYTHONPATH = Join-Path $Target 'tools'
$env:LLMWIKI_ROOT = $Target
$old = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
$json = (& $venvPy -m llmwiki --root $Target doctor --json 2>$null) -join "`n"
$ErrorActionPreference = $old
try { $doc = $json | ConvertFrom-Json } catch { $doc = $null }
if (-not $doc) { Write-Line $json; Exit-WithError -Code 'E07' -Message "doctor를 실행하지 못했습니다." -Hint "같은 문장을 다시 보내 주세요." }
foreach ($c in $doc.checks) { if ($c.level -ne 'PASS') { Write-Line ("  [{0}] {1}  {2}" -f $c.level, $c.name, $c.message) } }
Write-Line ("  PASS {0}개 생략 · FAIL {1} · WARN {2}" -f (@($doc.checks | Where-Object { $_.level -eq 'PASS' })).Count, $doc.fail, $doc.warn)
if (Test-Path -LiteralPath $tmpRoot) { Remove-Item -LiteralPath $tmpRoot -Recurse -Force -ErrorAction SilentlyContinue }
Write-Line ""
Write-Line "다음: Codex 앱에서 이 폴더로 '새 채팅'을 열고 「이 폴더의 AGENTS.md와 사용 가능한 스킬 목록을 말해줘」라고 보내세요."
if ([int]$doc.fail -gt 0) { Write-Line $doc.summary; exit 17 }
Write-Line $doc.summary
exit 0
