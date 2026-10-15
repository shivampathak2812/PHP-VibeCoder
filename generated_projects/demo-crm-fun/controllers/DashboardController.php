<?php
declare(strict_types=1);

namespace Controllers;

use Core\Controller;
use Core\Auth;
use Models\Contact;
use Models\Company;
use Models\Deal;
use Models\Task;

class DashboardController extends Controller {
    public function index(): void {
        Auth::requireAuth();

        $contactModel = new Contact();
        $companyModel = new Company();
        $dealModel = new Deal();
        $taskModel = new Task();

        $data = [
            'total_contacts' => $contactModel->count(),
            'total_companies' => $companyModel->count(),
            'pipeline_value' => $dealModel->getTotalPipelineValue(),
            'pending_tasks' => $taskModel->getPendingCount(),
            'deal_stages' => $dealModel->countByStage(),
            'recent_deals' => array_slice($dealModel->getAll(), 0, 5)
        ];

        $this->render('dashboard/index', $data);
    }
}