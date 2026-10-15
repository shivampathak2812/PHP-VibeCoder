<?php
declare(strict_types=1);

/**
 * Database Configuration.
 * Loads connection settings from environment variables if present,
 * or defaults to typical local environment parameters.
 */
return [
    'host'    => getenv('DB_HOST') !== false ? getenv('DB_HOST') : '127.0.0.1',
    'port'    => getenv('DB_PORT') !== false ? (int) getenv('DB_PORT') : 3306,
    'dbname'  => getenv('DB_NAME') !== false ? getenv('DB_NAME') : 'app_db',
    'charset' => 'utf8mb4',
    'user'    => getenv('DB_USER') !== false ? getenv('DB_USER') : 'root',
    'pass'    => getenv('DB_PASS') !== false ? getenv('DB_PASS') : '',
];