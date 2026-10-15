<?php
declare(strict_types=1);

namespace Models;

use Core\Model;

class Deal extends Model {
    public function getAll(): array {
        $sql = "
            SELECT d.*, 
                   CONCAT(c.first_name, ' ', c.last_name) as contact_name,
                   cmp.name as company_name,
                   u.name as owner_name
            FROM deals d
            LEFT JOIN contacts c ON d.contact_id = c.id
            LEFT JOIN companies cmp ON d.company_id = cmp.id
            LEFT JOIN users u ON d.user_id = u.id
            ORDER BY d.created_at DESC
        ";
        return $this->db->query($sql)->fetchAll();
    }

    public function findById(int $id): ?array {
        $sql = "
            SELECT d.*, 
                   CONCAT(c.first_name, ' ', c.last_name) as contact_name,
                   cmp.name as company_name,
                   u.name as owner_name
            FROM deals d
            LEFT JOIN contacts c ON d.contact_id = c.id
            LEFT JOIN companies cmp ON d.company_id = cmp.id
            LEFT JOIN users u ON d.user_id = u.id
            WHERE d.id = :id
        ";
        $stmt = $this->db->prepare($sql);
        $stmt->execute(['id' => $id]);
        $res = $stmt->fetch();
        return $res ?: null;
    }

    public function create(array $data): bool {
        $stmt = $this->db->prepare("
            INSERT INTO deals (title, amount, stage, expected_close_date, contact_id, company_id, user_id)
            VALUES (:title, :amount, :stage, :expected_close_date, :contact_id, :company_id, :user_id)
        ");
        return $stmt->execute([
            'title'               => $data['title'],
            'amount'              => (float)($data['amount'] ?? 0.00),
            'stage'               => $data['stage'] ?? 'New',
            'expected_close_date' => !empty($data['expected_close_date']) ? $data['expected_close_date'] : null,
            'contact_id'          => !empty($data['contact_id']) ? (int)$data['contact_id'] : null,
            'company_id'          => !empty($data['company_id']) ? (int)$data['company_id'] : null,
            'user_id'             => (int)$data['user_id']
        ]);
    }

    public function update(int $id, array $data): bool {
        $stmt = $this->db->prepare("
            UPDATE deals
            SET title = :title, amount = :amount, stage = :stage,
                expected_close_date = :expected_close_date, contact_id = :contact_id,
                company_id = :company_id, updated_at = NOW()
            WHERE id = :id
        ");
        return $stmt->execute([
            'id'                  => $id,
            'title'               => $data['title'],
            'amount'              => (float)($data['amount'] ?? 0.00),
            'stage'               => $data['stage'],
            'expected_close_date' => !empty($data['expected_close_date']) ? $data['expected_close_date'] : null,
            'contact_id'          => !empty($data['contact_id']) ? (int)$data['contact_id'] : null,
            'company_id'          => !empty($data['company_id']) ? (int)$data['company_id'] : null
        ]);
    }

    public function delete(int $id): bool {
        $stmt = $this->db->prepare("DELETE FROM deals WHERE id = :id");
        return $stmt->execute(['id' => $id]);
    }

    public function getTotalPipelineValue(): float {
        return (float)$this->db->query("SELECT SUM(amount) FROM deals WHERE stage != 'Lost'")->fetchColumn();
    }

    public function countByStage(): array {
        $stmt = $this->db->query("SELECT stage, COUNT(*) as count, SUM(amount) as total_amount FROM deals GROUP BY stage");
        return $stmt->fetchAll();
    }
}