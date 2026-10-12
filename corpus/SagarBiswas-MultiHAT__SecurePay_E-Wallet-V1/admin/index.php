<?php
// Admin Dashboard for SecurePay
// Shows user, wallet, and transaction statistics
require_once '../includes/db_connect.php';
require_once '../includes/functions.php';
require_admin();

// Helper function to format amounts
function formatAmount($amount)
{
    return number_format((float)$amount, 2, '.', '');
}

// Get total number of users
$userCount = 0;
$sql = "SELECT COUNT(*) AS total FROM users";
$result = $conn->query($sql);
if ($result && $row = $result->fetch_assoc()) {
    $userCount = $row['total'];
}

// Get total wallet balance
$totalBalance = 0;
$sql = "SELECT SUM(balance) AS total FROM wallets";
$result = $conn->query($sql);
if ($result && $row = $result->fetch_assoc()) {
    $totalBalance = $row['total'] ? $row['total'] : 0;
}

// Get number of transactions today
$todayCount = 0;
$today = date('Y-m-d');

// Fix: Use correct column name for transaction date
$sql = "SHOW COLUMNS FROM transactions LIKE 'timestamp'";
$result = $conn->query($sql);
if ($result && $result->num_rows === 0) {
    // If 'timestamp' column does not exist, try 'created_at' or 'date'
    $dateColumn = 'created_at';
    $sql = "SHOW COLUMNS FROM transactions LIKE 'created_at'";
    $result2 = $conn->query($sql);
    if ($result2 && $result2->num_rows === 0) {
        $dateColumn = 'date';
    }
} else {
    $dateColumn = 'timestamp';
}

$sql = "SELECT COUNT(*) AS total FROM transactions WHERE DATE($dateColumn) = ?";
$stmt = $conn->prepare($sql);
$stmt->bind_param('s', $today);
$stmt->execute();
$stmt->bind_result($todayCount);
$stmt->fetch();
$stmt->close();

// Get 10 most recent transactions with sender/receiver names

// Fix: Use correct column names for recent transactions
$recentTransactions = [];
// Detect available columns
$sql = "SHOW COLUMNS FROM transactions";
$result = $conn->query($sql);
$columns = [];
if ($result) {
    while ($row = $result->fetch_assoc()) {
        $columns[] = $row['Field'];
    }
}
$amountCol = in_array('amount', $columns) ? 'amount' : (in_array('value', $columns) ? 'value' : '');
$typeCol = in_array('type', $columns) ? 'type' : (in_array('transaction_type', $columns) ? 'transaction_type' : '');
$dateCol = in_array('timestamp', $columns) ? 'timestamp' : (in_array('created_at', $columns) ? 'created_at' : (in_array('date', $columns) ? 'date' : ''));


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

$sql = "SELECT t.id"
    . ($amountCol ? ", t.$amountCol" : "")
    . ($typeCol ? ", t.$typeCol" : "")
    . ($dateCol ? ", t.$dateCol" : "")
    . ", u1.$userNameCol AS sender, u2.$userNameCol AS receiver
        FROM transactions t
        LEFT JOIN users u1 ON t.sender_id = u1.id
        LEFT JOIN users u2 ON t.receiver_id = u2.id
        ORDER BY t." . ($dateCol ? $dateCol : 'id') . " DESC
        LIMIT 10";
$result = $conn->query($sql);
if ($result) {
    while ($row = $result->fetch_assoc()) {
        $recentTransactions[] = $row;
    }
}

?>
<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">
    <title>Admin Dashboard | SecurePay</title>
    <link rel="stylesheet" href="../assets/css/adminStyle.css">
</head>

<body class="page-admin-dashboard">
    <div class="container">
        <div id="header">
            <h1>╰(..:: Admin Dashboard ::..)╯</h1>
            <nav>
                <a href="users.php">Users</a>
                <a href="logout.php">Logout</a>
            </nav>
        </div>
        <br>
        <!-- Statistics Grid -->
        <div class="admin-grid">
            <div class="admin-card total-users">
                <h2>Total Users</h2>
                <div class="stat"><?php echo $userCount; ?></div>
            </div>
            <div class="admin-card total-users">
                <h2>Total Wallet Balance</h2>
                <div class="stat">$<?php echo formatAmount($totalBalance); ?></div>
            </div>
            <div class="admin-card total-users">
                <h2>Transactions Today</h2>
                <div class="stat"><?php echo $todayCount; ?></div>
            </div>
        </div>

        <!-- Recent Transactions Table -->
        <h2>Recent Transactions</h2>
        <table class="recent-table">
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Amount ($)</th>
                    <th>Type</th>
                    <th>Sender</th>
                    <th>Receiver</th>
                    <th class="timestamp">Timestamp</th>
                </tr>
            </thead>
            <tbody>
                <?php foreach ($recentTransactions as $tx): ?>
                    <tr>
                        <td><?php echo isset($tx['id']) ? $tx['id'] : '-'; ?></td>
                        <td><?php echo isset($tx['amount']) ? formatAmount($tx['amount']) : (isset($tx['value']) ? formatAmount($tx['value']) : '-'); ?></td>
                        <td><?php
                            if (isset($tx['type']) && !empty($tx['type'])) {
                                echo htmlspecialchars($tx['type']);
                            } elseif (isset($tx['transaction_type']) && !empty($tx['transaction_type'])) {
                                echo htmlspecialchars($tx['transaction_type']);
                            } elseif (
                                ((!isset($tx['receiver']) || $tx['receiver'] == '-' || empty($tx['receiver'])) &&
                                    isset($tx['sender']) && !empty($tx['sender']) &&
                                    isset($tx['amount']) && floatval($tx['amount']) > 0)
                            ) {
                                echo 'withdraw';
                            } else {
                                echo '-';
                            }
                            ?></td>
                        <td><?php echo htmlspecialchars($tx['sender'] ?? '-'); ?></td>
                        <td><?php echo htmlspecialchars($tx['receiver'] ?? '-'); ?></td>
                        <td class="timestamp"><?php
                                                if (isset($tx['timestamp'])) echo date('d-m-Y H:i', strtotime($tx['timestamp']));
                                                elseif (isset($tx['created_at'])) echo date('d-m-Y H:i', strtotime($tx['created_at']));
                                                elseif (isset($tx['date'])) echo date('d-m-Y H:i', strtotime($tx['date']));
                                                else echo '-';
                                                ?></td>
                    </tr>
                <?php endforeach; ?>
                <?php if (empty($recentTransactions)): ?>
                    <tr>
                        <td colspan="6">No transactions found.</td>
                    </tr>
                <?php endif; ?>
            </tbody>
        </table>
    </div>
</body>

</html>