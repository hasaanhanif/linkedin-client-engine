import json
import sys
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'scripts'))
from post_daily import build_prompt, choose_topic, validate_post


class ContentTests(unittest.TestCase):
    def test_topic_rotation(self):
        mon = datetime(2026, 11, 16, 8, tzinfo=ZoneInfo('Asia/Karachi'))
        tue = datetime(2026, 11, 17, 8, tzinfo=ZoneInfo('Asia/Karachi'))
        self.assertEqual(choose_topic(mon)[0], 'WordPress')
        self.assertEqual(choose_topic(tue)[0], 'n8n AI Automation')

    def test_rejects_unverified_results(self):
        text = 'Website design affects trust. ' * 22 + 'We increased conversions by 57%.'
        with self.assertRaises(ValueError):
            validate_post(text, [])

    def test_rejects_duplicate(self):
        text = 'A business website needs a clear next step. ' * 20
        with self.assertRaises(ValueError):
            validate_post(text, [{'text': text}])

    def test_accepts_normal_educational_post(self):
        text = ('A business website can be beautiful and still confuse visitors.\n\n'
                'Look at the first screen on mobile. Can a new visitor identify what you offer, '
                'who it is for and what to do next? If not, tighten the opening statement and '
                'give them one meaningful next step. A simple contact form is often more useful '
                'than a long list of features. \n\nTry asking a colleague who has never seen '
                'your website to explain the offer after a quick glance. Their hesitation can '
                'be useful feedback.\n\nWhat would you simplify on your homepage?')
        self.assertEqual(validate_post(text, []), text)

    def test_prompt_requires_true_claims(self):
        self.assertIn('NEVER invent clients', build_prompt(datetime(2026, 11, 18, tzinfo=ZoneInfo('Asia/Karachi')), []))


if __name__ == '__main__':
    unittest.main()
