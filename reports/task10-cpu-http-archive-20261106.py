"""Read qualified archive members without the hanging object-store filesystem.

Reuses an existing exact-key GET capability. Does not issue Zenith API calls,
change scoring, or claim that an additional immutable object was created.
"""
from pathlib import Path
import hashlib
import io
import json
import tarfile
import time
from urllib.parse import urlsplit

import requests


class RangeReader(io.RawIOBase):
    def __init__(self, url):
        assert urlsplit(url).scheme == 'https'
        self.session = requests.Session()
        self.session.trust_env = False
        self.url = url
        self.position = 0
        self.etag = None
        first, headers = self._range(0, 1)
        assert len(first) == 1
        self.size = int(headers['Content-Range'].rsplit('/', 1)[1])
        self.etag = headers.get('ETag')
        assert self.etag, 'archive ETag missing'

    def _range(self, start, size):
        headers = {'Range': f'bytes={start}-{start + size - 1}'}
        if self.etag:
            headers['If-Match'] = self.etag
        try:
            with self.session.get(self.url, headers=headers, stream=True, timeout=(10, 45)) as r:
                if r.status_code == 412:
                    raise RuntimeError('archive changed during read; retry CPU verification')
                if r.status_code != 206:
                    raise RuntimeError(f'archive range HTTP status {r.status_code}')
                content_range = r.headers.get('Content-Range', '')
                assert content_range.startswith(f'bytes {start}-'), 'archive range offset mismatch'
                chunks = []
                received = 0
                for chunk in r.iter_content(chunk_size=1024 * 1024):
                    received += len(chunk)
                    assert received <= size, 'archive range exceeded requested bound'
                    chunks.append(chunk)
                return b''.join(chunks), r.headers.copy()
        except requests.RequestException as e:
            # Requests exceptions can contain the capability URL. Never propagate it.
            raise RuntimeError('archive HTTP transport: ' + type(e).__name__) from None

    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        return self.position

    def seek(self, offset, whence=io.SEEK_SET):
        target = offset if whence == io.SEEK_SET else (
            self.position + offset if whence == io.SEEK_CUR else self.size + offset)
        if target < 0:
            raise ValueError('negative archive seek')
        self.position = target
        return target

    def read(self, size=-1):
        if self.position >= self.size:
            return b''
        if size is None or size < 0:
            size = self.size - self.position
        size = min(size, self.size - self.position)
        if not size:
            return b''
        raw, _ = self._range(self.position, size)
        assert len(raw) == size, 'short HTTP archive range'
        self.position += size
        return raw

    def close(self):
        self.session.close()
        super().close()


class VerifiedBlob(bytes):
    def __new__(cls, raw, proof):
        obj = super().__new__(cls, raw)
        obj.proof = proof
        return obj


def obtain_http_blob(root, meta):
    root = Path(root)
    key = meta['object_key']
    assert key.startswith('liyufeng/safelab_task10_new_variants_20261102/attach_stable_grasp_20261106/')
    assert f'/{root.name}/pack_gpu' in key
    bundle = json.loads((root / 'UPLOAD_CAPABILITIES_PRIVATE.json').read_text())
    slot = next(s for s in bundle['packs'].values() if s['key'] == key)
    assert slot['GET']['expires_epoch'] > time.time(), 'existing archive capability expired'
    assert meta['HTTPS_PUT_GET_verified'] and meta['qualified']
    sha = meta['member_sha256']
    with RangeReader(slot['GET']['url']) as reader:
        with tarfile.open(fileobj=reader, mode='r:') as outer:
            for member in outer:
                if member.name != meta['member'] or not member.isfile():
                    continue
                if member.size != meta['member_bytes']:
                    continue
                with outer.extractfile(member) as f:
                    raw = f.read()
                if hashlib.sha256(raw).hexdigest() != sha:
                    continue
                proof = {
                    'source_pack': key, 'source_member': member.name,
                    'member_sha256': sha, 'HTTP_member_SHA_verified': True,
                    'HTTP_snapshot_etag': reader.etag, 'HTTP_snapshot_bytes': reader.size,
                    'member_offset_data': member.offset_data,
                    'original_PUT_GET_verified': True,
                    'retention_validation': 'Original qualified HTTPS archive plus direct HTTPS range member SHA; no filesystem copy claimed.',
                    'immutable_copy_pending': True,
                }
                return VerifiedBlob(raw, proof)
    raise RuntimeError('qualified member not found in current HTTP archive')


def retain_archived_member(blob, sha):
    assert isinstance(blob, VerifiedBlob)
    assert hashlib.sha256(blob).hexdigest() == sha == blob.proof['member_sha256']
    return dict(blob.proof)
