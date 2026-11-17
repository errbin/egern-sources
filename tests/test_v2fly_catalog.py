import json
from pathlib import Path
import unittest

from tools.egern_hub.source_catalog import normalize


class V2FlyCatalogTests(unittest.TestCase):
    def test_domain_list_catalog_is_a_repository_rule_source(self):
        root = Path(__file__).resolve().parents[1]
        data = json.loads((root / 'catalog/v2fly--domain-list-community.json').read_text(encoding='utf-8'))
        manifest = normalize(data)
        self.assertEqual(manifest['version'], 1)
        self.assertEqual(manifest['repository'], 'https://github.com/v2fly/domain-list-community')
        self.assertEqual(manifest['discovery']['ref'], 'master')
        self.assertEqual(manifest['discovery']['rule_include'], ['data/*'])
        self.assertEqual(manifest['defaults']['license'], 'MIT')
        self.assertEqual(manifest['defaults']['category'], '网络分流')
        self.assertEqual(manifest['defaults']['policy'], 'PROXY')


if __name__ == '__main__':
    unittest.main()
