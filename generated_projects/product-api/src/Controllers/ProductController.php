<?php

declare(strict_types=1);

namespace App\Controllers;

use App\Database\Connection;
use App\Exceptions\NotFoundException;
use App\Exceptions\ValidationException;
use App\Http\Request;
use App\Http\Response;
use App\Models\Product;
use App\Repositories\ProductRepository;

class ProductController
{
    private ProductRepository $repository;

    public function __construct(?ProductRepository $repository = null)
    {
        $this->repository = $repository ?? new ProductRepository(Connection::getConnection());
    }

    public function index(Request $request): void
    {
        $products = $this->repository->findAll();

        Response::json([
            'status' => 'success',
            'data'   => $products,
        ], 200);
    }

    public function show(Request $request, string $id): void
    {
        $product = $this->findProductOrFail((int) $id);

        Response::json([
            'status' => 'success',
            'data'   => $product,
        ], 200);
    }

    public function store(Request $request): void
    {
        $data = $request->getBody();
        $this->validateProductData($data);

        $product = Product::fromArray($data);
        $createdProduct = $this->repository->create($product);

        Response::json([
            'status'  => 'success',
            'message' => 'Product created successfully',
            'data'    => $createdProduct,
        ], 201);
    }

    public function update(Request $request, string $id): void
    {
        $productId = (int) $id;
        $existingProduct = $this->findProductOrFail($productId);

        $data = $request->getBody();
        $this->validateProductData($data, isUpdate: true);

        $name = isset($data['name']) ? (string) $data['name'] : $existingProduct->name;
        $description = array_key_exists('description', $data) ? $data['description'] : $existingProduct->description;
        $price = isset($data['price']) ? (float) $data['price'] : $existingProduct->price;

        $updatedProduct = new Product(
            id: $productId,
            name: $name,
            description: $description !== null ? (string) $description : null,
            price: $price,
            createdAt: $existingProduct->createdAt
        );

        $this->repository->update($updatedProduct);

        Response::json([
            'status'  => 'success',
            'message' => 'Product updated successfully',
            'data'    => $updatedProduct,
        ], 200);
    }

    public function destroy(Request $request, string $id): void
    {
        $productId = (int) $id;
        $deleted = $this->repository->delete($productId);

        if (!$deleted) {
            throw new NotFoundException("Product with ID {$productId} not found.");
        }

        Response::json([
            'status'  => 'success',
            'message' => 'Product deleted successfully',
        ], 200);
    }

    private function findProductOrFail(int $id): Product
    {
        $product = $this->repository->findById($id);

        if (!$product) {
            throw new NotFoundException("Product with ID {$id} not found.");
        }

        return $product;
    }

    private function validateProductData(array $data, bool $isUpdate = false): void
    {
        $errors = [];

        if (!$isUpdate || array_key_exists('name', $data)) {
            if (!isset($data['name']) || trim((string) $data['name']) === '') {
                $errors['name'] = 'Product name is required and cannot be empty.';
            }
        }

        if (!$isUpdate || array_key_exists('price', $data)) {
            if (!isset($data['price']) || !is_numeric($data['price']) || (float) $data['price'] < 0) {
                $errors['price'] = 'Product price must be a valid non-negative number.';
            }
        }

        if (!empty($errors)) {
            throw new ValidationException($errors);
        }
    }
}