import json
from pathlib import Path
import unittest

from tools.egern_hub.source_catalog import normalize


class ACL4SSRCatalogTests(unittest.TestCase):
    def test_clash_ruleset_catalog_uses_declared_license_and_network_category(self):
        root = Path(__file__).resolve().parents[1]
        data = json.loads((root / 'catalog/acl4ssr--acl4ssr.json').read_text(encoding='utf-8'))
        manifest = normalize(data)
        self.assertEqual(manifest['version'], 1)
        self.assertEqual(manifest['repository'], 'https://github.com/ACL4SSR/ACL4SSR')
        self.assertEqual(manifest['discovery']['ref'], 'master')
        self.assertEqual(manifest['discovery']['rule_include'],
                         ['Clash/Ruleset/*.list', 'Clash/*.list'])
        self.assertTrue(manifest['discovery']['merge_same_repository'])
        self.assertEqual(manifest['defaults']['license'], 'CC-BY-SA-4.0')
        self.assertEqual(manifest['defaults']['category'], '网络分流')
        self.assertEqual(manifest['defaults']['policy'], 'PROXY')


if __name__ == '__main__':
    unittest.main()
