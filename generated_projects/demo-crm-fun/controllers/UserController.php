<?php
declare(strict_types=1);

namespace Controllers;

use Core\Controller;
use Core\Auth;
use Models\User;

class UserController extends Controller {
    public function index(): void {
        Auth::requireRoles(['admin']);
        $userModel = new User();
        $this->render('users/index', ['users' => $userModel->getAll()]);
    }

    public function create(): void {
        Auth::requireRoles(['admin']);
        $this->render('users/create');
    }

    public function store(): void {
        Auth::requireRoles(['admin']);
        $this->validateCsrf();

        $name = trim($_POST['name'] ?? '');
        $email = trim($_POST['email'] ?? '');
        $password = trim($_POST['password'] ?? '');
        $role = $_POST['role'] ?? 'agent';

        if (empty($name) || empty($email) || empty($password)) {
            $this->render('users/create', ['error' => 'All fields are required.']);
            return;
        }

        $userModel = new User();
        if ($userModel->findByEmail($email)) {
            $this->render('users/create', ['error' => 'An account with that email already exists.']);
            return;
        }

        $userModel->create($name, $email, $password, $role);
        $this->redirect('index.php?route=users');
    }

    public function delete(): void {
        Auth::requireRoles(['admin']);
        $this->validateCsrf();

        $id = (int)($_POST['id'] ?? 0);
        if ($id > 0 && $id !== Auth::id()) {
            $userModel = new User();
            $userModel->delete($id);
        }

        $this->redirect('index.php?route=users');
    }
}