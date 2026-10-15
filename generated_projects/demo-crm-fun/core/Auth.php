<?php
declare(strict_types=1);

namespace Core;

class Auth {
    public static function init(): void {
        if (session_status() === PHP_SESSION_NONE) {
            session_start([
                'cookie_httponly' => true,
                'cookie_samesite' => 'Lax'
            ]);
        }
    }

    public static function login(array $user): void {
        self::init();
        session_regenerate_id(true);
        $_SESSION['user_id'] = $user['id'];
        $_SESSION['user_name'] = $user['name'];
        $_SESSION['user_email'] = $user['email'];
        $_SESSION['user_role'] = $user['role'];
    }

    public static function logout(): void {
        self::init();
        $_SESSION = [];
        if (ini_get("session.use_cookies")) {
            $params = session_get_cookie_params();
            setcookie(session_name(), '', time() - 42000,
                $params["path"], $params["domain"],
                $params["secure"], $params["httponly"]
            );
        }
        session_destroy();
    }

    public static function check(): bool {
        self::init();
        return isset($_SESSION['user_id']);
    }

    public static function user(): ?array {
        self::init();
        if (!self::check()) {
            return null;
        }
        return [
            'id'    => $_SESSION['user_id'],
            'name'  => $_SESSION['user_name'],
            'email' => $_SESSION['user_email'],
            'role'  => $_SESSION['user_role']
        ];
    }

    public static function id(): ?int {
        self::init();
        return $_SESSION['user_id'] ?? null;
    }

    public static function hasRole(array $allowedRoles): bool {
        $user = self::user();
        if (!$user) {
            return false;
        }
        return in_array($user['role'], $allowedRoles, true);
    }

    public static function requireAuth(): void {
        if (!self::check()) {
            header('Location: index.php?route=login');
            exit;
        }
    }

    public static function requireRoles(array $roles): void {
        self::requireAuth();
        if (!self::hasRole($roles)) {
            header('HTTP/1.1 403 Forbidden');
            echo "403 Forbidden: You do not have permission to access this page.";
            exit;
        }
    }
}