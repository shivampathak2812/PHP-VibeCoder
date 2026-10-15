CREATE DATABASE IF NOT EXISTS php_connection_demo CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE php_connection_demo;

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    role VARCHAR(30) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT IGNORE INTO users (id, username, email, role) VALUES
(1, 'alice_dev', 'alice@example.com', 'developer'),
(2, 'bob_admin', 'bob@example.com', 'admin'),
(3, 'charlie_dba', 'charlie@example.com', 'dba'),
(4, 'dana_analyst', 'dana@example.com', 'analyst');