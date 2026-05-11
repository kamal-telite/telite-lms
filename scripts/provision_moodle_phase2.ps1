param(
    [string]$AdminUsername = "super_admin",
    [string]$EnvPath = "backend\.env",
    [string]$ContextPath = "backend\data\moodle_phase2_context.json"
)

$raw = docker exec moodle_app_final php /var/www/html/local/telite/cli/provision_phase2.php --adminuser=$AdminUsername --json
if ($LASTEXITCODE -ne 0) {
    throw "Failed to provision the Moodle Phase 2 service."
}

$result = $raw | ConvertFrom-Json
if (-not $result.token) {
    throw "The provisioning script did not return a Moodle service token."
}

$envLines = @()
if (Test-Path $EnvPath) {
    $envLines = Get-Content $EnvPath
}

$updated = $false
for ($i = 0; $i -lt $envLines.Count; $i++) {
    if ($envLines[$i] -match '^MOODLE_SERVICE_TOKEN=') {
        $envLines[$i] = "MOODLE_SERVICE_TOKEN=$($result.token)"
        $updated = $true
        break
    }
}

if (-not $updated) {
    $envLines += "MOODLE_SERVICE_TOKEN=$($result.token)"
}

Set-Content -Path $EnvPath -Value $envLines -Encoding UTF8

$sanitized = [ordered]@{
    service = $result.service
    settings = $result.settings
    users = $result.users
    courses = $result.courses
    categories = $result.categories
    roles = $result.roles
}

$contextDir = Split-Path -Parent $ContextPath
if ($contextDir -and -not (Test-Path $contextDir)) {
    New-Item -ItemType Directory -Force -Path $contextDir | Out-Null
}

$sanitized | ConvertTo-Json -Depth 8 | Set-Content -Path $ContextPath -Encoding UTF8

Write-Output "Moodle Phase 2 service is ready."
Write-Output "Updated token in $EnvPath"
Write-Output "Wrote Moodle context to $ContextPath"
Write-Output "Service shortname: $($result.service.shortname)"
Write-Output "Admin user: $AdminUsername"
