
from setuptools import setup, find_packages
import codecs
import os

here = os.path.abspath(os.path.dirname(__file__))

with codecs.open(os.path.join(here, "readme.MD"), encoding="utf-8") as fh:
    long_description = "\n" + fh.read()

VERSION = '0.0.4'
DESCRIPTION = 'Transforming python code to GLSL shaders.'

# Setting up
setup(
    name="shadermake",
    version=VERSION,
    author="EngDrom project",
    author_email="<engdrom.project@gmail.com>",
    description=DESCRIPTION,
    long_description_content_type="text/markdown",
    long_description=long_description,
    packages=[ 'shadermake', 'shadermake.engines' ],
    install_requires=[],
    url="https://github.com/EngDrom/ShaderMake",
    keywords=['python', 'opengl', 'glsl'],
    classifiers=[
        "Development Status :: 1 - Planning",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Operating System :: Unix",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: Microsoft :: Windows",
    ]
)
