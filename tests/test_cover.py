"""Album cover extraction and the dashboard poster caches.

Three independent layers, each of which failed silently at least once:
mutagen extraction per container, the Cover byte cache keyed by hash, and the
rendered poster cache keyed by (width, height, hash).
"""

import base64
import hashlib
import io
import os
import wave

import mutagen.id3
import mutagen.wave
import pytest
from PIL import Image

from src.frontend.cover import Cover
from src.frontend.dash import core as dash_core
from src.utils.file_extract import _pick_front, extract_cover

FAKE_COVER = b'NOT_A_REAL_JPEG'  # extract_cover never decodes, only the frontends do


def _request(backend, action, **extra):
    request = {'action': action, 'cwd': os.getcwd()}
    request.update(extra)
    return backend.dispatch(request)


def _write_wav(path):
    with wave.open(str(path), 'wb') as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(8000)
        f.writeframes(b'\x00\x00' * 800)
    return path


@pytest.fixture
def covered_wav(tmp_path):
    """WAV carrying an ID3 APIC frame, the tag branch MP3 and WAV share."""
    path = _write_wav(tmp_path / 'covered.wav')
    file = mutagen.wave.WAVE(path)
    file.add_tags()
    file.tags.add(mutagen.id3.APIC(mime='image/jpeg', type=3, desc='cover', data=FAKE_COVER))
    file.save()
    return str(path)


@pytest.fixture
def bare_wav(tmp_path):
    return str(_write_wav(tmp_path / 'bare.wav'))


def test_pick_front_prefers_front_cover():
    other = mutagen.id3.APIC(type=0, data=b'OTHER')
    front = mutagen.id3.APIC(type=3, data=b'FRONT')

    assert _pick_front([other, front]) == b'FRONT'
    assert _pick_front([other]) == b'OTHER'
    assert _pick_front([]) is None


def test_extract_cover_from_id3(covered_wav):
    assert extract_cover(covered_wav) == FAKE_COVER


def test_extract_cover_folder_fallback(bare_wav, tmp_path):
    (tmp_path / 'cover.jpg').write_bytes(FAKE_COVER)

    assert extract_cover(bare_wav) == FAKE_COVER


def test_extract_cover_folder_fallback_ignores_other_images(bare_wav, tmp_path):
    (tmp_path / 'back.jpg').write_bytes(FAKE_COVER)

    assert extract_cover(bare_wav) is None


def test_extract_cover_without_any_cover(bare_wav):
    assert extract_cover(bare_wav) is None


def test_extract_cover_unreadable_file(tmp_path):
    """mutagen wraps file errors in MutagenError, so a missing path must not raise."""
    assert extract_cover(tmp_path / 'no_such_file.mp3') is None
    assert extract_cover(tmp_path) is None


def test_poll_cover_hash_before_open(backend):
    attachment = _request(backend, 'poll')['attachment']

    assert attachment['cover_hash'] is None


def test_cover_after_open(backend, covered_wav):
    _request(backend, 'open', song=covered_wav)

    attachment = _request(backend, 'poll')['attachment']
    assert attachment['cover_hash'] == hashlib.sha256(FAKE_COVER).hexdigest()

    response = _request(backend, 'get_cover')
    assert response['code'] == 0
    assert base64.b64decode(response['attachment']['cover']) == FAKE_COVER


def test_get_cover_without_cover(backend, bare_wav):
    _request(backend, 'open', song=bare_wav)

    attachment = _request(backend, 'poll')['attachment']
    assert attachment['cover_hash'] is None

    response = _request(backend, 'get_cover')
    assert response['code'] == 1
    assert 'Cover unavailable' in response['msg']


def _jpeg(color, size=16):
    buffer = io.BytesIO()
    Image.new('RGB', (size, size), color).save(buffer, 'JPEG')
    return buffer.getvalue()


COVER_A = _jpeg('red')
COVER_B = _jpeg('blue')
PLACEHOLDER = _jpeg('gray')

HASH_A = hashlib.sha256(COVER_A).hexdigest()
HASH_B = hashlib.sha256(COVER_B).hexdigest()


def _counting_requester(covers, calls):
    def requester(action, **kwargs):
        calls.append(kwargs.get('cover_hash', action))
        return {'cover': base64.b64encode(covers.pop(0)).decode('ascii')}
    return requester


def test_cover_cache_requests_once_per_hash():
    covers = [COVER_A, COVER_B]
    calls = []
    cover = Cover(_counting_requester(covers, calls), placeholder=PLACEHOLDER, logger=None)

    assert cover.get_cover(HASH_A) == COVER_A
    assert cover.get_cover(HASH_A) == COVER_A
    assert len(calls) == 1

    assert cover.get_cover(HASH_B) == COVER_B
    assert len(calls) == 2


def test_cover_placeholder_when_request_fails():
    calls = []
    cover = Cover(lambda action, **kwargs: calls.append(action), placeholder=PLACEHOLDER, logger=None)

    assert cover.get_cover(HASH_A) == PLACEHOLDER
    assert cover.get_cover(HASH_A) == PLACEHOLDER
    assert len(calls) == 1


def _fake_dash(size=(4, 4)):
    """A Dash without a terminal, holding only what gen_cover_text touches."""
    dash = dash_core.Dash.__new__(dash_core.Dash)
    dash.cover_text = ''
    dash.old_cover_state = (None, None, None)
    dash._cover_size = lambda: size
    return dash


@pytest.fixture
def rendered(monkeypatch):
    calls = []
    real = dash_core.render_tui_cover

    def spy(cover_bytes, width, height):
        calls.append((cover_bytes, width, height))
        return real(cover_bytes, width, height)

    monkeypatch.setattr(dash_core, 'render_tui_cover', spy)
    return calls


def test_poster_caches_between_frames(rendered):
    dash = _fake_dash()

    first = dash.gen_cover_text(COVER_A, HASH_A)
    assert len(rendered) == 1

    assert dash.gen_cover_text(COVER_A, HASH_A) == first
    assert len(rendered) == 1


def test_poster_rerenders_when_cover_comes_back(rendered):
    """Song with a cover -> song without one -> back: the placeholder must not stick."""
    dash = _fake_dash()

    covered = dash.gen_cover_text(COVER_A, HASH_A)
    placeholder = dash.gen_cover_text(PLACEHOLDER, None)
    assert len(rendered) == 2
    assert placeholder != covered

    assert dash.gen_cover_text(COVER_A, HASH_A) == covered
    assert len(rendered) == 3


def test_poster_rerenders_on_resize(rendered):
    dash = _fake_dash()

    before = dash.gen_cover_text(COVER_A, HASH_A)
    dash._cover_size = lambda: (8, 8)

    assert dash.gen_cover_text(COVER_A, HASH_A) != before
    assert len(rendered) == 2
