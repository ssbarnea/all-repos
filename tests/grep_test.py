import subprocess
import sys
from unittest import mock

import pytest

from all_repos import clone
from all_repos.config import load_config
from all_repos.grep import grep
from all_repos.grep import main
from all_repos.grep import repos_matching


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


def test_repos_matching(file_config_files):
    config = load_config(file_config_files.cfg)
    ret = repos_matching(config, ['^OH'])
    assert ret == {'repo1', 'repo2'}
    ret = repos_matching(config, ['^OHAI'])
    assert ret == {'repo1'}
    ret = repos_matching(config, ['nope'])
    assert ret == set()


def test_repos_matching_cli(file_config_files, capsys):
    ret = main((
        '-C', str(file_config_files.cfg), '--repos-with-matches', '^OH',
    ))
    assert ret == 0
    out, _ = capsys.readouterr()
    assert out == '{}\n{}\n'.format(
        file_config_files.output_dir.join('repo1'),
        file_config_files.output_dir.join('repo2'),
    )

    ret = main((
        '-C', str(file_config_files.cfg), '--repos-with-matches', 'OHAI',
    ))
    assert ret == 0
    out, _ = capsys.readouterr()
    assert out == '{}\n'.format(file_config_files.output_dir.join('repo1'))

    ret = main((
        '-C', str(file_config_files.cfg), '--repos-with-matches', 'nope',
    ))
    assert ret == 1
    out, _ = capsys.readouterr()
    assert out == ''


def test_grep(file_config_files):
    config = load_config(file_config_files.cfg)
    ret = grep(config, ['^OH'])
    assert ret == {'repo1': b'f:OHAI\n', 'repo2': b'f:OHELLO\n'}
    ret = grep(config, ['^OHAI'])
    assert ret == {'repo1': b'f:OHAI\n'}
    ret = grep(config, ['nope'])
    assert ret == {}


def test_grep_cli(file_config_files, capsys):
    ret = main(('-C', str(file_config_files.cfg), '^OH'))
    assert ret == 0
    out, _ = capsys.readouterr()
    assert out == '{}:f:OHAI\n{}:f:OHELLO\n'.format(
        file_config_files.output_dir.join('repo1'),
        file_config_files.output_dir.join('repo2'),
    )

    ret = main(('-C', str(file_config_files.cfg), '^OHAI'))
    assert ret == 0
    out, _ = capsys.readouterr()
    assert out == '{}:f:OHAI\n'.format(
        file_config_files.output_dir.join('repo1'),
    )

    ret = main(('-C', str(file_config_files.cfg), 'nope'))
    assert ret == 1
    out, _ = capsys.readouterr()
    assert out == ''


def _test_grep_color(file_config_files, capsys, *, args=()):
    ret = main(('-C', str(file_config_files.cfg), 'OHAI', *args))
    assert ret == 0
    out, _ = capsys.readouterr()
    expected = (
        '\033[1;34m{}\033[m'
        '\033[36m:\033[m'
        'f'
        '\033[36m:\033[m'
        '\033[1;31mOHAI\033[m\n'
    ).format(file_config_files.output_dir.join('repo1'))
    assert out == expected


def test_grep_color_always(file_config_files, capsys):
    _test_grep_color(file_config_files, capsys, args=('--color', 'always'))


def test_grep_color_tty(file_config_files, capsys):
    with mock.patch.object(sys.stdout, 'isatty', return_value=True):
        _test_grep_color(file_config_files, capsys)


@pytest.mark.parametrize('args', ((), ('--repos-with-matches',)))
def test_grep_error(file_config_files, capfd, args):
    ret = main(('-C', str(file_config_files.cfg), *args))
    assert ret == 128
    out, err = capfd.readouterr()
    assert out == ''
    assert err == 'fatal: no pattern given.\n'
