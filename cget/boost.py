import os
from cget.util import cmd


def is_boost(directory):
    return os.path.isfile(os.path.join(directory, 'bootstrap.bat')) \
           or os.path.isfile(os.path.join(directory, 'bootstrap.sh'))


class Boost:
    def __init__(self, install_root=None):
        self.name = 'boost'
        self.install_root = install_root

    def is_fetched(self, src_dir, name):
        if name != 'boost':
            return False
        return is_boost(src_dir)

    def configure(self, src_dir=None, build_dir=None, options=None):
        args = [os.path.join(src_dir, 'bootstrap.bat')]
        cmd(args, cwd=src_dir)

    def build(self, src_dir: str = None, build_dir: str = None, options: dict = None, install: bool = True) -> object:
        b2 = os.path.join(src_dir, 'b2.exe')
        if not os.path.isfile(b2):
            self.configure(src_dir=src_dir, build_dir=build_dir, options=options)
        args = [b2] # os.path.join(src_dir, './b2'),
        args.append('--prefix=' + self.install_root)
        if build_dir is not None:
            args.append('--build-dir=' + build_dir)
        variant = options.get('config', None)
        if variant is not None:
            args.append('variant=' + variant.lower())
        generator = options.get('generator', None)
        if generator is not None:
            if generator.startswith('Visual Studio'):
                args.append('toolset=msvc')
            if generator.endswith('Win64'):
                args.append('address-model=64')
                args.append('architecture=x86')
        static = options.get('static', None)
        if static is not None:
            if static:
                args.append('link=static')
            else:
                args.append('link=shared')
        if install:
            args.append('install')
        else:
            args.append('stage')
        cmd(args, cwd=src_dir)

    def install(self, **kwargs):
        self.build(install=True, **kwargs)
