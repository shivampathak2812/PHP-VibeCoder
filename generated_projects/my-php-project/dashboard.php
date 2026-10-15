<?php

declare(strict_types=1);

require_once __DIR__ . '/config/database.php';
require_once __DIR__ . '/src/Session.php';
require_once __DIR__ . '/src/Auth.php';

use Config\Database;
use App\Session;
use App\Auth;

Session::start();

try {
    $dbConfig = new Database();
    $pdo = $dbConfig->getConnection();
    $auth = new Auth($pdo);
} catch (\Exception $e) {
    die("Database Connection Error: " . htmlspecialchars($e->getMessage()));
}

if (!$auth->isLoggedIn()) {
    header("Location: index.php");
    exit();
}

$currentUser = $auth->getCurrentUser();
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard - Secure Auth</title>
    <link rel="stylesheet" href="assets/css/style.css">
</head>
<body>
    <div class="dashboard-card">
        <div class="dashboard-header">
            <h2>Welcome, <?= htmlspecialchars($currentUser['name']) ?>!</h2>
            <p>You have successfully logged into the system.</p>
        </div>

        <div class="dashboard-content">
            <div class="info-group">
                <span class="info-label">User ID:</span>
                <span class="info-value"><?= htmlspecialchars((string)$currentUser['id']) ?></span>
            </div>
            <div class="info-group">
                <span class="info-label">Full Name:</span>
                <span class="info-value"><?= htmlspecialchars($currentUser['name']) ?></span>
            </div>
            <div class="info-group">
                <span class="info-label">Email Address:</span>
                <span class="info-value"><?= htmlspecialchars($currentUser['email']) ?></span>
            </div>
        </div>

        <div class="dashboard-actions">
            <a href="logout.php" class="btn btn-danger">Log Out</a>
        </div>
    </div>
</body>
</html>