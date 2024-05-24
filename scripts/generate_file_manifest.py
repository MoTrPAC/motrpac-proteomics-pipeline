import argparse
import sys
from base64 import b64decode
from typing import Iterator, Tuple


try:
    from google.cloud import storage
    from google.cloud.storage import Blob, Bucket
except ImportError:
    print("Please install google-cloud-storage", file=sys.stderr)
    sys.exit(1)

if sys.version_info[0] < 3:
    raise Exception("Must be using at least Python 3.9")
if sys.version_info[1] < 9:
    raise Exception("Must be using at least Python 3.9")

SEPARATOR = ","
storage_client = storage.Client()


def parse_bucket_path(path: str) -> Tuple[str, str]:
    """
    Split a full S3 path in bucket and key strings. 's3://bucket/key' -> ('bucket', 'key')
    :param path: S3 path (e.g. s3://bucket/key).
    :return: Tuple of bucket and key strings
    """
    if path.startswith("gs://") is False:
        raise ValueError(f"'{path}' is not a valid path. It MUST start with 'gs://'")

    # remove the gs:// prefix, then split on the first "/" character
    parts = path.replace("gs://", "").split("/", 1)
    # the bucket is the first split part
    bucket: str = parts[0]
    if bucket == "":
        raise ValueError("Empty bucket name received")
    if "/" in bucket or bucket == " ":
        raise ValueError(f"'{bucket}' is not a valid bucket name.")
    # the key is the second split part
    key: str = ""
    if len(parts) == 2:
        key = key if parts[1] is None else parts[1]

    return bucket.rstrip("/"), f"{key.rstrip('/')}/"


def generate_manifest(path, outfile):
    lines = 0
    data = "file_name,md5\n"

    bucket_name, prefix = parse_bucket_path(path)

    bucket: Bucket = storage_client.bucket(bucket_name)
    blob_list: Iterator[Blob] = bucket.list_blobs(prefix=prefix)

    for blob in blob_list:
        print(f"Processing {blob.name}")
        if blob.name.endswith("/") or "file_manifest" in blob.name:
            continue
        relative_filename = blob.name.removeprefix(prefix)
        decoded_hash = b64decode(blob.md5_hash).hex()
        data += f"{relative_filename},{decoded_hash}\n"
        lines += 1

    manifest_name = f"{prefix}{outfile}"

    print(f"Writing manifest to {manifest_name}")
    print(data)

    file_manifest_blob = Blob(bucket=bucket, name=manifest_name)
    file_manifest_blob.upload_from_string(data, content_type="text/csv")

    if lines == 0:
        raise Exception(f"No files found at {path}. Please double check")
    else:
        print(f"Wrote data for {lines} files")


def main():
    parser = argparse.ArgumentParser(
        description="Creates manifest for submission to BIC: a comma separated file "
                    "with relative file paths and md5 sums."
    )
    parser.add_argument(
        "data_path",
        help="Full path to folder containing all files for data submission "
             "(including gs:// prefix)",
    )
    parser.add_argument(
        "output", default="file_manifest.csv", help="Name of the output file"
    )
    args = parser.parse_args()
    generate_manifest(args.data_path, args.output)


if __name__ == "__main__":
    main()
