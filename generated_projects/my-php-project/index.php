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

if ($auth->isLoggedIn()) {
    header("Location: dashboard.php");
    exit();
}

$errorMessage = null;
$successMessage = Session::getFlash('success');

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $csrfToken = $_POST['csrf_token'] ?? '';
    if (!Session::validateCsrfToken($csrfToken)) {
        $errorMessage = "Invalid security token. Please refresh and try again.";
    } else {
        $email = $_POST['email'] ?? '';
        $password = $_POST['password'] ?? '';

        try {
            if ($auth->login($email, $password)) {
                header("Location: dashboard.php");
                exit();
            } else {
                $errorMessage = "Invalid email address or password.";
            }
        } catch (\Exception $e) {
            $errorMessage = $e->getMessage();
        }
    }
}

$csrfToken = Session::generateCsrfToken();
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login - Secure Auth</title>
    <link rel="stylesheet" href="assets/css/style.css">
</head>
<body>
    <div class="auth-card">
        <div class="auth-header">
            <h2>Welcome Back</h2>
            <p>Please log in to your account</p>
        </div>

        <?php if ($successMessage): ?>
            <div class="alert alert-success">
                <?= htmlspecialchars($successMessage) ?>
            </div>
        <?php endif; ?>

        <?php if ($errorMessage): ?>
            <div class="alert alert-danger">
                <?= htmlspecialchars($errorMessage) ?>
            </div>
        <?php endif; ?>

        <form action="index.php" method="POST" id="loginForm" novalidate>
            <input type="hidden" name="csrf_token" value="<?= htmlspecialchars($csrfToken) ?>">

            <div class="form-group">
                <label for="email">Email Address</label>
                <input type="email" id="email" name="email" class="form-control" placeholder="name@example.com" required value="<?= htmlspecialchars($_POST['email'] ?? '') ?>">
                <span class="error-text" id="emailError"></span>
            </div>

            <div class="form-group">
                <label for="password">Password</label>
                <input type="password" id="password" name="password" class="form-control" placeholder="Enter your password" required>
                <span class="error-text" id="passwordError"></span>
            </div>

            <button type="submit" class="btn btn-primary">Log In</button>
        </form>

        <div class="auth-footer">
            <p>Don't have an account? <a href="register.php">Create Account</a></p>
        </div>
    </div>

    <script src="assets/js/main.js"></script>
</body>
</html>