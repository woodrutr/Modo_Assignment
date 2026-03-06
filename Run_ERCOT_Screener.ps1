param(
    [switch]$CheckOnly,
    [switch]$NoBrowser,
    [int]$Port = 8501
)

$ErrorActionPreference = "Stop"

function Get-PythonInvocation {
    $candidates = @(
        @("py", "-3.13"),
        @("py", "-3.12"),
        @("py", "-3.11"),
        @("py", "-3.10"),
        @("py", "-3"),
        @("py"),
        @("python"),
        @("python3")
    )

    foreach ($candidate in $candidates) {
        $commandName = $candidate[0]
        if (-not (Get-Command $commandName -ErrorAction SilentlyContinue)) {
            continue
        }

        $extraArgs = @()
        if ($candidate.Count -gt 1) {
            $extraArgs = $candidate[1..($candidate.Count - 1)]
        }

        try {
            & $commandName @extraArgs -c "import sys"
            if ($LASTEXITCODE -eq 0) {
                return @{
                    Command = $commandName
                    Args = $extraArgs
                }
            }
        } catch {
            continue
        }
    }

    throw "No suitable Python launcher found. Install Python 3 and ensure 'py' or 'python' is available on PATH."
}

function Invoke-Python {
    param(
        [Parameter(Mandatory = $true)]
        [hashtable]$Invocation,
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments
    )

    & $Invocation.Command @($Invocation.Args + $Arguments)
    if ($LASTEXITCODE -ne 0) {
        throw "Python command failed: $($Invocation.Command) $($Invocation.Args -join ' ') $($Arguments -join ' ')"
    }
}

try {
    $rootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    Set-Location $rootDir

    $venvDir = Join-Path $rootDir ".venv-win"
    $venvPython = Join-Path $venvDir "Scripts\python.exe"
    $venvPip = Join-Path $venvDir "Scripts\pip.exe"
    $streamlitExe = Join-Path $venvDir "Scripts\streamlit.exe"

    Write-Host "Repository root: $rootDir"

    $pythonInvocation = Get-PythonInvocation

    if (-not (Test-Path $venvPython)) {
        Write-Host "Creating Windows virtual environment at .venv-win..."
        Invoke-Python -Invocation $pythonInvocation -Arguments @("-m", "venv", $venvDir)
    }

    try {
        & $venvPython -c "import gridstatus, pandas, pyarrow, streamlit"
        if ($LASTEXITCODE -ne 0) {
            throw "Dependency import check failed."
        }
    } catch {
        Write-Host "Installing pinned dependencies..."
        & $venvPip install -r (Join-Path $rootDir "requirements.txt")
        if ($LASTEXITCODE -ne 0) {
            throw "Dependency installation failed."
        }
    }

    $processedArtifacts = Get-ChildItem -Path (Join-Path $rootDir "data\processed") -Filter "ercot_dam_spp_utc_*.parquet" -ErrorAction SilentlyContinue
    if (-not $processedArtifacts) {
        Write-Host "No processed ERCOT artifacts found. Fetching data..."
        & $venvPython -m src.data.fetch
        if ($LASTEXITCODE -ne 0) {
            throw "ERCOT data fetch failed."
        }
    }

    Write-Host "Building metric artifacts..."
    & $venvPython -m src.analytics.metrics
    if ($LASTEXITCODE -ne 0) {
        throw "Metric build failed."
    }

    if ($CheckOnly) {
        Write-Host "Check-only mode complete. Bootstrap succeeded without launching Streamlit."
        exit 0
    }

    if (-not $NoBrowser) {
        Start-Job -ScriptBlock {
            param($LocalPort)
            Start-Sleep -Seconds 3
            Start-Process "http://127.0.0.1:$LocalPort"
        } -ArgumentList $Port | Out-Null
    }

    Write-Host "Launching Streamlit app on http://127.0.0.1:$Port ..."
    & $streamlitExe run (Join-Path $rootDir "app.py") --server.address 127.0.0.1 --server.port $Port
    exit $LASTEXITCODE
} catch {
    Write-Host ""
    Write-Host "Startup failed: $($_.Exception.Message)" -ForegroundColor Red
    throw
}
