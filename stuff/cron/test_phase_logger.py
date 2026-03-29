'''Unit tests for PhaseTracker.'''

import json
import unittest

from phase_logger import PhaseTracker


class TestPhaseTrackerSuccess(unittest.TestCase):
    '''Tests for fully successful phase runs.'''

    def test_single_success_phase(self) -> None:
        '''A single successful phase should record success with
        positive duration.'''
        tracker = PhaseTracker('test_job')
        with tracker.phase('step_one'):
            _ = 1 + 1
        summary = tracker.summary()
        self.assertEqual(summary['overall_status'], 'success')
        self.assertEqual(summary['phases_succeeded'], 1)
        self.assertEqual(summary['phases_failed'], 0)
        self.assertEqual(len(summary['phases']), 1)
        self.assertEqual(summary['phases'][0]['status'], 'success')
        self.assertGreaterEqual(
            summary['phases'][0]['duration_seconds'], 0.0)
        self.assertIsNone(summary['phases'][0]['error'])

    def test_multiple_success_phases(self) -> None:
        '''All phases succeeding should give overall success.'''
        tracker = PhaseTracker('test_job')
        with tracker.phase('one'):
            pass
        with tracker.phase('two'):
            pass
        with tracker.phase('three'):
            pass
        summary = tracker.summary()
        self.assertEqual(summary['overall_status'], 'success')
        self.assertEqual(summary['phases_succeeded'], 3)
        self.assertEqual(summary['phases_failed'], 0)


class TestPhaseTrackerFailure(unittest.TestCase):
    '''Tests for failed phase runs.'''

    def test_single_failure_records_error(self) -> None:
        '''A failed phase should record failed status and the error
        message.'''
        tracker = PhaseTracker('test_job')
        with self.assertRaises(RuntimeError):
            with tracker.phase('bad_step'):
                raise RuntimeError('something broke')
        summary = tracker.summary()
        self.assertEqual(summary['overall_status'], 'failure')
        self.assertEqual(summary['phases_failed'], 1)
        self.assertEqual(summary['phases'][0]['status'], 'failed')
        self.assertEqual(summary['phases'][0]['error'], 'something broke')
        self.assertGreaterEqual(
            summary['phases'][0]['duration_seconds'], 0.0)

    def test_all_phases_failing_gives_failure_status(self) -> None:
        '''If every phase fails, overall status should be failure.'''
        tracker = PhaseTracker('test_job')
        for name in ['a', 'b', 'c']:
            try:
                with tracker.phase(name):
                    raise ValueError(f'{name} failed')
            except ValueError:
                pass
        summary = tracker.summary()
        self.assertEqual(summary['overall_status'], 'failure')
        self.assertEqual(summary['phases_succeeded'], 0)
        self.assertEqual(summary['phases_failed'], 3)

    def test_exception_is_not_suppressed(self) -> None:
        '''The context manager must re-raise exceptions, not swallow
        them.'''
        tracker = PhaseTracker('test_job')
        with self.assertRaises(TypeError):
            with tracker.phase('raise_test'):
                raise TypeError('must propagate')


class TestPhaseTrackerPartialSuccess(unittest.TestCase):
    '''Tests for mixed success/failure runs.'''

    def test_partial_success(self) -> None:
        '''Mix of success and failure should give partial_success.'''
        tracker = PhaseTracker('test_job')
        with tracker.phase('good'):
            pass
        try:
            with tracker.phase('bad'):
                raise RuntimeError('fail')
        except RuntimeError:
            pass
        with tracker.phase('also_good'):
            pass
        summary = tracker.summary()
        self.assertEqual(summary['overall_status'], 'partial_success')
        self.assertEqual(summary['phases_succeeded'], 2)
        self.assertEqual(summary['phases_failed'], 1)


class TestPhaseTrackerSummaryFormat(unittest.TestCase):
    '''Tests for the summary output format.'''

    def test_summary_is_json_serializable(self) -> None:
        '''summary() output must be serializable to JSON without
        errors.'''
        tracker = PhaseTracker('test_job')
        with tracker.phase('step'):
            pass
        output = json.dumps(tracker.summary())
        parsed = json.loads(output)
        self.assertEqual(parsed['job_name'], 'test_job')

    def test_summary_contains_total_duration(self) -> None:
        '''Total duration should be the sum of all phase durations.'''
        tracker = PhaseTracker('test_job')
        with tracker.phase('a'):
            pass
        with tracker.phase('b'):
            pass
        summary = tracker.summary()
        expected = sum(p['duration_seconds'] for p in summary['phases'])
        self.assertAlmostEqual(
            summary['total_duration_seconds'], expected, places=3)


if __name__ == '__main__':
    unittest.main()
