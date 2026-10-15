<?php
declare(strict_types=1);

namespace Models;

use Core\Model;

class Company extends Model {
    public function getAll(): array {
        $stmt = $this->db->query("SELECT * FROM companies ORDER BY created_at DESC");
        return $stmt->fetchAll();
    }

    public function findById(int $id): ?array {
        $stmt = $this->db->prepare("SELECT * FROM companies WHERE id = :id");
        $stmt->execute(['id' => $id]);
        $res = $stmt->fetch();
        return $res ?: null;
    }

    public function create(array $data): bool {
        $stmt = $this->db->prepare("
            INSERT INTO companies (name, industry, phone, email, website, address)
            VALUES (:name, :industry, :phone, :email, :website, :address)
        ");
        return $stmt->execute([
            'name'     => $data['name'],
            'industry' => $data['industry'] ?? null,
            'phone'    => $data['phone'] ?? null,
            'email'    => $data['email'] ?? null,
            'website'  => $data['website'] ?? null,
            'address'  => $data['address'] ?? null
        ]);
    }

    public function update(int $id, array $data): bool {
        $stmt = $this->db->prepare("
            UPDATE companies 
            SET name = :name, industry = :industry, phone = :phone, email = :email, website = :website, address = :address, updated_at = NOW()
            WHERE id = :id
        ");
        return $stmt->execute([
            'id'       => $id,
            'name'     => $data['name'],
            'industry' => $data['industry'] ?? null,
            'phone'    => $data['phone'] ?? null,
            'email'    => $data['email'] ?? null,
            'website'  => $data['website'] ?? null,
            'address'  => $data['address'] ?? null
        ]);
    }

    public function delete(int $id): bool {
        $stmt = $this->db->prepare("DELETE FROM companies WHERE id = :id");
        return $stmt->execute(['id' => $id]);
    }

    public function count(): int {
        return (int)$this->db->query("SELECT COUNT(*) FROM companies")->fetchColumn();
    }
}