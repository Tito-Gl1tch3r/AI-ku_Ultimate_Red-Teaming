<?php
// dashboard/index.php
// Main dashboard for SecurePay user
require_once '../includes/db_connect.php';
require_once '../includes/functions.php';
require_login();

$user_id = $_SESSION['user_id'];
$username = $_SESSION['username'];

// Get current balance
$stmt = $conn->prepare('SELECT balance FROM wallets WHERE user_id = ?');
$stmt->bind_param('i', $user_id);
$stmt->execute();
$stmt->bind_result($balance);
$stmt->fetch();
$stmt->close();
$balance = $balance ?? 0.00;

// Get last 5 transactions
$sql = "SELECT t.*, su.username AS sender_name, ru.username AS receiver_name
        FROM transactions t
        LEFT JOIN users su ON t.sender_id = su.id
        LEFT JOIN users ru ON t.receiver_id = ru.id
        WHERE t.sender_id = ? OR t.receiver_id = ?
        ORDER BY t.created_at DESC
        LIMIT 5";
$stmt = $conn->prepare($sql);
$stmt->bind_param('ii', $user_id, $user_id);
$stmt->execute();
$result = $stmt->get_result();
$transactions = $result->fetch_all(MYSQLI_ASSOC);
$stmt->close();

// Get top 3 frequent recipients
$sql = "SELECT u.username, COUNT(*) as count
        FROM transactions t
        JOIN users u ON t.receiver_id = u.id
        WHERE t.sender_id = ? AND t.transaction_type = 'transfer'
        GROUP BY t.receiver_id
        ORDER BY count DESC
        LIMIT 3";
$stmt = $conn->prepare($sql);
$stmt->bind_param('i', $user_id);
$stmt->execute();
$result = $stmt->get_result();
$recipients = $result->fetch_all(MYSQLI_ASSOC);
$stmt->close();
?>
<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">
    <title>Dashboard - SecurePay</title>
    <link rel="stylesheet" href="../assets/css/style.css">
</head>

<body class="page-dashboard">
    <div class="container">
        <div class="hero">
            <div class="hero-logo">
                <img src="../imgs/SecurePAY.png" alt="SecurePay Logo" onerror="this.style.display='none'">
            </div>
            <div class="hero-title">Welcome, <?php echo htmlspecialchars($username); ?>!</div>
        </div>
        <div class="balance-card">
            <div class="balance-label">Current Balance</div>
            <div class="balance">-/<?php echo number_format($balance, 2); ?></div>
        </div>
        <div class="dashboard-links">
            <?php if (!empty($_SESSION['is_admin'])): ?>
                <a href="../add_funds.php">Add Funds</a>
            <?php else: ?>
                <a href="../withdraw.php">Withdraw</a>
            <?php endif; ?>
            <a href="../send_money.php">Send Money</a>
            <a href="../history.php">View History</a>
            <a href="../auth/logout.php" class="logout-link">Logout</a>
        </div>
        <div class="section">
            <h3>Last 5 Transactions</h3>
            <table>
                <tr>
                    <th>Date</th>
                    <th>Amount</th>
                    <th>To/From</th>
                    <th>Type</th>
                </tr>
                <?php foreach ($transactions as $t): ?>
                    <?php
                    $transaction = $t;
                    if (empty($transaction['transaction_type']) && is_null($transaction['receiver_id'])) {
                        $transaction['transaction_type'] = 'withdraw';
                    }
                    ?>
                    <tr>
                        <td><?php echo escape_html($transaction['created_at']); ?></td>
                        <td><?php echo format_transaction_amount($transaction, $user_id); ?></td>
                        <td><?php echo format_transaction_counterparty($transaction, $user_id); ?></td>
                        <td><?php echo escape_html(!empty($transaction['transaction_type']) ? ucfirst($transaction['transaction_type']) : 'Unknown'); ?></td>
                    </tr>
                <?php endforeach; ?>
                <?php if (empty($transactions)): ?>
                    <tr>
                        <td colspan="4" class="text-center">No transactions found.</td>
                    </tr>
                <?php endif; ?>
            </table>
        </div>
        <div class="section">
            <h3>Top 3 Frequent Recipients</h3>
            <ul class="recipients-list">
                <?php foreach ($recipients as $r): ?>
                    <li><?php echo htmlspecialchars($r['username']); ?> (<?php echo $r['count']; ?> transfers)</li>
                <?php endforeach; ?>
                <?php if (empty($recipients)): ?>
                    <li>No recipients yet.</li>
                <?php endif; ?>
            </ul>
        </div>
    </div>
</body>

</html>