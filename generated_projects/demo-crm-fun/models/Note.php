<?php
declare(strict_types=1);

namespace Models;

use Core\Model;

class Note extends Model {
    public function getByRelation(string $type, int $id): array {
        $sql = "
            SELECT n.*, u.name as author_name
            FROM notes n
            JOIN users u ON n.user_id = u.id
            WHERE n.related_type = :type AND n.related_id = :id
            ORDER BY n.created_at DESC
        ";
        $stmt = $this->db->prepare($sql);
        $stmt->execute(['type' => $type, 'id' => $id]);
        return $stmt->fetchAll();
    }

    public function create(int $userId, string $type, int $id, string $content): bool {
        $stmt = $this->db->prepare("
            INSERT INTO notes (user_id, related_type, related_id, content)
            VALUES (:user_id, :type, :id, :content)
        ");
        return $stmt->execute([
            'user_id' => $userId,
            'type'    => $type,
            'id'      => $id,
            'content' => $content
        ]);
    }
}