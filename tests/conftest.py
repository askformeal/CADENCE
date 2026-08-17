import wave

import pytest


@pytest.fixture
def audio_file(tmp_path):
    """Generate a short silent WAV file so tests don't depend on real audio."""
    path = tmp_path / 'test_audio.wav'
    with wave.open(str(path), 'wb') as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(8000)
        f.writeframes(b'\x00\x00' * (8000 * 3))
    return str(path)


@pytest.fixture
def database(tmp_path):
    """Database isolated in a temp file, never touching the real user DB."""
    from src.database import Database

    db = Database(tmp_path / 'test.db')
    yield db
    db.on_exit()


@pytest.fixture
def backend(tmp_path, monkeypatch):
    """Full backend with temp DB; player state must be cleaned up after."""
    monkeypatch.setattr('src.backend.DATABASE_PATH', tmp_path / 'test.db')
    from src.backend import Backend

    b = Backend()
    yield b
    b.exit()
    b.database.on_exit()
    b.player.on_exit()
