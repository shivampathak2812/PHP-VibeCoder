<?php

declare(strict_types=1);

namespace App\Http;

class Request
{
    private array $body;
    private string $method;
    private string $uri;

    public function __construct()
    {
        $this->method = strtoupper($_SERVER['REQUEST_METHOD'] ?? 'GET');
        
        $requestUri = $_SERVER['REQUEST_URI'] ?? '/';
        $parsedUrl = parse_url($requestUri, PHP_URL_PATH);
        $this->uri = is_string($parsedUrl) ? $parsedUrl : '/';

        $rawBody = file_get_contents('php://input');
        $decoded = json_decode($rawBody ?: '', true);

        $this->body = is_array($decoded) ? $decoded : [];
    }

    public function getMethod(): string
    {
        return $this->method;
    }

    public function getUri(): string
    {
        return $this->uri;
    }

    public function getBody(): array
    {
        return $this->body;
    }

    public function get(string $key, mixed $default = null): mixed
    {
        return $this->body[$key] ?? $default;
    }
}