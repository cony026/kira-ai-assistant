-- =====================================================================
-- Kira IA - Usuario de la aplicación con PRIVILEGIO MÍNIMO
--
-- La app NO debe conectarse como root: si alguien lograra inyectar SQL o robar
-- la DATABASE_URL, con root podría borrar o leer TODAS las bases del servidor.
-- kira_app solo puede leer y escribir filas en la base kira (no puede crear,
-- borrar ni alterar tablas, ni ver otras bases, ni crear usuarios).
--
-- Ejecutar UNA vez como administrador, DESPUÉS de schema.sql:
--   XAMPP (Shell):  mysql -u root < database/usuario_app.sql
--
-- Antes de ejecutarlo, cambia 'CAMBIA_ESTA_CLAVE' por una clave larga tuya.
-- Luego en el .env:
--   DATABASE_URL=mysql+pymysql://kira_app:TU_CLAVE@localhost:3306/kira
-- (En Docker este paso lo hace solo docker/mariadb-init/02_usuario_app.sh)
-- =====================================================================

CREATE USER IF NOT EXISTS 'kira_app'@'localhost' IDENTIFIED BY 'CAMBIA_ESTA_CLAVE';
CREATE USER IF NOT EXISTS 'kira_app'@'127.0.0.1' IDENTIFIED BY 'CAMBIA_ESTA_CLAVE';

GRANT SELECT, INSERT, UPDATE, DELETE ON kira.* TO 'kira_app'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE ON kira.* TO 'kira_app'@'127.0.0.1';
FLUSH PRIVILEGES;

-- Para revisar los permisos:   SHOW GRANTS FOR 'kira_app'@'localhost';
