import os
import ZODB.config
from .cache import S3BlobCache


class S3BlobCacheConfig(ZODB.config.BaseConfig):

    def open(self):
        options = {
            'cache_dir': self.config.cache_dir,
            'cache_size': self.config.cache_size,
            'bucket_name': self.config.bucket_name,
            'aws_access_key_id': os.environ.get('aws_access_key_id'),
            'aws_secret_access_key': os.environ.get('aws_secret_access_key'),
        }
        storage = self.config.storage.open()
        return S3BlobCache(storage, **options)
