from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from reference_service.service import (
    IdempotencyConflict,
    InvalidIdentifier,
    RewardService,
    UnknownReward,
)


class RewardServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = RewardService({"daily-welcome": 100, "lab-complete": 250})

    def test_first_claim_uses_server_catalog_and_updates_balance(self) -> None:
        result = self.service.claim_reward("account-a", "daily-welcome", "request-1")

        self.assertEqual(result.amount, 100)
        self.assertEqual(result.balance, 100)
        self.assertEqual(result.transaction_id, "txn-00000001")
        self.assertFalse(result.replayed)
        self.assertEqual(self.service.balance_for("account-a"), 100)

    def test_same_idempotency_key_returns_original_transaction(self) -> None:
        first = self.service.claim_reward("account-a", "daily-welcome", "request-1")
        replay = self.service.claim_reward("account-a", "daily-welcome", "request-1")

        self.assertTrue(replay.replayed)
        self.assertEqual(replay.transaction_id, first.transaction_id)
        self.assertEqual(replay.balance, first.balance)
        self.assertEqual(self.service.balance_for("account-a"), 100)

    def test_new_key_cannot_claim_same_reward_twice(self) -> None:
        first = self.service.claim_reward("account-a", "daily-welcome", "request-1")
        replay = self.service.claim_reward("account-a", "daily-welcome", "request-2")

        self.assertTrue(replay.replayed)
        self.assertEqual(replay.transaction_id, first.transaction_id)
        self.assertEqual(replay.idempotency_key, "request-2")
        self.assertEqual(self.service.balance_for("account-a"), 100)

    def test_idempotency_key_cannot_change_operation(self) -> None:
        self.service.claim_reward("account-a", "daily-welcome", "request-1")

        with self.assertRaises(IdempotencyConflict):
            self.service.claim_reward("account-a", "lab-complete", "request-1")
        self.assertEqual(self.service.balance_for("account-a"), 100)

    def test_accounts_have_independent_claim_and_balance_scopes(self) -> None:
        first = self.service.claim_reward("account-a", "daily-welcome", "same-request")
        second = self.service.claim_reward("account-b", "daily-welcome", "same-request")

        self.assertFalse(first.replayed)
        self.assertFalse(second.replayed)
        self.assertNotEqual(first.transaction_id, second.transaction_id)
        self.assertEqual(self.service.balance_for("account-a"), 100)
        self.assertEqual(self.service.balance_for("account-b"), 100)

    def test_distinct_rewards_accumulate_from_catalog(self) -> None:
        self.service.claim_reward("account-a", "daily-welcome", "request-1")
        result = self.service.claim_reward("account-a", "lab-complete", "request-2")

        self.assertEqual(result.amount, 250)
        self.assertEqual(result.balance, 350)

    def test_unknown_reward_is_rejected_without_balance_change(self) -> None:
        with self.assertRaises(UnknownReward):
            self.service.claim_reward("account-a", "client-invented", "request-1")
        self.assertEqual(self.service.balance_for("account-a"), 0)

    def test_identifiers_are_strictly_validated(self) -> None:
        invalid_values = ["", "contains spaces", "../escape", "x" * 65]
        for value in invalid_values:
            with self.subTest(value=value):
                with self.assertRaises(InvalidIdentifier):
                    self.service.claim_reward(value, "daily-welcome", "request-1")

    def test_catalog_rejects_boolean_and_non_positive_amounts(self) -> None:
        for amount in [True, 0, -1]:
            with self.subTest(amount=amount):
                with self.assertRaises(ValueError):
                    RewardService({"reward": amount})


if __name__ == "__main__":
    unittest.main()
