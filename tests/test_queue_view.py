"""Unit tests for Queue tab view selection (Task 8 review)."""

import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent / "app"))
from tabs.queue_tab import COMMITTED_STATUS, select_queue_view, texas_mappable_mask


class QueueViewTests(unittest.TestCase):
    def setUp(self):
        self.df = pd.DataFrame({
            'project_name': ['A', 'B', 'C', 'D'],
            'status': [
                COMMITTED_STATUS,
                COMMITTED_STATUS,
                'Under Study',
                'Early Stage',
            ],
            'proposed_mw': [20.0, 200.0, 500.0, 5.0],
            'lat': [29.76, 32.78, 31.0, None],
            'lon': [-95.37, -96.80, -99.9, -97.74],
        })

    def test_default_view_is_signed_ia_including_sub_75mw(self):
        view = select_queue_view(self.df, show_full_queue=False)
        self.assertEqual(set(view['project_name']), {'A', 'B'})
        self.assertTrue((view['proposed_mw'] < 75).any())

    def test_full_view_includes_under_study(self):
        view = select_queue_view(self.df, show_full_queue=True)
        self.assertEqual(len(view), 4)

    def test_headlines_not_limited_to_mappable_rows(self):
        view = select_queue_view(self.df, show_full_queue=True)
        mapped = view[texas_mappable_mask(view)]
        self.assertEqual(len(view), 4)
        self.assertEqual(len(mapped), 3)

    def test_no_75mw_cutoff_on_committed_view(self):
        view = select_queue_view(self.df, show_full_queue=False)
        self.assertIn(20.0, set(view['proposed_mw']))


if __name__ == '__main__':
    unittest.main()
