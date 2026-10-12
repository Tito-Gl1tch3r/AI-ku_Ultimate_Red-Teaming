from __future__ import annotations

import asyncio
from collections.abc import Sequence
from typing import Any

from tracesurface.config import DEFAULT_SETTINGS


class ChunkEvaluator:
    async def evaluate_loader(
        self,
        page: Any,
        code: str,
        params: Sequence[int | str],
    ) -> list[str]:
        try:
            return await asyncio.wait_for(
                page.evaluate(
                    """
                    (args) => {
                        const fn = new Function('return (' + args.code + ')')();
                        const results = [];
                        for (const p of args.params) {
                            try {
                                const r = fn(p);
                                if (typeof r === 'string'
                                    && r.includes('.js')
                                    && !r.includes('undefined')) {
                                    results.push(r);
                                }
                            } catch(e) {}
                        }
                        return [...new Set(results)];
                    }
                    """,
                    {"code": code, "params": params},
                ),
                timeout=DEFAULT_SETTINGS.collection.chunk_eval_timeout_ms / 1000,
            )

        except Exception:
            return []
