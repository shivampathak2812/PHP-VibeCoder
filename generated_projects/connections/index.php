<?php
declare(strict_types=1);

require_once __DIR__ . '/Database.php';
$config = require __DIR__ . '/config.php';

$db = new Database($config);
$connectionError = null;
$serverInfo = null;
$records = [];

try {
    $pdo = $db->getConnection();
    
    // Retrieve server metadata via the active PDO connection
    $serverInfo = [
        'driver'         => $pdo->getAttribute(PDO::ATTR_DRIVER_NAME),
        'server_version' => $pdo->getAttribute(PDO::ATTR_SERVER_VERSION),
        'client_version' => $pdo->getAttribute(PDO::ATTR_CLIENT_VERSION),
        'connection_status' => $pdo->getAttribute(PDO::ATTR_CONNECTION_STATUS),
    ];

    // Example of a safe, prepared query execution
    $stmt = $pdo->prepare('SELECT id, node_name, ip_address, status, created_at FROM server_nodes ORDER BY id ASC');
    $stmt->execute();
    $records = $stmt->fetchAll();

} catch (PDOException $e) {
    // Avoid exposing raw database passwords or internal traces to clients
    $connectionError = $e->getMessage();
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PHP Database Connection Guide</title>
    <link rel="stylesheet" href="css/style.css">
</head>
<body>
    <header class="header">
        <div class="container">
            <h1>Database Connection in Modern PHP</h1>
            <p>A complete reference for MySQL connections using PHP Data Objects (PDO)</p>
        </div>
    </header>

    <main class="container main-content">
        <!-- Status Card -->
        <section class="card status-card <?= $connectionError ? 'status-error' : 'status-success' ?>">
            <h2>Connection Status</h2>
            <?php if ($connectionError): ?>
                <div class="badge badge-error">Connection Failed</div>
                <p class="error-msg"><strong>Error details:</strong> <?= htmlspecialchars($connectionError, ENT_QUOTES, 'UTF-8') ?></p>
                <p>Ensure MySQL is running and verify the credentials in <code>config.php</code>.</p>
            <?php else: ?>
                <div class="badge badge-success">Connected Successfully</div>
                <div class="meta-grid">
                    <div><strong>Driver:</strong> <?= htmlspecialchars((string) $serverInfo['driver'], ENT_QUOTES, 'UTF-8') ?></div>
                    <div><strong>Server Version:</strong> <?= htmlspecialchars((string) $serverInfo['server_version'], ENT_QUOTES, 'UTF-8') ?></div>
                    <div><strong>DSN:</strong> <code><?= htmlspecialchars($db->getDsn(), ENT_QUOTES, 'UTF-8') ?></code></div>
                    <div><strong>Connection:</strong> <?= htmlspecialchars((string) $serverInfo['connection_status'], ENT_QUOTES, 'UTF-8') ?></div>
                </div>
            <?php endif; ?>
        </section>

        <!-- Educational Explanation Section -->
        <section class="card">
            <h2>How PHP Database Connection Works</h2>
            <div class="steps-grid">
                <article class="step">
                    <h3>1. Data Source Name (DSN)</h3>
                    <p>The DSN defines the driver type, host server, target database name, network port, and character encoding set (<code>utf8mb4</code> is recommended for full Unicode support).</p>
                    <pre><code>$dsn = "mysql:host=127.0.0.1;port=3306;dbname=app_db;charset=utf8mb4";</code></pre>
                </article>

                <article class="step">
                    <h3>2. Connection Driver & Options</h3>
                    <p>Options configure critical PDO behaviors, such as converting database errors into native catchable exceptions and preventing simulated prepared statements.</p>
                    <pre><code>$options = [
    PDO::ATTR_ERRMODE            => PDO::ERRMODE_EXCEPTION,
    PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
    PDO::ATTR_EMULATE_PREPARES   => false,
];</code></pre>
                </article>

                <article class="step">
                    <h3>3. Instantiation & Exception Handling</h3>
                    <p>Connections should always be encapsulated inside a <code>try/catch</code> block handling <code>PDOException</code> so that database secrets are not leaked in uncaught traces.</p>
                    <pre><code>try {
    $pdo = new PDO($dsn, $user, $pass, $options);
} catch (PDOException $e) {
    // Log exception and handle gracefully
}</code></pre>
                </article>
            </div>
        </section>

        <!-- Query Execution Demonstration -->
        <?php if (!$connectionError): ?>
        <section class="card">
            <h2>Query Execution via Prepared Statements</h2>
            <p>Once connected, execute queries using prepared statements to prevent SQL injection vulnerabilities:</p>
            
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Node Name</th>
                            <th>IP Address</th>
                            <th>Status</th>
                            <th>Created At</th>
                        </tr>
                    </thead>
                    <tbody>
                        <?php if (empty($records)): ?>
                            <tr>
                                <td colspan="5" class="text-center">No records found. Run the schema script to insert sample data.</td>
                            </tr>
                        <?php else: ?>
                            <?php foreach ($records as $row): ?>
                                <tr>
                                    <td><?= htmlspecialchars((string)$row['id'], ENT_QUOTES, 'UTF-8') ?></td>
                                    <td><?= htmlspecialchars($row['node_name'], ENT_QUOTES, 'UTF-8') ?></td>
                                    <td><code><?= htmlspecialchars($row['ip_address'], ENT_QUOTES, 'UTF-8') ?></code></td>
                                    <td>
                                        <span class="tag tag-<?= htmlspecialchars($row['status'], ENT_QUOTES, 'UTF-8') ?>">
                                            <?= htmlspecialchars(ucfirst($row['status']), ENT_QUOTES, 'UTF-8') ?>
                                        </span>
                                    </td>
                                    <td><?= htmlspecialchars($row['created_at'], ENT_QUOTES, 'UTF-8') ?></td>
                                </tr>
                            <?php endforeach; ?>
                        <?php endif; ?>
                    </tbody>
                </table>
            </div>
        </section>
        <?php endif; ?>
    </main>
</body>
</html>