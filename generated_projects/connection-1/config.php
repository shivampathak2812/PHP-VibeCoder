<?php
declare(strict_types=1);

/**
 * Reads database credentials and environment configuration with safe fallbacks.
 * Secrets should always come from environment variables in production.
 */
return [
    'host'    => (string) (getenv('DB_HOST') !== false ? getenv('DB_HOST') : '127.0.0.1'),
    'port'    => (string) (getenv('DB_PORT') !== false ? getenv('DB_PORT') : '3306'),
    'dbname'  => (string) (getenv('DB_NAME') !== false ? getenv('DB_NAME') : 'php_connection_demo'),
    'user'    => (string) (getenv('DB_USER') !== false ? getenv('DB_USER') : 'root'),
    'pass'    => (string) (getenv('DB_PASS') !== false ? getenv('DB_PASS') : ''),
    'charset' => 'utf8mb4',
    'debug'   => filter_var(getenv('APP_DEBUG') !== false ? getenv('APP_DEBUG') : 'false', FILTER_VALIDATE_BOOLEAN),
];