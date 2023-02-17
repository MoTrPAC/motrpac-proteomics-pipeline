import argparse
import json
import warnings

import dateparser
from google.cloud import storage


warnings.filterwarnings(
    "ignore", "Your application has authenticated using end user credentials"
)


def arg_parser():
    parser = argparse.ArgumentParser(description='Calculate a job completion time')
    parser.add_argument(
        '-p', '--project', required=True, type=str, help='GCP project name'
    )
    parser.add_argument(
        '-b',
        '--bucket_origin',
        required=True,
        type=str,
        help='Bucket with output files',
    )
    parser.add_argument(
        '-r',
        '--results_folder',
        required=True,
        type=str,
        help='Path to the results folder',
    )
    parser.add_argument(
        '-i',
        '--caper_job_id',
        required=True,
        type=str,
        help='Caper job id (E.g.: 9c6ff6fe-ce7d-4d23-ac18-9935614d6f9b)',
    )
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
    print('Caper Job ID:', caper_job_id)

    storage_client = storage.Client(project_name)
    blob = storage_client.bucket(bucket_origin).blob(f"{results_folder}/{caper_job_id}/metadata.json")

    if blob.exists():
        metadata = json.loads(blob.download_as_string().decode('utf-8'))
        start_time = dateparser.parse(metadata['start'])
        end_time = dateparser.parse(metadata['end'])
        print(f'Pipeline Running Time: {end_time - start_time}')
    else:
        print('\nMetadata file not found!!!\n')
        return

    if 'failures' in metadata and metadata['failures']:
        failures_length = len(metadata['failures'])
        print(f'PIPELINE ERRORS ({failures_length})')
        for i, failure in enumerate(metadata['failures']):
            causeby_len = len(failure['causedBy'])
            for j, causedBy in enumerate(failure['causedBy']):
                output = causedBy['message']
                print(f'\t- MESSAGE {j+1}: {output}')
    else:
        print('+ No errors found')

if __name__ == "__main__":
    main()
