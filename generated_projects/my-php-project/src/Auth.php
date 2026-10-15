<?php

declare(strict_types=1);

namespace App;

use PDO;
use InvalidArgumentException;
use RuntimeException;

class Auth
{
    public function __construct(private PDO $db)
    {
    }

    public function register(string $fullName, string $email, string $password): bool
    {
        $fullName = trim($fullName);
        $email = trim($email);

        if (empty($fullName)) {
            throw new InvalidArgumentException("Full Name is required.");
        }

        if (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
            throw new InvalidArgumentException("Please enter a valid email address.");
        }

        if (strlen($password) < 8) {
            throw new InvalidArgumentException("Password must be at least 8 characters long.");
        }

        $stmt = $this->db->prepare("SELECT id FROM users WHERE email = :email LIMIT 1");
        $stmt->execute(['email' => $email]);
        if ($stmt->fetch()) {
            throw new RuntimeException("An account with this email address already exists.");
        }

        $hashedPassword = password_hash($password, PASSWORD_BCRYPT, ['cost' => 12]);

        $stmt = $this->db->prepare(
            "INSERT INTO users (full_name, email, password, created_at) VALUES (:full_name, :email, :password, NOW())"
        );

        return $stmt->execute([
            'full_name' => $fullName,
            'email'     => $email,
            'password'  => $hashedPassword,
        ]);
    }

    public function login(string $email, string $password): bool
    {
        $email = trim($email);

        if (empty($email) || empty($password)) {
            throw new InvalidArgumentException("Please fill in all required fields.");
        }

        $stmt = $this->db->prepare("SELECT id, full_name, email, password FROM users WHERE email = :email LIMIT 1");
        $stmt->execute(['email' => $email]);
        $user = $stmt->fetch();

        if ($user && password_verify($password, $user['password'])) {
            Session::start();
            session_regenerate_id(true);

            Session::set('user_id', (int)$user['id']);
            Session::set('user_name', $user['full_name']);
            Session::set('user_email', $user['email']);

            return true;
        }

        return false;
    }

    public function isLoggedIn(): bool
    {
        return Session::get('user_id') !== null;
    }

    public function logout(): void
    {
        Session::destroy();
    }

    public function getCurrentUser(): ?array
    {
        if (!$this->isLoggedIn()) {
            return null;
        }

        return [
            'id'    => Session::get('user_id'),
            'name'  => Session::get('user_name'),
            'email' => Session::get('user_email'),
        ];
    }
}