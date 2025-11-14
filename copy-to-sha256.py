#!/usr/bin/env python3

# pip install backports.zstd

import os
import io
import logging
import stat
import argparse
import hashlib
import shutil
import tarfile

# --- New Zstandard import and setup ---
import sys
if sys.version_info >= (3, 14):
    from compression import zstd
else:
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

# --- New compression function ---
def compress_file_zstd(src_path, dst_path):
    """
    Compresses a file at src_path to a Zstandard compressed file at dst_path.
    Uses the highest compression level for minimal size.
    """
    compressor = zstd.ZstdCompressor(level=22)
    with open(src_path, 'rb') as src_file:
        with open(dst_path, 'wb') as dst_file:
            compressor.copy_stream(src_file,dst_file)
import struct

def compress_fileobj_zstd(src_fileobj, dst_path):
    """
    Compresses a file-like object to a Zstandard compressed file.
    """
    with open(dst_path, 'wb') as dst_file:
        src_fileobj.seek(0, io.SEEK_END)
        length = src_fileobj.tell()
        src_fileobj.seek(0)  # Ensure we're at the beginning
        dst_file.write(struct.pack('<i', length))
        if length>20000:
            zstd.ZstdCompressor(level=22).copy_stream(src_fileobj,dst_file)
        else:
            zstd.ZstdCompressor(level=3).copy_stream(src_fileobj,dst_file)
# --------------------------------


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

    if tar:
        handle_tar(logger, tar, to_path)
    else:
        handle_dir(logger, from_path, to_path)

def handle_dir(logger, from_path: str, to_path: str):
    def onerror(oserror):
        logger.warning(oserror)

    files = os.walk(from_path, onerror=onerror)

    for f in files:
        dirpath, dirnames, filenames = f

        for filename in filenames:
            absname = os.path.join(dirpath, filename)
            st = os.lstat(absname)
            mode = st.st_mode

            assert not stat.S_ISDIR(mode)
            if stat.S_ISLNK(mode) or stat.S_ISCHR(mode) or stat.S_ISBLK(mode) or stat.S_ISFIFO(mode) or stat.S_ISSOCK(mode):
                continue

            file_hash = hash_file(absname)
            filename = file_hash[0:HASH_LENGTH] + ".bin.zst"
            to_abs = os.path.join(to_path, filename)

            if os.path.exists(to_abs):
                logger.info("Exists, skipped {} ({})".format(to_abs, absname))
            else:
                logger.info("Compressing {} to {}".format(absname, to_abs))
                # --- Replaced shutil.copyfile with compression function ---
                compress_file_zstd(absname, to_abs)
                # ----------------------------------------------------------

def handle_tar(logger, tar, to_path: str):
    for member in tar.getmembers():
        if member.isfile() or member.islnk():
            f = tar.extractfile(member)
            file_hash = hash_fileobj(f)
            filename = file_hash[0:HASH_LENGTH] + ".bin.zst"
            to_abs = os.path.join(to_path, filename)

            if os.path.exists(to_abs):
                logger.info("Exists, skipped {} ({})".format(to_abs, member.name))
            else:
                logger.info("Extracted and compressing {} ({})".format(to_abs, member.name))
                # --- Compress the extracted file object directly ---
                compress_fileobj_zstd(f, to_abs)
                # ---------------------------------------------------

if __name__ == "__main__":
    main()
