from setuptools import setup, find_packages

version = '0.1'

setup(
    name='collective.s3blobs',
    version=version,
    description="ZODB ZEO client which retrieves blobs from Amazon S3",
    long_description=(open("README.rst").read() + "\n" +
                      open("CHANGES.rst").read()),
    classifiers=[
        "Framework :: Plone",
        "Programming Language :: Python",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    keywords='ZODB ZEO blobs aws s3',
    author='David Glick, Jazkarta',
    author_email='david@glicksoftware.com',
    url='https://github.com/collective/collective.z3blobs',
    license='BSD',
    packages=find_packages(exclude=['ez_setup']),
    namespace_packages=['collective'],
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'boto3',
        'python-magic',
        'setuptools',
        'ZODB3',
    ],
    entry_points="""
    [console_scripts]
    archive-blobs = collective.s3blobs.scripts.archive_blobs:main
    """,
)
