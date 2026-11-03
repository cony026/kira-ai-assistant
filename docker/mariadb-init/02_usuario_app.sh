#!/bin/bash
# Crea el usuario de la aplicación con privilegio mínimo (lo ejecuta MariaDB solo la
# primera vez que arranca con el volumen vacío). La clave viene de KIRA_DB_APP_PASSWORD.
set -e
mariadb -u root -p"${MARIADB_ROOT_PASSWORD}" <<SQL
CREATE USER IF NOT EXISTS 'kira_app'@'%' IDENTIFIED BY '${KIRA_DB_APP_PASSWORD}';
GRANT SELECT, INSERT, UPDATE, DELETE ON kira.* TO 'kira_app'@'%';
FLUSH PRIVILEGES;
SQL
echo "Usuario kira_app creado con permisos SELECT, INSERT, UPDATE, DELETE sobre kira.*"
