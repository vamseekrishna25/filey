from setuptools import setup, find_packages

def parse_requirements(filename):
    requirements = []
    with open(filename) as f:
        for line in f:
            line = line.strip()
            # Skip comments, blank lines, and pip options
            if line and not line.startswith('#') and not line.startswith('-'):
                requirements.append(line)
    return requirements

setup(
    name='wb',
    version='0.1',
    packages=find_packages(),
    package_data={'wb': ['templates/*.html']},
    entry_points={
        'console_scripts': [
            'wb=wb.main:main',
        ],
    },
    install_requires=parse_requirements('requirements.txt'),
    author='Viswantha Srinivas P',
    author_email='',
    description='A simple directory listing application',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.10',
)