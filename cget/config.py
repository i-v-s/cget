import os
import sys
import json
import re
import glob
import click
from cget.package import Package


class Config:
    def __init__(self, new=False):
        self.file_name = 'cget.json'
        self.package_dir = os.path.abspath('packages')
        self.name = None
        self.options = {}
        self.configs = {}
        self.default_cmake = 'cmake'
        self.default_cmake_gui = 'cmake-gui'
        if new:
            with open(self.file_name, 'x') as outfile:
                json.dump({'activeConfig': None, 'configs': {}}, outfile, indent=4)
        else:
            self.load()
        self.install_root = os.path.abspath('install-' + self.name)

    def load(self):
        data = json.load(open(self.file_name))
        self.name = data['activeConfig']
        self.configs = data['configs']
        if self.name is not None:
            self.options = self.configs[self.name]

    def save(self):
        data = {
            'activeConfig': self.name,
            'configs': self.configs,
        }
        with open(self.file_name, 'w') as outfile:
            json.dump(data, outfile, indent=4)

    def scan(self, path):
        path = os.path.join(path, '**/*onfig.cmake')
        result = 0
        defines = {}
        for fn in glob.iglob(path, recursive=True):
            (p, n) = os.path.split(fn)
            g = re.match('(\w+)Config.cmake', n)
            if g is None:
                g = re.match('(\w+)-config.cmake', n)
            if g is None:
                continue
            name = g.group(1)
            print('Found module ' + name)
            defines.update({name + '_DIR': p})
            result += 1
        self.options['define'].update(defines)
        return result

    def packages_gen(self, only_names=True):
        for fn in glob.iglob(os.path.join(self.package_dir, '*.json')):
            name = os.path.basename(fn)[:-5]
            if only_names:
                yield name
            else:
                yield Package(name, json.load(open(fn)), self)

    def set_active(self, name):
        self.name = name
        self.options = self.configs[name]

    def build_root(self, name=None):
        return os.path.abspath('build-' + (name or self.name))

    def arch_root(self):
        return os.path.abspath('src-arch')

    def src_root(self):
        return os.path.abspath('src')

    def cmake_executable(self):
        return self.options.get('cmake', self.default_cmake)

    def cmake_gui_executable(self):
        return self.options.get('cmake-gui', self.default_cmake_gui)

    def dump_configs(self):
        configs = self.configs
        if len(configs) > 0:
            for cf in configs.keys():
                if cf == self.name:
                    print('* ' + cf)
                else:
                    print('  ' + cf)
        else:
            print('No configs created.')

    def add(self, name, opts):
        self.configs.update({name: opts})
        os.mkdir(self.build_root(name))
        os.mkdir(self.install_root(name))

    def set(self, options):
        defines = self.options.get('define', {})
        if 'define' in options:
            defines.update(options['define'])
        self.configs[self.name].update(options)
        if defines:
            self.configs[self.name].update({'define': defines})
        self.options = self.configs[self.name]

    def get_package(self, string, new_if_nf=True):
        def parse_string(string):
            if re.match('^[\w-]+$', string) is not None:
                return string, None
            g = re.match('^([\w-]+),([\w:/\\\\-]+)$', string)
            if g is not None:
                return g.group(1), g.group(2)
            return (None, string)

        def parse_url(url):
            gh = re.match('^([\w-]+)/([\w-]+)$', url)
            if gh is not None:
                return gh.group(2), gh.group(2) + '.zip', 'https://github.com/' + url + '/archive/master.zip'
            u = re.match('^https?://(?:[\w/.]+/)+([\w\-.]+)$', url)
            if u is not None:
                return None, u.group(1), url

        (name, url) = parse_string(string)
        if name is not None:
            fn = os.path.join(self.package_dir, name + '.json')
            if os.path.isfile(fn):
                return Package(name, json.load(open(fn)), self)

        if new_if_nf:
            if url is None:
                click.echo('Package {0} not found'.format(name))
                sys.exit(2)
            (name, archive, url) = parse_url(url)
            return Package(name, {'archive': archive, 'url': url}, self)
        else:
            return None
