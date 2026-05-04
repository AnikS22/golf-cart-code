import os
from glob import glob
from setuptools import find_packages, setup

package_name = "gem_teleop"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages",
            ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        (os.path.join("share", package_name, "launch"), glob("launch/*.launch.py")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="FAU MPCR",
    maintainer_email="mpcrlab@gmail.com",
    description="F710 gamepad teleop → /dbw/cmd",
    license="Apache-2.0",
    entry_points={
        "console_scripts": [
            "joy_to_ackermann_node = gem_teleop.joy_to_ackermann_node:main",
        ],
    },
)
