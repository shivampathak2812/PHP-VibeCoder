<?php

declare(strict_types=1);

require_once __DIR__ . '/../src/Database.php';
require_once __DIR__ . '/../src/Csrf.php';
require_once __DIR__ . '/../src/Auth.php';

use App\Auth;

$auth = new Auth();
$auth->logout();

header('Location: login.php');
exit;