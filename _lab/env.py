"""环境配置类支持
"""

import os
import os.path as osp
import pickle as pkl
import shutil
import shlex

from typing import NamedTuple, List, Dict, Any
from . import LAB_DIR, VAR_DIR, Here, util


CACHE: Dict[type, Dict[str, Any]] = {}
"""环境缓存，记录了每个配置类中缓存了哪些属性，以及它们的值"""


def dump_cache():
    """保存环境缓存"""

    for cls, attrs in CACHE.items():
        for attr in attrs.keys():
            attrs[attr] = getattr(cls, attr)

    path = osp.join(VAR_DIR, ".cache")
    with open(path, "wb") as f:
        pkl.dump(CACHE, f)


def load_cache():
    """加载环境缓存"""

    global CACHE

    path = osp.join(VAR_DIR, ".cache")
    try:
        with open(path, "rb") as f:
            CACHE = pkl.load(f)
    except FileNotFoundError:
        return

    for cls, attrs in CACHE.items():
        for attr, value in attrs.items():
            setattr(cls, attr, value)


class EnvMeta(type):
    """环境元类"""

    def __new__(mcs, name, bases, attrs):
        cached = attrs.get("__cached__")
        assert cached is not None, "环境配置类中必须含有 __cached__ 属性"

        cls = super().__new__(mcs, name, bases, attrs)
        CACHE[cls] = {attr: attrs[attr] for attr in cached}

        return cls


# *==================================================================================* #
# * 配置项类
# *==================================================================================* #


class SshLab(NamedTuple):
    """SSH 远程实验室

    目前仅支持 Linux 主机
    """

    SSH: str
    """本地 SSH 命令路径"""

    HOST: str
    """目标主机"""

    PYEXE: str
    """远程 Python 解释器路径"""

    LAB_DIR: str
    """远程实验室目录"""

    PORT: int = None
    """端口"""

    USER: str = None
    """用户名"""

    ENVRC: str = None
    """远程环境变量文件路径"""

    def cmd(self, module: str, arg: List[str] = []) -> List[str]:
        """生成运行远程实验室命令的本地 SSH 命令

        :param str module: 模块名
        :param List[str] arg: 参数列表
        """

        cmd = [self.SSH, self.HOST]
        if self.USER:
            cmd += ["-l", self.USER]
        if self.PORT:
            cmd += ["-p", str(self.PORT)]

        rcmd = []

        if self.ENVRC:
            rcmd += [shlex.join([".", self.ENVRC]), "&&"]

        rcmd += [
            shlex.join(["cd", self.LAB_DIR]),
            "&&",
            shlex.join([self.PYEXE, "-m", module, *arg]),
        ]

        cmd += rcmd
        return cmd

    def here(self, __file__: str) -> Here:
        """获取远程实验室中的当前路径助手

        注意返回的文件助手不可用于本地文件操作！！！
        """

        relpath = osp.relpath(__file__, LAB_DIR)
        abspath = self.LAB_DIR + "/" + relpath
        return Here(abspath, lab_dir=self.LAB_DIR)

    def scp_send(self, src: str, dst: str) -> List[str]:
        """生成复制文件到远程实验室的命令

        :param str src: 本地路径
        :param str dst: 远程路径
        """

        scp = osp.join(osp.dirname(self.SSH), "scp")
        cmd = [scp, "-r"]
        if self.PORT:
            cmd += ["-P", str(self.PORT)]
        if self.USER:
            host = f"{self.USER}@{self.HOST}"
        else:
            host = self.HOST

        cmd += [src, f"{host}:{dst}"]
        return cmd

    def scp_recv(self, src: str, dst: str) -> List[str]:
        """生成从远程实验室复制文件的命令

        :param str src: 远程路径
        :param str dst: 本地路径
        """

        scp = osp.join(osp.dirname(self.SSH), "scp")
        cmd = [scp, "-r"]
        if self.PORT:
            cmd += ["-P", str(self.PORT)]
        if self.USER:
            host = f"{self.USER}@{self.HOST}"
        else:
            host = self.HOST

        cmd += [f"{host}:{src}", dst]
        return cmd


class ArchiveFile(NamedTuple):
    """归档文件"""

    FILE: str
    """文件路径"""

    TOP: str = None
    """包中的顶层目录，空串表示没有，None时自动推断"""

    def unpack(self, extract_dir: str) -> str:
        """解包并返回顶层目录的绝对路径"""

        if self.TOP is None:
            # 自动推断

            # 先解包到一个空临时目录
            tmp_dir = osp.join(extract_dir, util.randname())
            shutil.unpack_archive(self.FILE, tmp_dir)

            # 看看里面是不是只有一个目录
            content = os.listdir(tmp_dir)
            if len(content) == 1 and osp.isdir(osp.join(tmp_dir, content[0])):
                # 如果是，就认为它是顶层目录
                top_dir = content[0]
                shutil.move(osp.join(tmp_dir, top_dir), extract_dir)
                os.rmdir(tmp_dir)

            else:
                # 否则临时目录就是顶层目录
                top_dir = ""
                for i in content:
                    shutil.move(osp.join(tmp_dir, i), extract_dir)
                os.rmdir(tmp_dir)

            # 转成完整路径
            top_dir = osp.join(extract_dir, top_dir)

        else:
            shutil.unpack_archive(self.FILE, extract_dir)
            top_dir = osp.join(extract_dir, self.TOP)
            assert osp.exists(top_dir), f"解包后不存在 {top_dir}"

        return osp.abspath(top_dir)
