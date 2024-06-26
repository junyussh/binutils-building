from _lab import env


class Env(metaclass=env.EnvMeta):
    __cached__ = []

    SOURCE_DIR = "/root/binutils-gdb"
    BUILD_DIR_NAME = "binutils_build"
    PREFIX_DIR_NAME = "usr"
