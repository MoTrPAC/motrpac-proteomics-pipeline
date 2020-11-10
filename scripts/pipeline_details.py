
import argparse
import getopt
from google.cloud import storage
import json
import os
import pathlib
import re
import sys
import warnings
import dateparser
warnings.filterwarnings("ignore", "Your application has authenticated using end user credentials")

def arg_parser():
    parser = argparse.ArgumentParser(description='Calculate a job completion time')
    parser.add_argument('-p', '--project', required=True, type=str, help='GCP project name. Required.')
    parser.add_argument('-b', '--bucket_origin', required=True, type=str, help='Bucket with output files. Required.')
    parser.add_argument('-c', '--caper_job_id', required=True, type=str, help='Caper job id (E.g.: 9c6ff6fe-ce7d-4d23-ac18-9935614d6f9b)')
    return parser

def main():
    parser = arg_parser()
    args = parser.parse_args()
    
    print('')

    project_name = args.project
    print('GCP project:', project_name)

    bucket_origin = args.bucket_origin
    print('Bucket origin:', bucket_origin)

    caper_job_id = args.caper_job_id
    print('Caper Job ID:',caper_job_id)

    storage_client = storage.Client(project_name)
    # bucket_source = storage_client.get_bucket(bucket_origin)

    all_blobs = storage_client.list_blobs(bucket_origin)
    # regex = re.compile(r'.*/' + caper_job_id)

    for blob in all_blobs:
        if blob.name.endswith(caper_job_id + '/metadata.json'):
            filename = blob.name
            print('\nMetadata file location:\n', filename, '\n')
            filename = blob.name
            metadata = json.loads(blob.download_as_string(client=None))
            break

    start_time = dateparser.parse(metadata['start'])
    end_time = dateparser.parse(metadata['end'])

    print('\nPipeline Running Time: ',end_time - start_time)

    print('\n')

if __name__ == "__main__":
    main()
