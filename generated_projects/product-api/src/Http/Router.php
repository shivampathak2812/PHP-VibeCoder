<?php

declare(strict_types=1);

namespace App\Http;

use App\Exceptions\NotFoundException;

class Router
{
    private array $routes = [];

    public function addRoute(string $method, string $path, callable|array $handler): void
    {
        $this->routes[] = [
            'method'  => strtoupper($method),
            'path'    => $path,
            'handler' => $handler,
        ];
    }

    public function get(string $path, callable|array $handler): void
    {
        $this->addRoute('GET', $path, $handler);
    }

    public function post(string $path, callable|array $handler): void
    {
        $this->addRoute('POST', $path, $handler);
    }

    public function put(string $path, callable|array $handler): void
    {
        $this->addRoute('PUT', $path, $handler);
    }

    public function delete(string $path, callable|array $handler): void
    {
        $this->addRoute('DELETE', $path, $handler);
    }

    public function dispatch(Request $request): void
    {
        if ($request->getMethod() === 'OPTIONS') {
            Response::json(['status' => 'ok'], 200);
            return;
        }

        $requestMethod = $request->getMethod();
        $requestUri = rtrim($request->getUri(), '/');
        if ($requestUri === '') {
            $requestUri = '/';
        }

        foreach ($this->routes as $route) {
            if ($route['method'] !== $requestMethod) {
                continue;
            }

            $pattern = preg_replace('/\{([a-zA-Z0-9_]+)\}/', '(?P<$1>[^/]+)', $route['path']);
            $pattern = "#^" . rtrim($pattern, '/') . "$#";
            if ($route['path'] === '/') {
                $pattern = "#^/$#";
            }

            if (preg_match($pattern, $requestUri, $matches)) {
                $params = array_filter($matches, 'is_string', ARRAY_FILTER_USE_KEY);
                
                $handler = $route['handler'];

                if (is_array($handler)) {
                    [$class, $method] = $handler;
                    $controller = new $class();
                    call_user_func_array([$controller, $method], array_merge([$request], $params));
                    return;
                }

                if (is_callable($handler)) {
                    call_user_func_array($handler, array_merge([$request], $params));
                    return;
                }
            }
        }

        throw new NotFoundException("Endpoint {$requestMethod} {$requestUri} was not found.");
    }
}