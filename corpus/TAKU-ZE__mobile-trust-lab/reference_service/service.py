from __future__ import annotations

import re
import threading
from dataclasses import asdict, dataclass, replace
from typing import Mapping

IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$")
DEFAULT_REWARD_CATALOG = {
    "daily-welcome": 100,
    "security-lab-complete": 250,
}


class RewardServiceError(ValueError):
    """Base class for rejected reward operations."""


class InvalidIdentifier(RewardServiceError):
    """Raised when a request identifier is missing or malformed."""


class UnknownReward(RewardServiceError):
    """Raised when the requested reward is not in the server catalog."""


class IdempotencyConflict(RewardServiceError):
    """Raised when one idempotency key is reused for a different operation."""


@dataclass(frozen=True, slots=True)
class ClaimResult:
    account_id: str
    reward_id: str
    amount: int
    balance: int
    transaction_id: str
    idempotency_key: str
    replayed: bool

    def to_dict(self) -> dict[str, str | int | bool]:
        return asdict(self)


class RewardService:
    """In-memory reference for an atomic, server-authoritative reward ledger.

    The caller supplies identity, a catalog reward identifier, and an idempotency
    key. It never supplies the amount or resulting balance. The lock models the
    transaction boundary that a production database must enforce atomically.
    """

    def __init__(self, reward_catalog: Mapping[str, int] | None = None) -> None:
        catalog = dict(reward_catalog or DEFAULT_REWARD_CATALOG)
        if not catalog or any(not self._valid_identifier(key) for key in catalog):
            raise ValueError("reward catalog contains an invalid identifier")
        if any(not isinstance(amount, int) or isinstance(amount, bool) or amount <= 0 for amount in catalog.values()):
            raise ValueError("reward catalog amounts must be positive integers")

        self._catalog = catalog
        self._balances: dict[str, int] = {}
        self._claims: dict[tuple[str, str], ClaimResult] = {}
        self._idempotency: dict[tuple[str, str], ClaimResult] = {}
        self._next_transaction = 1
        self._lock = threading.RLock()

    @staticmethod
    def _valid_identifier(value: object) -> bool:
        return isinstance(value, str) and IDENTIFIER.fullmatch(value) is not None

    @classmethod
    def _require_identifier(cls, name: str, value: object) -> str:
        if not cls._valid_identifier(value):
            raise InvalidIdentifier(f"{name} must match {IDENTIFIER.pattern}")
        return value

    def reward_catalog(self) -> dict[str, int]:
        return dict(self._catalog)

    def balance_for(self, account_id: str) -> int:
        account_id = self._require_identifier("account_id", account_id)
        with self._lock:
            return self._balances.get(account_id, 0)

    def claim_reward(self, account_id: str, reward_id: str, idempotency_key: str) -> ClaimResult:
        account_id = self._require_identifier("account_id", account_id)
        reward_id = self._require_identifier("reward_id", reward_id)
        idempotency_key = self._require_identifier("idempotency_key", idempotency_key)

        if reward_id not in self._catalog:
            raise UnknownReward(f"unknown reward: {reward_id}")

        with self._lock:
            idempotency_scope = (account_id, idempotency_key)
            previous_operation = self._idempotency.get(idempotency_scope)
            if previous_operation is not None:
                if previous_operation.reward_id != reward_id:
                    raise IdempotencyConflict(
                        "idempotency key was already used for a different reward"
                    )
                return replace(previous_operation, replayed=True)

            claim_scope = (account_id, reward_id)
            previous_claim = self._claims.get(claim_scope)
            if previous_claim is not None:
                replay = replace(previous_claim, idempotency_key=idempotency_key, replayed=True)
                self._idempotency[idempotency_scope] = replay
                return replay

            amount = self._catalog[reward_id]
            balance = self._balances.get(account_id, 0) + amount
            result = ClaimResult(
                account_id=account_id,
                reward_id=reward_id,
                amount=amount,
                balance=balance,
                transaction_id=f"txn-{self._next_transaction:08d}",
                idempotency_key=idempotency_key,
                replayed=False,
            )
            self._next_transaction += 1
            self._balances[account_id] = balance
            self._claims[claim_scope] = result
            self._idempotency[idempotency_scope] = result
            return result
