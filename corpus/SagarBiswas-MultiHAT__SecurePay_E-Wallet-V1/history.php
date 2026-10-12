<?php
// history.php
// Shows the user's last 10 transactions with filter options
require_once 'includes/db_connect.php';
require_once 'includes/functions.php';
require_login();

$user_id = $_SESSION['user_id'];
$type_filter = $_GET['type'] ?? '';
$date_from = $_GET['from'] ?? '';
$date_to = $_GET['to'] ?? '';
$filter_error = '';

// Build filter query
$where = '(sender_id = ? OR receiver_id = ?)';
$params = [$user_id, $user_id];
$types = 'ii';
if ($type_filter && in_array($type_filter, ['add_fund', 'transfer', 'withdraw'], true)) {
    $where .= ' AND transaction_type = ?';
    $params[] = $type_filter;
    $types .= 's';
}
if ($date_from || $date_to) {
    if (!is_valid_ymd_date($date_from) || !is_valid_ymd_date($date_to)) {
        $filter_error = 'Please provide a valid start and end date.';
    } elseif ($date_from > $date_to) {
        $filter_error = 'Date From must be earlier than or equal to Date To.';
    } else {
        $where .= ' AND DATE(created_at) BETWEEN ? AND ?';
        $params[] = $date_from;
        $params[] = $date_to;
        $types .= 'ss';
    }
}

// Prepare query with JOINs to get usernames
$sql = "SELECT t.*, su.username AS sender_name, ru.username AS receiver_name
        FROM transactions t
        LEFT JOIN users su ON t.sender_id = su.id
        LEFT JOIN users ru ON t.receiver_id = ru.id
        WHERE $where
        ORDER BY t.created_at DESC
        LIMIT 10";
$stmt = $conn->prepare($sql);
$stmt->bind_param($types, ...$params);
$stmt->execute();
$result = $stmt->get_result();
$transactions = $result->fetch_all(MYSQLI_ASSOC);
$stmt->close();
?>
<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">
    <title>Transaction History - SecurePay</title>
    <link rel="stylesheet" href="assets/css/style.css">
</head>

<body class="page-history">
    <div class="history-wrapper">
        <h2>╰(..:: Transaction History ::..)╯</h2>
        <div class="container">
            <?php if ($filter_error): ?>
                <div class="alert error"><?php echo escape_html($filter_error); ?></div>
            <?php endif; ?>
            <form method="get" action="" class="filter-form">
                <label for="type">Type:</label>
                <select name="type" id="type">
                    <option value="">All</option>
                    <option value="add_fund" <?php if ($type_filter === 'add_fund') echo 'selected'; ?>>Add Fund</option>
                    <option value="transfer" <?php if ($type_filter === 'transfer') echo 'selected'; ?>>Transfer</option>
                    <option value="withdraw" <?php if ($type_filter === 'withdraw') echo 'selected'; ?>>Withdraw</option>
                </select>
                <label for="from">Date From:</label>
                <input type="date" id="from" name="from" value="<?php echo htmlspecialchars($date_from); ?>">
                <label for="to">Date To:</label>
                <input type="date" id="to" name="to" value="<?php echo htmlspecialchars($date_to); ?>">
                <button type="submit">Filter</button>
            </form>
            <table class="history-table">
                <thead>
                    <tr>
                        <th>Date</th>
                        <th>Amount</th>
                        <th>To/From</th>
                        <th>Type</th>
                    </tr>
                </thead>
                <tbody>
                <?php foreach ($transactions as $t): ?>
                    <tr>
                        <td data-label="Date"><?php echo escape_html($t['created_at']); ?></td>
                        <td data-label="Amount"><?php echo format_transaction_amount($t, $user_id); ?></td>
                        <td data-label="To/From">
                            <?php echo format_transaction_counterparty($t, $user_id); ?>
                        </td>
                        <td data-label="Type"><?php echo escape_html(ucfirst($t['transaction_type'])); ?></td>
                    </tr>
                <?php endforeach; ?>
                <?php if (empty($transactions)): ?>
                    <tr>
                        <td colspan="4" class="text-center">No transactions found.</td>
                    </tr>
                <?php endif; ?>
                </tbody>
            </table>
            <p><a href="dashboard/index.php">Back to Dashboard</a></p>
        </div>
    </div>
</body>

</html>