"""简单的工具函数
"""

import random


# *==================================================================================* #
# * 常用随机生成函数
# *==================================================================================* #


def randstr(length: int = 8) -> str:
    """生成随机 ASCII 可打印字符串"""

    return "".join(chr(random.randint(0x21, 0x7E)) for _ in range(length))


def randname(prefix: str = "", suffix: str = "", length: int = 8) -> str:
    """生成随机文件名"""

    chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    return prefix + "".join(random.choices(chars, k=length)) + suffix
