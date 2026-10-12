<?php
// send_money.php
// Allows a user to send money to another user securely (with CSRF protection)
require_once 'includes/db_connect.php';
require_once 'includes/functions.php';
require_login();

$user_id = $_SESSION['user_id'];
$success = $error = '';

$csrf_token = get_csrf_token();

// Fetch all other users for dropdown
$stmt = $conn->prepare('SELECT id, username FROM users WHERE id != ? AND is_blocked = 0');
$stmt->bind_param('i', $user_id);
$stmt->execute();
$result = $stmt->get_result();
$users = $result->fetch_all(MYSQLI_ASSOC);
$stmt->close();

// Get sender's current balance
$stmt = $conn->prepare('SELECT balance FROM wallets WHERE user_id = ?');
$stmt->bind_param('i', $user_id);
$stmt->execute();
$stmt->bind_result($balance);
$stmt->fetch();
$stmt->close();
$balance = $balance ?? 0.00;

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    // CSRF check
    if (!is_valid_csrf_token($_POST['csrf_token'] ?? '')) {
        $error = 'Security check failed. Please refresh and try again.';
    } else {
        // Sanitize and validate inputs
        $receiver_id = intval($_POST['receiver_id'] ?? 0);
        $amount = floatval($_POST['amount'] ?? 0);
        if ($receiver_id <= 0 || $receiver_id === $user_id) {
            $error = 'You cannot send money to yourself.';
        } elseif ($amount <= 0) {
            $error = 'Enter a valid amount.';
        } else {
            $stmtLock = null;
            $stmtReceiver = null;
            $stmtDeduct = null;
            $stmtCredit = null;
            $stmtTx = null;

            $conn->begin_transaction();
            try {
                // Lock sender row so balance check and deduction are atomic.
                $stmtLock = $conn->prepare('SELECT balance FROM wallets WHERE user_id = ? FOR UPDATE');
                $stmtLock->bind_param('i', $user_id);
                $stmtLock->execute();
                $stmtLock->bind_result($currentBalance);
                if (!$stmtLock->fetch()) {
                    throw new RuntimeException('Wallet not found for sender.');
                }
                $stmtLock->close();

                if ($amount > (float)$currentBalance) {
                    throw new RuntimeException('Insufficient balance.');
                }

                // Ensure receiver exists and is active.
                $stmtReceiver = $conn->prepare('SELECT id FROM users WHERE id = ? AND is_blocked = 0');
                $stmtReceiver->bind_param('i', $receiver_id);
                $stmtReceiver->execute();
                $stmtReceiver->store_result();
                if ($stmtReceiver->num_rows !== 1) {
                    throw new RuntimeException('Recipient is not available.');
                }
                $stmtReceiver->close();

                $stmtDeduct = $conn->prepare('UPDATE wallets SET balance = balance - ? WHERE user_id = ?');
                $stmtDeduct->bind_param('di', $amount, $user_id);
                $stmtDeduct->execute();
                if ($stmtDeduct->affected_rows !== 1) {
                    throw new RuntimeException('Could not update sender wallet.');
                }
                $stmtDeduct->close();

                $stmtCredit = $conn->prepare('INSERT INTO wallets (user_id, balance) VALUES (?, ?) ON DUPLICATE KEY UPDATE balance = balance + VALUES(balance)');
                $stmtCredit->bind_param('id', $receiver_id, $amount);
                $stmtCredit->execute();
                $stmtCredit->close();

                $stmtTx = $conn->prepare('INSERT INTO transactions (sender_id, receiver_id, amount, transaction_type) VALUES (?, ?, ?, "transfer")');
                $stmtTx->bind_param('iid', $user_id, $receiver_id, $amount);
                $stmtTx->execute();
                $stmtTx->close();

                $conn->commit();
                $success = 'Money sent successfully!';
                $balance = (float)$currentBalance - $amount;
            } catch (Throwable $e) {
                $conn->rollback();
                if ($e instanceof RuntimeException) {
                    $error = $e->getMessage();
                } else {
                    $error = 'Transaction failed. Please try again.';
                }
            }

            if ($stmtLock instanceof mysqli_stmt) {
                $stmtLock->close();
            }
            if ($stmtReceiver instanceof mysqli_stmt) {
                $stmtReceiver->close();
            }
            if ($stmtDeduct instanceof mysqli_stmt) {
                $stmtDeduct->close();
            }
            if ($stmtCredit instanceof mysqli_stmt) {
                $stmtCredit->close();
            }
            if ($stmtTx instanceof mysqli_stmt) {
                $stmtTx->close();
            }
        }
    }
}
?>
<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">
    <title>Send Money - SecurePay</title>
    <link rel="stylesheet" href="assets/css/style.css">
</head>

<body class="page-finance page-send-money">
    <div class="finance-card">
        <img src="imgs/send-money.png" alt="SecurePay Logo" class="finance-logo" onerror="this.style.display='none'">
        <h2 class="finance-title">Send Money</h2>
        <p class="balance-note">Your Balance: <strong>-/<?php echo number_format($balance, 2); ?></strong></p>
        <?php if ($success): ?>
            <div class="alert success"><?php echo escape_html($success); ?></div>
        <?php elseif ($error): ?>
            <div class="alert error"><?php echo escape_html($error); ?></div>
        <?php endif; ?>
        <form method="post" action="" autocomplete="off" class="finance-form">
            <label for="receiver_id">Recipient</label>
            <select name="receiver_id" id="receiver_id" required>
                <option value="">-- Select User --</option>
                <?php foreach ($users as $u): ?>
                    <option value="<?php echo (int)$u['id']; ?>"><?php echo escape_html($u['username']); ?></option>
                <?php endforeach; ?>
            </select>
            <label for="amount">Amount (-/)</label>
            <input type="number" name="amount" id="amount" min="0.01" step="0.01" required>
            <input type="hidden" name="csrf_token" value="<?php echo escape_html($csrf_token); ?>">
            <button type="submit">Send Money</button>
        </form>
        <p class="back-link"><a href="dashboard/index.php">&larr; Back to Dashboard</a></p>
    </div>
</body>

</html>