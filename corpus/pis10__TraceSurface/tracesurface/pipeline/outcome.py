from __future__ import annotations

import time
from dataclasses import dataclass

from tracesurface.models import ReplayStats, ScanJob, ScanSummary
from tracesurface.pipeline.messages import (
    BatchScanOutcome,
    ScanOutput,
    ScanProgress,
    StageFailure,
)


@dataclass(slots=True)
class OutcomeRecorder:
    total: int
    output: ScanOutput
    results: list[BatchScanOutcome]
    done_count: int = 0

    def record_failure(self, item: StageFailure) -> None:
        error = f"{item.stage}: {type(item.error).__name__}: {item.error}"
        self.results.append(BatchScanOutcome(item.url, ok=False, error=error))

        self.done_count += 1
        self.output.failure(self.done_count, self.total, item)

    def record_success(
        self,
        job: ScanJob,
        summary: ScanSummary,
        stats: ReplayStats,
        started_at: float,
    ) -> None:
        self.results.append(
            BatchScanOutcome(job.target_url, ok=True, stats=stats, summary=summary)
        )
        self.done_count += 1

        self.output.success(
            ScanProgress(
                self.done_count,
                self.total,
                job,
                summary,
                time.perf_counter() - started_at,
            ),
            stats,
        )

    def record_skipped(
        self,
        job: ScanJob,
        summary: ScanSummary,
        started_at: float,
    ) -> None:
        self.results.append(
            BatchScanOutcome(
                job.target_url,
                ok=False,
                summary=summary,
                skipped=True,
            )
        )
        self.done_count += 1
        self.output.skipped(
            ScanProgress(
                self.done_count,
                self.total,
                job,
                summary,
                time.perf_counter() - started_at,
            )
        )
