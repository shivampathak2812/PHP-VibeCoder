<?php

declare(strict_types=1);

require_once __DIR__ . '/../src/Database.php';
require_once __DIR__ . '/../src/Csrf.php';
require_once __DIR__ . '/../src/Auth.php';

use App\Auth;

$auth = new Auth();

if (!$auth->isLoggedIn()) {
    header('Location: login.php');
    exit;
}

$currentUser = $auth->getCurrentUser();
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard - Protected Area</title>
    <link rel="stylesheet" href="css/style.css">
</head>
<body>
    <div class="container">
        <div class="card">
            <h2>User Dashboard</h2>

            <div class="alert alert-success">
                Welcome back, <strong><?= htmlspecialchars($currentUser['username'], ENT_QUOTES, 'UTF-8') ?></strong>!
            </div>

            <div class="form-group">
                <label>User ID:</label>
                <p><strong><?= htmlspecialchars((string)$currentUser['id'], ENT_QUOTES, 'UTF-8') ?></strong></p>
            </div>

            <div class="form-group">
                <label>Email Address:</label>
                <p><strong><?= htmlspecialchars($currentUser['email'], ENT_QUOTES, 'UTF-8') ?></strong></p>
            </div>

            <div class="mt-4">
                <a href="logout.php" class="btn btn-danger">Log Out</a>
            </div>
        </div>
    </div>
</body>
</html>