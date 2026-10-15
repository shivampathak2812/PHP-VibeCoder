<?php
declare(strict_types=1);

namespace Controllers;

use Core\Controller;
use Core\Auth;
use Models\Deal;
use Models\Contact;
use Models\Company;

class DealController extends Controller {
    public function index(): void {
        Auth::requireAuth();
        $dealModel = new Deal();
        $config = require __DIR__ . '/../config/app.php';

        $this->render('deals/index', [
            'deals'       => $dealModel->getAll(),
            'deal_stages' => $config['deal_stages']
        ]);
    }

    public function create(): void {
        Auth::requireAuth();
        $contactModel = new Contact();
        $companyModel = new Company();
        $config = require __DIR__ . '/../config/app.php';

        $this->render('deals/create', [
            'contacts'    => $contactModel->getAll(),
            'companies'   => $companyModel->getAll(),
            'deal_stages' => $config['deal_stages']
        ]);
    }

    public function store(): void {
        Auth::requireAuth();
        $this->validateCsrf();

        $title = trim($_POST['title'] ?? '');
        $amount = (float)($_POST['amount'] ?? 0);

        if (empty($title)) {
            $this->redirect('index.php?route=deals/create');
            return;
        }

        $dealModel = new Deal();
        $dealModel->create([
            'title'               => $title,
            'amount'              => $amount,
            'stage'               => $_POST['stage'] ?? 'New',
            'expected_close_date' => $_POST['expected_close_date'] ?? null,
            'contact_id'          => $_POST['contact_id'] ?? null,
            'company_id'          => $_POST['company_id'] ?? null,
            'user_id'             => Auth::id()
        ]);

        $this->redirect('index.php?route=deals');
    }

    public function edit(): void {
        Auth::requireAuth();
        $id = (int)($_GET['id'] ?? 0);

        $dealModel = new Deal();
        $deal = $dealModel->findById($id);

        if (!$deal) {
            $this->redirect('index.php?route=deals');
        }

        $contactModel = new Contact();
        $companyModel = new Company();
        $config = require __DIR__ . '/../config/app.php';

        $this->render('deals/edit', [
            'deal'        => $deal,
            'contacts'    => $contactModel->getAll(),
            'companies'   => $companyModel->getAll(),
            'deal_stages' => $config['deal_stages']
        ]);
    }

    public function update(): void {
        Auth::requireAuth();
        $this->validateCsrf();

        $id = (int)($_POST['id'] ?? 0);
        $title = trim($_POST['title'] ?? '');

        if ($id <= 0 || empty($title)) {
            $this->redirect('index.php?route=deals');
        }

        $dealModel = new Deal();
        $dealModel->update($id, [
            'title'               => $title,
            'amount'              => (float)($_POST['amount'] ?? 0),
            'stage'               => $_POST['stage'] ?? 'New',
            'expected_close_date' => $_POST['expected_close_date'] ?? null,
            'contact_id'          => $_POST['contact_id'] ?? null,
            'company_id'          => $_POST['company_id'] ?? null
        ]);

        $this->redirect('index.php?route=deals');
    }

    public function delete(): void {
        Auth::requireRoles(['admin', 'manager']);
        $this->validateCsrf();

        $id = (int)($_POST['id'] ?? 0);
        if ($id > 0) {
            $dealModel = new Deal();
            $dealModel->delete($id);
        }

        $this->redirect('index.php?route=deals');
    }
}