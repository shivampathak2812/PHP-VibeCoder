<?php

declare(strict_types=1);

use App\Config\Env;
use App\Controllers\ProductController;
use App\Exceptions\NotFoundException;
use App\Exceptions\ValidationException;
use App\Http\Request;
use App\Http\Response;
use App\Http\Router;

// Simple PSR-4 Autoloader
spl_autoload_register(function (string $class): void {
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

// Load environment variables
$envPath = __DIR__ . '/../.env';
if (file_exists($envPath)) {
    Env::load($envPath);
}

// Exception and Error Handling
set_exception_handler(function (Throwable $e): void {
    if ($e instanceof NotFoundException) {
        Response::error($e->getMessage(), 404);
    }

    if ($e instanceof ValidationException) {
        Response::error($e->getMessage(), 422, $e->getErrors());
    }

    Response::error('An unexpected server error occurred: ' . $e->getMessage(), 500);
});

// Capture HTTP Request
$request = Request::capture();

// Register Routes
$router = new Router();

$router->get('/products', [ProductController::class, 'index']);
$router->get('/products/{id}', [ProductController::class, 'show']);
$router->post('/products', [ProductController::class, 'store']);
$router->put('/products/{id}', [ProductController::class, 'update']);
$router->delete('/products/{id}', [ProductController::class, 'destroy']);

// Dispatch Request
$router->dispatch($request);