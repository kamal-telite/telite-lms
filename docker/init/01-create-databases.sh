#!/bin/bash
set -e

# Load environment values or default fallbacks
PG_ADMIN_USER="${POSTGRES_USER:-postgres}"
PG_ADMIN_DB="${POSTGRES_DB:-postgres}"

M_USER="${MOODLE_DB_USER:-moodleuser}"
M_PASS="${MOODLE_DB_PASSWORD:-changeme}"
M_DB="${MOODLE_DB_NAME:-moodle}"

T_USER="${TELITE_POSTGRES_USER:-postgres}"
T_PASS="${TELITE_POSTGRES_PASSWORD:-CHANGE_ME}"
T_DB="${TELITE_POSTGRES_DB:-telite_backend}"

echo "Configuring PostgreSQL Databases and Users..."

# Run as superuser in the default database
psql -v ON_ERROR_STOP=1 --username "$PG_ADMIN_USER" --dbname "$PG_ADMIN_DB" <<-EOSQL
    -- 1. Create Moodle role
    DO \$\$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '$M_USER') THEN
            CREATE ROLE $M_USER WITH LOGIN PASSWORD '$M_PASS';
        END IF;
    END \$\$;

    -- 2. Create Backend role (only if it's not the default admin user)
    DO \$\$
    BEGIN
        IF '$T_USER' <> '$PG_ADMIN_USER' AND NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '$T_USER') THEN
            CREATE ROLE $T_USER WITH LOGIN PASSWORD '$T_PASS';
        END IF;
    END \$\$;

    -- 3. Create databases
    SELECT 'CREATE DATABASE $M_DB OWNER $M_USER'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$M_DB') \gexec

    SELECT 'CREATE DATABASE $T_DB OWNER $T_USER'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$T_DB') \gexec

    -- 4. Grant privileges
    GRANT ALL PRIVILEGES ON DATABASE $M_DB TO $M_USER;
    GRANT ALL PRIVILEGES ON DATABASE $T_DB TO $T_USER;

    -- 5. Revoke public access
    REVOKE ALL ON DATABASE $M_DB FROM PUBLIC;
    REVOKE ALL ON DATABASE $T_DB FROM PUBLIC;
EOSQL

echo "Configuring Schema Permissions on logical databases..."

# Run schema grants on Moodle database
psql -v ON_ERROR_STOP=1 --username "$PG_ADMIN_USER" --dbname "$M_DB" <<-EOSQL
    GRANT ALL ON SCHEMA public TO $M_USER;
EOSQL

# Run schema grants on Telite Backend database
psql -v ON_ERROR_STOP=1 --username "$PG_ADMIN_USER" --dbname "$T_DB" <<-EOSQL
    GRANT ALL ON SCHEMA public TO $T_USER;
EOSQL

echo "PostgreSQL initialization complete."
