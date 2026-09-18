<?php

declare(strict_types=1);

return [
    'host'     => $_ENV['DB_HOST'] ?? '127.0.0.1',
    'port'     => (int)($_ENV['DB_PORT'] ?? 3306),
    'dbname'   => $_ENV['DB_DATABASE'] ?? 'auth_db',
    'username' => $_ENV['DB_USERNAME'] ?? 'root',
    'password' => $_ENV['DB_PASSWORD'] ?? '',
    'charset'  => 'utf8mb4',
    'options'  => [
        PDO::ATTR_ERRMODE            => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
        PDO::ATTR_EMULATE_PREPARES   => false,
    ],
];