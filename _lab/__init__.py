import asyncio as aio
import datetime
import logging
import os
import os.path as osp
import shutil
import subprocess as subp
import sys
import shlex

from textwrap import indent, dedent
from typing import NamedTuple, Tuple, List

__all__ = (
    "os",
    "osp",
    "ENV",
    "ROOT",
    "PRINT",
    "__lab_command__",
    "LAB_DIR",
    "VAR_DIR",
    "DAT_DIR",
    "LOG_DIR",
    "TMP_DIR",
)


LAB_DIR = osp.abspath(osp.dirname(osp.dirname(__file__)))
VAR_DIR = osp.join(LAB_DIR, "var")
DAT_DIR = osp.join(LAB_DIR, "dat")
LOG_DIR = osp.join(LAB_DIR, "log")
TMP_DIR = osp.join(LAB_DIR, "tmp")

# 将实验室根目录加入 sys.path
sys.path.append(LAB_DIR)


# *==================================================================================* #
# * PRINT
# *==================================================================================* #


class Print:
    def __init__(self, indent=0) -> None:
        self._indent = indent

    def __call__(self, *args, sep=" ", end="\n", flush=False) -> "Print":
        text = sep.join(map(str, args)) + end
        if self._indent > 0:
            text = indent(text, "=" * (4 * self._indent - 2) + "> ")
        print(text, end="", flush=flush)
        return self

    def __enter__(self):
        self._indent += 1
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._indent -= 1

    def file(self, path):
        """将文件内容输出到控制台"""

        with open(path) as f:
            for line in f:
                self(line, end="")

    def __getitem__(self, path: str):
        """file 的快捷形式"""
        self.file(path)


PRINT = Print(int(os.getenv("LAB_PRINT_INDENT", 0)))


# *==================================================================================* #
# * LOG
# *==================================================================================* #


LOG_STAMP = datetime.datetime.now().strftime("%Y-%m-%d.%H:%M:%S.%f")
os.makedirs(osp.join(LOG_DIR, LOG_STAMP), exist_ok=False)

LOG_INDEX = osp.join(LOG_DIR, LOG_STAMP, "index")
logging.basicConfig(
    filename=LOG_INDEX,
    format="\n[%(asctime)s %(levelname)s %(name)s]\n%(message)s",
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper()),
)

for _ in range(3):
    PRINT(LOG_INDEX)
print()


class LogRun(NamedTuple):
    ret: int
    """返回值"""

    out: str
    """标准输出重定向文件路径"""

    err: str
    """标准错误重定向文件路径"""

    timing: datetime.timedelta
    """运行计时"""


class Logger(logging.Logger):

    def run(
        self,
        cmd: List[str],
        in_: str = None,
        env: dict = None,
        cwd: str = None,
        *,
        level=logging.INFO,
        envs: dict = None,
        check: bool = False,
        **kwargs,
    ) -> LogRun:
        """执行命令并记录日志

        其它额外参数将会被传递给 subprocess.run

        :param list[str] cmd: 命令行
        :param str in_: 标准输入文件的路径
        :param dict env: 额外环境变量，如果提供，会用 sys.environ 更新
        :param str cwd: 工作目录，默认为日志目录下的子目录
        :param level: 日志级别
        :param dict envs: 完整的环境变量，直接传递给 subprocess.run
        :param bool check: 是否检查返回值
        :return LogRun: 运行结果
        """

        assert isinstance(cmd, list), "cmd 必须是列表"

        now = datetime.datetime.now()
        run_dir = HERE.log("run", now.strftime("%Y-%m-%d.%H:%M:%S.%f"), md=True)
        run_out = osp.join(run_dir, "stdout")
        run_err = osp.join(run_dir, "stderr")

        if env:
            assert envs is None, "不能同时提供 env 和 envs"
            envs = env.copy()
            envs.update(os.environ)

        with open(run_out, "wb") as out, open(run_err, "wb") as err:
            proc = subp.run(
                cmd,
                stdin=open(in_, "rb") if in_ else None,
                stdout=out,
                stderr=err,
                env=envs,
                cwd=cwd if cwd else run_dir,
                **kwargs,
            )

        log_run = LogRun(
            ret=proc.returncode,
            out=run_out,
            err=run_err,
            timing=datetime.datetime.now() - now,
        )

        self.log(
            level,
            dedent(
                f"""\
                CWD: {cwd}
                RUN: {shlex.join(cmd)}
                IN_: {in_}
                OUT: {run_out}
                ERR: {run_err}
                ENV: {env if env is not None else envs}
                RET: {log_run.ret}
                ({log_run.timing})
                """
            ),
        )

        if check and log_run.ret:
            raise subp.CalledProcessError(log_run.ret, cmd)

        return log_run

    async def arun(
        self,
        cmd: List[str],
        in_: str = None,
        env: dict = None,
        cwd: str = None,
        *,
        level=logging.INFO,
        envs: dict = None,
        check=False,
        **kwargs,
    ) -> LogRun:
        """异步执行命令并记录日志

        参数同 run

        注意：该处的计时为异步计时，可能并不准确
        """

        assert isinstance(cmd, list), "cmd 必须是列表"

        now = datetime.datetime.now()
        run_dir = HERE.log("run", now.strftime("%Y-%m-%d.%H:%M:%S.%f"), md=True)
        run_out = osp.join(run_dir, "stdout")
        run_err = osp.join(run_dir, "stderr")

        if env:
            assert envs is None, "不能同时提供 env 和 envs"
            envs = env.copy()
            envs.update(os.environ)

        with open(run_out, "wb") as out, open(run_err, "wb") as err:
            proc = await aio.create_subprocess_exec(
                *cmd,
                stdin=open(in_, "rb") if in_ else None,
                stdout=out,
                stderr=err,
                env=envs,
                cwd=cwd if cwd else run_dir,
                **kwargs,
            )

        log_run = LogRun(
            ret=await proc.wait(),
            out=run_out,
            err=run_err,
            timing=datetime.datetime.now() - now,
        )

        self.log(
            level,
            dedent(
                f"""\
                CWD: {cwd}
                RUN: {shlex.join(cmd)}
                IN_: {in_}
                OUT: {run_out}
                ERR: {run_err}
                ENV: {env if env is not None else envs}
                RET: {log_run.ret}
                ({log_run.timing})
                """
            ),
        )

        if check and log_run.ret:
            raise subp.CalledProcessError(log_run.ret, cmd)

        return log_run

    def amap(self, af, it) -> None:
        """将异步函数应用于迭代器，然后并发执行所得协程

        :param _type_ af: 异步函数
        :param _type_ it: 迭代器
        """

        async def wrapper():
            await aio.gather(*map(af, it))

        aio.run(wrapper())

    def run_lab(
        self,
        module: str,
        arg: List[str] = [],
        env: dict = None,
        *,
        level=logging.INFO,
        envs: dict = None,
        **kwargs,
    ) -> int:
        """运行实验室里的命令模块，输入输出附加到当前控制台

        其余参数将会被传递给 subprocess.run

        :param str module: 模块名
        :param list[str] arg: 参数列表
        :param dict env: 额外环境变量，如果提供，会用 sys.environ 更新
        :param level: 日志级别
        :param dict envs: 完整的环境变量，直接传递给 subprocess.run
        :return int: 状态码
        """

        if env:
            assert envs is None, "不能同时提供 env 和 envs"
            envs = env.copy()
            envs.update(os.environ)
        envs["LAB_PRINT_INDENT"] = str(PRINT._indent + 1)

        proc = subp.run(
            [sys.executable, "-m", module, *arg],
            env=envs,
            cwd=ROOT.DIR,
            **kwargs,
        )

        self.log(
            level,
            dedent(
                f"""\
                LAB: {module}
                ARG: {arg}
                ENV: {env if env is not None else envs}
                RET: {proc.returncode}
                """
            ),
        )

        return proc.returncode

    def arun_lab(
        self,
        module: str,
        arg: List[str] = [],
        env: dict = None,
        *,
        level=logging.INFO,
        envs: dict = None,
        **kwargs,
    ):
        """异步运行实验室里的命令模块，输出重定向到日志目录

        这个函数只是对 arun 的简单封装
        """

        return self.arun(
            [sys.executable, "-m", module, *arg],
            in_=None,
            env=env,
            cwd=ROOT.DIR,
            level=level,
            envs=envs,
            **kwargs,
        )


# *==================================================================================* #
# * HERE
# *==================================================================================* #


class Here:

    def __init__(self, __file__: str, *, lab_dir=None) -> None:
        self.DIR = osp.abspath(osp.dirname(__file__))
        """当前文件所在目录的路径"""

        self.LAB_DIR = lab_dir or LAB_DIR
        self.VAR_DIR = osp.join(self.LAB_DIR, "var")
        self.LOG_DIR = osp.join(self.LAB_DIR, "log", LOG_STAMP)

    def __call__(self, *path: str) -> str:
        """获取 *path 在这里的绝对路径"""
        return osp.abspath(osp.join(self.DIR, *path))

    def var(self, *path: str, rm=False, mp=False, md=False) -> str:
        """获取这里的 *path 在变量目录中同构的绝对路径

        :param bool rm: 是否删除目标, defaults to False
        :param bool mp: 是否创建父目录, defaults to False
        :param bool md: 是否创建目标为目录, defaults to False
        :return str: 绝对路径
        """

        relpath = osp.relpath(self(*path), self.LAB_DIR)
        abspath = osp.abspath(osp.join(self.VAR_DIR, relpath))
        if rm:
            shutil.rmtree(abspath, ignore_errors=True)
        if mp:
            os.makedirs(osp.dirname(abspath), exist_ok=True)
        if md:
            os.makedirs(abspath, exist_ok=True)
        return abspath

    def log(self, *path: str, rm=False, mp=False, md=False) -> str:
        """获取这里的 *path 在日志目录中同构的绝对路径

        :param bool rm: 是否删除目标, defaults to False
        :param bool mp: 是否创建父目录, defaults to False
        :param bool md: 是否创建目标为目录, defaults to False
        :return str: 绝对路径
        """

        relpath = osp.relpath(self(*path), self.LAB_DIR)
        abspath = osp.abspath(osp.join(self.LOG_DIR, relpath))
        if rm:
            shutil.rmtree(abspath, ignore_errors=True)
        if mp:
            os.makedirs(osp.dirname(abspath), exist_ok=True)
        if md:
            os.makedirs(abspath, exist_ok=True)
        return abspath


HERE = Here(__file__)
ROOT = Here(HERE.DIR)


# *==================================================================================* #
# * __here_log__
# *==================================================================================* #


def __here_log__(__name__, __spec__, __file__) -> Tuple[Here, Logger]:
    """获取 HERE 和 LOG 对象"""

    loggerClass = logging.getLoggerClass()
    logging.setLoggerClass(Logger)

    if __spec__ is not None:
        logger = logging.getLogger(__spec__.name)
    else:
        logger = logging.getLogger(osp.basename(__file__))
    logging.setLoggerClass(loggerClass)

    return Here(__file__), logger


# *==================================================================================* #
# * __command_module__
# *==================================================================================* #


class MainOnly(Exception):
    """模块只能直接运行"""

    def __init__(self, name: str):
        super().__init__(f"模块 {name} 不应该被导入，只能直接运行！")


def __command_module__(__name__, __spec__, __file__) -> Tuple[Here, Logger]:
    """命令模块声明"""

    if __name__ != "__main__":
        raise MainOnly(__name__)

    HERE, LOG = __here_log__(__name__, __spec__, __file__)
    LOG.info(f"{sys.argv}")
    return HERE, LOG


# *==================================================================================* #
# * ENV
# *==================================================================================* #


from .env import load_cache

try:
    from env import Env
except ImportError:
    from environ import Env

ENV = Env
load_cache()
