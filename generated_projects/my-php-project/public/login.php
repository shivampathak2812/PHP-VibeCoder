<?php

declare(strict_types=1);

require_once __DIR__ . '/../src/Database.php';
require_once __DIR__ . '/../src/Csrf.php';
require_once __DIR__ . '/../src/Auth.php';

use App\Auth;
use App\Csrf;

$auth = new Auth();

if ($auth->isLoggedIn()) {
    header('Location: dashboard.php');
    exit;
}

$errorMessage = '';
$successMessage = '';

if (isset($_GET['registered']) && $_GET['registered'] === '1') {
    $successMessage = 'Account created successfully! Please log in.';
}

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $token = $_POST['csrf_token'] ?? '';

    if (!Csrf::validateToken($token)) {
        $errorMessage = 'Invalid submission security token. Please try again.';
    } else {
        $identity = $_POST['identity'] ?? '';
        $password = $_POST['password'] ?? '';

        $result = $auth->login($identity, $password);

        if ($result['success']) {
            header('Location: dashboard.php');
            exit;
        } else {
            $errorMessage = $result['message'];
        }
    }
}

$csrfToken = Csrf::generateToken();
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login - User Portal</title>
    <link rel="stylesheet" href="css/style.css">
</head>
<body>
    <div class="container">
        <div class="card">
            <h2>Account Login</h2>

            <?php if (!empty($errorMessage)): ?>
                <div class="alert alert-danger">
                    <?= htmlspecialchars($errorMessage, ENT_QUOTES, 'UTF-8') ?>
                </div>
            <?php endif; ?>

            <?php if (!empty($successMessage)): ?>
                <div class="alert alert-success">
                    <?= htmlspecialchars($successMessage, ENT_QUOTES, 'UTF-8') ?>
                </div>
            <?php endif; ?>

            <form action="login.php" method="POST">
                <input type="hidden" name="csrf_token" value="<?= htmlspecialchars($csrfToken, ENT_QUOTES, 'UTF-8') ?>">

                <div class="form-group">
                    <label for="identity">Username or Email</label>
                    <input type="text" id="identity" name="identity" required autofocus>
                </div>

                <div class="form-group">
                    <label for="password">Password</label>
                    <input type="password" id="password" name="password" required>
                </div>

                <button type="submit" class="btn">Sign In</button>
            </form>

            <div class="text-center mt-4">
                <p>Don't have an account? <a href="register.php" class="link">Register here</a></p>
            </div>
        </div>
    </div>
</body>
</html>