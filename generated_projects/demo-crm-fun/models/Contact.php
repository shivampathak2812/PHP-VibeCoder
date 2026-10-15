<?php
declare(strict_types=1);

namespace Models;

use Core\Model;

class Contact extends Model {
    public function getAll(): array {
        $sql = "
            SELECT c.*, cmp.name as company_name, u.name as assigned_user
            FROM contacts c
            LEFT JOIN companies cmp ON c.company_id = cmp.id
            LEFT JOIN users u ON c.assigned_to = u.id
            ORDER BY c.created_at DESC
        ";
        return $this->db->query($sql)->fetchAll();
    }

    public function findById(int $id): ?array {
        $sql = "
            SELECT c.*, cmp.name as company_name, u.name as assigned_user
            FROM contacts c
            LEFT JOIN companies cmp ON c.company_id = cmp.id
            LEFT JOIN users u ON c.assigned_to = u.id
            WHERE c.id = :id
        ";
        $stmt = $this->db->prepare($sql);
        $stmt->execute(['id' => $id]);
        $res = $stmt->fetch();
        return $res ?: null;
    }

    public function create(array $data): bool {
        $stmt = $this->db->prepare("
            INSERT INTO contacts (first_name, last_name, email, phone, position, company_id, assigned_to, status)
            VALUES (:first_name, :last_name, :email, :phone, :position, :company_id, :assigned_to, :status)
        ");
        return $stmt->execute([
            'first_name' => $data['first_name'],
            'last_name'  => $data['last_name'],
            'email'      => $data['email'] ?? null,
            'phone'      => $data['phone'] ?? null,
            'position'   => $data['position'] ?? null,
            'company_id' => !empty($data['company_id']) ? (int)$data['company_id'] : null,
            'assigned_to'=> !empty($data['assigned_to']) ? (int)$data['assigned_to'] : null,
            'status'     => $data['status'] ?? 'lead'
        ]);
    }

    public function update(int $id, array $data): bool {
        $stmt = $this->db->prepare("
            UPDATE contacts
            SET first_name = :first_name, last_name = :last_name, email = :email, phone = :phone,
                position = :position, company_id = :company_id, assigned_to = :assigned_to,
                status = :status, updated_at = NOW()
            WHERE id = :id
        ");
        return $stmt->execute([
            'id'         => $id,
            'first_name' => $data['first_name'],
            'last_name'  => $data['last_name'],
            'email'      => $data['email'] ?? null,
            'phone'      => $data['phone'] ?? null,
            'position'   => $data['position'] ?? null,
            'company_id' => !empty($data['company_id']) ? (int)$data['company_id'] : null,
            'assigned_to'=> !empty($data['assigned_to']) ? (int)$data['assigned_to'] : null,
            'status'     => $data['status'] ?? 'lead'
        ]);
    }

    public function delete(int $id): bool {
        $stmt = $this->db->prepare("DELETE FROM contacts WHERE id = :id");
        return $stmt->execute(['id' => $id]);
    }

    public function count(): int {
        return (int)$this->db->query("SELECT COUNT(*) FROM contacts")->fetchColumn();
    }
}