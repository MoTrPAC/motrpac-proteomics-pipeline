
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
    parser.add_argument('-p', '--project', required=True, type=str,
                        help='GCP project name')
    parser.add_argument('-b', '--bucket_origin', required=True, type=str,
                        help='Bucket with output files')
    parser.add_argument('-r', '--results_folder', required=True, type=str,
                        help='Path to the results folder')
    parser.add_argument('-i', '--caper_job_id', required=True, type=str,
                        help='Caper job id (E.g.: 9c6ff6fe-ce7d-4d23-ac18-9935614d6f9b)')
    return parser

def main():
    parser = arg_parser()
    args = parser.parse_args()

    project_name = args.project.rstrip('/')
    print('\nGCP project:', project_name)

    bucket_origin = args.bucket_origin.rstrip('/')
    print('Bucket origin:', bucket_origin)

    results_folder = args.results_folder.rstrip('/')
    print('Results folder:', results_folder)

    caper_job_id = args.caper_job_id
    print('Caper Job ID:',caper_job_id)

    storage_client = storage.Client(project_name)
    # bucket_source = storage_client.get_bucket(bucket_origin)

    # all_blobs = storage_client.list_blobs(bucket_origin)
    # regex = re.compile(r'.*/' + caper_job_id)
    all_blobs = storage_client.list_blobs(bucket_origin, prefix=results_folder)

    for blob in all_blobs:
        if blob.name.endswith(caper_job_id + '/metadata.json'):
            filename = blob.name
            print('\nMetadata file location:\n', filename, '\n')
            metadata = json.loads(blob.download_as_string(client=None))
            break
    
    if metadata.get('start'):
        start_time = dateparser.parse(metadata['start'])
        end_time = dateparser.parse(metadata['end'])
        print('Pipeline Running Time: ',end_time - start_time)
    else:
        print('\nStart time not available!!!\n')

    if metadata.get('failures'):
        failures_length = len(metadata['failures'])
        print('PIPELINE ERRORS (', failures_length, ')')
        for x in range(failures_length):
            causeby_len = len(metadata['failures'][x]['causedBy'])
            for y in range(causeby_len):
                output = metadata['failures'][x]['causedBy'][y]['message']
                print('\t- MESSAGE ', y+1,': ', output,"\n")
    else:
        print('+ No errors detected (congratulations)!\n')


if __name__ == "__main__":
    main()
