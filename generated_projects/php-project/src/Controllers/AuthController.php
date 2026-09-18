<?php

declare(strict_types=1);

namespace App\Controllers;

use App\Http\Request;
use App\Http\Response;
use App\Services\AuthService;
use InvalidArgumentException;
use RuntimeException;

class AuthController
{
    public function __construct(
        private readonly AuthService $authService
    ) {}

    /**
     * Endpoint handler: POST /api/register
     */
    public function register(Request $request): void
    {
        try {
            $user = $this->authService->register($request->getBody());
            Response::success('User registered successfully', $user->toArray(), 201);
        } catch (InvalidArgumentException $e) {
            $errors = json_decode($e->getMessage(), true);
            if (is_array($errors)) {
                Response::error('Validation failed', $errors, 422);
            } else {
                Response::error($e->getMessage(), [], 400);
            }
        } catch (RuntimeException $e) {
            Response::error($e->getMessage(), [], 409);
        }
    }

    /**
     * Endpoint handler: POST /api/login
     */
    public function login(Request $request): void
    {
        try {
            $user = $this->authService->login($request->getBody());
            Response::success('Login successful', [
                'user' => $user->toArray(),
            ], 200);
        } catch (InvalidArgumentException $e) {
            $errors = json_decode($e->getMessage(), true);
            if (is_array($errors)) {
                Response::error('Authentication failed', $errors, 401);
            } else {
                Response::error($e->getMessage(), [], 401);
            }
        }
    }
}