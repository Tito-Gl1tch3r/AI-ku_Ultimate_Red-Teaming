<?php
// db_connect.php
// Centralized MySQLi connection with environment-driven configuration.

mysqli_report(MYSQLI_REPORT_ERROR | MYSQLI_REPORT_STRICT);

$envFile = dirname(__DIR__) . '/.env';
if (is_readable($envFile)) {
    $lines = file($envFile, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES);
    foreach ($lines as $line) {
        $trimmed = trim($line);
        if ($trimmed === '' || strpos($trimmed, '#') === 0) {
            continue;
        }

        $parts = explode('=', $trimmed, 2);
        if (count($parts) !== 2) {
            continue;
        }

        $name = trim($parts[0]);
        $value = trim($parts[1]);
        $value = trim($value, " \t\n\r\0\x0B\"'");

        if ($name !== '' && getenv($name) === false) {
            putenv($name . '=' . $value);
            $_ENV[$name] = $value;
        }
    }
}

$host = getenv('SECUREPAY_DB_HOST') ?: '127.0.0.1';
$db   = getenv('SECUREPAY_DB_NAME') ?: 'securepay_db';
$user = getenv('SECUREPAY_DB_USER') ?: 'root';
$pass = getenv('SECUREPAY_DB_PASS') ?: '';
$port = (int)(getenv('SECUREPAY_DB_PORT') ?: 3306);

try {
    $conn = new mysqli($host, $user, $pass, $db, $port);
    $conn->set_charset('utf8mb4');
} catch (mysqli_sql_exception $e) {
    $isDebug = (getenv('SECUREPAY_APP_ENV') === 'development');
    if ($isDebug) {
        die('Database connection failed: ' . $e->getMessage());
    }
    http_response_code(500);
    die('Database connection failed. Please contact the administrator.');
}
