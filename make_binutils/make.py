# %%
import os
import os.path as osp
import shutil as sh

from _lab import __command_module__, ENV, ROOT, PRINT, cli

HERE, LOG = __command_module__(__name__, __spec__, __file__)

lab_dir = ROOT()
here_dir = HERE()

nproc = os.cpu_count()

# %%
def download_source():
    return

# %%
def prepare():
    abspath = HERE.var(ENV.BUILD_DIR_NAME, md=True)
    prefix = HERE.var(ENV.PREFIX_DIR_NAME, md=True)
    print(f"Create build directory: {abspath}")
    print(f"Create prefix directory: {prefix}")

# %%
def configure():
    build_dir = HERE.var(ENV.BUILD_DIR_NAME)
    
    print(f"Start configuring project, source dir: {ENV.SOURCE_DIR}")
    print(f"Build cache dir: {build_dir}")
    args1 = [
        f"{ENV.SOURCE_DIR}/configure",
        "--with-lib-path=\"/usr/lib:/usr/local/lib\"",
        "--enable-gold",
        "--disable-gdb",
        "--disable-werror",
        "--with-debuginfod",
        "--with-pic",
        "--with-system-zlib"
    ]
    result = " ".join(args1)
    print(result)
    LOG.run(result, cwd=build_dir, check=True)
    print("Configure finished")
# %%
def build():
    print(f"Start building project, source dir: {ENV.SOURCE_DIR}")
    build_dir = HERE.var(ENV.BUILD_DIR_NAME)
    print(f"Build cache dir: {build_dir}")
    print(f"CPU cores: {nproc}")

    configure_host = [
        "make",
        "configure-host",
        f"-j{nproc}"
    ]
    print("make configure host")
    LOG.run(configure_host, cwd=build_dir, check=True)
    tooldir = [
        "make",
        "tooldir=/usr",
        f"-j{nproc}"
    ]
    print("make tooldir")
    LOG.run(tooldir, cwd=build_dir, check=True)
    print("Building finished")
    
# %%
def install():
    build_dir = HERE.var(ENV.BUILD_DIR_NAME)
    prefix = HERE.var(ENV.PREFIX_DIR_NAME)
    args = [
        "make",
        f"prefix={prefix}",
        f"tooldir={prefix}",
        "install",
        f"-j{nproc}"
    ]
    print("make install")
    logrun = LOG.run(args, cwd=build_dir)
    if logrun.ret != 0:
        print("Error occurred")
        with open(logrun.err) as stderr:
            print(stderr.read())
    print(f"Binary files is located at {prefix}")
# %%
def validate():
    prefix = HERE.var(ENV.PREFIX_DIR_NAME)
    gold_path = osp.join(prefix, "bin", "ld.gold")
    arg = [gold_path, "-v"]
    print(f"test command: {arg}")
    logrun = LOG.run(arg, check=True)
    with open(logrun.out) as stdout:
        print(stdout.readlines())
# %%
def clean_build():
    build_dir = HERE.var(ENV.BUILD_DIR_NAME)
    prefix = HERE.var(ENV.PREFIX_DIR_NAME)

    print(f"Clean build dir: {build_dir}")
    LOG.run(["make", "clean"], cwd=build_dir, check=True)
    print(f"Clean prefix dir: {prefix}")
    try:
        sh.rmtree(prefix)
        print(f"Binary dir {prefix} deleted successful.")
    except OSError as e:
        print(f"Failed to remove {prefix} with error {e.strerror}")
    print("Clean finished")
# %%
