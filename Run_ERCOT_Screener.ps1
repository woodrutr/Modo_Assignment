$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

function Get-PythonLauncher {
    $candidates = @(
        @{ Command = "py"; Args = @("-3.13") },
        @{ Command = "py"; Args = @("-3.12") },
        @{ Command = "py"; Args = @("-3.11") },
        @{ Command = "py"; Args = @("-3.10") },
        @{ Command = "py"; Args = @("-3") },
        @{ Command = "py"; Args = @() },
        @{ Command = "python"; Args = @() },
        @{ Command = "python3"; Args = @() }
    )

    foreach ($candidate in $candidates) {
        if (Get-Command $candidate.Command -ErrorAction SilentlyContinue) {
            return $candidate
        }
    }

    throw "No supported Python launcher found."
}

$venvDir = Join-Path $scriptDir ".venv-win"
$venvPython = Join-Path $venvDir "Scripts\python.exe"
$venvPip = Join-Path $venvDir "Scripts\pip.exe"
$venvStreamlit = Join-Path $venvDir "Scripts\streamlit.exe"

if (-not (Test-Path $venvPython)) {
    $launcher = Get-PythonLauncher
    & $launcher.Command @($launcher.Args + @("-m", "venv", $venvDir))
}

& $venvPython -c "import gridstatus, pandas, plotly, pyarrow, streamlit" 2>$null
if ($LASTEXITCODE -ne 0) {
    & $venvPip install -r requirements.txt
}

$targetYear = & $venvPython -c "from src.config import SETTINGS; print(SETTINGS.target_year)"
$processedPath = & $venvPython -c "from src.config import SETTINGS; print(SETTINGS.processed_dam_path(SETTINGS.target_year))"
$metricsPath = & $venvPython -c "from src.config import SETTINGS; print(SETTINGS.metrics_path(SETTINGS.target_year))"
$dailyProfileWindowsPath = & $venvPython -c "from src.config import SETTINGS; print(SETTINGS.daily_profile_windows_path(SETTINGS.target_year))"
$hourlyProfileShapePath = & $venvPython -c "from src.config import SETTINGS; print(SETTINGS.hourly_profile_shape_path(SETTINGS.target_year))"
$metricsSchemaOk = & $venvPython -c "from pathlib import Path; import pandas as pd; from src.config import LENS_KEYS, SETTINGS, lens_metric_column; path = SETTINGS.metrics_path(SETTINGS.target_year); required = {'location','location_type','best_fit_lens','best_fit_rank','observations'}; [required.update({lens_metric_column(profile, duration, 'rank'), lens_metric_column(profile, duration, 'score'), lens_metric_column(profile, duration, 'effective_avg_price_usd_per_mwh'), lens_metric_column(profile, duration, 'annual_cost_reduction_pct')}) for profile, duration in LENS_KEYS]; print('1' if Path(path).exists() and required.issubset(pd.read_parquet(path).columns) else '0')"

if (-not (Test-Path $processedPath)) {
    & $venvPython -m src.data.fetch --year $targetYear
}

if (
    -not (Test-Path $metricsPath) -or
    -not (Test-Path $dailyProfileWindowsPath) -or
    -not (Test-Path $hourlyProfileShapePath) -or
    $metricsSchemaOk -ne "1"
) {
    & $venvPython -m src.analytics.metrics --year $targetYear
}

if ($env:CHECK_ONLY -eq "1") {
    Write-Host "Runner checks passed."
    exit 0
}

$port = if ($env:PORT) { $env:PORT } else { "8501" }
$url = "http://127.0.0.1:$port"
$openBrowser = if ($env:OPEN_BROWSER) { $env:OPEN_BROWSER } else { "1" }

if ($openBrowser -eq "1") {
    Start-Process $url | Out-Null
}

& $venvStreamlit run app.py --server.headless true --server.address 127.0.0.1 --server.port $port
