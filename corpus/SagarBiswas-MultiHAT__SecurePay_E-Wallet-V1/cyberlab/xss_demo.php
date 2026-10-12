<?php
// xss_demo.php
// XSS Demo: Shows both vulnerable and secure comment forms
// Uses global secure_toggle.php for mode
include 'secure_toggle.php';

// Use session to store comments for demo (not persistent)
$comments = $_SESSION['xss_comments'] ?? [];
$message = '';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $comment = $_POST['comment'] ?? '';
    if (trim($comment) === '') {
        $message = 'Comment cannot be empty!';
    } else {
        $comments[] = $comment;
        $_SESSION['xss_comments'] = $comments;
        $message = 'Comment posted!';
    }
}

// Helper for output (vulnerable vs secure)
function show_comment($c)
{
    if (isSecureMode()) {
        // Secure: escape HTML
        return htmlspecialchars($c);
    } else {
        // Vulnerable: raw output
        return $c;
    }
}
?>
<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">
    <title>XSS Demo - Cyber Lab</title>
    <link rel="stylesheet" href="../assets/css/cyberlab.css">
</head>

<body class="page-cyber page-cyber-xss">
    <div class="cyber-shell xss-shell">
        <h2 class="cyber-title">XSS Demo: Cross-Site Scripting</h2>
        <div class="toggle-btns">
            <div>
                <?php if (isSecureMode()): ?>
                    <span class="mode-badge mode-badge-secure">Secure Mode: ON</span>
                    <a href="?mode=vulnerable">Switch to Vulnerable</a>
                <?php else: ?>
                    <span class="mode-badge mode-badge-vulnerable">Vulnerable Mode: ON</span>
                    <a href="?mode=secure">Switch to Secure</a>
                <?php endif; ?>
            </div>
            <a href="index.php">Back to Lab Index</a>
        </div>
        <div class="xss-note">
            <strong>Try posting a comment like:</strong> <code>&lt;script&gt;alert('XSS')&lt;/script&gt;</code><br>
            <span class="xss-note-warning">Vulnerable mode will pop an alert. Secure mode will show the code as text.</span>
        </div>
        <?php if ($message): ?>
            <div class="alert <?php echo isSecureMode() ? 'success' : 'error'; ?>"><?php echo $message; ?></div>
        <?php endif; ?>
        <form method="post" action="" autocomplete="off">
            <label>Post a Comment:</label>
            <textarea name="comment" rows="3" placeholder="Type your hack here..."></textarea>
            <button type="submit">Submit</button>
        </form>
        <h3>Comments:</h3>
        <?php if (empty($comments)): ?>
            <div class="comment-box">No comments yet.</div>
        <?php else: ?>
            <?php foreach ($comments as $c): ?>
                <div class="comment-box">
                    <?php echo show_comment($c); ?>
                </div>
            <?php endforeach; ?>
        <?php endif; ?>
        <div class="terminal-footer">
            <span class="terminal-user">user@cyberlab</span>:<span class="terminal-path">~</span>$ <span class="terminal-note"># XSS Demo for Web Security - <b>Try to break it!</b></span>
        </div>
    </div>
</body>

</html>