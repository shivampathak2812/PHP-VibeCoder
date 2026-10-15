<?php
declare(strict_types=1);

spl_autoload_register(function ($class) {
    $prefix = '';
    $base_dir = __DIR__ . '/../';

    $classPath = str_replace('\\', '/', $class);
    $file = $base_dir . $classPath . '.php';

    if (file_exists($file)) {
        require $file;
    }
});

use Controllers\AuthController;
use Controllers\DashboardController;
use Controllers\ContactController;
use Controllers\CompanyController;
use Controllers\DealController;
use Controllers\TaskController;
use Controllers\UserController;

$route = $_GET['route'] ?? 'dashboard';

switch ($route) {
    case 'login':
        $controller = new AuthController();
        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            $controller->login();
        } else {
            $controller->showLogin();
        }
        break;

    case 'logout':
        (new AuthController())->logout();
        break;

    case 'dashboard':
        (new DashboardController())->index();
        break;

    case 'contacts':
        (new ContactController())->index();
        break;

    case 'contacts/show':
        (new ContactController())->show();
        break;

    case 'contacts/create':
        (new ContactController())->create();
        break;

    case 'contacts/store':
        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            (new ContactController())->store();
        }
        break;

    case 'contacts/edit':
        (new ContactController())->edit();
        break;

    case 'contacts/update':
        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            (new ContactController())->update();
        }
        break;

    case 'contacts/delete':
        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            (new ContactController())->delete();
        }
        break;

    case 'contacts/add-note':
        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            (new ContactController())->addNote();
        }
        break;

    case 'companies':
        (new CompanyController())->index();
        break;

    case 'companies/create':
        (new CompanyController())->create();
        break;

    case 'companies/store':
        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            (new CompanyController())->store();
        }
        break;

    case 'companies/edit':
        (new CompanyController())->edit();
        break;

    case 'companies/update':
        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            (new CompanyController())->update();
        }
        break;

    case 'companies/delete':
        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            (new CompanyController())->delete();
        }
        break;

    case 'deals':
        (new DealController())->index();
        break;

    case 'deals/create':
        (new DealController())->create();
        break;

    case 'deals/store':
        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            (new DealController())->store();
        }
        break;

    case 'deals/edit':
        (new DealController())->edit();
        break;

    case 'deals/update':
        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            (new DealController())->update();
        }
        break;

    case 'deals/delete':
        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            (new DealController())->delete();
        }
        break;

    case 'tasks':
        (new TaskController())->index();
        break;

    case 'tasks/store':
        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            (new TaskController())->store();
        }
        break;

    case 'tasks/update-status':
        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            (new TaskController())->updateStatus();
        }
        break;

    case 'tasks/delete':
        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            (new TaskController())->delete();
        }
        break;

    case 'users':
        (new UserController())->index();
        break;

    case 'users/create':
        (new UserController())->create();
        break;

    case 'users/store':
        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            (new UserController())->store();
        }
        break;

    case 'users/delete':
        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            (new UserController())->delete();
        }
        break;

    default:
        header("HTTP/1.0 404 Not Found");
        echo "404 Page Not Found";
        break;
}