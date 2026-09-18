<?php

declare(strict_types=1);

use App\Config\Database;
use App\Controllers\AuthController;
use App\Http\Request;
use App\Http\Response;
use App\Repositories\UserRepository;
use App\Services\AuthService;
use App\Utils\Env;

require_once __DIR__ . '/../src/Utils/Env.php';

// Load environment variables
Env::load(__DIR__ . '/../.env');

// Register PSR-4 autoloader if Composer vendor autoloader isn't present
if (file_exists(__DIR__ . '/../vendor/autoload.php')) {
    require_once __DIR__ . '/../vendor/autoload.php';
} else {
    spl_autoload_register(static function (string $class): void {
        $prefix = 'App\\';
        $baseDir = __DIR__ . '/../src/';
        $len = strlen($prefix);

        if (strncmp($prefix, $class, $len) !== 0) {
            return;
        }

        $relativeClass = substr($class, $len);
        $file = $baseDir . str_replace('\\', '/', $relativeClass) . '.php';

        if (file_exists($file)) {
            require_once $file;
        }
    });
}

// Enable standard error handling
set_exception_handler(static function (Throwable $e): void {
    Response::error('Internal Server Error', [
        'details' => $e->getMessage()
    ], 500);
});

$request = new Request();
$method = $request->getMethod();
$uri = rtrim($request->getUri(), '/');

// Initialize dependencies
$pdo = Database::getConnection();
$userRepository = new UserRepository($pdo);
$authService = new AuthService($userRepository);
$authController = new AuthController($authService);

// Simple API Router
if ($uri === '/api/register') {
    if ($method === 'POST') {
        $authController->register($request);
    } else {
        Response::error('Method Not Allowed', [], 405);
    }
} elseif ($uri === '/api/login') {
    if ($method === 'POST') {
        $authController->login($request);
    } else {
        Response::error('Method Not Allowed', [], 405);
    }
} else {
    Response::error('Resource not found', [], 404);
}