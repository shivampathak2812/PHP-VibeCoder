<?php

declare(strict_types=1);

namespace App\Models;

use JsonSerializable;

class Product implements JsonSerializable
{
    public function __construct(
        public readonly ?int $id,
        public string $name,
        public ?string $description,
        public float $price,
        public readonly ?string $createdAt = null
    ) {}

    public static function fromArray(array $data): self
    {
        return new self(
            id: isset($data['id']) ? (int) $data['id'] : null,
            name: (string) ($data['name'] ?? ''),
            description: isset($data['description']) ? (string) $data['description'] : null,
            price: (float) ($data['price'] ?? 0.0),
            createdAt: isset($data['created_at']) ? (string) $data['created_at'] : null
        );
    }

    public function toArray(): array
    {
        return [
            'id'          => $this->id,
            'name'        => $this->name,
            'description' => $this->description,
            'price'       => $this->price,
            'created_at'  => $this->createdAt,
        ];
    }

    public function jsonSerialize(): array
    {
        return $this->toArray();
    }
}