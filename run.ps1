param(
    [ValidateSet("adaptive", "fixed", "all", "build", "ui")]
    [string]$Mode = "adaptive",

    [ValidateSet("Debug", "Release")]
    [string]$Configuration = "Release",

    [switch]$Rebuild,

    [string]$OutputDir = ""
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

function Write-Step {
    param([string]$Text)
    Write-Host "`n=== $Text ===" -ForegroundColor Cyan
}

function Resolve-SolverPath {
    param([string]$Config)

    $candidates = @(
        (Join-Path $ProjectRoot "build\$Config\lab1_solver.exe"),
        (Join-Path $ProjectRoot "build\lab1_solver.exe")
    )

    foreach ($path in $candidates) {
        if (Test-Path $path) {
            return $path
        }
    }

    return $candidates[0]
}

function Ensure-Build {
    param([string]$Config, [bool]$DoRebuild)

    Write-Step "CMake configure"
    cmake -S . -B build

    Write-Step "CMake build ($Config)"
    if ($DoRebuild) {
        cmake --build build --config $Config --clean-first
    }
    else {
        cmake --build build --config $Config
    }
}

function Run-Solver {
    param(
        [string]$Solver,
        [string]$InputJson,
        [string]$OutDir
    )

    if (-not (Test-Path $InputJson)) {
        throw "Input JSON not found: $InputJson"
    }

    New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
    Write-Step "Run solver: $(Split-Path -Leaf $InputJson) -> $OutDir"
    & $Solver $InputJson $OutDir
}

$needBuild = $Mode -in @("adaptive", "fixed", "all", "build")
if ($needBuild) {
    Ensure-Build -Config $Configuration -DoRebuild:$Rebuild
}

$solverPath = Resolve-SolverPath -Config $Configuration

if (($Mode -in @("adaptive", "fixed", "all")) -and -not (Test-Path $solverPath)) {
    throw "Solver executable not found: $solverPath"
}

switch ($Mode) {
    "build" {
        Write-Host "Build completed." -ForegroundColor Green
    }
    "adaptive" {
        $input = Join-Path $ProjectRoot "input_examples\default_input.json"
        $out = if ($OutputDir) { $OutputDir } else { Join-Path $ProjectRoot "output" }
        Run-Solver -Solver $solverPath -InputJson $input -OutDir $out
    }
    "fixed" {
        $input = Join-Path $ProjectRoot "input_examples\fixed_step_input.json"
        $out = if ($OutputDir) { $OutputDir } else { Join-Path $ProjectRoot "output_fixed" }
        Run-Solver -Solver $solverPath -InputJson $input -OutDir $out
    }
    "all" {
        $adaptiveInput = Join-Path $ProjectRoot "input_examples\default_input.json"
        $fixedInput = Join-Path $ProjectRoot "input_examples\fixed_step_input.json"
        Run-Solver -Solver $solverPath -InputJson $adaptiveInput -OutDir (Join-Path $ProjectRoot "output")
        Run-Solver -Solver $solverPath -InputJson $fixedInput -OutDir (Join-Path $ProjectRoot "output_fixed")
    }
    "ui" {
        Write-Step "Install UI dependencies"
        python -m pip install -r (Join-Path $ProjectRoot "ui\requirements.txt")

        Write-Step "Run UI"
        python (Join-Path $ProjectRoot "ui\app.py")
    }
}

Write-Host "`nDone." -ForegroundColor Green
