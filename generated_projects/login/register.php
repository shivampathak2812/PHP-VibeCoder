<?php
require_once __DIR__ . '/config.php';
require_once __DIR__ . '/Auth.php';
require_once __DIR__ . '/Csrf.php';

if (Auth::isLoggedIn()) {
    header("Location: dashboard.php");
    exit;
}

$errors = [];
$oldUsername = '';
$oldEmail = '';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $submittedToken = $_POST['csrf_token'] ?? '';
    if (!Csrf::verifyToken($submittedToken)) {
        $errors[] = "CSRF Verification Failed.";
    } else {
        $username = $_POST['username'] ?? '';
        $email = $_POST['email'] ?? '';
        $password = $_POST['password'] ?? '';
        $confirmPassword = $_POST['confirm_password'] ?? '';

        $oldUsername = $username;
        $oldEmail = $email;

        $registrationAttempt = Auth::register($username, $email, $password, $confirmPassword);
        if ($registrationAttempt['success']) {
            header("Location: index.php?registered=1");
            exit;
        } else {
            $errors = $registrationAttempt['errors'];
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
    <title>Secure Access - Create Account</title>
    <link rel="stylesheet" href="css/style.css">
</head>
<body>
    <div class="auth-container">
        <div class="auth-card">
            <div class="auth-header">
                <h2>Create Account</h2>
                <p>Register below to get secure platform access</p>
            </div>

            <?php if (!empty($errors)): ?>
                <div class="alert alert-danger">
                    <ul class="error-list" style="margin: 0; padding-left: 20px;">
                        <?php foreach ($errors as $error): ?>
                            <li><?php echo htmlspecialchars($error, ENT_QUOTES, 'UTF-8'); ?></li>
                        <?php endforeach; ?>
                    </ul>
                </div>
            <?php endif; ?>

            <form action="register.php" method="POST">
                <input type="hidden" name="csrf_token" value="<?php echo htmlspecialchars($csrfToken, ENT_QUOTES, 'UTF-8'); ?>">
                
                <div class="form-group">
                    <label for="username">Username</label>
                    <input type="text" id="username" name="username" value="<?php echo htmlspecialchars($oldUsername, ENT_QUOTES, 'UTF-8'); ?>" required placeholder="3-20 characters (letters/numbers/underscores)">
                </div>

                <div class="form-group">
                    <label for="email">Email Address</label>
                    <input type="email" id="email" name="email" value="<?php echo htmlspecialchars($oldEmail, ENT_QUOTES, 'UTF-8'); ?>" required placeholder="you@domain.com">
                </div>

                <div class="form-group">
                    <label for="password">Password</label>
                    <input type="password" id="password" name="password" required placeholder="Minimum 8 characters">
                </div>

                <div class="form-group">
                    <label for="confirm_password">Confirm Password</label>
                    <input type="password" id="confirm_password" name="confirm_password" required placeholder="Repeat chosen password">
                </div>

                <button type="submit" class="btn btn-primary">Sign Up</button>
            </form>

            <div class="auth-footer">
                Already have an account? <a href="index.php">Log in instead</a>
            </div>
        </div>
    </div>
</body>
</html>