``collective.s3blobs``
======================

This package provides tools to help offload selected ZODB blobs
to be stored permanently in Amazon S3.

S3 Blob cache
-------------

The S3 blob cache sits between a ZODB connection and its underlying
storage. It first tries to load blobs from the underlying storage.
If the blob can't be loaded (e.g. because it has been archived to S3)
then the cache will try to fetch it from S3. Blobs fetched from S3
will be cached in a separate cache directory until it reaches a
size limit.

To add the cache to your Zope instance,
add this to your plone.recipe.zope2instance section in buildout::

    storage-wrapper =
        %% import collective.s3blobs
        <s3blobcache>
          cache-dir ${buildout:directory}/var/blobcache
          cache-size 100000000
          bucket-name your-s3-bucket
        </s3blobcache

(Note: This currently requires the ``storage-wrapper`` branch
of plone.recipe.zope2instance.)

S3 Archive script
-----------------

Adding this egg to your buildout installs a ``bin/archive-blobs``
script which can be used to selectively copy blobs from a
local blobstorage directory into an S3 bucket (for later access
by the cache)::

	Usage: ``archive-blobs [-h] [-a AGE] [-s SIZE] [-d] blob_dir bucket_name``

	Positional arguments:
	  blob_dir              Path to local blobstorage directory
	  bucket_name           S3 bucket name

	Optional arguments:
	  -h, --help            show this help message and exit
	  -a AGE, --age AGE     Only archive blobs created more than this many days
	                        ago. (Default: 1)
	  -s SIZE, --size SIZE  Only archive blobs more than this many bytes in size.
	                        (Default: 0)
	  -d, --destroy         Destroy local file after archiving?

To do:
------
[ ] setup instructions (including bucket permissions)
[ ] how to transition smoothly
[ ] make views link to signed download URL
[ ] packing
[ ] tests
