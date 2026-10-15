<?php
declare(strict_types=1);

$config = require __DIR__ . '/config.php';
require_once __DIR__ . '/Database.php';

$connectionError = null;
$pdo = null;
$searchResults = [];
$searchQuery = trim($_GET['q'] ?? '');

try {
    $pdo = Database::getConnection($config);

    // Demonstration of secure prepared statement taking user input
    if ($searchQuery !== '') {
        $stmt = $pdo->prepare(
            'SELECT id, username, email, role, created_at 
             FROM users 
             WHERE username LIKE :query OR role LIKE :query 
             ORDER BY id ASC'
        );
        $wildcard = '%' . $searchQuery . '%';
        $stmt->execute([':query' => $wildcard]);
        $searchResults = $stmt->fetchAll();
    } else {
        $stmt = $pdo->query('SELECT id, username, email, role, created_at FROM users ORDER BY id ASC');
        $searchResults = $stmt->fetchAll();
    }
} catch (RuntimeException $e) {
    $connectionError = $e->getMessage();
}

/**
 * Escapes output safely for HTML contexts.
 */
function e(?string $value): string
{
    return htmlspecialchars((string) $value, ENT_QUOTES, 'UTF-8');
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Understanding PHP Database Connections</title>
    <link rel="stylesheet" href="css/style.css">
</head>
<body>
    <div class="container">
        <header class="header">
            <h1>Database Connections in Modern PHP 8.x</h1>
            <p>A comprehensive architectural reference, safe code patterns, and live demonstration.</p>
        </header>

        <!-- Live Status Widget -->
        <section class="card status-card">
            <h2>Connection Diagnostics</h2>
            <?php if ($connectionError !== null): ?>
                <div class="alert alert-danger">
                    <strong>Connection Failed:</strong> <?= e($connectionError) ?>
                    <p class="small-text">Verify that MySQL is running and your connection settings match the environment.</p>
                </div>
            <?php else: ?>
                <div class="alert alert-success">
                    <strong>Connected Successfully!</strong>
                    <span>Server: <?= e($pdo->getAttribute(PDO::ATTR_SERVER_INFO)) ?></span>
                </div>
            <?php endif; ?>
        </section>

        <!-- Interactive Search Demo -->
        <?php if ($pdo !== null): ?>
            <section class="card">
                <h2>Live Parameterized Query Execution</h2>
                <p>This query takes user input and executes safely using a prepared statement with parameter binding.</p>
                <form method="GET" action="index.php" class="search-form">
                    <input 
                        type="text" 
                        name="q" 
                        value="<?= e($searchQuery) ?>" 
                        placeholder="Search by username or role..."
                        class="form-control"
                    >
                    <button type="submit" class="btn">Filter</button>
                    <?php if ($searchQuery !== ''): ?>
                        <a href="index.php" class="btn btn-secondary">Reset</a>
                    <?php endif; ?>
                </form>

                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>Username</th>
                                <th>Email</th>
                                <th>Role</th>
                                <th>Created</th>
                            </tr>
                        </thead>
                        <tbody>
                            <?php if (empty($searchResults)): ?>
                                <tr>
                                    <td colspan="5" class="text-center">No records found matching your query.</td>
                                </tr>
                            <?php else: ?>
                                <?php foreach ($searchResults as $user): ?>
                                    <tr>
                                        <td><?= e((string)$user['id']) ?></td>
                                        <td><strong><?= e($user['username']) ?></strong></td>
                                        <td><?= e($user['email']) ?></td>
                                        <td><span class="badge"><?= e($user['role']) ?></span></td>
                                        <td><?= e($user['created_at']) ?></td>
                                    </tr>
                                <?php endforeach; ?>
                            <?php endif; ?>
                        </tbody>
                    </table>
                </div>
            </section>
        <?php endif; ?>

        <!-- Educational Section: How Connections Work -->
        <section class="card">
            <h2>1. Anatomy of a Database Connection</h2>
            <p>
                Connecting to a database is an overhead-heavy network handshake:
            </p>
            <ol class="step-list">
                <li><strong>Transport Layer:</strong> PHP opens a TCP/IP socket (or local UNIX domain socket) to the database server port (typically <code>3306</code>).</li>
                <li><strong>Authentication &amp; Handshake:</strong> The client and server agree on an SSL/TLS protocol, exchange cryptographic challenges, and authenticate user credentials.</li>
                <li><strong>Session Configuration:</strong> Character encoding (such as <code>utf8mb4</code>) and session variables (time zones, SQL modes) are initialized.</li>
                <li><strong>Handle Creation:</strong> PHP instantiates an object wrapper (such as an instance of <code>PDO</code>) representing the open connection stream.</li>
            </ol>
        </section>

        <!-- Educational Section: PDO vs MySQLi -->
        <section class="card">
            <h2>2. PDO vs. MySQLi: Choosing the Right Driver</h2>
            <div class="comparison-grid">
                <div class="grid-col">
                    <h3>PDO (PHP Data Objects) &mdash; Recommended</h3>
                    <ul>
                        <li><strong>Database Neutral:</strong> Works with MySQL, PostgreSQL, SQLite, Oracle, and MS SQL Server through drivers.</li>
                        <li><strong>Named Parameters:</strong> Allows intuitive parameter mapping (<code>:username</code>, <code>:status</code>).</li>
                        <li><strong>Object Mapping:</strong> Features flexible fetching mechanisms directly into classes and data structures.</li>
                        <li><strong>Best For:</strong> Modern web applications, microservices, and applications that may switch or test against different databases.</li>
                    </ul>
                </div>
                <div class="grid-col">
                    <h3>MySQLi (MySQL Improved)</h3>
                    <ul>
                        <li><strong>MySQL Specific:</strong> Only works with MySQL and MariaDB servers.</li>
                        <li><strong>Dual Interface:</strong> Supports both Object-Oriented and Procedural paradigms.</li>
                        <li><strong>Positional Only:</strong> Standard prepared statements support only positional <code>?</code> placeholders.</li>
                        <li><strong>Best For:</strong> Legacy codebases or projects that explicitly require MySQL-exclusive features (such as asynchronous querying).</li>
                    </ul>
                </div>
            </div>
        </section>

        <!-- Educational Section: UNSAFE vs SAFE -->
        <section class="card">
            <h2>3. Security: Unsafe vs. Safe Querying</h2>
            <p>Never concatenate or interpolate variables directly into SQL statements.</p>
            
            <div class="code-comparison">
                <div class="code-box unsafe">
                    <div class="code-header">DANGEROUS: String Interpolation (SQL Injection Vulnerability)</div>
                    <pre><code>// NEVER DO THIS: An attacker can send: ' OR 1=1 -- 
$input = $_GET['username'];
$sql = "SELECT * FROM users WHERE username = '" . $input . "'";
$pdo-&gt;query($sql);</code></pre>
                </div>
                <div class="code-box safe">
                    <div class="code-header">SECURE: Prepared Statements with Parameter Binding</div>
                    <pre><code>// SAFE: The database treats the parameter strictly as data, never executable code.
$input = $_GET['username'];
$stmt = $pdo-&gt;prepare("SELECT * FROM users WHERE username = :name");
$stmt-&gt;execute([':name' =&gt; $input]);
$results = $stmt-&gt;fetchAll();</code></pre>
                </div>
            </div>
        </section>
    </div>
</body>
</html>