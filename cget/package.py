from urllib.request import urlretrieve
import os
import sys
import shutil
import json
import click
from cget import util
from cget.util import cmd
from cget.cmake import CMake
from cget.boost import Boost, is_boost
import cget.cmake as cmake
from cget.boost import Boost

CLEAN = 0
FETCHED = 1
CONFIGURED = 2
BUILT = 3
INSTALLED = 4


class Package:
    def __init__(self, name, data, config):
        self.name = name
        self.archive = data.get('archive', None)
        self.url = data.get('url', None)
        self.config = config
        self.builder = self.builder_by_name(data.get('builder', None))
        if name is not None and self.builder is None:
            src = self.src_dir()
            if os.path.isdir(src):
                self.choose_builder(src)

    def builder_by_name(self, builder_name):
        if builder_name is None:
            return None
        elif builder_name == 'cmake':
            return CMake(cmake=self.config.cmake_executable(), install_root=self.config.install_root)
        elif builder_name == 'boost':
            return Boost(install_root=self.config.install_root)

    def choose_builder(self, src_dir):
        try:
            self.name = cmake.parse_project_name(src_dir)
            self.builder = CMake(cmake=self.config.cmake_executable(), install_root=self.config.install_root)
        except FileNotFoundError:
            if is_boost(src_dir):
                self.name = 'boost'
                self.builder = Boost(install_root=self.config.install_root)
        print('Package name is', self.name)

    def save(self):
        with open(os.path.join(self.config.package_dir, self.name + '.json'), 'w') as outfile:
            json.dump({
                'archive': self.archive,
                'url': self.url,
                'builder': self.builder.name
            }, outfile, indent=4)

    def src_dir(self):
        return os.path.join(self.config.src_root(), self.name)

    def build_dir(self):
        return os.path.join(self.config.build_root(), self.name)

    def is_fetched(self):
        if self.name is None or self.builder is None:
            return False
        return self.builder.is_fetched(self.src_dir(), self.name)

    def fetch(self):
        fn = os.path.join(self.config.arch_root(), self.archive)
        if os.path.isfile(fn):
            click.echo('Using cached archive {0} '.format(fn))
        else:
            try:
                click.echo('Fetching file {0} ...'.format(self.url))
                urlretrieve(self.url, fn)
                click.echo('Ok.')
            except ConnectionError as e:
                click.echo(str(e))
                sys.exit(2)
        temp_dir = os.path.abspath('temp')

        re_extract = False
        exists = os.path.isdir(temp_dir)
        if not exists or re_extract:
            click.echo("Extracting archive {0} ...".format(fn))
            if exists:
                util.delete_dir(temp_dir)
            os.mkdir(temp_dir)
            util.extract_ar(archive=fn, dst=temp_dir)
        else:
            click.echo("Extracting skipped: using temporary")

        dirs = [o for o in os.listdir(temp_dir) if os.path.isdir(os.path.join(temp_dir, o))]
        if len(dirs) != 1:
            raise Exception('Wrong dir count')
        temp_src_dir = os.path.join(temp_dir, dirs[0])
        self.choose_builder(temp_src_dir)
        src_dir = self.src_dir()
        util.delete_dir(src_dir)
        os.rename(temp_src_dir, src_dir)
        util.delete_dir(temp_dir)
        self.stage = FETCHED
        self.save()
        click.echo("Sources placed to {0}".format(src_dir))

    def gui(self):
        bd = self.build_dir()
        if not os.path.isdir(bd):
            self.configure()
        gui = self.config.cmake_gui_executable()
        cmd([gui, bd])

    def configure(self):
        if not self.is_fetched():
            self.fetch()
        bd = self.build_dir()
        click.echo('Configuring {0}'.format(self.name))
        if not os.path.isdir(bd):
            os.mkdir(bd)
        self.builder.configure(src_dir=self.src_dir(), build_dir=bd, options=self.config.options)
        self.stage = CONFIGURED
        #self.config.update_package(self)

    def build(self):
        #if self.stage is None or self.stage < CONFIGURED:
        #    self.configure()
        click.echo('Building {0}'.format(self.name))
        self.builder.build(src_dir=self.src_dir(), build_dir=self.build_dir(), options=self.config.options)
        self.stage = BUILT
        #self.config.update_package(self)

    def install(self):
        #if self.stage is None or self.stage < BUILT:
        #    self.build()
        click.echo('Installing {0}'.format(self.name))
        self.builder.install(src_dir=self.src_dir(), build_dir=self.build_dir(), options=self.config.options)
        # Commit
        self.stage = INSTALLED
        #self.config.update_package(self)

    def clean(self):
        click.echo('Removing build and source directories')
        util.delete_dir(self.build_dir())
        util.delete_dir(self.src_dir())
        self.stage = CLEAN
        #self.config.update_package(self)
