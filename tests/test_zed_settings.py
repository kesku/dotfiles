import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from zed_settings import parse


class JsoncTests(unittest.TestCase):
    def test_comments_trailing_commas_and_strings(self):
        value = parse(r'''// header
        {"url": "https://example.invalid/a/*b*/", /* comment */
         "text": "quote: \" slash: \\", "commas": ",}",
         "list": [1, 2, /* trailing comment */],}
        ''')
        self.assertEqual(value['url'], 'https://example.invalid/a/*b*/')
        self.assertEqual(value['commas'], ',}')
        self.assertEqual(value['list'], [1, 2])

    def test_bad_comment_and_non_object_rejected(self):
        for value in ['{/* incomplete', '{ /*/ }', '[]']:
            with self.assertRaises(ValueError):
                parse(value)

    def test_invalid_jsonc_values_rejected(self):
        for value in ['{"items":[,]}', '{"items":[1,,]}', '{"number":NaN}', '{"number":Infinity}']:
            with self.assertRaises(ValueError):
                parse(value)
