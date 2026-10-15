<?php
use Core\Auth;
$currentUser = Auth::user();
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ProCRM - Customer Relationship Management</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css" rel="stylesheet">
    <link rel="stylesheet" href="css/style.css">
</head>
<body>
<?php if ($currentUser): ?>
<nav class="navbar navbar-expand-lg navbar-dark bg-dark sticky-top">
    <div class="container-fluid">
        <a class="navbar-brand fw-bold text-primary" href="index.php?route=dashboard">
            <i class="bi bi-diagram-3-fill me-1"></i> ProCRM
        </a>
        <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarMain">
            <span class="navbar-toggler-icon"></span>
        </button>
        <div class="collapse navbar-collapse" id="navbarMain">
            <ul class="navbar-nav me-auto mb-2 mb-lg-0">
                <li class="nav-item">
                    <a class="nav-link" href="index.php?route=dashboard"><i class="bi bi-speedometer2"></i> Dashboard</a>
                </li>
                <li class="nav-item">
                    <a class="nav-link" href="index.php?route=contacts"><i class="bi bi-people"></i> Contacts</a>
                </li>
                <li class="nav-item">
                    <a class="nav-link" href="index.php?route=companies"><i class="bi bi-building"></i> Companies</a>
                </li>
                <li class="nav-item">
                    <a class="nav-link" href="index.php?route=deals"><i class="bi bi-cash-stack"></i> Pipeline Deals</a>
                </li>
                <li class="nav-item">
                    <a class="nav-link" href="index.php?route=tasks"><i class="bi bi-check2-square"></i> Tasks</a>
                </li>
                <?php if ($currentUser['role'] === 'admin'): ?>
                <li class="nav-item">
                    <a class="nav-link text-warning" href="index.php?route=users"><i class="bi bi-shield-lock"></i> Users</a>
                </li>
                <?php endif; ?>
            </ul>
            <div class="d-flex align-items-center text-light">
                <span class="me-3 small"><i class="bi bi-person-circle"></i> <?= htmlspecialchars($currentUser['name']) ?> (<?= htmlspecialchars(strtoupper($currentUser['role'])) ?>)</span>
                <a href="index.php?route=logout" class="btn btn-outline-danger btn-sm"><i class="bi bi-box-arrow-right"></i> Logout</a>
            </div>
        </div>
    </div>
</nav>
<?php endif; ?>
<div class="container-fluid py-4">