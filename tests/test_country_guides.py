from pathlib import Path
import sys
import tempfile
import unittest
from xml.etree import ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from collect import PROGRAMS
from country_guides import build_country, directory, difference, editions, four_weeks_before

TOOL = {'id': 'processinghistory', 'url': '/processinghistory/', 'source': 'https://github.com/jsdyer/processinghistory'}


def row(issued, label):
    return {'issued': issued, 'label': label, 'observed': (issued or '2022-12-01') + 'T12:30:00Z',
            'evidence': 'https://example.ca/record'}


class CountryGuides(unittest.TestCase):
    def test_nearest_earlier_edition_is_dated_and_bounded(self):
        rows = [row('2026-09-10', '5 weeks'), row('2026-10-22', '2 weeks'),
                row('2026-10-22', '3 weeks'), row('2026-11-01', '4 weeks'), row('2026-11-25', '30 days')]
        timeline = editions(rows)
        self.assertEqual(four_weeks_before(rows[-1], timeline)['label'], '3 weeks')
        self.assertIsNone(four_weeks_before(rows[-1], timeline[:1]))
        self.assertIsNone(four_weeks_before(row(None, '1 week'), timeline))
        self.assertIn('9 days longer', difference('30 days', '3 weeks'))
        self.assertIn('2 weeks shorter', difference('1 week', '3 weeks'))
        self.assertIsNone(difference('No processing time available', '3 days'))

    def test_keep_withdrawn_profiles_exclude_thin_series_and_only_index_active(self):
        with tempfile.TemporaryDirectory() as directory_name:
            stage = Path(directory_name)
            rows = [row('2026-10-21', '7 days'), row('2026-11-11', '4 days')]
            histories = {key: rows[:] for key in PROGRAMS}
            checked = '2026-11-27T11:23:00Z'
            active = build_country(stage, TOOL, 'AA', 'Example & District', histories, checked)
            inactive_histories = {k: v + [row('2026-11-25', None if k == 'work' else 'No processing time available')]
                                  for k, v in histories.items()}
            inactive = build_country(stage, TOOL, 'BB', 'Example County', inactive_histories, checked)
            thin = {k: [row('2026-11-11', 'No processing time available')] for k in PROGRAMS}
            self.assertIsNone(build_country(stage, TOOL, 'CC', 'Example Region', thin, checked))
            self.assertEqual(active['active'], 4)
            self.assertEqual(inactive['active'], 0)
            directory(stage, TOOL, [active, inactive], checked)
            retired_html = (stage / 'records/bb/index.html').read_text()
            self.assertIn('noindex,follow', retired_html)
            self.assertIn('No row in this capture', retired_html)
            self.assertIn('No processing time available', retired_html)
            self.assertIn('last dated estimate', retired_html)
            self.assertIn('<a href="../">', retired_html)
            urls = [tag.text for tag in ET.parse(stage / 'sitemap.xml').findall('.//{*}loc')]
            self.assertEqual(urls, ['https://coolcode.ca/processinghistory/records/',
                                    'https://coolcode.ca/processinghistory/records/aa/'])
            self.assertIn('Example &amp; District', (stage / 'records/index.html').read_text())
