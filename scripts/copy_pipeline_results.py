"""
Copy the pipeline result for MSGF+ from the workflow outputs bucket/folder to the
destination bucket/folder.
"""

import argparse
import json
import logging
import re
import sys
import warnings
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from copy import copy
from functools import wraps
from pathlib import Path
from typing import List, Tuple, TypeVar

import dateparser
from google.api_core.exceptions import GoogleAPICallError, ServiceUnavailable
from google.cloud.storage import Bucket, Client

if sys.version_info >= (3, 10):
    from typing import ParamSpec
else:
    try:
        from typing_extensions import ParamSpec
    except ImportError:
        print("Please pip install `typing_extensions`", file=sys.stderr)
        sys.exit(1)

warnings.filterwarnings(
    "ignore",
    "Your application has authenticated using end user credentials",
)

MAPPING = {
    "DEBUG": 37,  # white
    "INFO": 36,  # cyan
    "WARNING": 33,  # yellow
    "ERROR": 31,  # red
    "CRITICAL": 41,  # white on red bg
}

PREFIX = "\033["
SUFFIX = "\033[0m"


class ColoredFormatter(logging.Formatter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def format(self, record):
        colored_record = copy(record)
        levelname = colored_record.levelname
        seq = MAPPING.get(levelname, 37)  # default white
        colored_record.levelname = f"{PREFIX}{seq}m{levelname}{SUFFIX}"
        return super().format(colored_record)


base_logger = logging.getLogger("copy_pipeline_results")
syslog = logging.StreamHandler()
formatter = ColoredFormatter(
    "%(levelname)s :: %(asctime)s.%(msecs)03d :: %(task)s :: %(message)s",
    datefmt="%Y/%M/%d %H:%M:%S",
)
syslog.setFormatter(formatter)
base_logger.setLevel(logging.INFO)
base_logger.addHandler(syslog)

P = ParamSpec("P")
R = TypeVar("R")
_DEFAULT_POOL = ThreadPoolExecutor()


def threadpool(f: Callable[P, R], pool: ThreadPoolExecutor | None = None) -> Callable[P, Future[R]]:
    """
    Decorator that wraps a function and runs it in a threadpool.

    :param f: The function to wrap
    :param pool: A threadpool to use, or the default threadpool if None
    :return: The wrapped function
    """

    @wraps(f)
    def wrap(*args, **kwargs) -> Future[R]:
        return (pool or _DEFAULT_POOL).submit(f, *args, **kwargs)

    return wrap


def trim_gs_prefix(full_file_path: str, bucket_name: str) -> str:
    """
    Replace the gs://bucket/ portion from the file path.

    :param full_file_path: The full file path
    :param bucket_name: The bucket name to replace
    """
    gs_bucket_name = f"gs://{bucket_name}/"
    return full_file_path.replace(gs_bucket_name, "")


def upload_string(
    bucket_destination: Bucket,
    str_content: str,
    destination_blob_name: str,
) -> None:
    """
    Upload a string to Google Cloud Storage.

    :param bucket_destination: the destination_bucket
    :param str_content: The string content to upload
    :param destination_blob_name: The filename of the file to create
    """
    b = bucket_destination.blob(destination_blob_name)
    b.upload_from_string(str_content)


def parse_bucket_path(path: str) -> tuple[str, str]:
    """
    Split a full S3/GCS path in to bucket and key strings.
    's3://bucket/key' -> ('bucket', 'key').

    :param path: S3/GCS path (e.g. s3://bucket/key).
    :return: Tuple of bucket and key strings
    """
    gcs_prefix = "gs://"
    s3_prefix = "s3://"

    if not path.startswith(s3_prefix) and not path.startswith(gcs_prefix):
        err_msg = f"'{path}' is not a valid path. It MUST start with 's3://' or 'gs://'"
        raise ValueError(err_msg)

    if path.startswith(gcs_prefix):
        parts = path.replace(gcs_prefix, "").split("/", 1)
    else:
        parts = path.replace(s3_prefix, "").split("/", 1)

    bucket: str = parts[0]
    if bucket == "":
        err_msg = "Empty bucket name received"
        raise ValueError(err_msg)
    if "/" in bucket or bucket == " ":
        err_msg = f"'{bucket}' is not a valid bucket name."
        raise ValueError(err_msg)
    key: str = ""
    if len(parts) == 2:
        key = key if parts[1] is None else parts[1]
    return bucket, key


class CopySpec:
    """
    Sets up a copy job from the target to the destination, contains common objects used
    across all tasks.
    """

    logger = logging.LoggerAdapter(base_logger, {"task": "General"})

    def __init__(
        self,
        wf_id: str,
        project: str,
        source_location: str,
        destination_location: str,
        *,
        dry_run: bool,
    ) -> None:
        """
        Create a CopySpec instance. Creates the source and destination bucket and folder
        names from the paths given, creates the Google Cloud Storage client, searches
        for and loads the metadata file from the source bucket/folder.

        :param wf_id: The workflow id (prefix in inputs.json)
        :param project: The project to create the storage client for
        :param source_location: The source of workflow outputs
            (e.g. gs://my-bucket/my-folder/outputs)
        :param destination_location: The destination to copy the outputs to
            (e.g. gs://my-bucket/my-outputs)
        :param dry_run: Whether to actually copy the files
        """
        source_bucket, source_folder = parse_bucket_path(source_location)
        destination_bucket, destination_folder = parse_bucket_path(destination_location)

        self.wf_id = wf_id
        self.client = Client(project=project)
        self.source_bucket = self.client.get_bucket(source_bucket)
        self.source_folder = source_folder.rstrip("/")
        self.destination_bucket = self.client.get_bucket(destination_bucket)
        self.destination_folder = destination_folder.rstrip("/")
        self.metadata = self.set_metadata()
        self.wf_inputs = {
            key.removeprefix("proteomics_msgfplus."): value
            for key, value in self.metadata["inputs"].items()
        }
        self.dry_run = dry_run

        start_time = dateparser.parse(self.metadata["start"])
        end_time = dateparser.parse(self.metadata["end"])
        self.logger.info("Pipeline Running Time: %s", end_time - start_time)

        self.tasks: list[TaskSpec] = []
        self.running_futures: list[Future[None]] = []

    def set_metadata(self) -> dict:
        """
        Find and set the metadata.json file in the source bucket/folder.

        :return: The loaded metadata.json object.
        """

        metadata = None
        self.logger.info("Searching for metadata.json in file list")
        # assume that the metadata file is called metadata.json
        metadata_blob = self.source_bucket.get_blob(f"{self.source_folder}/metadata.json")
        if metadata_blob is not None:
            self.logger.info("Metadata file location: %s", metadata_blob.name)
            return json.loads(metadata_blob.download_as_string(client=None))

        # if we can't find the metadata file, search for it
        bucket_content_list = self.client.list_blobs(
            self.source_bucket,
            prefix=f"{self.source_folder}/",
        )
        # Get and load the metadata.json file
        for blob in bucket_content_list:
            m = re.match("(.*.metadata.json)", blob.name)
            if m:
                self.logger.info("Metadata file location: %s", m[1])
                metadata = json.loads(blob.download_as_string(client=None))
                break

        if metadata is None:
            self.logger.error(
                "Error: unable to find metadata.json file in %s specified",
                f"gs://{self.source_bucket.name}/{self.source_folder}/",
            )
            sys.exit(1)

        return metadata

    def create_task(
        self,
        task_id: str,
        stdout_filename: Callable[[dict], str] | str | None,
        command_filename: Callable[[dict], str] | str | None,
        outputs: list[str],
        output_folder: str | None = None,
        inputs: List[Tuple[str, str]] = None,
    ) -> None:
        """
        Create a new TaskSpec and append it to the list of tasks to do.

        :param task_id: The id of the call
        :param stdout_filename: What to call the stdout file, takes either a static
            string, or a callable which takes the call_attempt dict as an argument
        :param command_filename:  What to call the command line file, takes either a
            static string, or a callable which takes the call_attempt dict as an argument
        :param outputs: The names of the outputs to copy, should be keys in the outputs
            dict
        :param output_folder: The folder to copy the results to, defers to TaskSpec if
            not provided
        :param inputs: Any global inputs to copy
        """
        self.tasks.append(
            TaskSpec(
                task_id,
                stdout_filename,
                command_filename,
                outputs,
                self,
                output_folder,
                inputs,
            ),
        )

    def run_tasks(self) -> List[None]:
        """Run all tasks for the copy job."""
        for task in self.tasks:
            task.run_copy()

        return [f.result() for f in as_completed(self.running_futures)]


class TaskSpec:
    """
    Holds all information for copying files for a given task.
    """

    def __init__(
        self,
        task_id: str,
        stdout_filename: Callable[[dict], str] | str | None,
        command_filename: Callable[[dict], str] | str | None,
        outputs: list[str],
        copy_spec: CopySpec,
        output_folder: str | None = None,
        inputs: List[Tuple[str, str]] = None,
    ) -> None:
        """
        Create a new TaskSpec.

        :param task_id: The id of the call
        :param stdout_filename: What to call the stdout file, takes either a static
            string, or a callable which takes the call_attempt dict as an argument
        :param command_filename:  What to call the command line file, takes either a
            static string, or a callable which takes the call_attempt dict as an argument
        :param outputs: The names of the outputs to copy, should be keys in the outputs
            dict
        :param copy_spec: The spec for the copy job which contains the source and
            information destination as well as the metadata
        :param output_folder: If not given, defaults to the task id pre-pended to _outputs
        :param inputs: Any global inputs to copy
        """
        self.task_id = task_id
        self._stdout_filename = stdout_filename
        self._command_filename = command_filename
        self.outputs = outputs
        self.inputs = inputs
        self.copy_spec = copy_spec
        self.output_folder = output_folder or f"{copy_spec.destination_folder}/{task_id}_outputs"

        self.calls = copy_spec.metadata["calls"][f"{copy_spec.wf_id}.{self.task_id}"]
        self.attempt = {}
        self.logger = logging.LoggerAdapter(base_logger, {"task": task_id.upper()})

    @property
    def command_filename(self) -> str:
        """
        Return the command filename, calling it if the provided command filename is a
        function.

        :return: The stdout filename
        """
        if callable(self._command_filename):
            return self._command_filename(self.attempt)
        return self._command_filename

    @property
    def stdout_filename(self) -> str:
        """
        Return the stdout filename, calling it if the provided stdout filename is a
        function.

        :return: The stdout filename
        """
        if callable(self._stdout_filename):
            return self._stdout_filename(self.attempt)
        return self._stdout_filename

    def write_command_to_file(self, call_attempt: dict, file_name: str) -> None:
        """
        Extract the command executed on each call available as text in the metadata.json
        file and save it in the bucket as a file.

        :param call_attempt: The call_attempt metadata object
        :param file_name: the file name
        """
        cmd_txt = call_attempt.get("commandLine")
        if cmd_txt is not None:
            cmd_txt_name = f"{self.output_folder}/{file_name}"
            self.logger.info("- Command to file: %s", cmd_txt_name)
            if not self.copy_spec.dry_run:
                new_blob_command = self.copy_spec.destination_bucket.blob(cmd_txt_name)
                new_blob_command.upload_from_string(cmd_txt, content_type="text/plain")
        else:
            self.logger.warning("----> Unable to copy commandLine")

    def run_copy(self) -> None:
        """
        Copy files from the source to the destination.
        """
        # copy any source files
        if self.inputs is not None:
            inputs_dict = self.copy_spec.wf_inputs
            for key, directory in self.inputs:
                self.copy_file_to_new_location(
                    inputs_dict,
                    key,
                    f"{directory.rstrip('/')}/{Path(inputs_dict[key]).name}".lstrip("/"),
                )

        for call_attempt in self.calls:
            # set the attempt to get the proper stdout filename
            self.attempt = call_attempt
            # copy any stdout file if given a filename
            if self.stdout_filename is not None and "stdout" in call_attempt:
                self.copy_file_to_new_location(
                    call_attempt,
                    "stdout",
                    self.stdout_filename,
                )

            # copy any commandline if given a filename
            if self.command_filename is not None:
                self.write_command_to_file(call_attempt, self.command_filename)

            execution_status = call_attempt["executionStatus"]
            if execution_status == "Done":
                # copy all outputs
                call_outputs = call_attempt["outputs"]
                for output in self.outputs:
                    self.copy_file_to_new_location(call_outputs, output)
            else:
                self.logger.warning(" (-) Execution Status: %s", execution_status)
                self.logger.warning(" (-) Data cannot be copied")

    def copy_file_to_new_location(
        self,
        attempt_outputs_dict: dict,
        output_name: str,
        new_filename: str = None,
    ) -> None:
        """
        Copy a file from the given dictionary at the key `output_name` in the source
        bucket to the destination bucket with the new path (and optional filename).

        :param attempt_outputs_dict: The dictionary being searched
        :param output_name: The key to look for the file in the `attempt_outputs_dict`
        :param new_filename: An optional new filename to give the object
        """
        file_to_copy = attempt_outputs_dict.get(output_name)
        if file_to_copy is not None:
            if isinstance(file_to_copy, list):
                for f in file_to_copy:
                    self.copy_single_file(f, new_filename, output_name)
            elif isinstance(file_to_copy, str):
                self.copy_single_file(file_to_copy, new_filename, output_name)
            else:
                self.logger.error(
                    "----> Unable to copy %s, key has unsupported type %s",
                    output_name,
                    type(file_to_copy),
                )
        else:
            self.logger.error("----> Unable to copy %s, key does not exist", output_name)

    @threadpool
    def copy_single_file(
        self,
        orig_filename: str,
        new_filename: str,
        output_name: str,
    ) -> None:
        """
        Copy a single file with the original filename to the new_filename.

        :param orig_filename: The original file's gs://path
        :param new_filename: The new file's filename
        :param output_name: The name of the output in the outputs dict
        """
        # remove the gs://<bucket>/ prefix from the data
        orig_file_bucket, orig_filename = parse_bucket_path(orig_filename)
        # if not supplied with a new filename, use the original base filename
        if new_filename is None:
            new_filename = Path(orig_filename).name
        # create the new file path
        new_file_path = f"{self.output_folder}/{new_filename}"
        # get the original file
        # avoid creating a new bucket instance if the file is in the same bucket
        if orig_file_bucket == self.copy_spec.source_bucket.name:
            original_file = self.copy_spec.source_bucket.get_blob(orig_filename)
        else:
            # get the other bucket
            other_bucket = self.copy_spec.client.get_bucket(orig_file_bucket)
            if other_bucket is None:
                self.logger.error(
                    "----> Unable to copy %s file at %s, bucket does not exist",
                    output_name,
                    orig_filename,
                )
                return
            # get the original file from the other bucket
            original_file = other_bucket.get_blob(orig_filename)
        # copy the original file if it exists, log an error if it doesn't
        if original_file is not None:
            if not self.copy_spec.dry_run:
                try:
                    self.copy_spec.source_bucket.copy_blob(
                        original_file,
                        self.copy_spec.destination_bucket,
                        new_file_path,
                    )
                except ServiceUnavailable as e:
                    if "use the Rewrite method" in e.message:
                        self.logger.warning(
                            "----> Unable to copy %s from %s to %s within Google's "
                            "allowed time. Attempting to copy using the rewrite method.",
                            output_name,
                            orig_filename,
                            f"gs://{self.copy_spec.destination_bucket.name}/" f"{new_file_path}",
                        )
                        try:
                            dest_blob = self.copy_spec.destination_bucket.blob(new_file_path)

                            rewrite_token = False

                            while True:
                                (
                                    rewrite_token,
                                    bytes_rewritten,
                                    bytes_to_rewrite,
                                ) = dest_blob.rewrite(original_file, token=rewrite_token)
                                self.logger.info(
                                    "%s: Progress so far: %.2f%% (%d/%d) bytes.",
                                    f"gs://{self.copy_spec.destination_bucket.name}/"
                                    f"{new_file_path}",
                                    bytes_rewritten / bytes_to_rewrite * 100,
                                    bytes_rewritten,
                                    bytes_to_rewrite,
                                )
                                if not rewrite_token:
                                    break
                        except GoogleAPICallError as e:
                            self.logger.error(
                                "----> Unable to rewrite %s from %s to %s. " "Google API error: %s",
                                output_name,
                                orig_filename,
                                f"gs://{self.copy_spec.destination_bucket.name}/"
                                f"{new_file_path}",
                                e,
                            )
                    else:
                        self.logger.error(
                            "----> Unable to copy %s from %s to %s. " "Google API error: %s",
                            output_name,
                            orig_filename,
                            f"gs://{self.copy_spec.destination_bucket.name}/" f"{new_file_path}",
                            e,
                        )
                except GoogleAPICallError as e:
                    self.logger.error(
                        "----> Unable to copy %s from %s to %s. " "Google API error: %s",
                        output_name,
                        orig_filename,
                        f"gs://{self.copy_spec.destination_bucket.name}/{new_file_path}",
                        e,
                    )

            log_copy = "Copied"
            if self.copy_spec.dry_run:
                log_copy = "DRY RUN: Copied"
            self.logger.info(
                "%s - %s file from %s to %s",
                log_copy,
                output_name,
                f"gs://{orig_file_bucket}/{orig_filename}",
                f"gs://{self.copy_spec.destination_bucket.name}/{new_file_path}",
            )
        else:
            self.logger.error(
                "----> Unable to copy %s from %s to %s",
                output_name,
                orig_filename,
                f"gs://{self.copy_spec.destination_bucket.name}/{new_file_path}",
            )


def create_args():
    parser = argparse.ArgumentParser(
        description="Copy proteomics pipeline output files to a desire location",
    )
    parser.add_argument(
        "-p",
        "--project",
        required=True,
        type=str,
        help="GCP project name. Required.",
    )
    parser.add_argument(
        "-o",
        "--origin",
        required=True,
        type=str,
        help="Bucket with output files. Required. "
        "(e.g. gs://my-bucket/test/results/input_test_gcp_s6-global-2files-8/)",
    )
    parser.add_argument(
        "-m",
        "--method_proteomics",
        required=True,
        type=str,
        choices=["msgfplus", "maxquant"],
        help="Proteomics Method. Currently supported: msgfplus or maxquant.",
    )
    parser.add_argument(
        "-d",
        "--destination",
        required=True,
        type=str,
        help="Full path to copy the files to. Required. "
        "(e.g. gs://my-bucket/test/results/input_test_gcp_s6-global-2files-8/)",
    )
    parser.add_argument(
        "-c",
        "--copy_what",
        required=True,
        default="results",
        type=str,
        choices=["full", "results", "ppinputs"],
        help="What would you like to copy: <full>: all msgfplus outputs "
        "<results>: plexedpiper results only",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't actually copy the files, just print what it's going to do",
    )
    return parser


def main():
    parser = create_args()
    args = parser.parse_args()
    logger = logging.LoggerAdapter(base_logger, {"task": "General"})

    project_name = args.project.rstrip("/")
    logger.info("GCP project: %s", project_name)
    origin = args.origin.rstrip("/")
    logger.info("Origin: %s", origin)
    destination = args.destination.rstrip("/")
    logger.info("Destination: %s", destination)
    method_proteomics = args.method_proteomics
    logger.info("+ Proteomics Pipeline METHOD: %s", method_proteomics)

    if args.dry_run:
        logger.info("This is a dry run, no files will be copied")

    if method_proteomics == "maxquant":
        logger.info("PROTEOMICS METHOD: maxquant")
        logger.info("+ Copy MAXQUANT outputs-----------------------------")
        copy_job = CopySpec(
            wf_id="proteomics_maxquant",
            project=project_name,
            source_location=origin,
            destination_location=destination,
            dry_run=args.dry_run,
        )
        copy_job.create_task(
            "maxquant",
            "console-maxquant-stdout.log",
            "maxquant-command.log",
            [
                "evidence",
                "modificationSpecificPeptides",
                "allPeptides",
                "peptides",
                "mzRange",
                "matchedFeatures",
                "ms3Scans",
                "proteinGroups",
                "msms",
                "runningTimes",
                "libraryMatch",
                "msmsScans",
                "parameters",
                "summary",
                "sites",
            ],
        )
    else:
        copy_job = CopySpec(
            wf_id="proteomics_msgfplus",
            project=project_name,
            source_location=origin,
            destination_location=destination,
            dry_run=args.dry_run,
        )
        logger.info("PROTEOMICS METHOD: msgfplus")
        if "inputs" in copy_job.metadata:
            is_ptm = copy_job.wf_inputs.get("isPTM") or (
                copy_job.wf_inputs.get("proteomics_experiment") != "pr"
            )
            if is_ptm is None:
                logger.warning("Unable to determine if PTM experiment, no key found")
                is_ptm = False

            if is_ptm:
                logger.info("######## PTM PROTEOMICS EXPERIMENT ########")
            else:
                logger.info(
                    "####### GLOBAL PROTEIN ABUNDANCE EXPERIMENT #######",
                )
        if args.copy_what == "full":
            logger.info("Ready to copy ALL MSGF-plus outputs")

            if "proteomics_msgfplus.ascore" in copy_job.metadata["calls"]:
                copy_job.create_task(
                    task_id="ascore",
                    stdout_filename=lambda x: f"{x['inputs']['seq_file_id']}-ascore-stdout.log",
                    command_filename="ascore-command.log",
                    outputs=[
                        "syn_plus_ascore",
                        "syn_ascore",
                        "syn_ascore_proteinmap",
                        "output_ascore_logfile",
                    ],
                )

            copy_job.create_task(
                task_id="msconvert_mzrefiner",
                stdout_filename=lambda x: f"{x['inputs']['sample_id']}-msconvert_mzrefiner-stdout.log",
                command_filename="msconvert_mzrefiner-command.log",
                outputs=["mzml_fixed"],
            )

            copy_job.create_task(
                task_id="ppm_errorcharter",
                stdout_filename=lambda x: f"{x['inputs']['sample_id']}-ppm_errorcharter-stdout.log",
                command_filename="ppm_errorcharter-command.log",
                outputs=["ppm_masserror_png", "ppm_histogram_png"],
            )

            copy_job.create_task(
                task_id="masic",
                stdout_filename=lambda x: f"{Path(x['inputs']['raw_file']).name.replace('.raw', '')}-masic-stdout.log",
                command_filename="masic-command.log",
                outputs=[
                    "ReporterIons_output_file",
                    "PeakAreaHistogram_output_file",
                    "RepIonObsRateHighAbundance_output_file",
                    "RepIonObsRate_output_txt_file",
                    "MSMS_scans_output_file",
                    "SICs_output_file",
                    "MS_scans_output_file",
                    "SICstats_output_file",
                    "ScanStatsConstant_output_file",
                    "RepIonStatsHighAbundance_output_file",
                    "ScanStatsEx_output_file",
                    "ScanStats_output_file",
                    "PeakWidthHistogram_output_file",
                    "RepIonStats_output_file",
                    "DatasetInfo_output_file",
                    "RepIonObsRate_output_png_file",
                ],
            )

            copy_job.create_task(
                task_id="msconvert",
                stdout_filename=lambda x: f"{Path(x['inputs']['raw_file']).name.replace('.raw', '')}-msconvert-stdout.log",
                command_filename="msconvert-command.log",
                outputs=["mzml"],
            )

            copy_job.create_task(
                task_id="msgf_identification",
                stdout_filename=lambda x: f"{x['inputs']['sample_id']}-msgf_identification-stdout.log",
                command_filename="msgf_identification-command.log",
                outputs=["rename_mzmlfixed", "mzid_final"],
            )

            copy_job.create_task(
                task_id="msgf_sequences",
                stdout_filename="msgf_sequences-stdout.log",
                command_filename="msgf_sequences-command.log",
                outputs=["revcat_fasta, sequencedb_files"],
            )

            copy_job.create_task(
                task_id="msgf_tryptic",
                stdout_filename=lambda x: f"{x['inputs']['sample_id']}" f"-msgf_tryptic-stdout.log",
                command_filename="msgf_tryptic-command.log",
                outputs=["mzid"],
            )

            copy_job.create_task(
                task_id="phrp",
                stdout_filename=lambda x: f"{Path(x['inputs']['input_tsv']).name.replace('.tsv', '')}-phrp-stdout.log",
                command_filename="phrp-command.log",
                outputs=[
                    "syn_ResultToSeqMap",
                    "fht",
                    "PepToProtMapMTS",
                    "syn_ProteinMods",
                    "syn_SeqToProteinMap",
                    "syn",
                    "syn_ModSummary",
                    "syn_SeqInfo",
                    "syn_ModDetails",
                ],
            )

            copy_job.create_task(
                task_id="mzidtotsvconverter",
                stdout_filename=lambda x: f"{x['inputs']['sample_id']}-mzidtotsvconverter-stdout.log",
                command_filename="mzidtotsvconverter-command.log",
                outputs=["tsv"],
            )

            if "proteomics_msgfplus.wrapper_pp" in copy_job.metadata["calls"]:
                copy_job.create_task(
                    task_id="wrapper_pp",
                    stdout_filename=None,
                    command_filename="wrapper_results-command.log",
                    outputs=[
                        "results_ratio",
                        "results_rii",
                        "final_output_masic_tar",
                        "final_output_phrp_tar",
                        "final_output_ascore",
                    ],
                )
            else:
                logger.error("(-) Plexed piper not available")

        elif args.copy_what == "ppinputs":
            logger.info("Ready to copy ONLY PlexedPiper results + inputs")
            copy_job.create_task(
                task_id="wrapper_pp",
                stdout_filename=None,
                command_filename=None,
                outputs=[
                    "results_ratio",
                    "results_rii",
                    "final_output_masic_tar",
                    "final_output_phrp_tar",
                    "final_output_ascore",
                ],
                output_folder=copy_job.destination_folder,
                inputs=[
                    ("fasta_sequence_db", ""),
                    ("sd_samples", "study_design"),
                    ("sd_fractions", "study_design"),
                    ("sd_references", "study_design"),
                ],
            )

        elif args.copy_what == "results":
            logger.info("Ready to copy ONLY PlexedPiper (RII + Ratio) results")
            if "proteomics_msgfplus.wrapper_pp" in copy_job.metadata["calls"]:
                copy_job.create_task(
                    task_id="wrapper_pp",
                    stdout_filename=None,
                    command_filename=None,
                    outputs=["results_ratio", "results_rii"],
                    output_folder=f"{copy_job.destination_folder}",
                )
            else:
                logger.error("(-) Plexed piper not available")
        else:
            err_msg = "You should not have gotten here"
            raise ValueError(err_msg)

        copy_job.run_tasks()
        _DEFAULT_POOL.shutdown(wait=True, cancel_futures=False)
        logger.info("All Done!")


if __name__ == "__main__":
    main()
