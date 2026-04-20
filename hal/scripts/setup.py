from setuptools import setup

setup(
    name="hal_buddy",
    version="0.1.0",
    packages=[],
    package_dir={"": ""},
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="POC Team",
    maintainer_email="poc@robotics.lab",
    description="HAL Buddy node",
    license="MIT",
    entry_points={
        "console_scripts": [
            "hal_buddy_node = hal_buddy_node:main",
        ],
    },
)
