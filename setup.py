import os
import sys
import sysconfig

from setuptools import setup

SITE_PACKAGES = sysconfig.get_path("purelib").split(sys.prefix + os.sep)[1]

setup(data_files=[(SITE_PACKAGES, ["src/safe_exec/safe_exec.pth"])])
