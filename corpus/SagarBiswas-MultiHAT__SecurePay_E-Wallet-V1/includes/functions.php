<?php
// functions.php
// Common reusable functions for session management, auth guards, validation, and formatting.

if (session_status() === PHP_SESSION_NONE) {
    $isHttps = (!empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off');
    ini_set('session.use_strict_mode', '1');
    ini_set('session.use_only_cookies', '1');
    session_set_cookie_params([
        'lifetime' => 0,
        'path' => '/',
        'secure' => $isHttps,
        'httponly' => true,
        'samesite' => 'Lax',
    ]);
    session_start();
}

function sanitize_input($data)
{
    return trim(stripslashes((string)$data));
}

function escape_html($value)
{
    return htmlspecialchars((string)$value, ENT_QUOTES, 'UTF-8');
}

function is_logged_in()
{
    return isset($_SESSION['user_id']);
}

function get_project_base_path()
{
    $script = str_replace('\\', '/', $_SERVER['SCRIPT_NAME'] ?? '');
    $markers = ['/admin/', '/auth/', '/dashboard/', '/cyberlab/'];

    foreach ($markers as $marker) {
        $pos = strpos($script, $marker);
        if ($pos !== false) {
            return rtrim(substr($script, 0, $pos), '/');
        }
    }

    $dir = dirname($script);
    if ($dir === '/' || $dir === '\\') {
        return '';
    }

    return rtrim($dir, '/');
}

function build_project_url($relativePath)
{
    $base = get_project_base_path();
    return ($base ? $base : '') . '/' . ltrim($relativePath, '/');
}

function redirect_to($relativePath)
{
    header('Location: ' . build_project_url($relativePath));
    exit();
}

function logout_user()
{
    $_SESSION = [];

    if (ini_get('session.use_cookies')) {
        $params = session_get_cookie_params();
        setcookie(session_name(), '', [
            'expires' => time() - 42000,
            'path' => $params['path'] ?? '/',
            'domain' => $params['domain'] ?? '',
            'secure' => $params['secure'] ?? false,
            'httponly' => $params['httponly'] ?? true,
            'samesite' => $params['samesite'] ?? 'Lax',
        ]);
    }

    session_unset();
    session_destroy();
}

function logout_and_redirect($relativePath)
{
    logout_user();
    redirect_to($relativePath);
}

function get_area_login_path()
{
    $scriptName = str_replace('\\', '/', $_SERVER['SCRIPT_NAME'] ?? '');
    $isAdminArea = strpos($scriptName, '/admin/') !== false;
    return $isAdminArea ? 'admin/login.php' : 'auth/login.php';
}

function require_login()
{
    $timeoutSeconds = 300;
    $loginPath = get_area_login_path();

    if (!is_logged_in()) {
        redirect_to($loginPath);
    }

    if (isset($_SESSION['last_activity']) && (time() - (int)$_SESSION['last_activity'] > $timeoutSeconds)) {
        session_unset();
        session_destroy();
        redirect_to($loginPath . '?timeout=1');
    }

    $_SESSION['last_activity'] = time();
}

function require_admin()
{
    require_login();
    if (empty($_SESSION['is_admin'])) {
        redirect_to('dashboard/index.php');
    }
}

function require_non_admin()
{
    require_login();
    if (!empty($_SESSION['is_admin'])) {
        redirect_to('dashboard/index.php');
    }
}

function get_csrf_token()
{
    if (empty($_SESSION['csrf_token']) || !is_string($_SESSION['csrf_token'])) {
        $_SESSION['csrf_token'] = bin2hex(random_bytes(32));
    }
    return $_SESSION['csrf_token'];
}

function is_valid_csrf_token($token)
{
    if (!is_string($token) || !isset($_SESSION['csrf_token'])) {
        return false;
    }
    return hash_equals($_SESSION['csrf_token'], $token);
}

function validate_csrf_token($token)
{
    return is_valid_csrf_token($token);
}

function is_valid_ymd_date($value)
{
    if (!is_string($value)) {
        return false;
    }
    $date = DateTime::createFromFormat('Y-m-d', $value);
    return $date instanceof DateTime && $date->format('Y-m-d') === $value;
}

function format_money($amount)
{
    return number_format((float)$amount, 2);
}

function format_transaction_amount($transaction, $currentUserId)
{
    $type = $transaction['transaction_type'] ?? '';
    $amount = format_money($transaction['amount'] ?? 0);

    if ($type === 'add_fund') {
        return '(+) -/' . $amount;
    }

    if ($type === 'withdraw') {
        return '(-) -/' . $amount;
    }

    if ($type === 'transfer') {
        if ((int)($transaction['sender_id'] ?? 0) === (int)$currentUserId) {
            return '(-) -/' . $amount;
        }
        return '(+) -/' . $amount;
    }

    if (empty($transaction['receiver_name']) && (int)($transaction['sender_id'] ?? 0) === (int)$currentUserId) {
        return '(-) -/' . $amount;
    }

    return '-/' . $amount;
}

function format_transaction_counterparty($transaction, $currentUserId)
{
    $type = $transaction['transaction_type'] ?? '';

    if ($type === 'add_fund') {
        return 'Self';
    }

    if ($type === 'withdraw' || (empty($transaction['receiver_name']) && (int)($transaction['sender_id'] ?? 0) === (int)$currentUserId)) {
        return '-';
    }

    if ((int)($transaction['sender_id'] ?? 0) === (int)$currentUserId) {
        return 'To: ' . escape_html($transaction['receiver_name'] ?? 'Unknown');
    }

    return 'From: ' . escape_html($transaction['sender_name'] ?? 'Unknown');
}

function transactions_support_withdraw($conn)
{
    static $cachedSupport = null;
    if ($cachedSupport !== null) {
        return $cachedSupport;
    }

    $result = $conn->query("SHOW COLUMNS FROM transactions LIKE 'transaction_type'");
    if (!$result || $result->num_rows === 0) {
        $cachedSupport = false;
        return false;
    }

    $column = $result->fetch_assoc();
    $typeDefinition = strtolower((string)($column['Type'] ?? ''));
    $cachedSupport = strpos($typeDefinition, "'withdraw'") !== false;

    return $cachedSupport;
}
