import json
from pathlib import Path
import tempfile
import unittest
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from collect import pack,retain,read_json

class CaptureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.history=Path(__file__).resolve().parents[1]/'web/data/history'
        cls.sample=read_json(next(iter(sorted(cls.history.glob('*.json')))),[])[0]
    def source(self):
        s=self.sample
        return {k:{**{c:s['dictionary'][i] for c,i in zip(s['countries'],r['values']) if i},'lastupdated':'September 4, 2018'} for k,r in s['programs'].items()}
    def test_missing_edition_stays_missing(self):
        d=self.source();d['work']['lastupdated']=''
        s=pack(json.dumps(d).encode(),'2018-09-09T00:00:00Z','https://example.org/')
        self.assertIsNone(s['programs']['work']['issued'])
    def test_invalid_partial_source_rejected(self):
        d=self.source();d['work']={'lastupdated':'September 4, 2018'}
        with self.assertRaises(ValueError):pack(json.dumps(d).encode(),'2018-09-09T00:00:00Z','https://example.org/')
    def test_duplicate_and_source_correction(self):
        with tempfile.TemporaryDirectory() as temp:
            self.assertTrue(retain(Path(temp),self.sample))
            self.assertFalse(retain(Path(temp),self.sample))
            with self.assertRaises(ValueError):retain(Path(temp),dict(self.sample,sha256='different'))
