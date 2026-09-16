"""Album cover extraction, the backend downscale, and the dashboard poster caches.

Three independent layers, each of which failed silently at least once:
mutagen extraction per container, the Cover byte cache keyed by hash, and the
rendered poster cache keyed by (width, height, hash).
"""

import base64
import hashlib
import io
import logging
import os
from pathlib import Path
import wave

import mutagen.id3
import mutagen.wave
import pytest
from PIL import Image

from src.constants import MAX_COVER_CACHE, MAX_COVER_SIDE
from src.frontend.cover import Cover
from src.frontend.dash import core as dash_core
from src.utils.file_extract import _pick_front, extract_cover


def _jpeg(color, size=16):
    if isinstance(size, int):
        size = (size, size)
    buffer = io.BytesIO()
    Image.new('RGB', size, color).save(buffer, 'JPEG', quality=90)
    return buffer.getvalue()


COVER_IMAGE = _jpeg('purple', 32)
COVER_A = _jpeg('red')
COVER_B = _jpeg('blue')
PLACEHOLDER = _jpeg('gray')
HASH_A = hashlib.sha256(COVER_A).hexdigest()
HASH_B = hashlib.sha256(COVER_B).hexdigest()
LOGGER = logging.getLogger(__name__)


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


def _open_and_get_cover(backend, song):
    _request(backend, 'open', song=song)
    attachment = _request(backend, 'poll')['attachment']
    response = _request(backend, 'get_cover')
    return attachment, response


@pytest.fixture
def covered_wav(tmp_path):
    """WAV carrying an ID3 APIC frame, the tag branch MP3 and WAV share."""
    path = _write_wav(tmp_path / 'covered.wav')
    file = mutagen.wave.WAVE(path)
    file.add_tags()
    file.tags.add(mutagen.id3.APIC(mime='image/jpeg', type=3, desc='cover', data=COVER_IMAGE))
    file.save()
    return str(path)


@pytest.fixture
def bare_wav(tmp_path):
    return str(_write_wav(tmp_path / 'bare.wav'))


@pytest.fixture
def folder_cover_wav(tmp_path):
    """WAV with a separate cover.jpg next to it, sized on request."""
    def build(color='green', size=(1200, 600)):
        folder = tmp_path / f'folder_{size[0]}x{size[1]}'
        folder.mkdir(exist_ok=True)
        (folder / 'cover.jpg').write_bytes(_jpeg(color, size))
        return str(_write_wav(folder / 'song.wav'))
    return build


def test_pick_front_prefers_front_cover():
    other = mutagen.id3.APIC(type=0, data=b'OTHER')
    front = mutagen.id3.APIC(type=3, data=b'FRONT')

    assert _pick_front([other, front]) == b'FRONT'
    assert _pick_front([other]) == b'OTHER'
    assert _pick_front([]) is None


def test_extract_cover_from_id3(covered_wav):
    assert extract_cover(covered_wav) == COVER_IMAGE


def test_extract_cover_folder_fallback(bare_wav, tmp_path):
    (tmp_path / 'cover.jpg').write_bytes(COVER_IMAGE)

    assert extract_cover(bare_wav) == COVER_IMAGE


def test_extract_cover_folder_fallback_ignores_other_images(bare_wav, tmp_path):
    (tmp_path / 'back.jpg').write_bytes(COVER_IMAGE)

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
    """The poll hash must describe the bytes get_cover actually serves, not the raw tag."""
    attachment, response = _open_and_get_cover(backend, covered_wav)
    data = base64.b64decode(response['attachment']['cover'])

    assert response['code'] == 0
    assert attachment['cover_hash'] == hashlib.sha256(data).hexdigest()
    with Image.open(io.BytesIO(data)) as image:
        assert image.format == 'JPEG'
        assert max(image.size) <= MAX_COVER_SIDE


def test_cover_is_downscaled(backend, folder_cover_wav):
    song = folder_cover_wav(size=(1200, 1200))

    attachment, response = _open_and_get_cover(backend, song)
    data = base64.b64decode(response['attachment']['cover'])

    with Image.open(io.BytesIO(data)) as image:
        assert image.size == (MAX_COVER_SIDE, MAX_COVER_SIDE)
    assert len(data) < (Path(song).parent / 'cover.jpg').stat().st_size


def test_cover_downscale_keeps_aspect(backend, folder_cover_wav):
    """A 2:1 cover must stay 2:1 with no black bars baked in."""
    song = folder_cover_wav(color='red', size=(1200, 600))

    attachment, response = _open_and_get_cover(backend, song)
    data = base64.b64decode(response['attachment']['cover'])

    with Image.open(io.BytesIO(data)) as image:
        assert image.size == (MAX_COVER_SIDE, MAX_COVER_SIDE // 2)
        red, green, blue = image.convert('RGB').getpixel((1, 1))
    assert (red, green, blue) != (0, 0, 0)


def test_cover_is_not_upscaled(backend, folder_cover_wav):
    song = folder_cover_wav(color='blue', size=(100, 100))

    attachment, response = _open_and_get_cover(backend, song)
    data = base64.b64decode(response['attachment']['cover'])

    with Image.open(io.BytesIO(data)) as image:
        assert image.size == (100, 100)


def test_get_cover_without_cover(backend, bare_wav):
    attachment = _request(backend, 'open', song=bare_wav)
    assert attachment['code'] == 0

    attachment = _request(backend, 'poll')['attachment']
    assert attachment['cover_hash'] is None

    response = _request(backend, 'get_cover')
    assert response['code'] == 1
    assert 'Cover unavailable' in response['msg']


def _folder_cover_song(tmp_path, name, cover_bytes):
    folder = tmp_path / name
    folder.mkdir()
    (folder / 'cover.jpg').write_bytes(cover_bytes)
    return str(_write_wav(folder / 'song.wav'))


def test_undecodable_cover_falls_back_to_placeholder(backend, tmp_path):
    """Garbage bytes named cover.jpg must not kill the poll, and must not leave a
    hash describing bytes that get_cover never served."""
    song = _folder_cover_song(tmp_path, 'garbage', b'this is not an image at all' * 40)

    _request(backend, 'open', song=song)
    attachment = _request(backend, 'poll')['attachment']

    assert attachment['cover_hash'] is None
    response = _request(backend, 'get_cover')
    assert response['code'] == 1
    assert 'Cover unavailable' in response['msg']


def test_truncated_cover_falls_back_to_placeholder(backend, tmp_path):
    """A cover missing its last bytes opens fine (Image.open only reads the header)
    and only fails when the pixels are decoded."""
    source = _jpeg('green', 400)
    song = _folder_cover_song(tmp_path, 'truncated', source[:len(source) - 200])

    _request(backend, 'open', song=song)
    attachment = _request(backend, 'poll')['attachment']

    assert attachment['cover_hash'] is None
    response = _request(backend, 'get_cover')
    assert response['code'] == 1


def test_broken_cover_does_not_retry_every_poll(backend, tmp_path, caplog):
    """The path is remembered even when processing fails, so a broken cover is
    warned about once instead of on every poll."""
    song = _folder_cover_song(tmp_path, 'garbage', b'not an image' * 40)

    _request(backend, 'open', song=song)
    with caplog.at_level('WARNING'):
        _request(backend, 'poll')
        warnings = _cover_warnings(caplog)
        _request(backend, 'poll')
        _request(backend, 'poll')

    assert len(warnings) == 1
    assert len(_cover_warnings(caplog)) == 1


def _cover_warnings(caplog):
    return [r for r in caplog.records if 'Failed to process cover' in r.getMessage()]


def _counting_requester(covers, calls):
    def requester(action, **kwargs):
        calls.append(kwargs.get('cover_hash', action))
        return {'cover': base64.b64encode(covers.pop(0)).decode('ascii')}
    return requester


def test_cover_cache_requests_once_per_hash():
    covers = [COVER_A, COVER_B]
    calls = []
    cover = Cover(_counting_requester(covers, calls), placeholder=PLACEHOLDER, logger=LOGGER)

    assert cover.get_cover(HASH_A) == COVER_A
    assert cover.get_cover(HASH_A) == COVER_A
    assert len(calls) == 1

    assert cover.get_cover(HASH_B) == COVER_B
    assert len(calls) == 2


def test_cover_cache_serves_a_previous_cover_from_memory():
    """A -> B -> A must come back out of the cache: the requester runs dry, so a
    third request would raise instead of quietly passing."""
    covers = [COVER_A, COVER_B]
    calls = []
    cover = Cover(_counting_requester(covers, calls), placeholder=PLACEHOLDER, logger=LOGGER)

    assert cover.get_cover(HASH_A) == COVER_A
    assert cover.get_cover(HASH_B) == COVER_B
    assert cover.get_cover(HASH_A) == COVER_A
    assert cover.get_cover(HASH_B) == COVER_B

    assert len(calls) == 2
    assert len(cover.cover_cache) == 2


def test_cover_cache_stays_bounded():
    """Every new song pushes a cover in, so the cache must evict instead of
    growing with the whole library."""
    counter = {'count': 0}

    def requester(action, **kwargs):
        counter['count'] += 1
        return {'cover': base64.b64encode(_jpeg((counter['count'], 0, 0))).decode('ascii')}

    cover = Cover(requester, placeholder=PLACEHOLDER, logger=LOGGER)
    for index in range(MAX_COVER_CACHE + 10):
        cover.get_cover(f'{HASH_A}-{index}')

    assert counter['count'] == MAX_COVER_CACHE + 10
    assert len(cover.cover_cache) <= MAX_COVER_CACHE


def test_cover_placeholder_when_request_fails():
    calls = []
    cover = Cover(lambda action, **kwargs: calls.append(action), placeholder=PLACEHOLDER, logger=LOGGER)

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
