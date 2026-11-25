"""Storage-level atomic replacement, not multi-worker read/modify/write safety."""
import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from app.models.schema import IdeaBrief, SessionData
from app.services.session_storage import FileStorage


def session(label):
    return SessionData(
        session_id='same',
        idea_brief=IdeaBrief(raw_input=label, normalized_summary=label),
        created_at='2026-01-01', updated_at='2026-01-01',
    )


def test_concurrent_complete_saves_use_independent_temporaries(tmp_path, monkeypatch):
    stores = [FileStorage(str(tmp_path)), FileStorage(str(tmp_path))]
    gate = threading.Barrier(2)
    write_text = Path.write_text
    fdopen = os.fdopen

    def synchronized_write(path, *args, **kwargs):
        result = write_text(path, *args, **kwargs)
        if path.name.endswith('.tmp'):
            gate.wait(timeout=5)
        return result

    class SynchronizedFile:
        def __init__(self, handle):
            self.handle = handle

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return self.handle.__exit__(*args)

        def write(self, data):
            result = self.handle.write(data)
            self.handle.flush()
            gate.wait(timeout=5)
            return result

    monkeypatch.setattr(Path, 'write_text', synchronized_write)
    monkeypatch.setattr(os, 'fdopen', lambda *a, **k: SynchronizedFile(fdopen(*a, **k)))
    with ThreadPoolExecutor(2) as executor:
        futures = [executor.submit(stores[i].save, 'same', session(str(i))) for i in range(2)]
        for future in futures:
            future.result(timeout=10)
    assert json.loads((tmp_path / 'same.json').read_text())['idea_brief']['raw_input'] in {'0', '1'}
    assert list(tmp_path.glob('*.tmp')) == []


def test_replace_failure_preserves_previous_session_and_cleans_temp(tmp_path, monkeypatch):
    store = FileStorage(str(tmp_path))
    store.save('same', session('previous'))
    previous = (tmp_path / 'same.json').read_bytes()

    def fail(*args, **kwargs):
        raise OSError('synthetic replace failure')

    monkeypatch.setattr(Path, 'replace', fail)
    with pytest.raises(OSError, match='synthetic replace'):
        store.save('same', session('new'))
    assert (tmp_path / 'same.json').read_bytes() == previous
    assert list(tmp_path.glob('*.tmp')) == []


def test_serialization_failure_leaves_no_temporary(tmp_path):
    store = FileStorage(str(tmp_path))

    class BrokenSession:
        def model_dump_json(self):
            raise ValueError('synthetic serialization failure')

    with pytest.raises(ValueError, match='synthetic serialization'):
        store.save('same', BrokenSession())
    assert list(tmp_path.iterdir()) == []


@pytest.mark.skipif(os.name == 'nt', reason='POSIX file modes')
def test_existing_group_readable_mode_is_preserved(tmp_path):
    store = FileStorage(str(tmp_path))
    store.save('same', session('old'))
    (tmp_path / 'same.json').chmod(0o664)
    store.save('same', session('new'))
    assert (tmp_path / 'same.json').stat().st_mode & 0o777 == 0o664


@pytest.mark.skipif(os.name == 'nt', reason='POSIX umask')
@pytest.mark.parametrize('mask,expected', [(0o022, 0o644), (0o077, 0o600)])
def test_new_file_uses_kernel_umask_in_isolated_process(tmp_path, mask, expected):
    import subprocess
    import sys

    code = """
import os, sys
from app.services.session_storage import FileStorage
class Payload:
    def model_dump_json(self): return '{}'
os.umask(int(sys.argv[2]))
FileStorage(sys.argv[1]).save('fresh', Payload())
"""
    subprocess.run([sys.executable, '-c', code, str(tmp_path), str(mask)], check=True)
    assert (tmp_path / 'fresh.json').stat().st_mode & 0o777 == expected


def test_fdopen_failure_closes_descriptor_and_removes_temp(tmp_path, monkeypatch):
    store = FileStorage(str(tmp_path))
    descriptors = []

    def fail(fd, *args, **kwargs):
        descriptors.append(fd)
        raise OSError('synthetic fdopen failure')

    monkeypatch.setattr(os, 'fdopen', fail)
    with pytest.raises(OSError, match='synthetic fdopen'):
        store.save('same', session('new'))
    assert list(tmp_path.iterdir()) == []
    with pytest.raises(OSError):
        os.fstat(descriptors[0])


def test_exclusive_name_collision_retries_without_touching_other_file(tmp_path, monkeypatch):
    import app.services.session_storage as module

    occupied = tmp_path / '.same.json.occupied.tmp'
    occupied.write_text('other writer')
    names = iter(['occupied', 'fresh'])
    monkeypatch.setattr(module.secrets, 'token_hex', lambda n: next(names))
    FileStorage(str(tmp_path)).save('same', session('new'))
    assert occupied.read_text() == 'other writer'
    assert not (tmp_path / '.same.json.fresh.tmp').exists()


@pytest.mark.skipif(os.name == 'nt', reason='POSIX fchmod')
def test_mode_copy_failure_closes_descriptor_and_preserves_target(tmp_path, monkeypatch):
    store = FileStorage(str(tmp_path))
    store.save('same', session('previous'))
    previous = (tmp_path / 'same.json').read_bytes()
    descriptors = []

    def fail(fd, mode):
        descriptors.append(fd)
        raise OSError('synthetic chmod failure')

    monkeypatch.setattr(os, 'fchmod', fail)
    with pytest.raises(OSError, match='synthetic chmod'):
        store.save('same', session('new'))
    assert (tmp_path / 'same.json').read_bytes() == previous
    assert list(tmp_path.glob('*.tmp')) == []
    with pytest.raises(OSError):
        os.fstat(descriptors[0])
