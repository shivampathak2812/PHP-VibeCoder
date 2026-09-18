<?php

declare(strict_types=1);

namespace App\Repositories;

use App\Models\Product;
use PDO;

class ProductRepository
{
    public function __construct(private readonly PDO $db) {}

    /**
     * @return Product[]
     */
    public function findAll(): array
    {
        $sql = "SELECT id, name, description, price, created_at FROM products ORDER BY id DESC";
        $stmt = $this->db::prepare($sql);
        $stmt = $this->db->prepare($sql);
        $stmt->execute();

        $products = [];
        while ($row = $stmt->fetch()) {
            $products[] = Product::fromArray($row);
        }

        return $products;
    }

    public function findById(int $id): ?Product
    {
        $sql = "SELECT id, name, description, price, created_at FROM products WHERE id = :id LIMIT 1";
        $stmt = $this->db->prepare($sql);
        $stmt->bindValue(':id', $id, PDO::PARAM_INT);
        $stmt->execute();

        $row = $stmt->fetch();
        if (!$row) {
            return null;
        }

        return Product::fromArray($row);
    }

    public function create(Product $product): Product
    {
        $sql = "INSERT INTO products (name, description, price) VALUES (:name, :description, :price)";
        $stmt = $this->db->prepare($sql);

        $stmt->bindValue(':name', $product->name, PDO::PARAM_STR);
        $stmt->bindValue(':description', $product->description, $product->description === null ? PDO::PARAM_NULL : PDO::PARAM_STR);
        $stmt->bindValue(':price', $product->price);
        $stmt->execute();

        $insertedId = (int) $this->db->lastInsertId();
        
        return $this->findById($insertedId);
    }

    public function update(Product $product): bool
    {
        $sql = "UPDATE products SET name = :name, description = :description, price = :price WHERE id = :id";
        $stmt = $this->db->prepare($sql);

        $stmt->bindValue(':id', $product->id, PDO::PARAM_INT);
        $stmt->bindValue(':name', $product->name, PDO::PARAM_STR);
        $stmt->bindValue(':description', $product->description, $product->description === null ? PDO::PARAM_NULL : PDO::PARAM_STR);
        $stmt->bindValue(':price', $product->price);

        return $stmt->execute();
    }

    public function delete(int $id): bool
    {
        $sql = "DELETE FROM products WHERE id = :id";
        $stmt = $this->db->prepare($sql);
        $stmt->bindValue(':id', $id, PDO::PARAM_INT);
        $stmt->execute();

        return $stmt->rowCount() > 0;
    }
}