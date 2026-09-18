<?php

declare(strict_types=1);

namespace App\Repositories;

use App\Models\User;
use PDO;

class UserRepository
{
    public function __construct(
        private readonly PDO $db
    ) {}

    /**
     * Find user by email address.
     */
    public function findByEmail(string $email): ?User
    {
        $sql = 'SELECT id, name, email, password, created_at, updated_at FROM users WHERE email = :email LIMIT 1';
        $stmt = $this->db->prepare($sql);
        $stmt->execute(['email' => $email]);

        $row = $stmt->fetch();
        if (!$row) {
            return null;
        }

        return User::fromArray($row);
    }

    /**
     * Find user by ID.
     */
    public function findById(int $id): ?User
    {
        $sql = 'SELECT id, name, email, password, created_at, updated_at FROM users WHERE id = :id LIMIT 1';
        $stmt = $this->db->prepare($sql);
        $stmt->execute(['id' => $id]);

        $row = $stmt->fetch();
        if (!$row) {
            return null;
        }

        return User::fromArray($row);
    }

    /**
     * Create a new user record.
     */
    public function create(User $user): User
    {
        $sql = 'INSERT INTO users (name, email, password) VALUES (:name, :email, :password)';
        $stmt = $this->db->prepare($sql);
        
        $stmt->execute([
            'name' => $user->name,
            'email' => $user->email,
            'password' => $user->password,
        ]);

        $lastId = (int) $this->db->lastInsertId();
        
        return $this->findById($lastId) ?? new User(
            id: $lastId,
            name: $user->name,
            email: $user->email,
            password: $user->password
        );
    }
}