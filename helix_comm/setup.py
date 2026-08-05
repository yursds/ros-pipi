from setuptools import find_packages, setup

package_name = "helix_comm"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
    ],
    install_requires=["setuptools", "roslibpy", "pyyaml"],
    zip_safe=True,
    maintainer="softbots-cp",
    maintainer_email="softbots-cp@softbots-cp",
    description="ROS 2 package to communicate with Helix robot via rosbridge",
    license="MIT",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "helix_client = helix_comm.helix_client:main",
            "helix_info = helix_comm.helix_info:main",
            "helix_control = helix_comm.cli:main",
            "helix_bridge = helix_comm.bridge:main",
        ],
    },
)
