<?php

declare(strict_types=1);

/**
 * One shared PDO connection for the whole app.
 *
 * Usage:
 *   require_once __DIR__ . '/../src/Database.php';
 *   $pdo = Database::connection();
 */
final class Database
{
    private static ?PDO $pdo = null;

    public static function connection(): PDO
    {
        if (self::$pdo instanceof PDO) {
            return self::$pdo;
        }

        $config = self::config();

        $dsn = sprintf(
            'mysql:host=%s;port=%s;dbname=%s;charset=%s',
            $config['host'],
            $config['port'],
            $config['name'],
            $config['charset']
        );

        try {
            self::$pdo = new PDO($dsn, $config['user'], $config['pass'], [
                PDO::ATTR_ERRMODE            => PDO::ERRMODE_EXCEPTION,
                PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
                PDO::ATTR_EMULATE_PREPARES   => false,
            ]);
        } catch (PDOException $e) {
            error_log('Database connection failed: ' . $e->getMessage());

            throw new RuntimeException(
                $config['debug']
                    ? 'Database connection failed: ' . $e->getMessage()
                    : 'Database connection failed.'
            );
        }

        return self::$pdo;
    }

    /** True when APP_DEBUG is on (show detailed errors). */
    public static function debug(): bool
    {
        return (bool) self::config()['debug'];
    }

    private static function config(): array
    {
        static $config = null;

        return $config ??= require __DIR__ . '/../config/database.php';
    }
}
