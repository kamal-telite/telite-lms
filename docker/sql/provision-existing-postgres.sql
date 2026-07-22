\set ON_ERROR_STOP on

SELECT CASE
    WHEN EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'postgres') THEN
        format(
            'ALTER ROLE postgres WITH LOGIN SUPERUSER CREATEDB CREATEROLE REPLICATION BYPASSRLS PASSWORD %L',
            :'postgres_password'
        )
    ELSE
        format(
            'CREATE ROLE postgres LOGIN SUPERUSER CREATEDB CREATEROLE REPLICATION BYPASSRLS PASSWORD %L',
            :'postgres_password'
        )
END \gexec



SELECT CASE
    WHEN EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'telite_backend_user') THEN
        format('ALTER ROLE telite_backend_user WITH LOGIN PASSWORD %L', :'telite_password')
    ELSE
        format('CREATE ROLE telite_backend_user LOGIN PASSWORD %L', :'telite_password')
END \gexec

SELECT 'CREATE DATABASE telite_backend OWNER telite_backend_user'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'telite_backend') \gexec

ALTER DATABASE postgres OWNER TO postgres;
ALTER DATABASE telite_backend OWNER TO telite_backend_user;


GRANT ALL PRIVILEGES ON DATABASE telite_backend TO telite_backend_user;

REVOKE ALL ON DATABASE telite_backend FROM PUBLIC;


\connect telite_backend
GRANT ALL ON SCHEMA public TO telite_backend_user;
