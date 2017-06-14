def s3_blob_filename(oid, serial):
    return oid.encode('hex') + serial.encode('hex') + '.blob'
