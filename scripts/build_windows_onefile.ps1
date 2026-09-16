$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

$entry = "gui.py"
$name = "kit-prrc.exe"

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw "uv was not found on PATH. Install uv, reopen the shell, and retry."
}

# 同步项目开发环境与依赖
Write-Host ">>> Synchronizing project dependencies with uv..." -ForegroundColor Cyan
uv sync

# 如果存在旧的运行中进程，先行停止以避免文件锁冲突
Get-Process -Name "kit-prrc", "PipelineResistance" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue


# 清理已知历史构建中间目录

Remove-Item -Recurse -Force -ErrorAction SilentlyContinue `
    "dist\gui.build", "dist\gui.dist", "dist\gui.onefile-build", "dist\$name"

Write-Host ">>> [Phase 1] Building Standalone validation artifact..." -ForegroundColor Cyan
uv run python -m nuitka `
    --mode=standalone `
    --assume-yes-for-downloads `
    --enable-plugin=anti-bloat `
    --enable-plugin=tk-inter `
    --windows-console-mode=disable `
    --output-dir=dist `
    --output-filename=$name `
    $entry

if ($LASTEXITCODE -ne 0) {
    throw "Standalone build failed with exit code $LASTEXITCODE"
}

Write-Host ">>> [Phase 2] Building Onefile production artifact..." -ForegroundColor Cyan
uv run python -m nuitka `
    --mode=onefile `
    --assume-yes-for-downloads `
    --enable-plugin=anti-bloat `
    --enable-plugin=tk-inter `
    --windows-console-mode=disable `
    --output-dir=dist `
    --output-filename=$name `
    $entry

if ($LASTEXITCODE -ne 0) {
    throw "Onefile build failed with exit code $LASTEXITCODE"
}

$artifact = Join-Path (Get-Location) "dist\$name"
if (-not (Test-Path $artifact)) {
    throw "Nuitka completed without producing the expected artifact: $artifact"
}

$item = Get-Item $artifact
$sizeMb = [math]::Round($item.Length / 1MB, 2)
Write-Host ">>> Successfully built Onefile EXE:" -ForegroundColor Green
Write-Host "    Path: $($item.FullName)"
Write-Host "    Size: $($item.Length) bytes ($sizeMb MB)"
