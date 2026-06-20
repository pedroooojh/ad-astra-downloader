$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$bin = Join-Path $root "bin"
$temp = Join-Path $env:TEMP "ad-astra-downloader-tools"
New-Item -ItemType Directory -Force -Path $bin, $temp | Out-Null

$ytDlp = Join-Path $bin "yt-dlp.exe"
if (-not (Test-Path $ytDlp)) {
    Invoke-WebRequest -Uri "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe" -OutFile $ytDlp
}

$python = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) { throw "Crie a .venv e instale requirements.txt antes de preparar as ferramentas." }
$ffmpeg = & $python -c "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())"
if (-not (Test-Path $ffmpeg)) { throw "FFmpeg portátil não foi encontrado." }
Copy-Item -LiteralPath $ffmpeg.Trim() -Destination (Join-Path $bin "ffmpeg.exe") -Force

Write-Host "yt-dlp e FFmpeg preparados em $bin"
