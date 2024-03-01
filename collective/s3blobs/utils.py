def s3_blob_filename(oid, serial):
    return oid.hex() + serial.hex() + '.blob'
