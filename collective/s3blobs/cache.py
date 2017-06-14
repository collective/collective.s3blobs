from .utils import s3_blob_filename
import boto3
import logging
import os
import stat
import threading
import time
import ZODB.POSException
import ZEO.ClientStorage

logger = logging.getLogger(__name__)


class S3BlobCache(object):
    """A read-only cache of blobs retrieved from Amazon S3.

    First tries to get the blob from the (local) underlying storage,
    then tries S3.
    """

    def __init__(
            self, storage, cache_dir, bucket_name,
            aws_access_key_id=None, aws_secret_access_key=None,
            cache_size=20 * ZEO.ClientStorage.MB):
        self.storage = storage

        session = boto3.Session(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
        )
        self.bucket = session.resource('s3').Bucket(bucket_name)
        self.cache_dir = cache_dir

        # Initialize blob cache directory
        if 'zeocache' not in ZODB.blob.LAYOUTS:
            ZODB.blob.LAYOUTS['zeocache'] = ZEO.ClientStorage.BlobCacheLayout()
        self.fshelper = ZODB.blob.FilesystemHelper(
            cache_dir, layout_name='zeocache')
        self.fshelper.create()
        self.fshelper.checkSecure()

        # Set up to limit cache size
        self._blob_cache_size = cache_size
        self._blob_data_bytes_loaded = 0
        if cache_size is not None:
            self._blob_cache_size_check = cache_size * .1
            self._check_blob_size()

    # Pass thru most methods to the underlying storage

    def __getattr__(self, name):
        return getattr(self.storage, name)

    def __len__(self):
        return len(self.storage)

    def __repr__(self):
        normal_storage = self.storage
        return '<S3BlobCache proxy for %r at %s>' % (
            normal_storage, hex(id(self)))

    def isBlobLocal(self, oid, serial):
        """Check if blob can be found in the underlying storage.

        (Useful for determining whether to serve the blob
        directly from S3 or not.)
        """
        try:
            self.storage.loadBlob(oid, serial)
        except ZODB.POSException.POSKeyError:
            return False
        return True

    def loadBlob(self, oid, serial):
        """Load a blob.

        First tries from underlying storage, then from S3.
        """
        start = time.time()
        try:
            blob_filename = self.storage.loadBlob(oid, serial)
            logger.debug('Fetched blob from ZEO in %ss' % (time.time() - start))
        except ZODB.POSException.POSKeyError:
            blob_filename = self.loadS3Blob(oid, serial)
            logger.debug('Fetched blob from S3 in %ss' % (time.time() - start))
        return blob_filename

    def loadS3Blob(self, oid, serial):
        """Load a blob from S3."""

        # Check if it's already in the cache
        cache_filename = self.fshelper.getBlobFilename(oid, serial)
        if os.path.exists(cache_filename):
            return ZEO.ClientStorage._accessed(cache_filename)

        # If not, download from S3...
        # First, we'll create the directory for this oid, if it doesn't exist.
        self.fshelper.createPathForOID(oid)

        # OK, it's not here and we (or someone) needs to get it.  We
        # want to avoid getting it multiple times.  We want to avoid
        # getting it multiple times even accross separate client
        # processes on the same machine. We'll use file locking.

        lock = ZEO.ClientStorage._lock_blob(cache_filename)
        try:
            # We got the lock, so it's our job to download it.  First,
            # we'll double check that someone didn't download it while we
            # were getting the lock:

            if os.path.exists(cache_filename):
                return ZEO.ClientStorage._accessed(cache_filename)

            # Actually download the blob.  When this function
            # returns, it will have been sent. (The receiving will
            # have been handled by the asyncore thread.)
            self.downloadBlob(oid, serial)

            if os.path.exists(cache_filename):
                return ZEO.ClientStorage._accessed(cache_filename)

            raise ZODB.POSException.POSKeyError("No blob file", oid, serial)
        finally:
            lock.close()

    def downloadBlob(self, oid, serial):
        """Fetch a blob from S3 into the cache."""

        key = s3_blob_filename(oid, serial)

        # Confirm blob cache directory is locked for writes
        cache_filename = self.fshelper.getBlobFilename(oid, serial)
        lock_filename = os.path.join(os.path.dirname(cache_filename), '.lock')
        assert os.path.exists(lock_filename)

        # Download
        self.bucket.download_file(key, cache_filename)
        os.chmod(cache_filename, stat.S_IREAD)

        # Cache bookkeeping
        self._blob_data_bytes_loaded += os.path.getsize(cache_filename)
        self._check_blob_size(self._blob_data_bytes_loaded)

    def openCommittedBlobFile(self, oid, serial, blob=None):
        blob_filename = self.loadBlob(oid, serial)
        try:
            if blob is None:
                return open(blob_filename, 'rb')
            else:
                return ZODB.blob.BlobFile(blob_filename, 'r', blob)
        except (IOError):
            # The file got removed while we were opening.
            # Fall through and try again with the protection of the lock.
            pass

        lock = ZEO.ClientStorage._lock_blob(blob_filename)
        try:
            blob_filename = self.loadBlob(oid, serial)
            if blob is None:
                return open(blob_filename, 'rb')
            else:
                return ZODB.blob.BlobFile(blob_filename, 'r', blob)
        finally:
            lock.close()

    def close(self):
        self.storage.close()
        if self._check_blob_size_thread is not None:
            self._check_blob_size_thread.join()

    _check_blob_size_thread = None
    def _check_blob_size(self, bytes=None):
        if self._blob_cache_size is None:
            return

        if (bytes is not None) and (bytes < self._blob_cache_size_check):
            return

        self._blob_data_bytes_loaded = 0

        target = max(self._blob_cache_size - self._blob_cache_size_check, 0)

        check_blob_size_thread = threading.Thread(
            target=ZEO.ClientStorage._check_blob_cache_size,
            args=(self.cache_dir, target),
            )
        check_blob_size_thread.setDaemon(True)
        check_blob_size_thread.start()
        self._check_blob_size_thread = check_blob_size_thread
