<?php
// cyberlab/index.php
// Cybersecurity Demo Lab overview with global secure/vulnerable toggle
include 'secure_toggle.php';

// Helper for mode label
function modeLabel()
{
    if (isSecureMode()) {
        return '<span class="mode-badge mode-badge-secure">Secure Mode</span>';
    } else {
        return '<span class="mode-badge mode-badge-vulnerable">Vulnerable Mode</span>';
    }
}
?>
<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">
    <title>Cybersecurity Attack Demo Lab - SecurePay</title>
    <link rel="stylesheet" href="../assets/css/cyberlab.css">
</head>

<body class="page-cyber page-cyber-index">
    <div class="cyber-shell">
        <h1 class="cyber-title">Cybersecurity Attack <br>Demo Lab</h1>

        <div class="mode-toggle">
            <?php echo modeLabel(); ?>
            <?php if (isSecureMode()): ?>
                <a href="?mode=vulnerable" class="cyber-switch">Switch to Vulnerable</a>
            <?php else: ?>
                <a href="?mode=secure" class="cyber-switch">Switch to Secure</a>
            <?php endif; ?>
        </div>
        <div class="desc">
            <p>This lab demonstrates common web vulnerabilities and their fixes. Toggle between <strong>Vulnerable</strong> and <strong>Secure</strong> modes globally.</p>
            <ul>
                <li><strong>XSS (Cross-Site Scripting):</strong> Inject scripts via user input. <a href="xss_demo.php">Try XSS Demo</a></li>

            </ul>
        </div>
        <div class="lab-btns">
            <a href="xss_demo.php">XSS Demo</a>
        </div>
    </div>
</body>

</html>