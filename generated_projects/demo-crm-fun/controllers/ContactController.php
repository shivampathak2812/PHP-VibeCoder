<?php
declare(strict_types=1);

namespace Controllers;

use Core\Controller;
use Core\Auth;
use Models\Contact;
use Models\Company;
use Models\User;
use Models\Note;

class ContactController extends Controller {
    public function index(): void {
        Auth::requireAuth();
        $contactModel = new Contact();
        $this->render('contacts/index', ['contacts' => $contactModel->getAll()]);
    }

    public function show(): void {
        Auth::requireAuth();
        $id = (int)($_GET['id'] ?? 0);

        $contactModel = new Contact();
        $contact = $contactModel->findById($id);

        if (!$contact) {
            $this->redirect('index.php?route=contacts');
        }

        $noteModel = new Note();
        $notes = $noteModel->getByRelation('contact', $id);

        $this->render('contacts/show', [
            'contact' => $contact,
            'notes'   => $notes
        ]);
    }

    public function create(): void {
        Auth::requireAuth();
        $companyModel = new Company();
        $userModel = new User();

        $this->render('contacts/create', [
            'companies' => $companyModel->getAll(),
            'users'     => $userModel->getAll()
        ]);
    }

    public function store(): void {
        Auth::requireAuth();
        $this->validateCsrf();

        $firstName = trim($_POST['first_name'] ?? '');
        $lastName = trim($_POST['last_name'] ?? '');

        if (empty($firstName) || empty($lastName)) {
            $companyModel = new Company();
            $userModel = new User();
            $this->render('contacts/create', [
                'error'     => 'First and last names are required.',
                'companies' => $companyModel->getAll(),
                'users'     => $userModel->getAll()
            ]);
            return;
        }

        $contactModel = new Contact();
        $contactModel->create([
            'first_name'  => $firstName,
            'last_name'   => $lastName,
            'email'       => trim($_POST['email'] ?? ''),
            'phone'       => trim($_POST['phone'] ?? ''),
            'position'    => trim($_POST['position'] ?? ''),
            'company_id'  => $_POST['company_id'] ?? null,
            'assigned_to' => $_POST['assigned_to'] ?? null,
            'status'      => $_POST['status'] ?? 'lead'
        ]);

        $this->redirect('index.php?route=contacts');
    }

    public function edit(): void {
        Auth::requireAuth();
        $id = (int)($_GET['id'] ?? 0);

        $contactModel = new Contact();
        $contact = $contactModel->findById($id);

        if (!$contact) {
            $this->redirect('index.php?route=contacts');
        }

        $companyModel = new Company();
        $userModel = new User();

        $this->render('contacts/edit', [
            'contact'   => $contact,
            'companies' => $companyModel->getAll(),
            'users'     => $userModel->getAll()
        ]);
    }

    public function update(): void {
        Auth::requireAuth();
        $this->validateCsrf();

        $id = (int)($_POST['id'] ?? 0);
        $firstName = trim($_POST['first_name'] ?? '');
        $lastName = trim($_POST['last_name'] ?? '');

        if ($id <= 0 || empty($firstName) || empty($lastName)) {
            $this->redirect('index.php?route=contacts');
        }

        $contactModel = new Contact();
        $contactModel->update($id, [
            'first_name'  => $firstName,
            'last_name'   => $lastName,
            'email'       => trim($_POST['email'] ?? ''),
            'phone'       => trim($_POST['phone'] ?? ''),
            'position'    => trim($_POST['position'] ?? ''),
            'company_id'  => $_POST['company_id'] ?? null,
            'assigned_to' => $_POST['assigned_to'] ?? null,
            'status'      => $_POST['status'] ?? 'lead'
        ]);

        $this->redirect('index.php?route=contacts');
    }

    public function delete(): void {
        Auth::requireRoles(['admin', 'manager']);
        $this->validateCsrf();

        $id = (int)($_POST['id'] ?? 0);
        if ($id > 0) {
            $contactModel = new Contact();
            $contactModel->delete($id);
        }

        $this->redirect('index.php?route=contacts');
    }

    public function addNote(): void {
        Auth::requireAuth();
        $this->validateCsrf();

        $contactId = (int)($_POST['contact_id'] ?? 0);
        $content = trim($_POST['content'] ?? '');

        if ($contactId > 0 && !empty($content)) {
            $noteModel = new Note();
            $noteModel->create(Auth::id(), 'contact', $contactId, $content);
        }

        $this->redirect('index.php?route=contacts/show&id=' . $contactId);
    }
}