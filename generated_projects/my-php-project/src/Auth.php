<?php

declare(strict_types=1);

namespace App;

use PDO;

class Auth
{
    private PDO $db;

    public function __construct()
    {
        $this::startSecureSession();
        $this->db = Database::getConnection();
    }

    public static function startSecureSession(): void
    {
        if (session_status() === PHP_SESSION_NONE) {
            session_start([
                'cookie_httponly' => true,
                'cookie_samesite' => 'Strict',
                'use_only_cookies' => true,
            ]);
        }
    }

    public function register(string $username, string $email, string $password): array
    {
        $username = trim($username);
        $email = filter_var(trim($email), FILTER_VALIDATE_EMAIL);

        if (!$email) {
            return ['success' => false, 'message' => 'Invalid email address format.'];
        }

        if (strlen($username) < 3 || strlen($username) > 50) {
            return ['success' => false, 'message' => 'Username must be between 3 and 50 characters.'];
        }

        if (strlen($password) < 8) {
            return ['success' => false, 'message' => 'Password must be at least 8 characters long.'];
        }

        // Check if user or email already exists
        $stmt = $this->db->prepare('SELECT id FROM users WHERE email = :email OR username = :username LIMIT 1');
        $stmt->execute([
            'email' => $email,
            'username' => $username,
        ]);

        if ($stmt->fetch()) {
            return ['success' => false, 'message' => 'Username or Email is already registered.'];
        }

        $passwordHash = password_hash($password, PASSWORD_DEFAULT);

        $insertStmt = $this->db->prepare('INSERT INTO users (username, email, password_hash) VALUES (:username, :email, :password_hash)');
        $created = $insertStmt->execute([
            'username' => $username,
            'email' => $email,
            'password_hash' => $passwordHash,
        ]);

        if ($created) {
            return ['success' => true, 'message' => 'Registration successful! You can now log in.'];
        }

        return ['success' => false, 'message' => 'An error occurred during registration. Please try again.'];
    }

    public function login(string $identity, string $password): array
    {
        $identity = trim($identity);

        if (empty($identity) || empty($password)) {
            return ['success' => false, 'message' => 'Please fill in all required fields.'];
        }

        $stmt = $this->db->prepare('SELECT id, username, email, password_hash FROM users WHERE email = :identity OR username = :identity LIMIT 1');
        $stmt->execute(['identity' => $identity]);
        $user = $stmt->fetch();

        if (!$user || !password_verify($password, $user['password_hash'])) {
            return ['success' => false, 'message' => 'Invalid credentials provided.'];
        }

        // Regenerate session ID to prevent session fixation attacks
        session_regenerate_id(true);

        $_SESSION['user_id'] = (int)$user['id'];
        $_SESSION['username'] = $user['username'];
        $_SESSION['email'] = $user['email'];
        $_SESSION['logged_in'] = true;

        return ['success' => true, 'message' => 'Login successful.'];
    }

    public function isLoggedIn(): bool
    {
        return isset($_SESSION['logged_in']) && $_SESSION['logged_in'] === true;
    }

    public function getCurrentUser(): ?array
    {
        if (!$this->isLoggedIn()) {
            return null;
        }

        return [
            'id' => $_SESSION['user_id'],
            'username' => $_SESSION['username'],
            'email' => $_SESSION['email'],
        ];
    }

    public function logout(): void
    {
        $_SESSION = [];

        if (ini_get('session.use_cookies')) {
            $params = session_get_cookie_params();
            setcookie(
                session_name(),
                '',
                time() - 42000,
                $params['path'],
                $params['domain'],
                $params['secure'],
                $params['httponly']
            );
        }

        session_destroy();
    }
}