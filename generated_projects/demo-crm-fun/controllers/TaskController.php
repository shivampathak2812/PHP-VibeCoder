<?php
declare(strict_types=1);

namespace Controllers;

use Core\Controller;
use Core\Auth;
use Models\Task;
use Models\User;

class TaskController extends Controller {
    public function index(): void {
        Auth::requireAuth();
        $taskModel = new Task();
        $userModel = new User();

        $this->render('tasks/index', [
            'tasks' => $taskModel->getAll(),
            'users' => $userModel->getAll()
        ]);
    }

    public function store(): void {
        Auth::requireAuth();
        $this->validateCsrf();

        $title = trim($_POST['title'] ?? '');
        $dueDate = trim($_POST['due_date'] ?? '');

        if (!empty($title) && !empty($dueDate)) {
            $taskModel = new Task();
            $taskModel->create([
                'title'        => $title,
                'description'  => trim($_POST['description'] ?? ''),
                'due_date'     => $dueDate,
                'priority'     => $_POST['priority'] ?? 'Medium',
                'status'       => 'Pending',
                'assigned_to'  => $_POST['assigned_to'] ?? Auth::id(),
                'related_type' => null,
                'related_id'   => null
            ]);
        }

        $this->redirect('index.php?route=tasks');
    }

    public function updateStatus(): void {
        Auth::requireAuth();
        $this->validateCsrf();

        $id = (int)($_POST['id'] ?? 0);
        $status = $_POST['status'] ?? 'Pending';

        if ($id > 0) {
            $taskModel = new Task();
            $taskModel->updateStatus($id, $status);
        }

        $this->redirect('index.php?route=tasks');
    }

    public function delete(): void {
        Auth::requireRoles(['admin', 'manager']);
        $this->validateCsrf();

        $id = (int)($_POST['id'] ?? 0);
        if ($id > 0) {
            $taskModel = new Task();
            $taskModel->delete($id);
        }

        $this->redirect('index.php?route=tasks');
    }
}