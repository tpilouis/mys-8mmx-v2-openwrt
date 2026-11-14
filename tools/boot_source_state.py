"""Check actual source contents without changing the developer's Git index."""
from pathlib import Path
import os
import subprocess
import tempfile


def verify_source_trees(root, policy, patch):
    trees = {}
    for name, source in policy['sources'].items():
        directory = Path(root) / name
        def git(*args, environment=None):
            return subprocess.check_output(['git', '-C', str(directory), *args],
                                           env=environment, stderr=subprocess.PIPE, text=True).strip()
        if git('rev-parse', 'HEAD') != source['commit']:
            raise ValueError('Unexpected source commit: ' + name)
        if name != 'u-boot':
            if git('diff', 'HEAD', '--'):
                raise ValueError('Unexpected tracked source modifications: ' + name)
            trees[name] = git('rev-parse', 'HEAD^{tree}')
            continue
        paths = [line.split('\t')[-1] for line in git('apply', '--numstat', str(patch)).splitlines()]
        with tempfile.TemporaryDirectory(prefix='myir-boot-index-') as temporary:
            environment = dict(os.environ, GIT_INDEX_FILE=str(Path(temporary) / 'index'))
            git('read-tree', 'HEAD', environment=environment)
            git('apply', '--cached', '--whitespace=nowarn', str(patch), environment=environment)
            expected = git('write-tree', environment=environment)
            git('read-tree', 'HEAD', environment=environment)
            git('add', '-u', environment=environment)
            git('add', '--', *paths, environment=environment)
            actual = git('write-tree', environment=environment)
            if actual != expected:
                raise ValueError('U-Boot source differs from the pinned base plus board patch')
            trees[name] = actual
    return trees
