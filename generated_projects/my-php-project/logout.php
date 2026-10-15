<?php

declare(strict_types=1);

require_once __DIR__ . '/src/Session.php';

use App\Session;

Session::start();
Session::destroy();

header("Location: index.php");
exit();