<?php
// add_funds.php
// Allows a logged-in user to add funds to their wallet
require_once 'includes/db_connect.php';
require_once 'includes/functions.php';
require_admin();

$user_id = $_SESSION['user_id'];
$success = $error = '';
$csrf_token = get_csrf_token();

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    if (!is_valid_csrf_token($_POST['csrf_token'] ?? '')) {
        $error = 'Security check failed. Please refresh and try again.';
    } else {
        // Sanitize and validate amount
        $amount = floatval($_POST['amount'] ?? 0);
        if ($amount <= 0) {
            $error = 'Please enter a valid amount.';
        } else {
            // Start transaction for atomicity
            $conn->begin_transaction();
            try {
                // Update wallet balance (insert if not exists)
                $stmt = $conn->prepare('INSERT INTO wallets (user_id, balance) VALUES (?, ?) ON DUPLICATE KEY UPDATE balance = balance + VALUES(balance)');
                $stmt->bind_param('id', $user_id, $amount);
                $stmt->execute();
                $stmt->close();

                // Insert transaction record
                $stmt2 = $conn->prepare('INSERT INTO transactions (sender_id, receiver_id, amount, transaction_type) VALUES (?, ?, ?, "add_fund")');
                $stmt2->bind_param('iid', $user_id, $user_id, $amount);
                $stmt2->execute();
                $stmt2->close();

                $conn->commit();
                $success = 'Funds added successfully!';
            } catch (Exception $e) {
                $conn->rollback();
                $error = 'Error adding funds. Please try again.';
            }
        }
    }
}
// Get current balance
$stmt = $conn->prepare('SELECT balance FROM wallets WHERE user_id = ?');
$stmt->bind_param('i', $user_id);
$stmt->execute();
$stmt->bind_result($balance);
$stmt->fetch();
$stmt->close();
$balance = $balance ?? 0.00;
?>
<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">
    <title>Add Funds - SecurePay</title>
    <link rel="stylesheet" href="assets/css/style.css">
</head>

<body class="page-finance page-add-funds">
    <div class="finance-card">
        <h2 class="finance-title">╰(..:: Add Funds ::..)╯</h2>

        <p class="balance-note">Current Balance: <strong>-/<?php echo number_format($balance, 2); ?></strong></p>
        <?php if ($success): ?>
            <div class="alert success"><?php echo escape_html($success); ?></div>
        <?php elseif ($error): ?>
            <div class="alert error"><?php echo escape_html($error); ?></div>
        <?php endif; ?>
        <form method="post" action="" autocomplete="off" class="finance-form">
            <input type="hidden" name="csrf_token" value="<?php echo escape_html($csrf_token); ?>">
            <label for="amount">Amount to Add (-/)</label>
            <input type="number" id="amount" name="amount" min="1" step="0.01" required>
            <button type="submit">Add Funds</button>
        </form>
        <p class="back-link"><a href="dashboard/index.php">Back to Dashboard</a></p>
    </div>
</body>

</html>