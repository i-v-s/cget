import click, os, functools, sys

from cget import __version__
from cget.prefix import CGetPrefix
from cget.prefix import PackageBuild
import cget.util as util
from cget.config import Config

aliases = {
    'rm': 'remove',
    'ls': 'list'
}


class AliasedGroup(click.Group):
    def get_command(self, ctx, cmd_name):
        rv = click.Group.get_command(self, ctx, cmd_name)
        if rv is not None:
            return rv
        return click.Group.get_command(self, ctx, aliases[cmd_name])


@click.group(cls=AliasedGroup, context_settings={'help_option_names': ['-h', '--help']})
@click.version_option(version=__version__, prog_name='cget')
@click.option('-p', '--prefix', envvar='CGET_PREFIX', help='Set prefix used to install packages')
@click.option('-v', '--verbose', is_flag=True, envvar='VERBOSE', help="Enable verbose mode")
@click.option('-B', '--build-path', envvar='CGET_BUILD_PATH', help='Set the path for the build directory to use when building the package')
@click.pass_context
def cli(ctx, prefix, verbose, build_path):
    ctx.obj = {}
    if prefix: ctx.obj['PREFIX'] = prefix
    if verbose: ctx.obj['VERBOSE'] = verbose
    if build_path: ctx.obj['BUILD_PATH'] = build_path


def use_config(f):
    def w(*args, **kwargs):
        try:
            cfg = Config()
        except FileNotFoundError:
            print('Current directory is not initialized.')
            sys.exit(1)
        f(cfg, *args, **kwargs)
    return w


#@load_config
def use_prefix(f):
    # @click.option('-p', '--prefix', help='Set prefix used to install packages')
    @click.option('-v', '--verbose', is_flag=True, help="Enable verbose mode")
    # @click.option('-B', '--build-path', help='Set the path for the build directory to use when building the package')
    @click.pass_obj
    @functools.wraps(f)
    @use_config
    def w(cfg, obj, verbose, *args, **kwargs):
        p = CGetPrefix(cfg, verbose or obj.get('VERBOSE'))
        f(p, *args, **kwargs)
    return w


def get_opts(f):
    @click.option('-t', '--toolchain', required=False, help="Set cmake toolchain file to use")
    @click.option('-G', '--generator', required=False, help='Set the generator for CMake to use')
    @click.option('--cxx', required=False, help="Set c++ compiler")
    @click.option('--cxxflags', required=False, help="Set additional c++ flags")
    @click.option('--ldflags', required=False, help="Set additional linker flags")
    @click.option('--std', required=False, help="Set C++ standard if available")
    @click.option('-D', '--define', multiple=True, help="Extra configuration variables to pass to CMake")
    @click.option('--shared', is_flag=True, help="Set toolchain to build shared libraries by default")
    @click.option('--static', is_flag=True, help="Set toolchain to build static libraries by default")
    @click.option('--debug', is_flag=True, help="Set toolchain to build debug configuration")
    @click.option('--release', is_flag=True, help="Set toolchain to build release configuration")
    def w( *args, **kwargs):
        if kwargs.get('shared', False) and kwargs.get('static', False):
            click.echo("ERROR: shared and static are not supported together")
            sys.exit(1)
        if kwargs.get('debug', False) and kwargs.get('release', False):
            click.echo("ERROR: shared and static are not supported together")
            sys.exit(1)
        kw = {}
        options = {}
        defines = {}
        for k, v in kwargs.items():
            if k in ['toolchain', 'generator', 'cxx', 'cxxflags', 'ldflags', 'std']:
                if v is not None:
                    options.update({k: v})
            elif k == 'define':
                for d in v:
                    try:
                        [name, val] = d.split('=', maxsplit=1)
                        defines.update({name: val})
                    except ValueError:
                        defines.update({v: True})
            elif k == 'static':
                if v:
                    options.update({'static' : True})
            elif k == 'shared':
                if v:
                    options.update({'static': False})
            elif k == 'release':
                if v:
                    options.update({'config': 'Release'})
            elif k == 'debug':
                if v:
                    defines.update({'config': 'Debug'})
            else:
                kw.update({k : v})
        if defines:
            options.update({'define': defines})
        f(options, *args, **kw) #toolchain, generator, cxx, cxxflags, ldflags, std, define, shared, static,
    return w


@cli.group(name='config', invoke_without_command=True)
@click.pass_context
@use_config
def config_group(config, ctx):
    if ctx.invoked_subcommand is None:
        config.dump_configs()
    else:
        ctx.obj = config


@config_group.command(name='add')
@click.argument('name')
@get_opts
@click.pass_obj
def config_add(config, opts, name):
    config.add(name, opts)
    config.save()
    print('config ' + name + ' added')


@config_group.command(name='set')
@get_opts
@click.pass_obj
def config_set(config, opts):
    if config.name is None:
        click.echo('No config activated')
        sys.exit(1)
    config.set(opts)
    config.save()
    print('config ' + config.name + ' updated')


@config_group.command(name='scan')
@click.argument('path', type=click.Path(exists=True))
@click.pass_obj
def config_scan(config, path):
    if config.name is None:
        click.echo('No config activated')
        sys.exit(1)
    count = config.scan(path)
    if count > 0:
        config.save()
        click.echo('config ' + config.name + ' updated')
    else:
        click.echo('Nothing found')


@cli.command(name='init')
def init_command():
    try:
        config = Config(new=True)
        os.mkdir('src')
        os.mkdir('src-arch')
        os.mkdir('packages')
        print('Directory initialized.')
    except FileExistsError:
        print('Current directory already initialized.')


@cli.command(name='fetch')
@click.argument('name')
@use_config
def fetch_command(config, name):
    package = config.get_package(name, new_if_nf=True)
    package.fetch()


@cli.command(name='configure')
@click.argument('name')
@use_config
def fetch_command(config, name):
    package = config.get_package(name, new_if_nf=True)
    package.configure()


@cli.command(name='gui')
@click.argument('name')
@use_config
def fetch_command(config, name):
    package = config.get_package(name, new_if_nf=True)
    package.gui()


@cli.command(name='build')
@click.argument('name')
@use_config
def build_command(config, name):
    package = config.get_package(name, new_if_nf=True)
    package.build()


@cli.command(name='install')
@click.argument('name')
@use_config
def install_command(config, name):
    package = config.get_package(name, new_if_nf=True)
    package.install()


@cli.command(name='clean')
@click.argument('name')
@use_config
def clean_command(config, name):
    package = config.get_package(name, new_if_nf=True)
    package.clean()


@cli.command(name='list')
@use_config
def list_command(config):
    empty = True
    for name in config.packages_gen():
        click.echo(name)
        empty = False
    if empty:
        click.echo('No packages found')


@cli.command(name='init1')
@use_prefix
@click.option('-t', '--toolchain', required=False, help="Set cmake toolchain file to use")
@click.option('-G', '--generator', envvar='CGET_GENERATOR', help='Set the generator for CMake to use')
@click.option('--cxx', required=False, help="Set c++ compiler")
@click.option('--cxxflags', required=False, help="Set additional c++ flags")
@click.option('--ldflags', required=False, help="Set additional linker flags")
@click.option('--std', required=False, help="Set C++ standard if available")
@click.option('-D', '--define', multiple=True, help="Extra configuration variables to pass to CMake")
@click.option('--shared', is_flag=True, help="Set toolchain to build shared libraries by default")
@click.option('--static', is_flag=True, help="Set toolchain to build static libraries by default")
def init1_command(prefix, toolchain, generator, cxx, cxxflags, ldflags, std, define, shared, static):
    """ Initialize install directory """
    if shared and static:
        click.echo("ERROR: shared and static are not supported together")
        sys.exit(1)
    defines = util.to_define_dict(define)
    if shared: defines['BUILD_SHARED_LIBS'] = 'On'
    if static: defines['BUILD_SHARED_LIBS'] = 'Off'
    if generator: prefix.generator = generator
    prefix.write_cmake(
        always_write=True, 
        toolchain=toolchain,
        generator=generator,
        cxx=cxx,
        cxxflags=cxxflags, 
        ldflags=ldflags, 
        std=std, 
        defines=defines)


@cli.command(name='install1')
@use_prefix
@click.option('-U', '--update', is_flag=True, help="Update package")
@click.option('-t', '--test', is_flag=True, help="Test package before installing by running ctest or check target")
@click.option('--test-all', is_flag=True, help="Test all packages including its dependencies before installing by running ctest or check target")
@click.option('-f', '--file', default=None, help="Install packages listed in the file")
@click.option('-D', '--define', multiple=True, help="Extra configuration variables to pass to CMake")
@click.option('-G', '--generator', envvar='CGET_GENERATOR', help='Set the generator for CMake to use')
@click.option('-X', '--cmake', help='Set cmake file to use to build project')
@click.option('--debug', is_flag=True, help="Install debug version")
@click.option('--release', is_flag=True, help="Install release version")
@click.option('--insecure', is_flag=True, help="Don't use https urls")
@click.argument('pkgs', nargs=-1, type=click.STRING)
def install1_command(prefix, pkgs, define, file, test, test_all, update, generator, cmake, debug, release, insecure):
    """ Install packages """
    if debug and release:
        click.echo("ERROR: debug and release are not supported together")
        sys.exit(1)
    variant = 'Release'
    if debug: variant = 'Debug'
    pbs = [PackageBuild(pkg, define=define, cmake=cmake, variant=variant) for pkg in pkgs]
    for pb in util.flat([prefix.from_file(file), pbs]):
        with prefix.try_("Failed to build package {}".format(pb.to_name()), on_fail=lambda: prefix.remove(pb)):
            click.echo(prefix.install(pb, test=test, test_all=test_all, update=update, generator=generator, insecure=insecure))


@cli.command(name='build1')
@use_prefix
@click.option('-t', '--test', is_flag=True, help="Test package by running ctest or check target")
@click.option('-c', '--configure', is_flag=True, help="Configure cmake")
@click.option('-C', '--clean', is_flag=True, help="Remove build directory")
@click.option('-P', '--path', is_flag=True, help="Show path to build directory")
@click.option('-D', '--define', multiple=True, help="Extra configuration variables to pass to CMake")
@click.option('-T', '--target', default=None, help="Cmake target to build")
@click.option('-y', '--yes', is_flag=True, default=False)
@click.option('-G', '--generator', envvar='CGET_GENERATOR', help='Set the generator for CMake to use')
@click.argument('pkg', nargs=1, default='.', type=click.STRING)
def build1_command(prefix, pkg, define, test, configure, clean, path, yes, target, generator):
    """ Build package """
    pb = PackageBuild(pkg).merge_defines(define)
    with prefix.try_("Failed to build package {}".format(pb.to_name())):
        if configure: prefix.build_configure(pb)
        elif path: click.echo(prefix.build_path(pb))
        elif clean: 
            if not yes: yes = click.confirm("Are you sure you want to delete the build directory?")
            if yes: prefix.build_clean(pb)
        else: prefix.build(pb, test=test, target=target, generator=generator)


@cli.command(name='remove')
@use_prefix
@click.argument('pkgs', nargs=-1, type=click.STRING)
@click.option('-y', '--yes', is_flag=True, default=False)
@click.option('-U', '--unlink', is_flag=True, default=False, help="Unlink package but don't remove it")
@click.option('-A', '--all', is_flag=True, default=False, help="Select all packages installed")
def remove_command(prefix, pkgs, yes, unlink, all):
    """ Remove packages """
    if all: pkgs = [None]
    verb = "unlink" if unlink else "remove"
    pkgs_set = set((dep.name for pkg in pkgs for dep in prefix.list(pkg, recursive=True)))
    click.echo("The following packages will be removed:")
    for pkg in pkgs_set: click.echo(pkg)
    if not yes: yes = click.confirm("Are you sure you want to {} these packages?".format(verb))
    if yes:
        for pkg in pkgs_set:
            with prefix.try_("Failed to {} package {}".format(verb, pkg)):
                prefix.unlink(pkg, delete=not unlink)
                click.echo("{} package {}".format(verb, pkg))


# TODO: Make this command hidden
@cli.command(name='size')
@use_prefix
@click.argument('n')
def size_command(prefix, n):
    pkgs = len(list(util.ls(prefix.get_package_directory(), os.path.isdir)))
    if pkgs != int(n):
        raise util.BuildError("Not the correct number of items: {}".format(pkgs))

@cli.command(name='clean1')
@use_prefix
@click.option('-y', '--yes', is_flag=True, default=False)
@click.option('--cache', is_flag=True, default=False, help="Removes any cache files")
def clean1_command(prefix, yes, cache):
    """ Clear directory """
    if cache:
        prefix.clean_cache()
    else:
        if not yes: yes = click.confirm("Are you sure you want to delete all cget packages in {}?".format(prefix.prefix))
        if yes: prefix.clean()

@cli.command(name='pkg-config', context_settings=dict(
    ignore_unknown_options=True,
))
@use_prefix
@click.argument('args', nargs=-1, type=click.UNPROCESSED)
def pkg_config_command(prefix, args):
    """ Pkg config """
    prefix.cmd.pkg_config(args)


if __name__ == '__main__':
    cli()

