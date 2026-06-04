param(
    [string]$ContainerName = "moodle_db_final",
    [string]$AdminUser = "moodleuser",
    [string]$AdminDatabase = "postgres"
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$envPath = Join-Path $root ".env"
$sqlPath = Join-Path $root "docker\sql\provision-existing-postgres.sql"

if (-not (Test-Path $envPath)) {
    throw "Missing root .env file at $envPath"
}

if (-not (Test-Path $sqlPath)) {
    throw "Missing SQL file at $sqlPath"
}

$vars = @{}
Get-Content $envPath | ForEach-Object {
    if ($_ -match '^\s*#' -or $_ -notmatch '=') {
        return
    }

    $name, $value = $_ -split '=', 2
    $vars[$name.Trim()] = $value.Trim()
}

$required = @(
    "POSTGRES_PASSWORD",
    "MOODLE_DB_PASSWORD",
    "TELITE_POSTGRES_PASSWORD"
)

foreach ($name in $required) {
    if (-not $vars.ContainsKey($name) -or [string]::IsNullOrWhiteSpace($vars[$name])) {
        throw "Missing required value in .env: $name"
    }
}

$sql = Get-Content $sqlPath -Raw
$dockerArgs = @(
    "exec",
    "-i",
    $ContainerName,
    "psql",
    "-v", "ON_ERROR_STOP=1",
    "-v", "postgres_password=$($vars["POSTGRES_PASSWORD"])",
    "-v", "moodle_password=$($vars["MOODLE_DB_PASSWORD"])",
    "-v", "telite_password=$($vars["TELITE_POSTGRES_PASSWORD"])",
    "-U", $AdminUser,
    "-d", $AdminDatabase
)

$sql | docker @dockerArgs

if ($LASTEXITCODE -ne 0) {
    throw "Provisioning failed for container $ContainerName"
}

Write-Host ""
Write-Host "Databases:"
docker exec $ContainerName psql -U $AdminUser -d $AdminDatabase -c "\l"

Write-Host ""
Write-Host "Roles:"
docker exec $ContainerName psql -U $AdminUser -d $AdminDatabase -c "\du"
