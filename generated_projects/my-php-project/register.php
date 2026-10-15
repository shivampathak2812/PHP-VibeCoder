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

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $csrfToken = $_POST['csrf_token'] ?? '';
    if (!Session::validateCsrfToken($csrfToken)) {
        $errorMessage = "Invalid security token. Please refresh and try again.";
    } else {
        $fullName = $_POST['full_name'] ?? '';
        $email = $_POST['email'] ?? '';
        $password = $_POST['password'] ?? '';
        $confirmPassword = $_POST['confirm_password'] ?? '';

        if ($password !== $confirmPassword) {
            $errorMessage = "Passwords do not match.";
        } else {
            try {
                if ($auth->register($fullName, $email, $password)) {
                    Session::setFlash('success', 'Account created successfully! You can now log in.');
                    header("Location: index.php");
                    exit();
                }
            } catch (\Exception $e) {
                $errorMessage = $e->getMessage();
            }
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
    <title>Register - Secure Auth</title>
    <link rel="stylesheet" href="assets/css/style.css">
</head>
<body>
    <div class="auth-card">
        <div class="auth-header">
            <h2>Create Account</h2>
            <p>Join us today by filling out the form below</p>
        </div>

        <?php if ($errorMessage): ?>
            <div class="alert alert-danger">
                <?= htmlspecialchars($errorMessage) ?>
            </div>
        <?php endif; ?>

        <form action="register.php" method="POST" id="registerForm" novalidate>
            <input type="hidden" name="csrf_token" value="<?= htmlspecialchars($csrfToken) ?>">

            <div class="form-group">
                <label for="full_name">Full Name</label>
                <input type="text" id="full_name" name="full_name" class="form-control" placeholder="John Doe" required value="<?= htmlspecialchars($_POST['full_name'] ?? '') ?>">
                <span class="error-text" id="nameError"></span>
            </div>

            <div class="form-group">
                <label for="email">Email Address</label>
                <input type="email" id="email" name="email" class="form-control" placeholder="name@example.com" required value="<?= htmlspecialchars($_POST['email'] ?? '') ?>">
                <span class="error-text" id="emailError"></span>
            </div>

            <div class="form-group">
                <label for="password">Password</label>
                <input type="password" id="password" name="password" class="form-control" placeholder="At least 8 characters" required>
                <span class="error-text" id="passwordError"></span>
            </div>

            <div class="form-group">
                <label for="confirm_password">Confirm Password</label>
                <input type="password" id="confirm_password" name="confirm_password" class="form-control" placeholder="Re-enter password" required>
                <span class="error-text" id="confirmPasswordError"></span>
            </div>

            <button type="submit" class="btn btn-primary">Register</button>
        </form>

        <div class="auth-footer">
            <p>Already have an account? <a href="index.php">Log In</a></p>
        </div>
    </div>

    <script src="assets/js/main.js"></script>
</body>
</html>