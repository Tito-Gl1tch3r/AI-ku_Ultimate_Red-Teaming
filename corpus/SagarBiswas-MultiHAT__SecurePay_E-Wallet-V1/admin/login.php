<?php
// Admin Login for SecurePay
require_once '../includes/db_connect.php';
require_once '../includes/functions.php';

$email = '';
$errors = [];
$csrf_token = get_csrf_token();

if (isset($_SESSION['user_id'])) {
    if (!empty($_SESSION['is_admin'])) {
        redirect_to('admin/index.php');
    }
    redirect_to('dashboard/index.php');
}

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $email = trim($_POST['email'] ?? '');

    if (!is_valid_csrf_token($_POST['csrf_token'] ?? '')) {
        $errors[] = 'Security check failed. Please refresh and try again.';
    }

    $password = $_POST['password'] ?? '';
    if (empty($errors)) {
        // Find admin user by email
        $sql = "SELECT id, username, password, is_admin, is_blocked, failed_attempts, lock_until FROM users WHERE email = ?";
        $stmt = $conn->prepare($sql);
        $stmt->bind_param('s', $email);
        $stmt->execute();
        $stmt->bind_result($id, $username, $hash, $is_admin, $is_blocked, $failed_attempts, $lock_until);
        if ($stmt->fetch()) {
            // Clear expired locks
            if (!empty($lock_until) && strtotime($lock_until) <= time()) {
                $clear = $conn->prepare('UPDATE users SET failed_attempts = 0, lock_until = NULL WHERE id = ?');
                $clear->bind_param('i', $id);
                $clear->execute();
                $clear->close();
                $failed_attempts = 0;
                $lock_until = null;
            }

            // Enforce lock if active
            if (!empty($lock_until) && strtotime($lock_until) > time()) {
                $remaining = max(0, strtotime($lock_until) - time());
                $minutes = floor($remaining / 60);
                $seconds = $remaining % 60;
                $errors[] = 'Too many failed attempts. Try again in ' . ($minutes > 0 ? $minutes . 'm ' : '') . $seconds . 's.';
            } elseif ((int)$is_blocked === 1) {
                $errors[] = 'Your account has been blocked. Please contact support.';
            } elseif (!$is_admin) {
                $errors[] = 'Invalid admin credentials.';
            } elseif (password_verify($password, $hash)) {
                // Reset counters on success
                $reset = $conn->prepare('UPDATE users SET failed_attempts = 0, lock_until = NULL WHERE id = ?');
                $reset->bind_param('i', $id);
                $reset->execute();
                $reset->close();

                session_regenerate_id(true);
                $_SESSION['user_id'] = $id;
                $_SESSION['username'] = $username;
                $_SESSION['is_admin'] = true;
                $_SESSION['last_activity'] = time();
                redirect_to('admin/index.php');
            } else {
                // increment attempts and maybe lock
                $failed_attempts = (int)$failed_attempts + 1;
                if ($failed_attempts >= 3) {
                    $lock_until_dt = date('Y-m-d H:i:s', time() + 3 * 60);
                    $upd = $conn->prepare('UPDATE users SET failed_attempts = ?, lock_until = ? WHERE id = ?');
                    $upd->bind_param('isi', $failed_attempts, $lock_until_dt, $id);
                    $upd->execute();
                    $upd->close();
                    $errors[] = 'Incorrect password. Admin access locked for 3 minutes.';
                } else {
                    $upd = $conn->prepare('UPDATE users SET failed_attempts = ? WHERE id = ?');
                    $upd->bind_param('ii', $failed_attempts, $id);
                    $upd->execute();
                    $upd->close();
                    $remaining_attempts = 3 - $failed_attempts;
                    $errors[] = 'Incorrect password. Attempts left: ' . $remaining_attempts . '.';
                }
            }
        } else {
            $errors[] = 'Invalid admin credentials.';
        }
        $stmt->close();
    }
}
?>
<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">
    <title>Admin Login | SecurePay</title>
    <link rel="stylesheet" href="../assets/css/adminStyle.css">
</head>

<body class="page-admin-auth">
    <div class="container">
        <div class="logo">
            <img src="../imgs/SecurePAY.png" alt="SecurePay Logo" onerror="this.style.display='none'">
        </div>
        <div class="login-title">Admin Login</div>
        <?php if ($errors): ?>
            <div class="alert error">
                <?php foreach ($errors as $error): ?>
                    <p><?php echo escape_html($error); ?></p>
                <?php endforeach; ?>
            </div>
        <?php endif; ?>
        <form method="post" class="admin-auth-form">
            <input type="hidden" name="csrf_token" value="<?php echo escape_html($csrf_token); ?>">
            <label for="email">Email</label>
            <input type="email" name="email" id="email" value="<?php echo escape_html($email); ?>" required autofocus placeholder="Enter your email">
            <label for="password">Password</label>
            <input type="password" name="password" id="password" required placeholder="Enter your password">
            <button type="submit">Login</button>
        </form>
    </div>
</body>

</html>