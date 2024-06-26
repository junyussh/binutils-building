import os
import os.path as osp
import pkgutil

from importlib import import_module
from . import MainOnly


def auto_help(__spec__):
    """用在包的 __main__.py 中，打印所有可用的命令子模块"""

    print(__spec__.origin)
    pkgdir = osp.dirname(__spec__.origin)
    root_name = __spec__.name.rstrip(".__main__")
    print(f"{root_name} :")
    counter = 0
    for finder, name, ispkg in pkgutil.iter_modules([pkgdir]):
        if ispkg:
            continue
        if name.startswith("_"):
            continue
        try:
            import_module(f"{root_name}.{name}")
        except MainOnly:
            print(f"\t.{name}")
            counter += 1
        except Exception:
            pass
    print("TOTAL", counter)


def ensure_indir(path: str) -> str:
    """确保输入目录的路径有效"""

    if not osp.exists(path):
        raise NotADirectoryError(f"输入目录 {path} 不存在")
    if not osp.isdir(path):
        raise NotADirectoryError(f"路径 {path} 不是目录")
    return osp.abspath(path)


def ensure_infile(path: str) -> str:
    """确保输入文件的路径有效"""

    if not osp.exists(path):
        raise FileNotFoundError(f"输入文件 {path} 不存在")
    if not osp.isfile(path):
        raise IsADirectoryError(f"路径 {path} 不是文件")
    return osp.abspath(path)


def ensure_outdir(path: str) -> str:
    """确保输出目录的路径可用"""

    os.makedirs(path, exist_ok=True)
    if not osp.isdir(path):
        raise NotADirectoryError(f"无法创建输出目录 {path}")
    return osp.abspath(path)


def ensure_outfile(path: str) -> str:
    """确保输出文件的路径可用"""

    if osp.exists(path) and not osp.isfile(path):
        raise IsADirectoryError(f"路径 {path} 不是文件")
    if parent := osp.dirname(path):
        os.makedirs(parent, exist_ok=True)
        if not osp.isdir(parent):
            raise NotADirectoryError(f"无法创建输出文件的上级目录 {parent}")
    return osp.abspath(path)
