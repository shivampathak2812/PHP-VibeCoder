<?php
declare(strict_types=1);

namespace Models;

use Core\Model;

class Task extends Model {
    public function getAll(): array {
        $sql = "
            SELECT t.*, u.name as assigned_name
            FROM tasks t
            LEFT JOIN users u ON t.assigned_to = u.id
            ORDER BY t.due_date ASC, t.id DESC
        ";
        return $this->db->query($sql)->fetchAll();
    }

    public function create(array $data): bool {
        $stmt = $this->db->prepare("
            INSERT INTO tasks (title, description, due_date, priority, status, assigned_to, related_type, related_id)
            VALUES (:title, :description, :due_date, :priority, :status, :assigned_to, :related_type, :related_id)
        ");
        return $stmt->execute([
            'title'        => $data['title'],
            'description'  => $data['description'] ?? null,
            'due_date'     => $data['due_date'],
            'priority'     => $data['priority'] ?? 'Medium',
            'status'       => $data['status'] ?? 'Pending',
            'assigned_to'  => !empty($data['assigned_to']) ? (int)$data['assigned_to'] : null,
            'related_type' => $data['related_type'] ?? null,
            'related_id'   => !empty($data['related_id']) ? (int)$data['related_id'] : null
        ]);
    }

    public function updateStatus(int $id, string $status): bool {
        $stmt = $this->db->prepare("UPDATE tasks SET status = :status, updated_at = NOW() WHERE id = :id");
        return $stmt->execute(['id' => $id, 'status' => $status]);
    }

    public function delete(int $id): bool {
        $stmt = $this->db->prepare("DELETE FROM tasks WHERE id = :id");
        return $stmt->execute(['id' => $id]);
    }

    public function getPendingCount(): int {
        return (int)$this->db->query("SELECT COUNT(*) FROM tasks WHERE status != 'Completed'")->fetchColumn();
    }
}