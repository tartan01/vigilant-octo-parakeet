-- H2 schema for local evaluation.
-- Table / column names are IDENTICAL to membersite/store.py (DDL + DDL_MIGRATIONS),
-- so switching to the MySQL profile needs no code change.
CREATE TABLE IF NOT EXISTS users (
    email VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255) DEFAULT '',
    role VARCHAR(32) DEFAULT 'member',
    created_at VARCHAR(64),
    last_login VARCHAR(64),
    login_count INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS products (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(255),
    subtitle VARCHAR(255),
    description CLOB,
    price DOUBLE DEFAULT 0,
    category VARCHAR(64),
    cover VARCHAR(512) DEFAULT '',
    badge VARCHAR(64),
    stock INTEGER DEFAULT -1,
    hidden INTEGER DEFAULT 0,
    created_at VARCHAR(64),
    format VARCHAR(128),
    delivery CLOB,
    size VARCHAR(128),
    author VARCHAR(128),
    sample CLOB,
    content CLOB,
    file_url VARCHAR(512),
    link_url VARCHAR(512),
    link_code VARCHAR(128),
    code_pool CLOB,
    email_template CLOB
);

CREATE TABLE IF NOT EXISTS orders (
    id VARCHAR(64) PRIMARY KEY,
    email VARCHAR(255),
    items CLOB,
    total DOUBLE DEFAULT 0,
    status VARCHAR(32) DEFAULT 'delivered',
    created_at VARCHAR(64),
    delivery_method VARCHAR(32),
    delivery_target VARCHAR(255),
    deliveries CLOB,
    fulfilled_at VARCHAR(64)
);

-- Separate admin table: the console keeps its own credentials (never in the
-- public users table). Password is a BCrypt hash, never plaintext.
CREATE TABLE IF NOT EXISTS console_admins (
    username VARCHAR(64) PRIMARY KEY,
    password_hash VARCHAR(255) NOT NULL,
    created_at VARCHAR(64)
);
