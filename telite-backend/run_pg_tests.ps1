$ErrorActionPreference = "Stop"

# Initialize PGDATA
$pgdata = "C:\tmp\pgdata_test"
if (Test-Path $pgdata) {
    Remove-Item -Recurse -Force $pgdata
}

& "C:\Program Files\PostgreSQL\16\bin\initdb.exe" -D $pgdata -U postgres -A trust

# Start Postgres
& "C:\Program Files\PostgreSQL\16\bin\pg_ctl.exe" -D $pgdata -l $pgdata\logfile start -o "-p 55432"

Start-Sleep -Seconds 3

# Create DB
& "C:\Program Files\PostgreSQL\16\bin\psql.exe" -U postgres -p 55432 -d postgres -c "CREATE DATABASE test_telite_backend;"

$env:PYTHONPATH="."
& pytest tests/test_phase_c_audit.py -v

# Stop Postgres
& "C:\Program Files\PostgreSQL\16\bin\pg_ctl.exe" -D $pgdata stop
