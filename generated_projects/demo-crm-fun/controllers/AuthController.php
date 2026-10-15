<?php
declare(strict_types=1);

namespace Controllers;

use Core\Controller;
use Core\Auth;
use Models\User;

class AuthController extends Controller {
    public function showLogin(): void {
        if (Auth::check()) {
            $this->redirect('index.php?route=dashboard');
        }
        $this->render('auth/login');
    }

    public function login(): void {
        $this->validateCsrf();

        $email = trim($_POST['email'] ?? '');
        $password = trim($_POST['password'] ?? '');

        if (empty($email) || empty($password)) {
            $this->render('auth/login', ['error' => 'Please provide both email and password.']);
            return;
        }

        $userModel = new User();
        $user = $userModel->findByEmail($email);

        if ($user && password_verify($password, $user['password_hash'])) {
            Auth::login($user);
            $this->redirect('index.php?route=dashboard');
        } else {
            $this->render('auth/login', ['error' => 'Invalid email or password credentials.']);
        }
    }

    public function logout(): void {
        Auth::logout();
        $this->redirect('index.php?route=login');
    }
}