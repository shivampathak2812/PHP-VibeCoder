<?php
require_once __DIR__ . '/config.php';
require_once __DIR__ . '/Auth.php';

// Strict session check
Auth::requireLogin();

// Safely bind identity attributes
$username = $_SESSION['username'] ?? 'User';
$email = $_SESSION['email'] ?? 'Unknown';
$lastLogin = $_SESSION['last_login'] ?? time();
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard - Secure User Portal</title>
    <link rel="stylesheet" href="css/style.css">
</head>
<body>
    <div class="dashboard-wrapper">
        <header class="dashboard-header">
            <div class="header-container">
                <span class="logo">SecureApp</span>
                <a href="logout.php" class="btn btn-secondary">Logout</a>
            </div>
        </header>

        <main class="dashboard-content">
            <div class="dashboard-card">
                <h2>Welcome Back, <?php echo htmlspecialchars($username, ENT_QUOTES, 'UTF-8'); ?>!</h2>
                <p class="subtitle">You have authenticated successfully. Below are your session diagnostics:</p>
                
                <div class="profile-details">
                    <div class="detail-row">
                        <strong>Username:</strong>
                        <span><?php echo htmlspecialchars($username, ENT_QUOTES, 'UTF-8'); ?></span>
                    </div>
                    <div class="detail-row">
                        <strong>Registered Email:</strong>
                        <span><?php echo htmlspecialchars($email, ENT_QUOTES, 'UTF-8'); ?></span>
                    </div>
                    <div class="detail-row">
                        <strong>Session Initiated:</strong>
                        <span><?php echo date('Y-m-d H:i:s', $lastLogin); ?></span>
                    </div>
                    <div class="detail-row">
                        <strong>Current IP Context:</strong>
                        <span><?php echo htmlspecialchars($_SERVER['REMOTE_ADDR'] ?? 'Unknown', ENT_QUOTES, 'UTF-8'); ?></span>
                    </div>
                </div>
            </div>
        </main>
    </div>
</body>
</html>