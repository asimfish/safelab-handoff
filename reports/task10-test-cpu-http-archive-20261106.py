import hashlib
import io
import json
from pathlib import Path
import tarfile
import tempfile
import time
import unittest
from unittest.mock import patch

import requests
import cpu_http_archive as module


class FakeResponse:
    def __init__(self, status, raw, headers):
        self.status_code = status
        self.raw = raw
        self.headers = requests.structures.CaseInsensitiveDict(headers)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def iter_content(self, chunk_size):
        yield self.raw


class FakeSession:
    archive = b''
    changed = False
    ignore_range = False

    def get(self, url, headers, **kwargs):
        if self.changed and 'If-Match' in headers:
            return FakeResponse(412, b'', {})
        if self.ignore_range:
            return FakeResponse(200, b'', {})
        a, b = map(int, headers['Range'].split('=')[1].split('-'))
        b = min(b, len(self.archive) - 1)
        return FakeResponse(206, self.archive[a:b + 1],
                            {'content-range': f'bytes {a}-{b}/{len(self.archive)}', 'etag': 'snapshot1'})

    def close(self):
        pass


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / 'fixture'
        self.root.mkdir()
        self.key = 'liyufeng/safelab_task10_new_variants_20261102/attach_stable_grasp_20261106/fixture/pack_gpu0.tar'
        self.target = b'a complete closed case fixture'
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode='w:') as t:
            for name, raw in [('case.tar.gz', b'old'), ('case.tar.gz', self.target), ('later', b'unrelated')]:
                info = tarfile.TarInfo(name)
                info.size = len(raw)
                t.addfile(info, io.BytesIO(raw))
        FakeSession.archive = buf.getvalue()
        FakeSession.changed = FakeSession.ignore_range = False
        self.meta = {'object_key': self.key, 'member': 'case.tar.gz',
                     'member_bytes': len(self.target), 'member_sha256': hashlib.sha256(self.target).hexdigest(),
                     'HTTPS_PUT_GET_verified': True, 'qualified': True}
        self.write_cap(time.time() + 300)
        self.mock = patch.object(module.requests, 'Session', FakeSession)
        self.mock.start()

    def tearDown(self):
        self.mock.stop()
        self.tmp.cleanup()

    def write_cap(self, expiry):
        (self.root / 'UPLOAD_CAPABILITIES_PRIVATE.json').write_text(json.dumps(
            {'packs': {'0': {'key': self.key, 'GET': {'url': 'https://example.invalid/private', 'expires_epoch': expiry}}}}))

    def test_valid_exact_member_and_proof(self):
        blob = module.obtain_http_blob(self.root, self.meta)
        self.assertEqual(blob, self.target)
        proof = module.retain_archived_member(blob, self.meta['member_sha256'])
        self.assertTrue(proof['HTTP_member_SHA_verified'])
        self.assertTrue(proof['immutable_copy_pending'])
        self.assertNotIn('immutable_case_object_key', proof)
        self.assertNotIn('url', proof)

    def test_unrelated_truncated_tail_does_not_hide_valid_closed_member(self):
        # The qualified earlier member remains intact; a later TAR body is incomplete.
        raw = FakeSession.archive
        with tarfile.open(fileobj=io.BytesIO(raw), mode='r:') as t:
            final = list(t)[-1]
        FakeSession.archive = raw[:final.offset_data]
        self.assertEqual(module.obtain_http_blob(self.root, self.meta), self.target)

    def test_sha_mismatch_is_never_qualified(self):
        self.meta['member_sha256'] = '0' * 64
        with self.assertRaises(RuntimeError):
            module.obtain_http_blob(self.root, self.meta)

    def test_changed_etag_is_retry_not_result(self):
        FakeSession.changed = True
        with self.assertRaisesRegex(RuntimeError, 'changed during read'):
            module.obtain_http_blob(self.root, self.meta)

    def test_server_ignoring_range_is_rejected_before_body(self):
        FakeSession.ignore_range = True
        with self.assertRaisesRegex(RuntimeError, 'HTTP status 200'):
            module.obtain_http_blob(self.root, self.meta)

    def test_expired_capability_is_rejected(self):
        self.write_cap(time.time() - 1)
        with self.assertRaisesRegex(AssertionError, 'expired'):
            module.obtain_http_blob(self.root, self.meta)

    def test_cross_workpack_key_is_rejected(self):
        self.meta['object_key'] = self.key.replace('/fixture/', '/different/')
        with self.assertRaises(AssertionError):
            module.obtain_http_blob(self.root, self.meta)

    def test_retention_rechecks_member_sha(self):
        blob = module.obtain_http_blob(self.root, self.meta)
        with self.assertRaises(AssertionError):
            module.retain_archived_member(blob, '0' * 64)


if __name__ == '__main__':
    unittest.main()
