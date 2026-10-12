<?php
// withdraw.php
require_once 'includes/db_connect.php';
require_once 'includes/functions.php';
require_non_admin();

$user_id = $_SESSION['user_id'];
$errors = [];
$success = '';
$csrf_token = get_csrf_token();

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    if (!is_valid_csrf_token($_POST['csrf_token'] ?? '')) {
        $errors[] = 'Security check failed. Please refresh and try again.';
    } elseif (!transactions_support_withdraw($conn)) {
        $errors[] = 'Withdraw transactions are not enabled. Please run add_withdraw_transaction_type.sql and try again.';
    } else {
        $amount = floatval($_POST['amount'] ?? 0);
        if ($amount <= 0) {
            $errors[] = 'Please enter a valid withdrawal amount.';
        } else {
            $stmtBalance = null;
            $stmtUpdate = null;
            $stmtInsert = null;

            $conn->begin_transaction();
            try {
                // Lock wallet row to prevent concurrent double-withdraw.
                $stmtBalance = $conn->prepare('SELECT balance FROM wallets WHERE user_id = ? FOR UPDATE');
                $stmtBalance->bind_param('i', $user_id);
                $stmtBalance->execute();
                $stmtBalance->bind_result($currentBalance);

                if (!$stmtBalance->fetch()) {
                    throw new RuntimeException('Wallet not found.');
                }
                $stmtBalance->close();

                if ($amount > (float)$currentBalance) {
                    throw new RuntimeException('Insufficient balance.');
                }

                $stmtUpdate = $conn->prepare('UPDATE wallets SET balance = balance - ? WHERE user_id = ?');
                $stmtUpdate->bind_param('di', $amount, $user_id);
                $stmtUpdate->execute();
                if ($stmtUpdate->affected_rows !== 1) {
                    throw new RuntimeException('Could not update wallet balance.');
                }
                $stmtUpdate->close();

                $stmtInsert = $conn->prepare('INSERT INTO transactions (sender_id, receiver_id, amount, transaction_type) VALUES (?, NULL, ?, "withdraw")');
                $stmtInsert->bind_param('id', $user_id, $amount);
                $stmtInsert->execute();
                $stmtInsert->close();

                $conn->commit();
                $success = 'Withdrawal successful!';
            } catch (Throwable $e) {
                $conn->rollback();
                if ($e instanceof RuntimeException) {
                    $errors[] = $e->getMessage();
                } else {
                    $errors[] = 'Withdrawal failed. Please try again.';
                }
            }

            if ($stmtBalance instanceof mysqli_stmt) {
                $stmtBalance->close();
            }
            if ($stmtUpdate instanceof mysqli_stmt) {
                $stmtUpdate->close();
            }
            if ($stmtInsert instanceof mysqli_stmt) {
                $stmtInsert->close();
            }
        }
    }
}
?>
<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">
    <title>Withdraw - SecurePay</title>
    <link rel="stylesheet" href="assets/css/style.css">
</head>

<body class="page-finance page-withdraw">
    <div class="finance-card">
        <div class="card-header">
            <h2>Withdraw Funds</h2>
        </div>
        <?php if ($errors): ?>
            <div class="alert error">
                <?php foreach ($errors as $e) echo '<p>' . escape_html($e) . '</p>'; ?>
            </div>
        <?php endif; ?>
        <?php if ($success): ?>
            <div class="alert success">
                <p><?php echo escape_html($success); ?></p>
            </div>
        <?php endif; ?>
        <form method="post" action="" autocomplete="off" class="finance-form">
            <input type="hidden" name="csrf_token" value="<?php echo escape_html($csrf_token); ?>">
            <label for="amount">Amount</label>
            <input type="number" id="amount" name="amount" step="0.01" min="0.01" required placeholder="Enter amount to withdraw">
            <button type="submit">Withdraw</button>
        </form>
        <div class="back-link">
            <a href="dashboard/index.php">&larr; Back to Dashboard</a>
        </div>
    </div>
</body>

</html>