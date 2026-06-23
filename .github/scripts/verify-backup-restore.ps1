param(
    [string]$PostgresImage = "postgres:16"
)

$ErrorActionPreference = "Stop"

$suffix = [Guid]::NewGuid().ToString("N").Substring(0, 10)
$source = "telite_restore_source_$suffix"
$target = "telite_restore_target_$suffix"
$dump = "restore-drill-$suffix.dump"

function Wait-Postgres {
    param([string]$Container)

    for ($i = 0; $i -lt 30; $i++) {
        docker exec $Container pg_isready -U postgres | Out-Null
        if ($LASTEXITCODE -eq 0) {
            return
        }
        Start-Sleep -Seconds 2
    }

    throw "Postgres did not become ready in container $Container"
}

try {
    docker run -d --name $source -e POSTGRES_PASSWORD=postgres $PostgresImage | Out-Null
    docker run -d --name $target -e POSTGRES_PASSWORD=postgres $PostgresImage | Out-Null

    Wait-Postgres -Container $source
    Wait-Postgres -Container $target

    docker exec $source psql -U postgres -d postgres -c "CREATE TABLE restore_probe (id integer primary key, name text not null);" | Out-Null
    docker exec $source psql -U postgres -d postgres -c "INSERT INTO restore_probe (id, name) VALUES (1, 'telite-restore-ok');" | Out-Null
    docker exec $source pg_dump -U postgres -d postgres -Fc -f "/tmp/$dump" | Out-Null
    docker cp "${source}:/tmp/$dump" $dump | Out-Null
    docker cp $dump "${target}:/tmp/$dump" | Out-Null
    docker exec $target pg_restore -U postgres -d postgres "/tmp/$dump" | Out-Null

    $result = docker exec $target psql -U postgres -d postgres -tAc "SELECT name FROM restore_probe WHERE id = 1;"
    if ($result.Trim() -ne "telite-restore-ok") {
        throw "Restore probe failed. Expected telite-restore-ok, got '$result'"
    }

    Write-Host "Backup/restore verification passed."
}
finally {
    if (Test-Path $dump) {
        Remove-Item -LiteralPath $dump -Force
    }
    docker rm -f $source 2>$null | Out-Null
    docker rm -f $target 2>$null | Out-Null
}

