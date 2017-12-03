import click, os, multiprocessing
import cget.util as util


class Builder:
    def __init__(self, prefix, arch_dir, src_dir, build_dir):
        self.prefix = prefix
        self.src_dir = src_dir
        self.arch_dir = arch_dir
        self.build_dir = build_dir # self.get_path('build')
        self.cmake_original_file = '__cget_original_cmake_file__.cmake'

    def get_path(self, *args):
        return os.path.join(self.top_dir, *args)

    def get_build_path(self, *args):
        return self.get_path('build', *args)

    def is_make_generator(self):
        return os.path.exists(os.path.join(self.build_dir, 'Makefile'))

    def cmake(self, options=None, use_toolchain=False, **kwargs):
        if use_toolchain: self.prefix.cmd.cmake(options=util.merge({'-DCMAKE_TOOLCHAIN_FILE': self.prefix.toolchain}, options), **kwargs)
        else: self.prefix.cmd.cmake(options=options, **kwargs)

    def show_log(self, log):
        if self.prefix.verbose and os.path.exists(log):
            click.echo(open(log).read())

    def show_logs(self):
        self.show_log(self.get_build_path('CMakeFiles', 'CMakeOutput.log'))
        self.show_log(self.get_build_path('CMakeFiles', 'CMakeError.log'))

    def fetch(self, url, fname, hash=None, copy=False, insecure=False, pkg=None):
        self.prefix.log("fetch:", url)
        if insecure: url = url.replace('https', 'http')
        if pkg is not None:
            f = os.path.join(self.arch_dir, pkg['archive'])
        if not os.path.isfile(f):
            f = util.retrieve_url(url, self.arch_dir, copy=copy, insecure=insecure, hash=hash)
        if os.path.isfile(f):
            click.echo("Extracting archive {0} ...".format(f))
            temp_dir = os.path.abspath('temp')
            util.delete_dir(temp_dir)
            os.mkdir(temp_dir)
            util.extract_ar(archive=f, dst=temp_dir)
            dirs = [o for o in os.listdir(temp_dir) if os.path.isdir(os.path.join(temp_dir, o))]
            if len(dirs) != 1:
                raise Exception('wrong count')
            util.delete_dir(os.path.join(self.src_dir, fname))
            os.rename(os.path.join(temp_dir, dirs[0]), os.path.join(self.src_dir, fname))
            util.delete_dir(temp_dir)
            return os.path.join(self.src_dir, fname)
        return next(util.get_dirs(self.top_dir)) # list of dirs dirs, found in top_dir

    def configure(self, src_dir, defines=None, generator=None, install_prefix=None, test=True, variant=None):
        self.prefix.log("configure")
        util.mkdir(self.build_dir)
        args = [
            src_dir, 
            '-DCGET_CMAKE_DIR={}'.format(util.cget_dir('cmake')), 
            '-DCGET_CMAKE_ORIGINAL_SOURCE_FILE={}'.format(os.path.join(src_dir, self.cmake_original_file))
        ]
        for d in defines or []:
            args.append('-D{0}'.format(d))
        if generator is not None: args = ['-G', generator] + args
        if self.prefix.verbose: args.extend(['-DCMAKE_VERBOSE_MAKEFILE=On'])
        if test: args.extend(['-DBUILD_TESTING=On'])
        else: args.extend(['-DBUILD_TESTING=Off'])
        args.extend(['-DCMAKE_BUILD_TYPE={}'.format(variant or 'Release')])
        if install_prefix is not None: args.extend(['-DCMAKE_INSTALL_PREFIX=' + install_prefix])
        try:
            self.cmake(args=args, cwd=self.build_dir, use_toolchain=True)
        except:
            self.show_logs()
            raise

    def build(self, target=None, variant=None, cwd=None):
        self.prefix.log("build")
        args = ['--build', self.build_dir]
        if variant is not None: args.extend(['--config', variant])
        if target is not None: args.extend(['--target', target])
        if self.is_make_generator(): 
            args.extend(['--', '-j', str(multiprocessing.cpu_count())])
            if self.prefix.verbose: args.append('VERBOSE=1')
        self.cmake(args=args, cwd=cwd)

    def test(self, variant=None):
        self.prefix.log("test")
        util.try_until(
            lambda: self.build(target='check', variant=variant or 'Release'),
            lambda: self.prefix.cmd.ctest((self.prefix.verbose and ['-VV'] or []) + ['-C', variant], cwd=self.build_dir)
        )
