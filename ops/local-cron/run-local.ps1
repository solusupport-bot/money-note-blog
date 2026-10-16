# 2026-10-16 solusupport-bot 계정의 GitHub Actions가 정지돼 있어서(다른 레포들과 동일 원인)
# blog-build.yml의 매시 정각 스케줄이 돌지 않는다. 같은 파이프라인(publish_gate.py ->
# publish_next.py -> build.py -> git commit/push)을 이 PC에서 직접 실행한다.
# 작업 스케줄러: MoneyNoteBlog-HourlyBuild (1시간마다)
#
# GitHub Pages는 원래 actions/deploy-pages로 배포됐는데 Actions 정지로 막혀 있었다.
# 2026-10-16: money-note-blog가 private 레포라 Free 플랜에서는 애초에 GitHub Pages
# 자체가 안 되는 걸 확인하고, land-in-korea/pickloot-site와 같은 방식으로 Cloudflare
# Pages(Workers)로 직접 배포하도록 전환했다. git push는 백업/이력용으로 계속 한다.

$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$logFile = Join-Path $PSScriptRoot "run-local.log"
function Log($msg) { Add-Content -Path $logFile -Value "$(Get-Date -Format o) $msg" -Encoding utf8 }

$mutex = New-Object System.Threading.Mutex($false, "Global\MoneyNoteBlogCron")
if (-not $mutex.WaitOne([TimeSpan]::FromMinutes(10))) { Log "SKIP: 이전 실행이 아직 진행 중"; exit 0 }

try {
    Set-Location $repo
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $env:GIT_TERMINAL_PROMPT = '0'
    $env:PYTHONUTF8 = '1'
    $env:PYTHONIOENCODING = 'utf-8'

    git pull -q --rebase --autostash origin main 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        git rebase --abort 2>&1 | Out-Null
        Log "FAIL: 실행 전 git pull 실패 — 이번 실행을 건너뜁니다."
        return
    }

    $gateOut = & python automation/publish_gate.py 2>&1 | Out-String
    Add-Content -Path $logFile -Value $gateOut -Encoding utf8
    if ($LASTEXITCODE -ne 0) {
        Log "SKIP: 발행 게이트 - 아직 목표 시각 전이거나 오늘 이미 발행됨"
        return
    }

    $nextOut = & python automation/publish_next.py 2>&1 | Out-String
    Add-Content -Path $logFile -Value $nextOut -Encoding utf8
    if ($LASTEXITCODE -ne 0) { Log "FAIL: publish_next.py (exit $LASTEXITCODE)"; return }

    $buildOut = & python automation/build.py 2>&1 | Out-String
    Add-Content -Path $logFile -Value $buildOut -Encoding utf8
    if ($LASTEXITCODE -ne 0) { Log "FAIL: build.py (exit $LASTEXITCODE)"; return }

    git add content/ automation/topics.json site/
    git diff --cached --quiet
    $didCommit = ($LASTEXITCODE -ne 0)
    if ($didCommit) {
        git commit -q -m "chore: 신규 글 발행 및 사이트 빌드 (local-cron)"
        Log "commit: 신규 글 발행 및 사이트 빌드"
    } else {
        Log "OK: 변경 없음 (발행할 원고가 없었을 수 있음)"
    }

    git push -q origin main 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) { Log "WARN: git push 실패 — 원격에 새 커밋이 있을 수 있음, 다음 실행에서 재시도됨" } else { Log "OK: push 완료" }

    if ($didCommit) {
        $deployOut = & npx wrangler deploy 2>&1 | Out-String
        Add-Content -Path $logFile -Value $deployOut -Encoding utf8
        if ($LASTEXITCODE -ne 0) { Log "FAIL: wrangler pages deploy (exit $LASTEXITCODE)" } else { Log "OK: wrangler pages deploy 완료" }
    }
} finally {
    $mutex.ReleaseMutex()
}
