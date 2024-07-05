from setuptools import setup, find_packages

setup(
    name="lsp_client",
    version="0.0.1",
    description="An incomplete client implemenation of the Language Server Protocol in Python.",
    long_description=open("README.rst").read(),
    long_description_content_type="text/x-rst",
    author="Christian Kissig",
    url="https://github.com/chriskissig/python-lsp-client",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
    install_requires=[
    ],
    extras_require={
        'dev': ['flake8'],
    },
    entry_points={
        'console_scripts': [
            'flake8 = flake8.main.cli:main',
        ],
    },
)
