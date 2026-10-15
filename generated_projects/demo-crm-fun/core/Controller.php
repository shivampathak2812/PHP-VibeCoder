<?php
declare(strict_types=1);

namespace Core;

abstract class Controller {
    protected function render(string $view, array $data = []): void {
        extract($data);
        $viewFile = __DIR__ . '/../views/' . $view . '.php';

        if (!file_exists($viewFile)) {
            die("View file not found: " . htmlspecialchars($view, ENT_QUOTES, 'UTF-8'));
        }

        require __DIR__ . '/../views/layout/header.php';
        require $viewFile;
        require __DIR__ . '/../views/layout/footer.php';
    }

    protected function redirect(string $url): void {
        header("Location: " . $url);
        exit;
    }

    protected function validateCsrf(): void {
        $token = $_POST['csrf_token'] ?? null;
        if (!Csrf::verifyToken($token)) {
            die("CSRF Token Verification Failed.");
        }
    }
}