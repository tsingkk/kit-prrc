$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

$entry = "gui.py"
$name = "kit管道阻力降计算工具.exe"

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw "uv was not found on PATH. Install uv, reopen the shell, and retry."
}

# 同步项目开发环境与依赖
Write-Host ">>> Synchronizing project dependencies with uv..." -ForegroundColor Cyan
uv sync

# 如果存在旧的运行中进程，先行停止以避免文件锁冲突
Get-Process -Name "kit-prrc", "PipelineResistance", "kit管道阻力降计算工具" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue

# 清理已知历史构建中间目录与旧产物
Remove-Item -Recurse -Force -ErrorAction SilentlyContinue `
    "dist\gui.build", "dist\gui.dist", "dist\gui.onefile-build", "dist\$name", "dist\kit-prrc.exe"

Write-Host ">>> Building minimal Onefile executable with Nuitka..." -ForegroundColor Cyan

uv run python -m nuitka `
    --mode=onefile `
    --assume-yes-for-downloads `
    --lto=yes `
    --deployment `
    --remove-output `
    --enable-plugin=anti-bloat `
    --enable-plugin=tk-inter `
    --python-flag=no_docstrings `
    --python-flag=no_asserts `
    --python-flag=no_site `
    --nofollow-import-to=unittest,pydoc,doctest,pdb,bdb,difflib `
    --nofollow-import-to=email,http,urllib,xml,html `
    --nofollow-import-to=ssl,hashlib,hmac,secrets `
    --nofollow-import-to=sqlite3,lzma,bz2 `
    --nofollow-import-to=multiprocessing,concurrent,asyncio,socket,select,selectors `
    --nofollow-import-to=tkinter.tix,tkinter.colorchooser,tkinter.filedialog,tkinter.simpledialog,tkinter.dnd,idlelib,turtle `
    '--noinclude-data-files=tcl/tzdata/*' `
    '--noinclude-data-files=tcl/msgs/*' `
    '--noinclude-data-files=tcl/opt0.4/*' `
    '--noinclude-data-files=tcl/http1.0/*' `
    '--noinclude-data-files=tk/msgs/*' `
    '--noinclude-data-files=tk/images/*' `
    '--noinclude-data-files=tcl/encoding/jis*' `
    '--noinclude-data-files=tcl/encoding/ksc*' `
    '--noinclude-data-files=tcl/encoding/shiftjis*' `
    '--noinclude-data-files=tcl/encoding/euc-*' `
    '--noinclude-data-files=tcl/encoding/big5*' `
    '--noinclude-data-files=tcl/encoding/cp932*' `
    '--noinclude-data-files=tcl/encoding/cp949*' `
    '--noinclude-data-files=tcl/encoding/cp950*' `
    '--noinclude-data-files=tcl/encoding/cns11643*' `
    '--noinclude-data-files=tcl/encoding/iso2022*' `
    '--noinclude-data-files=tcl/encoding/mac*' `
    '--noinclude-data-files=tcl/encoding/ebcdic*' `
    '--noinclude-dlls=libcrypto*,libssl*,sqlite3*,liblzma*,libbz2*' `
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
