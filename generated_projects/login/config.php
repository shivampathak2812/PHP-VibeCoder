<?php
/**
 * Global Configuration Settings & Safe Session Initialization
 */

// Error reporting settings - Hide details from production output, log them instead
error_reporting(E_ALL);
ini_set('display_errors', 0);
ini_set('log_errors', 1);

// Database Connection Parameters
define('DB_HOST', '127.0.0.1');
define('DB_PORT', '3306');
define('DB_NAME', 'secure_login_db');
define('DB_USER', 'root');
define('DB_PASS', '');

// Session Hardening Rules
ini_set('session.use_only_cookies', 1);
ini_set('session.use_trans_sid', 0);

if (session_status() === PHP_SESSION_NONE) {
    session_start([
        'cookie_lifetime' => 0, // Session cookie dies when browser closes
        'cookie_path' => '/',
        'cookie_httponly' => true, // Prevents JavaScript access to cookies
        'cookie_secure' => isset($_SERVER['HTTPS']) && $_SERVER['HTTPS'] === 'on', // Transmit only over secure links
        'cookie_samesite' => 'Strict' // Mitigates CSRF vulnerabilities
    ]);
}