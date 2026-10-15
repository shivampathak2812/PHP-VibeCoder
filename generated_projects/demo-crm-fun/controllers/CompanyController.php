<?php
declare(strict_types=1);

namespace Controllers;

use Core\Controller;
use Core\Auth;
use Models\Company;

class CompanyController extends Controller {
    public function index(): void {
        Auth::requireAuth();
        $companyModel = new Company();
        $this->render('companies/index', ['companies' => $companyModel->getAll()]);
    }

    public function create(): void {
        Auth::requireAuth();
        $this->render('companies/create');
    }

    public function store(): void {
        Auth::requireAuth();
        $this->validateCsrf();

        $name = trim($_POST['name'] ?? '');
        if (empty($name)) {
            $this->render('companies/create', ['error' => 'Company name is required.']);
            return;
        }

        $companyModel = new Company();
        $companyModel->create([
            'name'     => $name,
            'industry' => trim($_POST['industry'] ?? ''),
            'phone'    => trim($_POST['phone'] ?? ''),
            'email'    => trim($_POST['email'] ?? ''),
            'website'  => trim($_POST['website'] ?? ''),
            'address'  => trim($_POST['address'] ?? '')
        ]);

        $this->redirect('index.php?route=companies');
    }

    public function edit(): void {
        Auth::requireAuth();
        $id = (int)($_GET['id'] ?? 0);
        $companyModel = new Company();
        $company = $companyModel->findById($id);

        if (!$company) {
            $this->redirect('index.php?route=companies');
        }

        $this->render('companies/edit', ['company' => $company]);
    }

    public function update(): void {
        Auth::requireAuth();
        $this->validateCsrf();

        $id = (int)($_POST['id'] ?? 0);
        $name = trim($_POST['name'] ?? '');

        if ($id <= 0 || empty($name)) {
            $this->redirect('index.php?route=companies');
        }

        $companyModel = new Company();
        $companyModel->update($id, [
            'name'     => $name,
            'industry' => trim($_POST['industry'] ?? ''),
            'phone'    => trim($_POST['phone'] ?? ''),
            'email'    => trim($_POST['email'] ?? ''),
            'website'  => trim($_POST['website'] ?? ''),
            'address'  => trim($_POST['address'] ?? '')
        ]);

        $this->redirect('index.php?route=companies');
    }

    public function delete(): void {
        Auth::requireRoles(['admin', 'manager']);
        $this->validateCsrf();

        $id = (int)($_POST['id'] ?? 0);
        if ($id > 0) {
            $companyModel = new Company();
            $companyModel->delete($id);
        }

        $this->redirect('index.php?route=companies');
    }
}