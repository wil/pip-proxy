import os
import errno
import shutil

from pip.vcs import vcs
def patched_update_editable(self, obtain=True):
    if not obtain:
        # don't support "export" yet
        return self._orig_update_editable(obtain=obtain)

    if os.path.exists(self.source_dir):
        # ignore and let it do its stuff
        return self._orig_update_editable(obtain=obtain)

    cache_path = os.path.expanduser(os.path.join('~', '.pipproxy', 'src', self.name))
    if os.path.exists(cache_path):
        # exists already, copy over (XXX: what if different branch / revision etc.?)
        print "Copying from %s to %s" % (cache_path, self.source_dir)
        shutil.copytree(cache_path, self.source_dir, symlinks=True)
        return self._orig_update_editable(obtain=obtain)

    try:
        os.makedirs(os.path.dirname(cache_path))
    except OSError, e:
        if e.errno != errno.EEXIST:
            raise

    if not self.url:
        return self._orig_update_editable(obtain=obtain)

    assert self.editable
    assert self.source_dir
    if self.url.startswith('file:'):
        # we don't care about file: urls
        return self._orig_update_editable(obtain=obtain)

    vc_type, url = self.url.split('+', 1)
    backend = vcs.get_backend(vc_type)
    if backend:
        vcs_backend = backend(self.url)
        vcs_backend.obtain(cache_path)
        shutil.copytree(cache_path, self.source_dir, symlinks=True)
    else:
        assert 0, (
            'Unexpected version control type (in %s): %s'
            % (self.url, vc_type))


def main():
    from pipproxy.pippatch.venv import restart_in_venv as patched_restart_in_venv
    import pip.venv
    import pip.basecommand
    pip.venv.restart_in_venv = patched_restart_in_venv
    pip.basecommand.restart_in_venv = patched_restart_in_venv


    from pip.req import InstallRequirement
    InstallRequirement._orig_update_editable, InstallRequirement.update_editable = \
        InstallRequirement.update_editable, patched_update_editable

    #InstallRequirement.update_editable = lambda *args, **kwargs: False

    #from pip.commands.install import InstallRequirement
    #InstallRequirement.update_editable = lambda *args, **kwargs: False

    from pip import main as pip_main
    pip_main()
