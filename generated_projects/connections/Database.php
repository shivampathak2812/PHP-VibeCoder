<?php
declare(strict_types=1);

class Database
{
    private ?PDO $connection = null;

    /**
     * @param array{
     *     host: string,
     *     port: int,
     *     dbname: string,
     *     charset: string,
     *     user: string,
     *     pass: string
     * } $config
     */
    public function __construct(
        private readonly array $config
    ) {}

    /**
     * Establishes and returns a PDO instance.
     *
     * @throws PDOException If the connection fails.
     */
    public function getConnection(): PDO
    {
        if ($this->connection !== null) {
            return $this->connection;
        }

        // 1. Construct the Data Source Name (DSN)
        $dsn = sprintf(
            'mysql:host=%s;port=%d;dbname=%s;charset=%s',
            $this->config['host'],
            $this->config['port'],
            $this->config['dbname'],
            $this->config['charset']
        );

        // 2. Set driver options
        $options = [
            // Throw exceptions on SQL errors for reliable error handling
            PDO::ATTR_ERRMODE            => PDO::ERRMODE_EXCEPTION,
            // Return query results as associative arrays by default
            PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
            // Disable emulation to enforce native prepared statements
            PDO::ATTR_EMULATE_PREPARES   => false,
        ];

        // 3. Instantiate the connection
        $this->connection = new PDO($dsn, $this->config['user'], $this->config['pass'], $options);

        return $this->connection;
    }

    /**
     * Helper to return the DSN without exposing credentials.
     */
    public function getDsn(): string
    {
        return sprintf(
            'mysql:host=%s;port=%d;dbname=%s;charset=%s',
            $this->config['host'],
            $this->config['port'],
            $this->config['dbname'],
            $this->config['charset']
        );
    }
}