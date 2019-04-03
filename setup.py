from setuptools import setup

setup(
    name='patchbox-cli',
    version='1.0',
    packages=['patchbox', 'patchbox.modules'],
    include_package_data=True,
    install_requires=[
        'click',
    ],
    entry_points='''
        [console_scripts]
        patchbox-config=patchbox.cli:cli
    ''',
)
