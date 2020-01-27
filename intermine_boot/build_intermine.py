import os
import tempfile
import subprocess
import re
import sys
import click
from git import Repo, RemoteProgress

IM_INSTALL_DIRS = [['plugin'], ['intermine'], ['bio'],
                   ['bio', 'sources'], ['bio', 'postprocess']]

IM_VERSION_PATH = ['intermine', 'build.gradle']
BIO_VERSION_PATH = ['bio', 'build.gradle']

def op_code_to_label(op_code):
    if op_code == 33:
        return 'Receiving objects:'
    if op_code == 65:
        return 'Resolving deltas:'
    return ''


class GitProgressPrinter(RemoteProgress):
    progress = None

    def update(self, op_code, cur_count, max_count=100.0, message=''):
        if cur_count <= 1:
            self.progress = click.progressbar(length=int(max_count),
                                              label=op_code_to_label(op_code))
        self.progress.pos = cur_count
        self.progress.update(0)

        if cur_count == max_count:
            self.progress.render_finish()


def read_version_string(file_path):
    with open(file_path) as file:
        for line in file:
            match = re.findall(r'version[\s=]+\'(.*)\'', line)
            if match:
                return match[0]

    click.echo('Failed to read version string from ' + file_path, err=True)
    click.echo("It's likely the source files have changed and intermine_boot needs to be updated to work again.", err=True)
    sys.exit(1)


def main(im_repo, im_branch):
    with tempfile.TemporaryDirectory(prefix='intermine_boot_') as tmpdir:

        click.echo('Cloning GitHub repository for building InterMine')

        im_repo_dir = os.path.join(tmpdir, 'intermine')

        Repo.clone_from(im_repo, im_repo_dir,
                        progress=GitProgressPrinter(),
                        multi_options=['--single-branch',
                                       '--branch ' + im_branch])

        click.echo('Will build ' + im_branch + ' branch of ' + im_repo)

        with click.progressbar(length=len(IM_INSTALL_DIRS)*2,
                               show_eta=False,
                               label='Building InterMine:') as im_progress:

            im_progress.update(0)

            for install_dir in IM_INSTALL_DIRS:

                subprocess.run(['./gradlew', 'clean'],
                               check=True,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE,
                               cwd=os.path.join(im_repo_dir, *install_dir))
                im_progress.update(1)
                subprocess.run(['./gradlew', 'install'],
                               check=True,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE,
                               cwd=os.path.join(im_repo_dir, *install_dir))
                im_progress.update(1)

        im_build_file = os.path.join(im_repo_dir, *IM_VERSION_PATH)
        bio_build_file = os.path.join(im_repo_dir, *BIO_VERSION_PATH)

        return {
            'im_version': read_version_string(im_build_file),
            'bio_version': read_version_string(bio_build_file)
        }
