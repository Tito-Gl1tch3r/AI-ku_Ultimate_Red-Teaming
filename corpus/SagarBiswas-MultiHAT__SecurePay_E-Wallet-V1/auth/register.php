<?php
// register.php
// User registration form and logic
require_once '../includes/db_connect.php';
require_once '../includes/functions.php';

if (isset($_SESSION['user_id'])) {
    if (!empty($_SESSION['is_admin'])) {
        redirect_to('admin/index.php');
    }
    redirect_to('dashboard/index.php');
}

$username = $email = $password = $confirm_password = '';
$errors = [];
$success = '';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    if (!validate_csrf_token($_POST['csrf_token'] ?? null)) {
        $errors[] = 'Invalid request. Please refresh the page and try again.';
    }

    // Sanitize and validate inputs
    $username = sanitize_input($_POST['username'] ?? '');
    $email = sanitize_input($_POST['email'] ?? '');
    $password = $_POST['password'] ?? '';
    $confirm_password = $_POST['confirm_password'] ?? '';

    if (empty($username) || strlen($username) < 3) {
        $errors[] = 'Username must be at least 3 characters.';
    }
    if (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
        $errors[] = 'Invalid email address.';
    }
    if (strlen($password) < 6) {
        $errors[] = 'Password must be at least 6 characters.';
    }
    if ($password !== $confirm_password) {
        $errors[] = 'Passwords do not match.';
    }

    // Check if email already exists
    if (empty($errors)) {
        $stmt = $conn->prepare('SELECT id FROM users WHERE email = ?');
        $stmt->bind_param('s', $email);
        $stmt->execute();
        $stmt->store_result();
        if ($stmt->num_rows > 0) {
            $errors[] = 'Email already registered.';
        }
        $stmt->close();
    }

    // Register user
    if (empty($errors)) {
        $hashed_password = password_hash($password, PASSWORD_DEFAULT);
        $stmt = $conn->prepare('INSERT INTO users (username, email, password) VALUES (?, ?, ?)');
        $stmt->bind_param('sss', $username, $email, $hashed_password);
        if ($stmt->execute()) {
            $success = 'Registration successful!';
            $username = $email = '';
        } else {
            $errors[] = 'Registration failed. Please try again.';
        }
        $stmt->close();
    }
}
?>
<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">
    <title>Register - SecurePay</title>
    <link rel="stylesheet" href="../assets/css/style.css">
</head>

<body class="page-auth">
    <div class="container">
        <div class="logo">
            <img src="../imgs/SecurePAY.png" alt="SecurePay Logo" onerror="this.style.display='none'">
        </div>
        <div class="register-title">Create your SecurePay account</div>
        <?php if ($errors): ?>
            <div class="alert error">
                <?php foreach ($errors as $e) echo '<p>' . escape_html($e) . '</p>'; ?>
            </div>
        <?php endif; ?>
        <?php if ($success): ?>
            <div class="alert success"><?php echo escape_html($success); ?></div>
            <div class="login-link">
                <span class="auth-muted">Proceed to</span> <a href="login.php">Login</a>.
            </div>
        <?php endif; ?>
        <form method="post" action="" autocomplete="off" onsubmit="return validateForm()" class="auth-form">
            <input type="hidden" name="csrf_token" value="<?php echo escape_html(get_csrf_token()); ?>">
            <label for="username">Username</label>
            <input type="text" id="username" name="username" value="<?php echo escape_html($username); ?>" required minlength="3" placeholder="Enter your username">
            <label for="email">Email</label>
            <input type="email" id="email" name="email" value="<?php echo escape_html($email); ?>" required placeholder="Enter your email">
            <label for="password">Password</label>
            <input type="password" id="password" name="password" required minlength="6" placeholder="Enter your password">
            <label for="confirm_password">Confirm Password</label>
            <input type="password" id="confirm_password" name="confirm_password" required minlength="6" placeholder="Confirm your password">
            <button type="submit">Register</button>
        </form>
        <div class="login-link">
            <br>
            <span class="auth-muted">Already have an account?</span> <a href="login.php">Login here</a>.
        </div>
    </div>
    <script src="../assets/js/validate.js"></script>
</body>

</html>