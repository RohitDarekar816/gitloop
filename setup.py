from setuptools import setup, find_packages

setup(
    name="gitloop",
    version="0.1.1",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "requests",
        "colorama",
        "pytz"
    ],
    entry_points={
        "console_scripts": [
            "gitloop=clitool.github:main"
        ]
    },
    author="Rohit Darekar",
    description="A CLI tool to keep you in loop with Github",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/RohitDarekar816/gitloop",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
    ],
    python_requires=">=3.6",
)
