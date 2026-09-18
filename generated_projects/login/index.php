<?php
require_once __DIR__ . '/config.php';
require_once __DIR__ . '/Auth.php';
require_once __DIR__ . '/Csrf.php';

if (Auth::isLoggedIn()) {
    header("Location: dashboard.php");
    exit;
}

$error = '';
$success = '';

if (isset($_GET['registered'])) {
    $success = "Registration complete! Please enter your details below to log in.";
}

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $submittedToken = $_POST['csrf_token'] ?? '';
    if (!Csrf::verifyToken($submittedToken)) {
        $error = "CSRF Token validation failed. Please refresh and try again.";
    } else {
        $identity = $_POST['identity'] ?? '';
        $password = $_POST['password'] ?? '';

        $loginAttempt = Auth::login($identity, $password);
        if ($loginAttempt['success']) {
            header("Location: dashboard.php");
            exit;
        } else {
            $error = $loginAttempt['error'];
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
    <title>Secure Access - Sign In</title>
    <link rel="stylesheet" href="css/style.css">
</head>
<body>
    <div class="auth-container">
        <div class="auth-card">
            <div class="auth-header">
                <h2>Welcome Back</h2>
                <p>Please enter your credentials to access your account</p>
            </div>

            <?php if (!empty($error)): ?>
                <div class="alert alert-danger"><?php echo htmlspecialchars($error, ENT_QUOTES, 'UTF-8'); ?></div>
            <?php endif; ?>

            <?php if (!empty($success)): ?>
                <div class="alert alert-success"><?php echo htmlspecialchars($success, ENT_QUOTES, 'UTF-8'); ?></div>
            <?php endif; ?>

            <form action="index.php" method="POST">
                <input type="hidden" name="csrf_token" value="<?php echo htmlspecialchars($csrfToken, ENT_QUOTES, 'UTF-8'); ?>">
                
                <div class="form-group">
                    <label for="identity">Username or Email</label>
                    <input type="text" id="identity" name="identity" required placeholder="Enter username or email address" autocomplete="username">
                </div>

                <div class="form-group">
                    <label for="password">Password</label>
                    <input type="password" id="password" name="password" required placeholder="••••••••" autocomplete="current-password">
                </div>

                <button type="submit" class="btn btn-primary">Sign In</button>
            </form>

            <div class="auth-footer">
                Don't have an account? <a href="register.php">Create free account</a>
            </div>
        </div>
    </div>
</body>
</html>