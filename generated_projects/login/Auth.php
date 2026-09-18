<?php
require_once __DIR__ . '/config.php';
require_once __DIR__ . '/Database.php';

class Auth {
    /**
     * Handle register routines with rigorous server-side checks
     */
    public static function register(string $username, string $email, string $password, string $confirmPassword): array {
        $errors = [];
        $username = trim($username);
        $email = trim($email);

        if (empty($username)) {
            $errors[] = "Username cannot be blank.";
        } elseif (!preg_match('/^[a-zA-Z0-9_]{3,20}$/', $username)) {
            $errors[] = "Username must be 3-20 characters long and contain only letters, numbers, and underscores.";
        }

        if (empty($email)) {
            $errors[] = "Email address cannot be blank.";
        } elseif (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
            $errors[] = "Please provide a valid email structure.";
        }

        if (empty($password)) {
            $errors[] = "Password is required.";
        } elseif (strlen($password) < 8) {
            $errors[] = "Password must be at least 8 characters long.";
        }

        if ($password !== $confirmPassword) {
            $errors[] = "Passwords do not match.";
        }

        if (!empty($errors)) {
            return ['success' => false, 'errors' => $errors];
        }

        $db = Database::getConnection();

        try {
            $stmt = $db->prepare("SELECT id FROM users WHERE username = ? OR email = ? LIMIT 1");
            $stmt->execute([$username, $email]);
            if ($stmt->fetch()) {
                return ['success' => false, 'errors' => ["Username or email address is already taken."]];
            }

            $passwordHash = password_hash($password, PASSWORD_DEFAULT);

            $insertStmt = $db->prepare("INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)");
            $insertStmt->execute([$username, $email, $passwordHash]);

            return ['success' => true, 'message' => "Successfully registered! You can now log in below."];
        } catch (PDOException $e) {
            error_log("Registration Exception: " . $e->getMessage());
            return ['success' => false, 'errors' => ["A server-side error occurred. Please try again later."]];
        }
    }

    /**
     * Handle authentication mapping with session regeneration safeguards
     */
    public static function login(string $identity, string $password): array {
        $identity = trim($identity);
        if (empty($identity) || empty($password)) {
            return ['success' => false, 'error' => "Please enter both credentials."];
        }

        $db = Database::getConnection();

        try {
            $stmt = $db->prepare("SELECT * FROM users WHERE username = ? OR email = ? LIMIT 1");
            $stmt->execute([$identity, $identity]);
            $user = $stmt->fetch();

            if ($user && password_verify($password, $user['password_hash'])) {
                // Safeguard against session hijacking & fixation
                session_regenerate_id(true);

                $_SESSION['user_id'] = $user['id'];
                $_SESSION['username'] = $user['username'];
                $_SESSION['email'] = $user['email'];
                $_SESSION['last_login'] = time();

                return ['success' => true];
            }

            return ['success' => false, 'error' => "Invalid credentials. Please try again."];
        } catch (PDOException $e) {
            error_log("Login Exception: " . $e->getMessage());
            return ['success' => false, 'error' => "An internal system error occurred."];
        }
    }

    /**
     * Check if user is logged in
     */
    public static function isLoggedIn(): bool {
        return isset($_SESSION['user_id']);
    }

    /**
     * Guard pages from unauthorized access
     */
    public static function requireLogin(): void {
        if (!self::isLoggedIn()) {
            header("Location: index.php");
            exit;
        }
    }

    /**
     * Safely destroy credentials, cookies and session variables
     */
    public static function logout(): void {
        $_SESSION = [];
        if (ini_get("session.use_cookies")) {
            $params = session_get_cookie_params();
            setcookie(
                session_name(),
                '',
                time() - 42000,
                $params["path"],
                $params["domain"],
                $params["secure"],
                $params["httponly"]
            );
        }
        session_destroy();
    }
}