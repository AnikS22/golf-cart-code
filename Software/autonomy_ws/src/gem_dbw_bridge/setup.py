from setuptools import find_packages, setup

package_name = "gem_dbw_bridge"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages",
            ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
    ],
    install_requires=["setuptools", "python-can"],
    zip_safe=True,
    maintainer="FAU MPCR",
    maintainer_email="mpcrlab@gmail.com",
    description="Real-cart DBW bridge — ROS 2 ↔ SocketCAN",
    license="Apache-2.0",
    entry_points={
        "console_scripts": [
            "gem_dbw_bridge_node = gem_dbw_bridge.gem_dbw_bridge_node:main",
        ],
    },
)
