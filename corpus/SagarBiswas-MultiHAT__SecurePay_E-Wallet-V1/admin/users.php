<?php
// Admin User Management for SecurePay
// Allows admin to view, reset password, block/unblock, and delete users.
require_once '../includes/db_connect.php';
require_once '../includes/functions.php';
require_admin();

// Helper: Format amounts
function formatAmount($amount)
{
    return number_format((float)$amount, 2, '.', '');
}

// Helper: Generate random password
function generatePassword($length = 8)
{
    $chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
    $pass = '';
    for ($i = 0; $i < $length; $i++) {
        $pass .= $chars[random_int(0, strlen($chars) - 1)];
    }
    return $pass;
}

// Alert message
$alert = '';
$csrf_token = get_csrf_token();

// Handle POST actions
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    if (!is_valid_csrf_token($_POST['csrf_token'] ?? '')) {
        $alert = '<div class="alert error">Security check failed. Please refresh and try again.</div>';
    }

    // Reset Password
    if (empty($alert) && isset($_POST['reset_password'])) {
        $user_id = intval($_POST['user_id']);
        // Generate and hash new password
        $new_pass = generatePassword();
        $hash = password_hash($new_pass, PASSWORD_DEFAULT);
        $stmt = $conn->prepare('UPDATE users SET password = ? WHERE id = ?');
        $stmt->bind_param('si', $hash, $user_id);
        if ($stmt->execute()) {
            $alert = '<div class="alert success text-center">Password reset! New password: <b class="generated-password">' . htmlspecialchars($new_pass) . '</b></div>';
        } else {
            $alert = '<div class="alert error">Failed to reset password.</div>';
        }
        $stmt->close();
    }
    // Block/Unblock User
    if (empty($alert) && isset($_POST['toggle_block'])) {
        $user_id = intval($_POST['user_id']);
        $is_admin = intval($_POST['is_admin']);
        $is_blocked = intval($_POST['is_blocked']);
        if ($is_admin || $user_id === (int)$_SESSION['user_id']) {
            $alert = '<div class="alert error">Cannot block/unblock admin accounts.</div>';
        } else {
            $new_state = $is_blocked ? 0 : 1;
            $stmt = $conn->prepare('UPDATE users SET is_blocked = ? WHERE id = ?');
            $stmt->bind_param('ii', $new_state, $user_id);
            if ($stmt->execute()) {
                $alert = '<div class="alert success">User ' . ($new_state ? 'blocked' : 'unblocked') . ' successfully.</div>';
            } else {
                $alert = '<div class="alert error">Failed to update block status.</div>';
            }
            $stmt->close();
        }
    }
    // Delete User
    if (empty($alert) && isset($_POST['delete_user'])) {
        $user_id = intval($_POST['user_id']);
        $is_admin = intval($_POST['is_admin']);
        if ($is_admin || $user_id === (int)$_SESSION['user_id']) {
            $alert = '<div class="alert error">Cannot delete admin accounts.</div>';
        } else {
            $conn->begin_transaction();
            try {
                // Delete transactions
                $stmt = $conn->prepare('DELETE FROM transactions WHERE sender_id = ? OR receiver_id = ?');
                $stmt->bind_param('ii', $user_id, $user_id);
                $stmt->execute();
                $stmt->close();

                // Delete wallet
                $stmt = $conn->prepare('DELETE FROM wallets WHERE user_id = ?');
                $stmt->bind_param('i', $user_id);
                $stmt->execute();
                $stmt->close();

                // Delete user
                $stmt = $conn->prepare('DELETE FROM users WHERE id = ?');
                $stmt->bind_param('i', $user_id);
                $stmt->execute();
                $stmt->close();

                $conn->commit();
                $alert = '<div class="alert success">User deleted successfully.</div>';
            } catch (Throwable $e) {
                $conn->rollback();
                $alert = '<div class="alert error">Failed to delete user.</div>';
            }
        }
    }
}

// Fetch all users with wallet balances

// Detect correct user name column
$userNameCol = 'full_name';
$sql = "SHOW COLUMNS FROM users LIKE 'full_name'";
$result = $conn->query($sql);
if ($result && $result->num_rows === 0) {
    $userNameCol = 'name';
    $sql = "SHOW COLUMNS FROM users LIKE 'name'";
    $result2 = $conn->query($sql);
    if ($result2 && $result2->num_rows === 0) {
        $userNameCol = 'username';
    }
}

// Detect if is_blocked column exists
$hasBlocked = true;
$sql = "SHOW COLUMNS FROM users LIKE 'is_blocked'";
$result = $conn->query($sql);
if ($result && $result->num_rows === 0) {
    $hasBlocked = false;
}

$sql = "SELECT u.id, u.$userNameCol, u.email, u.is_admin" . ($hasBlocked ? ", u.is_blocked" : "") . ", w.balance
        FROM users u
        LEFT JOIN wallets w ON u.id = w.user_id
        ORDER BY u.id ASC";
$result = $conn->query($sql);
$users = [];
if ($result) {
    while ($row = $result->fetch_assoc()) {
        $users[] = $row;
    }
}
?>
<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">
    <title>User Management | SecurePay Admin</title>
    <link rel="stylesheet" href="../assets/css/adminStyle.css">
    <script>
        // Confirm before deleting user
        function confirmDelete() {
            return confirm('Are you sure you want to delete this user? This action cannot be undone.');
        }
    </script>
</head>

<body class="page-admin-users">
    <div class="logo-wrap">
        <img src="../imgs/SecurePAY.png" alt="SecurePay Logo" class="logo-img">
        <div class="brand-title">SecurePay</div>
    </div>
    <div class="container">
        <div class="topbar">
            <h1>╰(..:: User Management ::..)╯</h1>
            <nav class="topbar-nav">
                <a href="index.php" class="topbar-link">Dashboard</a>
                <a href="logout.php" class="topbar-link topbar-link-danger">Logout</a>
            </nav>
        </div>
        <?php if ($alert) echo $alert; ?>
        <table class="user-table">
            <thead>
                <tr>
                    <th>User ID</th>
                    <th>Full Name</th>
                    <th>Email</th>
                    <th>Wallet Balance ($)</th>
                    <th>Admin?</th>
                    <th>Blocked?</th>
                    <th class="actions-cell">Actions</th>
                </tr>
            </thead>
            <tbody>
                <?php foreach ($users as $user): ?>
                    <tr>
                        <td><?php echo isset($user['id']) ? $user['id'] : '-'; ?></td>
                        <td><?php
                            if (isset($user['full_name'])) echo htmlspecialchars($user['full_name']);
                            elseif (isset($user['name'])) echo htmlspecialchars($user['name']);
                            elseif (isset($user['username'])) echo htmlspecialchars($user['username']);
                            else echo '-';
                            ?></td>
                        <td><?php echo isset($user['email']) ? htmlspecialchars($user['email']) : '-'; ?></td>
                        <td><?php echo isset($user['balance']) ? formatAmount($user['balance']) : '0.00'; ?></td>
                        <td><?php echo isset($user['is_admin']) && $user['is_admin'] ? 'Yes' : 'No'; ?></td>
                        <td><?php echo isset($user['is_blocked']) ? ($user['is_blocked'] ? 'Yes' : 'No') : '-'; ?></td>
                        <td class="actions-cell">
                            <!-- Reset Password Button -->
                            <form method="post" class="inline-form">
                                <input type="hidden" name="csrf_token" value="<?php echo escape_html($csrf_token); ?>">
                                <input type="hidden" name="user_id" value="<?php echo isset($user['id']) ? $user['id'] : ''; ?>">
                                <button type="submit" name="reset_password" class="action-btn reset-btn">Reset Password</button>
                            </form>
                            <!-- Block/Unblock Button -->
                            <form method="post" class="inline-form">
                                <input type="hidden" name="csrf_token" value="<?php echo escape_html($csrf_token); ?>">
                                <input type="hidden" name="user_id" value="<?php echo isset($user['id']) ? $user['id'] : ''; ?>">
                                <input type="hidden" name="is_admin" value="<?php echo isset($user['is_admin']) ? $user['is_admin'] : 0; ?>">
                                <input type="hidden" name="is_blocked" value="<?php echo isset($user['is_blocked']) ? $user['is_blocked'] : 0; ?>">
                                <button type="submit" name="toggle_block" class="action-btn block-btn">
                                    <?php echo isset($user['is_blocked']) ? ($user['is_blocked'] ? 'Unblock' : 'Block') : 'Block'; ?>
                                </button>
                            </form>
                            <!-- Delete Button -->
                            <form method="post" class="inline-form" onsubmit="return confirmDelete();">
                                <input type="hidden" name="csrf_token" value="<?php echo escape_html($csrf_token); ?>">
                                <input type="hidden" name="user_id" value="<?php echo isset($user['id']) ? $user['id'] : ''; ?>">
                                <input type="hidden" name="is_admin" value="<?php echo isset($user['is_admin']) ? $user['is_admin'] : 0; ?>">
                                <button type="submit" name="delete_user" class="action-btn delete-btn">Delete</button>
                            </form>
                        </td>
                    </tr>
                <?php endforeach; ?>
                <?php if (empty($users)): ?>
                    <tr>
                        <td colspan="7">No users found.</td>
                    </tr>
                <?php endif; ?>
            </tbody>
        </table>
    </div>
</body>

</html>