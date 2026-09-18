<?php

declare(strict_types=1);

namespace App\Services;

use App\Models\User;
use App\Repositories\UserRepository;
use InvalidArgumentException;
use RuntimeException;

class AuthService
{
    public function __construct(
        private readonly UserRepository $userRepository
    ) {}

    /**
     * Register a new user.
     */
    public function register(array $data): User
    {
        $errors = $this->validateRegistrationData($data);
        if (!empty($errors)) {
            throw new InvalidArgumentException(json_encode($errors) ?: 'Validation error');
        }

        $email = trim((string) $data['email']);
        $existingUser = $this->userRepository->findByEmail($email);
        if ($existingUser !== null) {
            throw new RuntimeException('Email address is already registered');
        }

        $hashedPassword = password_hash((string) $data['password'], PASSWORD_DEFAULT);

        $newUser = new User(
            id: null,
            name: trim((string) $data['name']),
            email: $email,
            password: $hashedPassword
        );

        return $this->userRepository->create($newUser);
    }

    /**
     * Authenticate a user by credentials.
     */
    public function login(array $data): User
    {
        $email = trim((string) ($data['email'] ?? ''));
        $password = (string) ($data['password'] ?? '');

        if (empty($email) || empty($password)) {
            throw new InvalidArgumentException(json_encode(['auth' => 'Email and password are required']) ?: '');
        }

        $user = $this->userRepository->findByEmail($email);
        if ($user === null) {
            throw new InvalidArgumentException(json_encode(['auth' => 'Invalid email or password']) ?: '');
        }

        if (!password_verify($password, $user->password)) {
            throw new InvalidArgumentException(json_encode(['auth' => 'Invalid email or password']) ?: '');
        }

        return $user;
    }

    /**
     * Validate registration request parameters.
     */
    private function validateRegistrationData(array $data): array
    {
        $errors = [];

        $name = trim((string) ($data['name'] ?? ''));
        $email = trim((string) ($data['email'] ?? ''));
        $password = (string) ($data['password'] ?? '');

        if ($name === '') {
            $errors['name'] = 'Name is required';
        } elseif (mb_strlen($name) > 100) {
            $errors['name'] = 'Name must not exceed 100 characters';
        }

        if ($email === '') {
            $errors['email'] = 'Email is required';
        } elseif (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
            $errors['email'] = 'Provide a valid email address';
        } elseif (mb_strlen($email) > 255) {
            $errors['email'] = 'Email must not exceed 255 characters';
        }

        if ($password === '') {
            $errors['password'] = 'Password is required';
        } elseif (mb_strlen($password) < 8) {
            $errors['password'] = 'Password must be at least 8 characters long';
        }

        return $errors;
    }
}