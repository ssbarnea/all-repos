import json
import subprocess
import sys
from unittest import mock

import pytest

from all_repos import clone
from testing.auto_namedtuple import auto_namedtuple
from testing.git import revparse


def _init_repo(pth):
    subprocess.check_call(('git', 'init', pth))
    subprocess.check_call((
        'git', '-C', pth, 'commit', '--allow-empty', '-m', pth,
    ))
    subprocess.check_call((
        'git', '-C', pth, 'config',
        'receive.denyCurrentBranch', 'updateInstead',
    ))
    return revparse(pth)


@pytest.fixture
def file_config(tmpdir):
    dir1 = tmpdir.join('1')
    dir2 = tmpdir.join('2')
    rev1 = _init_repo(dir1)
    rev2 = _init_repo(dir2)

    repos_json = tmpdir.join('repos.json')
    repos_json.write(json.dumps({'repo1': str(dir1), 'repo2': str(dir2)}))

    cfg = tmpdir.join('config.json')
    cfg.write(json.dumps({
        'output_dir': 'output',
        'source': 'all_repos.source.json_file',
        'source_settings': {'filename': str(repos_json)},
        'push': 'all_repos.push.merge_to_master',
        'push_settings': {},
    }))
    cfg.chmod(0o600)
    return auto_namedtuple(
        output_dir=tmpdir.join('output'),
        cfg=cfg,
        repos_json=repos_json,
        dir1=dir1,
        dir2=dir2,
        rev1=rev1,
        rev2=rev2,
    )


def _write_file_commit(git, filename, contents):
    git.join(filename).write(contents)
    subprocess.check_call(('git', '-C', git, 'add', '.'))
    subprocess.check_call(('git', '-C', git, 'commit', '-mfoo'))


@pytest.fixture
def file_config_files(file_config):
    _write_file_commit(file_config.dir1, 'f', 'OHAI\n')
    _write_file_commit(file_config.dir2, 'f', 'OHELLO\n')
    clone.main(('--config-filename', str(file_config.cfg)))
    return file_config


@pytest.fixture(autouse=True)
def not_a_tty():
    with mock.patch.object(sys.stdout, 'isatty', return_value=False) as mck:
        yield mck