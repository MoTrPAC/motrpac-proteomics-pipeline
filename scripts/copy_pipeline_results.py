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
from pathlib import Path

import dateparser
from google.cloud import storage
from google.cloud.storage import Bucket

logging.basicConfig(filename="example.log", encoding="utf-8", level=logging.DEBUG)

warnings.filterwarnings(
    "ignore",
    "Your application has authenticated using end user credentials",
)

logger = logging.getLogger(__name__)


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


def copy_file_to_new_location(
    attempt_outputs_dict: dict,
    output_name: str,
    source_bucket: Bucket,
    dest_bucket: Bucket,
    dest_folder_name: str,
    new_filename: str = None,
) -> None:
    """
    Copy a file from the given dictionary at the key `output_name` in the source
    bucket to the destination bucket with the new path (and optional filename).

    :param attempt_outputs_dict: The dictionary being searched
    :param output_name: The key to look for the file in the `attempt_outputs_dict`
    :param source_bucket: The source bucket
    :param dest_bucket: The destination bucket
    :param dest_folder_name: The folder to place the file in
    :param new_filename: An optional new filename to give the object
    """
    file_to_copy = attempt_outputs_dict.get(output_name)
    if file_to_copy is not None:
        # remove the gs://<bucket>/ prefix from the data
        trimmed_file_path = trim_gs_prefix(
            attempt_outputs_dict[output_name],
            source_bucket.name,
        )
        # if not supplied with a new filename, use the original base filename
        if new_filename is None:
            new_filename = Path(trimmed_file_path).name
        # create the new file path
        new_file_path = dest_folder_name + new_filename
        # get the original file
        original_file = source_bucket.get_blob(trimmed_file_path)
        # copy the original file if it exists, log an error if it doesn't
        if original_file is not None:
            source_bucket.copy_blob(original_file, dest_bucket, new_file_path)
            logger.info(
                "- Copied %s file to: %s",
                output_name,
                f"gs://{dest_bucket.name}/{new_file_path}",
            )
        else:
            logger.warning(
                "----> Unable to copy %s at %s to %s",
                output_name,
                attempt_outputs_dict[output_name],
                f"gs://{dest_bucket.name}/{new_file_path}",
            )
    else:
        logger.warning(
            "----> Unable to copy %s, key does not exist",
            output_name,
        )


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

    def __init__(
        self,
        wf_id: str,
        project: str,
        source_location: str,
        destination_location: str,
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
        """
        source_bucket, source_folder = parse_bucket_path(source_location)
        destination_bucket, destination_folder = parse_bucket_path(destination_location)

        self.wf_id = wf_id
        self.client = storage.Client(project=project)
        self.source_bucket = self.client.get_bucket(source_bucket)
        self.source_folder = source_folder.rstrip("/") + "/"
        self.destination_bucket = self.client.get_bucket(destination_bucket)
        self.destination_folder = destination_folder.rstrip("/") + "/"
        self.metadata = self.set_metadata()

        start_time = dateparser.parse(self.metadata["start"])
        end_time = dateparser.parse(self.metadata["end"])
        logger.info("Pipeline Running Time: %s \n", end_time - start_time)

        self.tasks: list[TaskSpec] = []

    def set_metadata(self) -> dict:
        """
        Find and set the metadata.json file in the source bucket/folder.

        :return: The loaded metadata.json object.
        """
        bucket_content_list = self.client.list_blobs(
            self.source_bucket,
            prefix=self.source_folder,
        )
        metadata = None
        # Get and load the metadata.json file
        for blob in bucket_content_list:
            m = re.match("(.*.metadata.json)", blob.name)
            if m:
                logger.info("\nMetadata file location: %sm[1]")
                metadata = json.loads(blob.download_as_string(client=None))
                break

        if metadata is None:
            logger.error(
                "Error: unable to find metadata.json file in %s specified",
                f"gs://{self.source_bucket.name}/{self.source_folder}",
            )
            sys.exit(1)

        return metadata

    def create_task(
        self,
        task_id: str,
        stdout_filename: Callable[[dict], str] | str | None,
        command_filename: Callable[[dict], str] | str,
        outputs: list[str],
        output_folder: str | None = None,
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
        """
        self.tasks.append(
            TaskSpec(
                task_id,
                stdout_filename,
                command_filename,
                outputs,
                self,
                output_folder,
            ),
        )

    def run_tasks(self) -> None:
        """Run all tasks for the copy job."""
        for task in self.tasks:
            task.run_copy()


class TaskSpec:
    """
    Holds all information for copying files for a given task.
    """

    def __init__(
        self,
        task_id: str,
        stdout_filename: Callable[[dict], str] | str,
        command_filename: Callable[[dict], str] | str,
        outputs: list[str],
        copy_spec: CopySpec,
        output_folder: str | None = None,
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
        """
        self.task_id = task_id
        self._stdout_filename = stdout_filename
        self._command_filename = command_filename
        self.outputs = outputs
        self.copy_spec = copy_spec
        self.output_folder = (
            output_folder or f"{copy_spec.destination_folder}/{task_id}_outputs"
        )
        self.calls = copy_spec.metadata["calls"][f"{copy_spec.wf_id}.{self.task_id}"]
        self.attempt = {}

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
        cmd_txt = call_attempt["commandLine"]
        if cmd_txt is not None:
            cmd_txt_name = f"{self.output_folder}/{file_name}"
            logger.info("- Command to file: %s", cmd_txt_name)
            new_blob_command = self.copy_spec.destination_bucket.blob(cmd_txt_name)
            new_blob_command.upload_from_string(cmd_txt, content_type="text/plain")
        else:
            logger.warning("----> Unable to copy commandLine")

    def run_copy(self) -> None:
        """
        Copy the outputs from the source to the destination.
        """
        logger.info(
            "\n %s, OUTPUTS---------------------------------\n",
            self.task_id.capitalize(),
        )
        for call_attempt in self.calls:
            self.attempt = call_attempt
            if "stdout" in call_attempt:
                self.copy_file_to_new_location(
                    call_attempt,
                    "stdout",
                    self.stdout_filename,
                )

            self.write_command_to_file(
                call_attempt=call_attempt,
                file_name=self.command_filename,
            )

            execution_status = call_attempt["executionStatus"]
            if execution_status == "Done":
                call_outputs = call_attempt["outputs"]
                for output in self.outputs:
                    self.copy_file_to_new_location(
                        call_outputs,
                        output,
                    )
            else:
                logger.warning(" (-) Execution Status: %s", execution_status)
                logger.warning(" (-) Data cannot be copied")

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
                logger.error(
                    "----> Unable to copy %s, key has unsupported type %s",
                    output_name,
                    type(file_to_copy),
                )
        else:
            logger.error("----> Unable to copy %s, key does not exist", output_name)

    def copy_single_file(
        self, original_filename: str, new_filename: str, output_name: str,
    ) -> None:
        """
        Copy a single file with the original filename to the new_filename.

        :param original_filename: The original file's filename
        :param new_filename: The new file's filename
        :param output_name: The name of the output in the outputs dict
        """
        # remove the gs://<bucket>/ prefix from the data
        trimmed_file_path = trim_gs_prefix(
            original_filename,
            self.copy_spec.source_bucket.name,
        )
        # if not supplied with a new filename, use the original base filename
        if new_filename is None:
            new_filename = Path(trimmed_file_path).name
        # create the new file path
        new_file_path = f"{self.output_folder}/{new_filename}"
        # get the original file
        original_file = self.copy_spec.source_bucket.get_blob(trimmed_file_path)
        # copy the original file if it exists, log an error if it doesn't
        if original_file is not None:
            self.copy_spec.source_bucket.copy_blob(
                original_file,
                self.copy_spec.destination_bucket.name,
                new_file_path,
            )
            logger.info(
                "- Copied %s file to: %s",
                output_name,
                f"gs://{self.copy_spec.destination_bucket.name}/{new_file_path}",
            )
        else:
            logger.error(
                "----> Unable to copy %s at %s to %s",
                output_name,
                original_filename,
                f"gs://{self.copy_spec.destination_bucket.name}/{new_file_path}",
            )


# Copy wrapper_pp results to the same or different bucket
def copy_ppinputs(
    metadata: dict,
    dest_root_folder: str,
    bucket_source: Bucket,
    bucket_destination: Bucket,
):
    # Check whether isPTM

    logger.info("+ Proteomics experiment results")
    wrapper_method = "proteomics_msgfplus.wrapper_pp"

    if wrapper_method not in metadata["calls"]:
        logger.error("(-) Plexed piper not available")
        return

    inputs = metadata["inputs"]

    for key, directory in [
        ("proteomics_msgfplus.fasta_sequence_db", ""),
        ("proteomics_msgfplus.sd_samples", "study_design/"),
        ("proteomics_msgfplus.sd_fractions", "study_design/"),
        ("proteomics_msgfplus.sd_references", "study_design/"),
    ]:
        copy_file_to_new_location(
            inputs,
            key,
            bucket_source,
            bucket_destination,
            dest_root_folder + directory,
        )

    wrapper_results_calls = metadata["calls"][wrapper_method]
    for call_attempt in wrapper_results_calls:
        execution_status = trim_gs_prefix(
            call_attempt["executionStatus"],
            bucket_source.name,
        )
        if execution_status == "Done":
            call_outputs = call_attempt["outputs"]
            for output in [
                "results_ratio",
                "results_rii",
                "final_output_masic_tar",
                "final_output_phrp_tar",
                "final_output_ascore",
            ]:
                copy_file_to_new_location(
                    call_outputs,
                    output,
                    bucket_source,
                    bucket_destination,
                    dest_root_folder,
                )
        else:
            logger.warning(" (-) Execution Status: %s", execution_status)
            logger.warning(" (-) Data cannot be copied")


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
        "-b",
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
        help="Proteomics Method. Currently supported: msgfplus or maxquant.",
    )
    parser.add_argument(
        "-o",
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
    return parser


def main():
    parser = create_args()
    args = parser.parse_args()

    project_name = args.project.rstrip("/")
    logger.info("\nGCP project: %s", project_name)

    origin = args.origin.rstrip("/")
    logger.info("Origin: %s", origin)
    destination = args.origin.rstrip("/")
    logger.info("Destination: %s", destination)

    method_proteomics = args.method_proteomics
    logger.info("+ Proteomics Pipeline METHOD: %s", method_proteomics)

    if method_proteomics == "maxquant":
        logger.info("PROTEOMICS METHOD: maxquant")
        logger.info("+ Copy MAXQUANT outputs-----------------------------\n")
        copy_job = CopySpec("proteomics_maxquant", project_name, origin, destination)
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
        copy_job = CopySpec("proteomics_msgfplus", project_name, origin, destination)
        if args.copy_what == "full":
            logger.info("PROTEOMICS METHOD: msgfplus")

            if "inputs" in copy_job.metadata:
                is_ptm = copy_job.metadata["inputs"]["proteomics_msgfplus.isPTM"]
                if is_ptm:
                    logger.info("\n####### PTM PROTEOMICS EXPERIMENT #######\n")
                else:
                    logger.info(
                        "\n####### GLOBAL PROTEIN ABUNDANCE EXPERIMENT #######\n",
                    )
                logger.info("Ready to copy ALL MSGF-plus outputs")

            if "proteomics_msgfplus.ascore" in copy_job.metadata["calls"]:
                copy_job.create_task(
                    "ascore",
                    lambda x: x["inputs"]["seq_file_id"] + "-ascore-stdout.log",
                    "ascore-command.log",
                    [
                        "syn_plus_ascore",
                        "syn_ascore",
                        "syn_ascore_proteinmap",
                        "output_ascore_logfile",
                    ],
                )

            copy_job.create_task(
                "msconvert_mzrefiner",
                lambda x: f"{x['inputs']['sample_id']}-msconvert_mzrefiner-stdout.log",
                "msconvert_mzrefiner-command.log",
                ["mzml_fixed"],
            )

            copy_job.create_task(
                "ppm_errorcharter",
                lambda x: f"{x['inputs']['sample_id']}-ppm_errorcharter-stdout.log",
                "ppm_errorcharter-command.log",
                ["ppm_masserror_png", "ppm_histogram_png"],
            )

            copy_job.create_task(
                "masic",
                lambda x: f"{Path(x['inputs']['raw_file']).name.replace('.raw', '')}-masic-stdout.log",
                "masic-command.log",
                [
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
                "msconvert",
                lambda x: f"{Path(x['inputs']['raw_file']).name.replace('.raw', '')}-msconvert-stdout.log",
                "msconvert-command.log",
                ["mzml"],
            )

            copy_job.create_task(
                "msgf_identification",
                lambda x: f"{x['inputs']['sample_id']}-msgf_identification-stdout.log",
                "msgf_identification-command.log",
                ["rename_mzmlfixed", "mzid_final"],
            )

            copy_job.create_task(
                "msgf_sequences",
                "msgf_sequences-stdout.log",
                "msgf_sequences-command.log",
                ["revcat_fasta, sequencedb_files"],
            )

            copy_job.create_task(
                "msgf_tryptic",
                lambda x: f"{x['inputs']['sample_id']}-msgf_tryptic-stdout.log",
                "msgf_tryptic-command.log",
                ["mzid"],
            )

            copy_job.create_task(
                "phrp",
                lambda x: f"{Path(x['inputs']['input_tsv']).name.replace('.tsv', '')}-phrp-stdout.log",
                "phrp-command.log",
                [
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
                "mzidtotsvconverter",
                lambda x: f"{x['inputs']['sample_id']}-mzidtotsvconverter-stdout.log",
                "mzidtotsvconverter-command.log",
                ["tsv"],
            )

            if "proteomics_msgfplus.wrapper_pp" in copy_job.metadata["calls"]:
                copy_job.create_task(
                    "wrapper_pp",
                    None,
                    "wrapper_results-command.log",
                    ["tsv"],
                )
            else:
                logger.error("(-) Plexed piper not available")
                return

        elif args.copy_what == "ppinputs":
            if "inputs" in copy_job.metadata:
                is_ptm = copy_job.metadata["inputs"]["proteomics_msgfplus.isPTM"]
                if is_ptm:
                    logger.info("\n######## PTM PROTEOMICS EXPERIMENT ########\n")
                else:
                    logger.info(
                        "\n####### GLOBAL PROTEIN ABUNDANCE EXPERIMENT #######\n",
                    )
                logger.info("Ready to copy ONLY PlexedPiper (RII + Ratio) results")
                logger.info(
                    "\nWRAPPER: PlexedPiper output----------------------------\n",
                )

                copy_ppinputs(
                    copy_job.metadata,
                    copy_job.destination_folder,
                    copy_job.source_bucket,
                    copy_job.destination_bucket,
                )
        elif args.copy_what == "results":
            if "inputs" in copy_job.metadata:
                is_ptm = copy_job.metadata["inputs"]["proteomics_msgfplus.isPTM"]
                if is_ptm:
                    logger.info("\n####### PTM PROTEOMICS EXPERIMENT #######\n")
                else:
                    logger.info(
                        "\n####### GLOBAL PROTEIN ABUNDANCE EXPERIMENT #######\n",
                    )

                logger.info("Ready to copy ONLY PlexedPiper (RII + Ratio) results")
                if "proteomics_msgfplus.wrapper_pp" in copy_job.metadata["calls"]:
                    copy_job.create_task(
                        "wrapper_pp",
                        None,
                        "wrapper_results-command.log",
                        ["tsv"],
                    )
                else:
                    logger.error("(-) Plexed piper not available")
                    return
        else:
            err_msg = "You should not have gotten here"
            raise ValueError(err_msg)

        copy_job.run_tasks()


if __name__ == "__main__":
    main()
