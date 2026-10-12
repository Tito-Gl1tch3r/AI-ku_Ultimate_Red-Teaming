<?php
// login.php
// User login form and logic
require_once '../includes/db_connect.php';
require_once '../includes/functions.php';

$email = $password = '';
$errors = [];
$csrf_token = get_csrf_token();

if (isset($_SESSION['user_id'])) {
    if (!empty($_SESSION['is_admin'])) {
        redirect_to('admin/index.php');
    }
    redirect_to('dashboard/index.php');
}

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    if (!is_valid_csrf_token($_POST['csrf_token'] ?? '')) {
        $errors[] = 'Security check failed. Please refresh and try again.';
    }

    $email = sanitize_input($_POST['email'] ?? '');
    // ?? used to provide a default value(empty string) if the key doesn't exist;
    $password = $_POST['password'] ?? '';

    if (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
        $errors[] = 'Invalid email address.';
    }
    if (empty($password)) {
        $errors[] = 'Password is required.';
    }

    if (empty($errors)) {
        $stmt = $conn->prepare('SELECT id, username, password, is_admin, is_blocked, failed_attempts, lock_until FROM users WHERE email = ?');
        $stmt->bind_param('s', $email);
        $stmt->execute();
        $stmt->store_result();
        if ($stmt->num_rows === 1) {
            $stmt->bind_result($id, $username, $hashed_password, $is_admin, $is_blocked, $failed_attempts, $lock_until);
            $stmt->fetch();

            // If lock expired, clear it eagerly
            if (!empty($lock_until) && strtotime($lock_until) <= time()) {
                $clear = $conn->prepare('UPDATE users SET failed_attempts = 0, lock_until = NULL WHERE id = ?');
                $clear->bind_param('i', $id);
                $clear->execute();
                $clear->close();
                $failed_attempts = 0;
                $lock_until = null;
            }

            // If still locked, show remaining time
            if (!empty($lock_until) && strtotime($lock_until) > time()) {
                $remaining = max(0, strtotime($lock_until) - time());
                $minutes = floor($remaining / 60);
                $seconds = $remaining % 60;
                $errors[] = 'Too many failed attempts. Try again in ' . ($minutes > 0 ? $minutes . 'm ' : '') . $seconds . 's.';
            } elseif ($is_blocked == 1) {
                $errors[] = 'Your account has been blocked. Please contact support.';
            } elseif (password_verify($password, $hashed_password)) {
                // Successful login: reset counters
                $reset = $conn->prepare('UPDATE users SET failed_attempts = 0, lock_until = NULL WHERE id = ?');
                $reset->bind_param('i', $id);
                $reset->execute();
                $reset->close();

                // Set session variables
                session_regenerate_id(true);
                $_SESSION['user_id'] = $id;
                $_SESSION['username'] = $username;
                $_SESSION['is_admin'] = $is_admin ? true : false;
                $_SESSION['last_activity'] = time();
                if ($is_admin) {
                    redirect_to('admin/index.php');
                }
                redirect_to('dashboard/index.php');
            } else {
                // Wrong password: increment attempts and maybe lock
                $failed_attempts = (int)$failed_attempts + 1;
                if ($failed_attempts >= 3) {
                    $lock_until_dt = date('Y-m-d H:i:s', time() + 3 * 60);
                    $upd = $conn->prepare('UPDATE users SET failed_attempts = ?, lock_until = ? WHERE id = ?');
                    $upd->bind_param('isi', $failed_attempts, $lock_until_dt, $id);
                    $upd->execute();
                    $upd->close();
                    $errors[] = 'Incorrect password. Account locked for 3 minutes.';
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
            $errors[] = 'Invalid email or password.';
        }
        $stmt->close();
    }
}
?>
<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">
    <title>Login - SecurePay</title>
    <link rel="stylesheet" href="../assets/css/style.css">
</head>

<body class="page-auth">
    <div class="container">
        <div class="logo">
            <img src="../imgs/SecurePAY.png" alt="SecurePay Logo" onerror="this.style.display='none'">
        </div>
        <div class="login-title">Sign in to SecurePay</div>
        <?php if ($errors): ?>
            <div class="alert error">
                <?php foreach ($errors as $e) echo '<p>' . escape_html($e) . '</p>'; ?>
            </div>
        <?php endif; ?>
        <form method="post" action="" autocomplete="off" onsubmit="return validateLogin()" class="auth-form">
            <input type="hidden" name="csrf_token" value="<?php echo escape_html($csrf_token); ?>">
            <label for="email">Email</label>
            <input type="email" id="email" name="email" value="<?php echo escape_html($email); ?>" required placeholder="Enter your email">
            <label for="password">Password</label>
            <input type="password" id="password" name="password" required placeholder="Enter your password">
            <button type="submit">Login</button>
        </form>
        <div class="register-link">
            <br>
            <span class="auth-muted">Don't have an account?</span> <a href="register.php">Register here</a>.
        </div>
    </div>
    <script src="../assets/js/validate.js"></script>
</body>

</html>