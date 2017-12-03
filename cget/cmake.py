import re
import os
from cget.util import cmd, delete_dir


def parse_project_name(directory):
    fn = os.path.join(directory, 'CMakeLists.txt')
    if not os.path.isfile(fn):
        raise FileNotFoundError('CMakeLists.txt not found')
    with open(fn, 'r') as file:
        for line in file:
            g = re.match('^\s*project\s*\(\s*([\w-]+)(?:\s.*)?\)', line.lower())
            if g is not None:
                return g.group(1)
    raise ValueError('Unable to parse CMake project name')


def parse_cache(directory, names):
    fn = os.path.join(directory, 'CMakeCache.txt')
    if not os.path.isfile(fn):
        raise FileNotFoundError('CMakeCache.txt not found')
    result = {}
    with open(fn, 'r') as file:
        for line in file:
            g = re.match('^\s*([\w:]+)=(.*)\s*$', line)
            if g is not None and g.group(1) in names:
                result.update({g.group(1): g.group(2)})
    return result


class CMake:
    def __init__(self, cmake=None, install_root=None):
        self.install_root = install_root
        self.cmake = cmake
        self.name = 'cmake'

    def need_reconfig(self, build_dir, options):
        if not os.path.isdir(build_dir):
            return False
        try:
            generator = options.get('generator', None)
            if generator is None:
                return False
            cache = parse_cache(build_dir, ['CMAKE_GENERATOR:INTERNAL'])
            return cache.get('CMAKE_GENERATOR:INTERNAL', None) != generator
        except FileNotFoundError:
            return True

    def configure(self, src_dir=None, build_dir=None, options=None):
        if self.need_reconfig(build_dir, options):
            delete_dir(build_dir)
        if not os.path.isdir(build_dir):
            os.mkdir(build_dir)
        args = [self.cmake, '-DCMAKE_INSTALL_PREFIX=' + self.install_root]
        for o, v in options.items():
            if o == 'define':
                args += ['-D' + d + '=' + dv for d, dv in v.items()]
            elif o == 'generator':
                args += ['-G', v]
        args.append(src_dir)
        cmd(args, cwd=build_dir)

    def build(self, src_dir=None, build_dir=None, options=None):
        args = [self.cmake, '--build', build_dir]
        cfg = options.get('config', None)
        if cfg is not None:
            args += ['--config', cfg]
        cmd(args, cwd=build_dir)

    def is_fetched(self, src_dir, name):
        try:
            return name == parse_project_name(src_dir)
        except FileNotFoundError or ValueError:
            return False
