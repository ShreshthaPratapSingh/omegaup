'''Observability utility for cron job phases.

Provides a PhaseTracker class that tracks the execution status and
wall-clock duration of each phase in a cron job, producing structured
summaries suitable for JSON logging.
'''

import logging
import time
from contextlib import contextmanager
from typing import Any, Dict, Iterator, List, Optional


class PhaseTracker:
    '''Tracks cron job phases with timing and status information.

    Usage:
        tracker = PhaseTracker('update_ranks')
        with tracker.phase('user_rank'):
            update_user_rank()
        with tracker.phase('author_rank'):
            update_author_rank()
        logging.info('Summary: %s', tracker.summary())

    Each phase transitions through: pending -> running -> success/failed.
    Exceptions are never suppressed; they pass through the context
    manager and are re-raised after recording the failure.
    '''

    def __init__(self, job_name: str) -> None:
        self._job_name = job_name
        self._phases: List[Dict[str, Any]] = []

    @contextmanager
    def phase(self, name: str) -> Iterator[None]:
        '''Context manager that tracks a single phase.

        Records start time on entry. On successful exit, marks the
        phase as success. On exception, marks it as failed with the
        error message, then re-raises the exception.
        '''
        phase_record: Dict[str, Any] = {
            'name': name,
            'status': 'running',
            'duration_seconds': 0.0,
            'error': None,
        }
        self._phases.append(phase_record)
        start = time.monotonic()
        try:
            yield
            phase_record['status'] = 'success'
        except Exception as exc:
            phase_record['status'] = 'failed'
            phase_record['error'] = str(exc)
            raise
        finally:
            phase_record['duration_seconds'] = round(
                time.monotonic() - start, 4)

    def summary(self) -> Dict[str, Any]:
        '''Returns a structured summary of all tracked phases.

        The summary contains:
        - job_name: name of the cron job
        - overall_status: 'success', 'partial_success', or 'failure'
        - total_duration_seconds: sum of all phase durations
        - phases_succeeded: count of successful phases
        - phases_failed: count of failed phases
        - phases: list of individual phase records
        '''
        succeeded = sum(
            1 for p in self._phases if p['status'] == 'success')
        failed = sum(
            1 for p in self._phases if p['status'] == 'failed')
        total_duration = sum(p['duration_seconds'] for p in self._phases)

        if failed == 0:
            overall_status = 'success'
        elif succeeded == 0:
            overall_status = 'failure'
        else:
            overall_status = 'partial_success'

        return {
            'job_name': self._job_name,
            'overall_status': overall_status,
            'total_duration_seconds': round(total_duration, 4),
            'phases_succeeded': succeeded,
            'phases_failed': failed,
            'phases': list(self._phases),
        }
