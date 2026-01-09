#!/usr/bin/env python3


import os
import io
import logging
import stat
import argparse
import hashlib
import shutil
import tarfile

# --------------------------------------
import sys
if sys.version_info >= (3, 14):
    from compression import zstd
else:
    # pip install zstandard
    import zstandard as zstd
# --------------------------------------

HASH_LENGTH = 8

def hash_file(filename) -> str:
    with open(filename, "rb", buffering=0) as f:
        return hash_fileobj(f)

def hash_fileobj(f) -> str:
    h = hashlib.sha256()
    for b in iter(lambda: f.read(128*1024), b""):
        h.update(b)
    return h.hexdigest()


def main():
    logging.basicConfig(format="%(message)s")
    logger = logging.getLogger("copy")
    logger.setLevel(logging.DEBUG)

    args = argparse.ArgumentParser(description="...",
                                   formatter_class=argparse.RawTextHelpFormatter)
    args.add_argument("from_path", metavar="from", help="from")
    args.add_argument("to_path", metavar="to", help="to")

    args = args.parse_args()

    from_path = os.path.normpath(args.from_path)
    to_path = os.path.normpath(args.to_path)

    if os.path.isfile(from_path):
        tar = tarfile.open(from_path, "r")
    else:
        tar = None

    handle_tar(logger, tar, to_path)


def handle_tar(logger, tar, to_path: str):
    for member in tar.getmembers():
        if member.isfile() or member.islnk():
            f = tar.extractfile(member)
            file_hash = hash_fileobj(f)
            # ---------------------------------------------------
            f.seek(0, io.SEEK_END)
            length = f.tell()
            filename = file_hash[0:HASH_LENGTH] + "-" + str(length) + ".bin.zst"
            # ---------------------------------------------------
            to_abs = os.path.join(to_path, filename)

            if os.path.exists(to_abs):
                logger.info("Exists, skipped {} ({})".format(to_abs, member.name))
            else:
                logger.info("Extracted and compressing {} ({})".format(to_abs, member.name))
                # ---------------------------------------------------
                f.seek(0)
                with open(to_abs, 'wb') as dst_file:
                    if length>20000:
                        zstd.ZstdCompressor(level=19).copy_stream(f,dst_file)
                    else:
                        zstd.ZstdCompressor(level=3).copy_stream(f,dst_file)
                # ---------------------------------------------------

if __name__ == "__main__":
    main()
