[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$ProjectRoot = $PSScriptRoot
$PythonCommand = Get-Command python -ErrorAction SilentlyContinue
if (-not $PythonCommand) {
    throw 'Python 3.11 or newer is required to build releases. Install Python from https://www.python.org/downloads/windows/'
}

Push-Location $ProjectRoot
try {
    $version = (& python -c "import config; print(config.APP_VERSION)").Trim()
    $publisher = (& python -c "import config; print(config.APP_PUBLISHER)").Trim()
    if ($LASTEXITCODE -ne 0 -or $version -notmatch '^\d+\.\d+\.\d+(?:\.\d+)?$') {
        throw 'Could not read a valid APP_VERSION from config.py.'
    }

    $required = @(
        'assets\issa.ico', 'assets\issa-logo.png',
        'ffmpeg\bin\ffmpeg.exe', 'ffmpeg\bin\ffprobe.exe',
        'runtime\yt-dlp.exe', 'runtime\SHA2-256SUMS', 'runtime\deno.exe', 'runtime\deno.exe.sha256sum', 'runtime\DENO_LICENSE.md',
        'ISSA.spec', 'installer\ISSA.iss'
    )
    foreach ($item in $required) {
        if (-not (Test-Path -LiteralPath (Join-Path $ProjectRoot $item) -PathType Leaf)) {
            throw "Required build input is missing: $item"
        }
    }

    $sumLine = Get-Content -LiteralPath 'runtime\SHA2-256SUMS' | Where-Object { $_ -match '\syt-dlp\.exe$' } | Select-Object -First 1
    if (-not $sumLine) { throw 'runtime\SHA2-256SUMS has no yt-dlp.exe entry.' }
    $expectedHash = ($sumLine -split '\s+')[0].ToLowerInvariant()
    $actualHash = (Get-FileHash -Algorithm SHA256 -LiteralPath 'runtime\yt-dlp.exe').Hash.ToLowerInvariant()
    if ($expectedHash -ne $actualHash) { throw 'runtime\yt-dlp.exe failed its official SHA-256 verification.' }
    $denoExpected = ((Get-Content -LiteralPath 'runtime\deno.exe.sha256sum' -Raw) -split '\s+')[0].ToLowerInvariant()
    $denoActual = (Get-FileHash -Algorithm SHA256 -LiteralPath 'runtime\deno.exe').Hash.ToLowerInvariant()
    if ($denoExpected -ne $denoActual) { throw 'runtime\deno.exe failed its official SHA-256 verification.' }

    & python tools\generate_brand.py
    if ($LASTEXITCODE -ne 0) { throw 'Brand generation failed.' }
    & python -m pip install --disable-pip-version-check -r requirements-build.txt
    if ($LASTEXITCODE -ne 0) { throw 'Build dependency installation failed.' }

    foreach ($directory in @('build-release', 'dist-app', 'dist-installer')) {
        $path = Join-Path $ProjectRoot $directory
        if (Test-Path -LiteralPath $path) { Remove-Item -LiteralPath $path -Recurse -Force }
    }

    & python -m PyInstaller --noconfirm --clean --workpath build-release --distpath dist-app ISSA.spec
    if ($LASTEXITCODE -ne 0) { throw 'PyInstaller build failed.' }

    $appRoot = Join-Path $ProjectRoot 'dist-app\ISSA'
    $packagedFiles = @(
        'ISSA.exe',
        '_internal\ffmpeg\bin\ffmpeg.exe',
        '_internal\ffmpeg\bin\ffprobe.exe',
        '_internal\runtime\yt-dlp.exe',
        '_internal\runtime\deno.exe',
        '_internal\runtime\DENO_LICENSE.md',
        '_internal\assets\issa.ico',
        '_internal\assets\issa-logo.png'
    )
    foreach ($item in $packagedFiles) {
        if (-not (Test-Path -LiteralPath (Join-Path $appRoot $item) -PathType Leaf)) {
            throw "Packaged application is incomplete; missing: $item"
        }
    }

    $iscc = Get-Command ISCC.exe -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -First 1
    if (-not $iscc) {
        $isccCandidates = @(
            (Join-Path ${env:ProgramFiles(x86)} 'Inno Setup 6\ISCC.exe'),
            (Join-Path $env:ProgramFiles 'Inno Setup 6\ISCC.exe'),
            (Join-Path $env:LOCALAPPDATA 'Programs\Inno Setup 6\ISCC.exe')
        )
        $iscc = $isccCandidates | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
    }
    if (-not $iscc) {
        throw 'Inno Setup 6 is required. Install it from https://jrsoftware.org/isdl.php and rerun this command.'
    }

    & $iscc "/DMyAppVersion=$version" "/DMyAppPublisher=$publisher" 'installer\ISSA.iss'
    if ($LASTEXITCODE -ne 0) { throw 'Inno Setup compilation failed.' }
    $installer = Join-Path $ProjectRoot 'dist-installer\ISSA-Setup.exe'
    if (-not (Test-Path -LiteralPath $installer -PathType Leaf)) { throw 'Installer output was not created.' }

    Write-Host "Build complete: $installer" -ForegroundColor Green
    Write-Host 'Optional Authenticode signing should be applied to the app EXE before ISCC and to the setup EXE after ISCC.'
}
finally {
    Pop-Location
}
