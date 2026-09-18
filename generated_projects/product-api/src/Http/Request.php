<?php

declare(strict_types=1);

namespace App\Http;

class Request
{
    private array $body;

    public function __construct(
        private readonly string $method,
        private readonly string $uri,
        private readonly array $queryParams
    ) {
        $this->body = $this->parseBody();
    }

    public static function capture(): self
    {
        $method = $_SERVER['REQUEST_METHOD'] ?? 'GET';
        $uri = parse_url($_SERVER['REQUEST_URI'] ?? '/', PHP_URL_PATH);
        
        return new self($method, $uri, $_GET);
    }

    private function parseBody(): array
    {
        if ($this->method === 'OPTIONS') {
            return [];
        }

        $input = file_get_contents('php://input');
        if (empty($input)) {
            return $_POST;
        }

        $decoded = json_decode($input, true);
        if (json_last_error() === JSON_ERROR_NONE && is_array($decoded)) {
            return $decoded;
        }

        return $_POST;
    }

    public function getMethod(): string
    {
        return strtoupper($this->method);
    }

    public function getUri(): string
    {
        return $this->uri;
    }

    public function getQueryParams(): array
    {
        return $this->queryParams;
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