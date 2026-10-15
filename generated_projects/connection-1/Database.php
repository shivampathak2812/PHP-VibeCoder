<?php
declare(strict_types=1);

/**
 * Manages the PDO connection lifecycle.
 */
class Database
{
    private static ?PDO $instance = null;

    /**
     * Private constructor prevents external instantiation.
     */
    private function __construct()
    {
    }

    /**
     * Establishes and returns a shared PDO connection instance.
     *
     * @param array{
     *     host: string,
     *     port: string,
     *     dbname: string,
     *     user: string,
     *     pass: string,
     *     charset: string,
     *     debug: bool
     * } $config
     * @return PDO
     * @throws RuntimeException If connection cannot be established.
     */
    public static function getConnection(array $config): PDO
    {
        if (self::$instance === null) {
            $dsn = sprintf(
                'mysql:host=%s;port=%s;dbname=%s;charset=%s',
                $config['host'],
                $config['port'],
                $config['dbname'],
                $config['charset']
            );

            $options = [
                // Forces PDO to throw exceptions on any SQL or connection error
                PDO::ATTR_ERRMODE            => PDO::ERRMODE_EXCEPTION,
                // Automatically fetch rows as associative arrays (column => value)
                PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
                // Disables client-side emulation to ensure native prepared statements
                PDO::ATTR_EMULATE_PREPARES   => false,
                // Sets connection timeout in seconds
                PDO::ATTR_TIMEOUT            => 5,
            ];

            try {
                self::$instance = new PDO($dsn, $config['user'], $config['pass'], $options);
            } catch (PDOException $e) {
                // Log actual database credentials and error message to server logs
                error_log(sprintf('[Database Error] %s', $e->getMessage()));

                if ($config['debug'] === true) {
                    throw new RuntimeException(
                        sprintf('Database connection failed: %s', $e->getMessage()),
                        (int) $e->getCode(),
                        $e
                    );
                }

                // Never expose raw database host or error details in production
                throw new RuntimeException('A database error occurred. Please try again later.');
            }
        }

        return self::$instance;
    }
}