<?php
declare(strict_types=1);

require_once __DIR__ . '/../includes/functions.php';

function assert_true($condition, string $message): void
{
    if (!$condition) {
        throw new RuntimeException($message);
    }
}

function assert_same($expected, $actual, string $message): void
{
    if ($expected !== $actual) {
        throw new RuntimeException($message . " Expected: " . var_export($expected, true) . ", Actual: " . var_export($actual, true));
    }
}

function run_test_suite(): array
{
    $tests = [
        'valid ymd date accepted' => function (): void {
            assert_true(is_valid_ymd_date('2024-02-29'), 'Expected leap-day date to be valid.');
        },
        'invalid ymd date rejected' => function (): void {
            assert_true(!is_valid_ymd_date('2024-02-30'), 'Expected invalid date to be rejected.');
        },
        'csrf token alias works' => function (): void {
            $token = get_csrf_token();
            assert_true(validate_csrf_token($token), 'Expected CSRF token alias to validate generated token.');
            assert_true(!validate_csrf_token('invalid-token'), 'Expected invalid CSRF token to fail validation.');
        },
        'transaction amount formatting transfer sent' => function (): void {
            $tx = [
                'transaction_type' => 'transfer',
                'sender_id' => 10,
                'receiver_id' => 11,
                'amount' => 123.45,
            ];
            assert_same('(-) -/123.45', format_transaction_amount($tx, 10), 'Expected outgoing transfer amount format.');
        },
        'transaction amount formatting transfer received' => function (): void {
            $tx = [
                'transaction_type' => 'transfer',
                'sender_id' => 5,
                'receiver_id' => 10,
                'amount' => 50,
            ];
            assert_same('(+) -/50.00', format_transaction_amount($tx, 10), 'Expected incoming transfer amount format.');
        },
        'transaction counterparty escapes names' => function (): void {
            $tx = [
                'transaction_type' => 'transfer',
                'sender_id' => 10,
                'receiver_id' => 15,
                'receiver_name' => '<script>alert(1)</script>',
            ];
            assert_same('To: &lt;script&gt;alert(1)&lt;/script&gt;', format_transaction_counterparty($tx, 10), 'Expected escaped counterparty output.');
        },
    ];

    $results = [];
    $passed = 0;
    $failed = 0;

    foreach ($tests as $name => $test) {
        try {
            $test();
            $results[] = "[PASS] {$name}";
            $passed++;
        } catch (Throwable $e) {
            $results[] = "[FAIL] {$name}: " . $e->getMessage();
            $failed++;
        }
    }

    return [
        'results' => $results,
        'passed' => $passed,
        'failed' => $failed,
    ];
}
