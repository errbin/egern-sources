import tempfile
from pathlib import Path
import unittest
from tools.egern_hub.catalog import initialize
from tools.egern_hub.source_catalog import normalize
from tools.validate import validate

class StandaloneCatalogTests(unittest.TestCase):
    def test_public_catalog_is_valid_without_converter(self):
        self.assertGreater(validate(Path(__file__).resolve().parents[1]),0)
    def test_initializer_accepts_directory_and_rejects_duplicates(self):
        with tempfile.TemporaryDirectory() as folder:
            path=initialize(folder,'https://github.com/Example/Rules','main',files=['rules/'])
            self.assertEqual(validate(folder),1)
            with self.assertRaises(ValueError):initialize(folder,'https://github.com/Example/Rules','main')
    def test_initializer_supports_telegram_without_private_dependencies(self):
        with tempfile.TemporaryDirectory() as folder:
            initialize(folder,'https://t.me/ExampleChannel')
            self.assertEqual(validate(folder),1)
    def test_manual_conversion_status_is_rejected(self):
        with self.assertRaises(ValueError):normalize({'version':2,'repository':'https://github.com/A/B','defaults':{},'discovery':{'type':'repository','ref':'main'},'converted':True})
