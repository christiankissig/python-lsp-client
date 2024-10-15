from setuptools import setup, find_packages

extras_require = dict()
extras_require['dev'] = [
    'black',
    'flake8',
    'isort',
]

extras_require['test'] = [
    'pytest',
    'pytest-asyncio',
]

extras_require['ci'] = [
    *extras_require['test'],
    'pytest-cov',
]

setup(
    name="lsp_client",
    version="0.0.2",
    description="A client implementation of the Language Server Protocol in Python.",
    long_description=open("README.rst").read(),
    long_description_content_type="text/x-rst",
    author="Christian Kissig",
    url="https://github.com/christiankissig/python-lsp-client",
    packages=find_packages(),
    package_data={
        "*": ["*.txt", "*.rst", "*.md"]
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
    install_requires=[
        'pydantic>=2.9.0',
    ],
    extras_require=extras_require,
    entry_points={
        'console_scripts': [
            'flake8 = flake8.main.cli:main',
        ],
    },
)
