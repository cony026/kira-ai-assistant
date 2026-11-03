-- =====================================================================
-- Kira IA - Esquema de base de datos MySQL
-- Ejecutar una vez:  mysql -u root -p < database/schema.sql
-- (El backend también crea las tablas solo al arrancar si no existen.)
-- =====================================================================

CREATE DATABASE IF NOT EXISTS kira
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE kira;

-- Cuentas de usuario + perfil de preferencias
CREATE TABLE IF NOT EXISTS usuarios (
    id                INT AUTO_INCREMENT PRIMARY KEY,
    nombre            VARCHAR(30)  NOT NULL,
    email             VARCHAR(120) NOT NULL UNIQUE,
    password_hash     VARCHAR(255) NOT NULL,          -- nunca la contraseña en texto plano
    email_verificado  BOOLEAN NOT NULL DEFAULT FALSE, -- se confirma con el código enviado al correo
    codigo_hash       VARCHAR(255) NULL,              -- hash del código de 6 dígitos vigente
    codigo_expira     DATETIME NULL,
    codigo_intentos   INT NOT NULL DEFAULT 0,
    codigo_enviado_en DATETIME NULL,
    fecha_nacimiento  DATE NULL,
    consolas          JSON NULL,                      -- ej. ["PC","Nintendo Switch"]
    generos           JSON NULL,                      -- ej. ["RPG","Indie"]
    perfil_completo   BOOLEAN NOT NULL DEFAULT FALSE,
    acepta_privacidad_en DATETIME NULL,               -- consentimiento informado (Ley 21.719)
    creado_en         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Historial de consultas al agente RAG
CREATE TABLE IF NOT EXISTS historial_chat (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id  INT  NOT NULL,
    mensaje     TEXT NOT NULL,
    respuesta   TEXT NOT NULL,
    tokens_entrada INT NOT NULL DEFAULT 0,          -- informados por Gemini (costos)
    tokens_salida  INT NOT NULL DEFAULT 0,
    latencia_ms    INT NOT NULL DEFAULT 0,
    creado_en   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_chat_usuario FOREIGN KEY (usuario_id)
        REFERENCES usuarios(id) ON DELETE CASCADE,
    INDEX idx_chat_usuario (usuario_id),
    INDEX idx_chat_fecha (creado_en)
);

-- Si las tablas ya existían de una versión anterior, agrega las columnas nuevas
-- (MariaDB 10.0+ acepta IF NOT EXISTS; en MySQL 8 ignora el error "Duplicate column").
ALTER TABLE usuarios       ADD COLUMN IF NOT EXISTS acepta_privacidad_en DATETIME NULL;
ALTER TABLE historial_chat ADD COLUMN IF NOT EXISTS tokens_entrada INT NOT NULL DEFAULT 0;
ALTER TABLE historial_chat ADD COLUMN IF NOT EXISTS tokens_salida  INT NOT NULL DEFAULT 0;
ALTER TABLE historial_chat ADD COLUMN IF NOT EXISTS latencia_ms    INT NOT NULL DEFAULT 0;
