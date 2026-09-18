<?php

declare(strict_types=1);

namespace App\Http;

class Response
{
    /**
     * Send a JSON response with HTTP status code.
     */
    public static function json(mixed $data, int $statusCode = 200): void
    {
        http_response_code($statusCode);
        header('Content-Type: application/json; charset=UTF-8');
        header('X-Content-Type-Options: nosniff');
        
        echo json_encode($data, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);
        exit;
    }

    /**
     * Helper for success responses.
     */
    public static function success(string $message, mixed $data = null, int $statusCode = 200): void
    {
        $payload = [
            'status' => 'success',
            'message' => $message,
        ];

        if ($data !== null) {
            $payload['data'] = $data;
        }

        self::json($payload, $statusCode);
    }

    /**
     * Helper for error responses.
     */
    public static function error(string $message, array $errors = [], int $statusCode = 400): void
    {
        $payload = [
            'status' => 'error',
            'message' => $message,
        ];

        if (!empty($errors)) {
            $payload['errors'] = $errors;
        }

        self::json($payload, $statusCode);
    }
}