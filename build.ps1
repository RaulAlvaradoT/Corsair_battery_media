param(
    [switch]$SkipInstaller
)

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
Set-Location $root

# --- Localizar un Python base válido ---------------------------------------
function Find-BasePython {
    $candidates = @(
        @{ Exe = "py";      Args = @("-3") },
        @{ Exe = "python";  Args = @() },
        @{ Exe = "python3"; Args = @() }
    )
    foreach ($c in $candidates) {
        if (-not (Get-Command $c.Exe -ErrorAction SilentlyContinue)) { continue }
        try {
            & $c.Exe @($c.Args + @("-c", "import sys")) *> $null
            if ($LASTEXITCODE -eq 0) { return $c }
        } catch { }
    }

    # Búsqueda en ubicaciones de instalación comunes (cuando no está en el PATH)
    $globs = @(
        "$env:LOCALAPPDATA\Python\pythoncore-*\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python*\python.exe",
        "$env:ProgramFiles\Python*\python.exe",
        "${env:ProgramFiles(x86)}\Python*\python.exe"
    )
    foreach ($g in $globs) {
        $found = Get-ChildItem $g -ErrorAction SilentlyContinue |
            Sort-Object FullName -Descending | Select-Object -First 1
        if (-not $found) { continue }
        try {
            & $found.FullName -c "import sys" *> $null
            if ($LASTEXITCODE -eq 0) { return @{ Exe = $found.FullName; Args = @() } }
        } catch { }
    }
    return $null
}

$base = Find-BasePython
if (-not $base) {
    Write-Host "No se encontró Python 3.10 o superior en esta máquina." -ForegroundColor Red
    Write-Host "Instálalo desde https://www.python.org/downloads/windows/" -ForegroundColor Red
    Write-Host "Importante: marca 'Add python.exe to PATH' durante la instalación." -ForegroundColor Red
    Write-Host "Después vuelve a ejecutar:  powershell -ExecutionPolicy Bypass -File .\build.ps1" -ForegroundColor Red
    exit 1
}

# --- Crear / validar el entorno virtual ------------------------------------
$venvPython = Join-Path $root ".venv\Scripts\python.exe"
$venvOk = $false
if (Test-Path $venvPython) {
    try {
        & $venvPython -c "import sys" *> $null
        if ($LASTEXITCODE -eq 0) { $venvOk = $true }
    } catch { }
}

if (-not $venvOk) {
    if (Test-Path ".venv") {
        Write-Host "El entorno virtual existente no es válido (creado en otro equipo). Se recreará..." -ForegroundColor Yellow
        Remove-Item -LiteralPath ".venv" -Recurse -Force
    }
    Write-Host "Creando entorno virtual..." -ForegroundColor Cyan
    & $base.Exe @($base.Args + @("-m", "venv", ".venv"))
    if ($LASTEXITCODE -ne 0) { throw "No se pudo crear el entorno virtual." }
}

# --- Dependencias -----------------------------------------------------------
Write-Host "Instalando dependencias..." -ForegroundColor Cyan
& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -r requirements.txt

# --- Ejecutable -------------------------------------------------------------
Write-Host "Compilando el ejecutable con PyInstaller..." -ForegroundColor Cyan
& $venvPython -m PyInstaller --noconfirm app.spec

$exe = Join-Path $root "dist\CorsairBatteryLevel.exe"
if (-not (Test-Path $exe)) { throw "PyInstaller no generó $exe" }

# --- Instalador -------------------------------------------------------------
if (-not $SkipInstaller) {
    $iscc = @(
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
        "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
    ) | Where-Object { Test-Path $_ } | Select-Object -First 1

    if (-not $iscc) {
        Write-Host "Inno Setup 6 no está instalado; se omite el instalador." -ForegroundColor Yellow
        Write-Host "Descárgalo de https://jrsoftware.org/isdl.php y vuelve a ejecutar el script." -ForegroundColor Yellow
    } else {
        Write-Host "Compilando el instalador con Inno Setup..." -ForegroundColor Cyan
        & $iscc "installer\CorsairBatteryLevel.iss"
    }
}

Write-Host "Compilación terminada. Resultado en .\dist" -ForegroundColor Green
