import argparse
import json
import os
import re  # regular expressions
import sys
import warnings

import dateparser
from google.cloud import storage
from google.cloud.storage import Bucket


warnings.filterwarnings(
    "ignore", "Your application has authenticated using end user credentials"
)


def trim_gs_prefix(full_file_path, bucket_name):
    """
    Replace the gs://bucket/ portion from the file path
    """
    gs_bucket_name = f"gs://{bucket_name}/"
    new_str = full_file_path.replace(gs_bucket_name, "")
    return new_str


def upload_string(bucket_destination, str_content, destination_blob_name):
    b = bucket_destination.blob(destination_blob_name)
    b.upload_from_string(str_content)


def copy_file_to_new_location(
    attempt_outputs_dict: dict,
    output_name: str,
    source_bucket: Bucket,
    dest_bucket: Bucket,
    dest_folder_name: str,
    new_filename: str = None,
):
    """
    Copies a file from the given dictionary at the key `output_name` in the source
    bucket to the destination bucket with the new path (and optional filename)

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
            new_filename = os.path.basename(trimmed_file_path)
        # create the new file path
        new_file_path = dest_folder_name + new_filename
        # get the original file
        original_file = source_bucket.get_blob(trimmed_file_path)
        # copy the original file if it exists, log an error if it doesn't
        if original_file is not None:
            source_bucket.copy_blob(original_file, dest_bucket, new_file_path)
            print(
                f"- Copied {output_name} file to: "
                f"gs://{dest_bucket.name}/{new_file_path}"
            )
        else:
            print(
                f"----> Unable to copy {output_name} at "
                f"{attempt_outputs_dict[output_name]} "
                f"to gs://{dest_bucket.name}/{new_file_path}",
                file=sys.stderr,
            )
    else:
        print(
            f"----> Unable to copy {output_name}, key does not exist",
            file=sys.stderr,
        )


def write_command_to_file(
    metadata, x, method, results_output, bucket_destination, file_name
):
    """
    The command executed on each call is available as text in the
    metadata.json file. This function extracts the command and saves it
    in the bucket as a file.

    :param x: index
    :param metadata: the metadata object
    :param method: the call method name
    :param results_output: the prefix name for the file
    :param bucket_destination: bucket destination name
    :param file_name: the file name
    """

    if "commandLine" in metadata["calls"][method][x]:
        cmd_txt = metadata["calls"][method][x]["commandLine"]
        if cmd_txt is not None:
            cmd_txt_name = results_output + file_name
            print("- Command to file:", cmd_txt_name)
            new_blob_command = bucket_destination.blob(cmd_txt_name)
            new_blob_command.upload_from_string(cmd_txt, content_type="text/plain")
    else:
        print("----> Unable to copy commandLine")


# Copy ascore results to the same or different bucket
def copy_ascore(metadata, dest_root_folder, bucket_source, bucket_destination):
    ascore_output = dest_root_folder + "ascore_outputs/"
    ascore_calls = metadata["calls"]["proteomics_msgfplus.ascore"]

    for x, call_attempt in enumerate(ascore_calls):
        # # STDOUT, which requires to rename the file
        if "stdout" in call_attempt:
            seq_id = call_attempt["inputs"]["seq_file_id"]
            copy_file_to_new_location(
                call_attempt,
                "stdout",
                bucket_source,
                bucket_destination,
                ascore_output,
                seq_id + "-ascore-stdout.log",
            )

        write_command_to_file(
            metadata=metadata,
            x=x,
            method="proteomics_msgfplus.ascore",
            results_output=ascore_output,
            bucket_destination=bucket_destination,
            file_name="ascore-command.log",
        )

        executionStatus = trim_gs_prefix(
            call_attempt["executionStatus"],
            bucket_source.name,
        )
        if executionStatus == "Done":
            attempt_outputs = call_attempt["outputs"]
            for output in [
                "syn_plus_ascore",
                "syn_ascore",
                "syn_ascore_proteinmap",
                "output_ascore_logfile",
            ]:
                copy_file_to_new_location(
                    attempt_outputs,
                    output,
                    bucket_source,
                    bucket_destination,
                    ascore_output,
                )

        else:
            print(" (-) Execution Status: ", executionStatus)
            print(" (-) Data cannot be copied")


# Copy msconvert_mzrefiner results to the same or different bucket
def copy_msconvert_mzrefiner(
    metadata, dest_root_folder, bucket_source, bucket_destination
):
    msconvert_mzrefiner_output = dest_root_folder + "msconvert_mzrefiner_outputs/"
    msconvert_mzrefiner_calls = metadata["calls"][
        "proteomics_msgfplus.msconvert_mzrefiner"
    ]

    for x, call_attempt in enumerate(msconvert_mzrefiner_calls):
        if "stdout" in call_attempt:
            # STDOUT, which requires to rename the file
            seq_id = call_attempt["inputs"]["sample_id"]
            copy_file_to_new_location(
                call_attempt,
                "stdout",
                bucket_source,
                bucket_destination,
                msconvert_mzrefiner_output,
                seq_id + "-msconvert_mzrefiner-stdout.log",
            )

        write_command_to_file(
            metadata=metadata,
            x=x,
            method="proteomics_msgfplus.msconvert_mzrefiner",
            results_output=msconvert_mzrefiner_output,
            bucket_destination=bucket_destination,
            file_name="msconvert_mzrefiner-command.log",
        )

        executionStatus = trim_gs_prefix(
            call_attempt["executionStatus"],
            bucket_source.name,
        )
        if executionStatus == "Done":
            attempt_outputs = call_attempt["outputs"]
            copy_file_to_new_location(
                attempt_outputs,
                "mzml_fixed",
                bucket_source,
                bucket_destination,
                msconvert_mzrefiner_output,
            )
        else:
            print(" (-) Execution Status: ", executionStatus)
            print(" (-) Data cannot be copied")


def copy_ppm_errorcharter(metadata, dest_root_folder, bucket_source, bucket_destination):
    ppm_errorcharter_output = dest_root_folder + "output_ppm_errorcharter/"
    ppm_errorcharter_calls = metadata["calls"]["proteomics_msgfplus.ppm_errorcharter"]

    for x, call_attempt in enumerate(ppm_errorcharter_calls):
        if "stdout" in call_attempt:
            seq_id = call_attempt["inputs"]["sample_id"]
            copy_file_to_new_location(
                call_attempt,
                "stdout",
                bucket_source,
                bucket_destination,
                ppm_errorcharter_output,
                seq_id + "-ppm_errorcharter-stdout.log",
            )

        write_command_to_file(
            metadata=metadata,
            x=x,
            method="proteomics_msgfplus.ppm_errorcharter",
            results_output=ppm_errorcharter_output,
            bucket_destination=bucket_destination,
            file_name="ppm_errorcharter-command.log",
        )

        executionStatus = trim_gs_prefix(
            call_attempt["executionStatus"],
            bucket_source.name,
        )
        if executionStatus == "Done":
            attempt_outputs = call_attempt["outputs"]
            for output in ["ppm_masserror_png", "ppm_histogram_png"]:
                copy_file_to_new_location(
                    attempt_outputs,
                    output,
                    bucket_source,
                    bucket_destination,
                    ppm_errorcharter_output,
                )
        else:
            print(" (-) Execution Status: ", executionStatus)
            print(" (-) Data cannot be copied")


# WARNING: ID IS COMING FROM THE RAW FILE NAME:
def copy_masic(metadata, dest_root_folder, bucket_source, bucket_destination):
    masic_output = dest_root_folder + "masic_outputs/"
    masic_calls = metadata["calls"]["proteomics_msgfplus.masic"]

    for x, call_attempt in enumerate(masic_calls):
        # print('\nBlob-', x, ' ', end = '')
        if "stdout" in call_attempt:
            # WARNING: ID IS COMING FROM THE RAW FILE NAME:
            seq_id = os.path.basename(call_attempt["inputs"]["raw_file"]).replace(
                ".raw", ""
            )
            copy_file_to_new_location(
                call_attempt,
                "stdout",
                bucket_source,
                bucket_destination,
                masic_output,
                seq_id + "-masic-stdout.log",
            )

        write_command_to_file(
            metadata=metadata,
            x=x,
            method="proteomics_msgfplus.masic",
            results_output=masic_output,
            bucket_destination=bucket_destination,
            file_name="masic-command.log",
        )

        executionStatus = trim_gs_prefix(
            call_attempt["executionStatus"],
            bucket_source.name,
        )
        if executionStatus == "Done":
            attempt_outputs = call_attempt["outputs"]
            for output in [
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
            ]:
                copy_file_to_new_location(
                    attempt_outputs,
                    output,
                    bucket_source,
                    bucket_destination,
                    masic_output,
                )

        else:
            print(" (-) Execution Status: ", executionStatus)
            print(" (-) Data cannot be copied")


# Copy msconvert results to the same or different bucket
def copy_msconvert(metadata, dest_root_folder, bucket_source, bucket_destination):
    msconvert_output = dest_root_folder + "msconvert_outputs/"
    msconvert_calls = metadata["calls"]["proteomics_msgfplus.msconvert"]

    for x, call_attempt in range(msconvert_calls):
        if "stdout" in call_attempt:
            seq_id = os.path.basename(call_attempt["inputs"]["raw_file"]).replace(
                ".raw", ""
            )
            copy_file_to_new_location(
                call_attempt,
                "stdout",
                bucket_source,
                bucket_destination,
                msconvert_output,
                seq_id + "-msconvert-stdout.log",
            )

        write_command_to_file(
            metadata=metadata,
            x=x,
            method="proteomics_msgfplus.msconvert",
            results_output=msconvert_output,
            bucket_destination=bucket_destination,
            file_name="msconvert-command.log",
        )

        executionStatus = trim_gs_prefix(
            call_attempt["executionStatus"],
            bucket_source.name,
        )
        if executionStatus == "Done":
            call_outputs = call_attempt["outputs"]
            copy_file_to_new_location(
                call_outputs,
                "mzml",
                bucket_source,
                bucket_destination,
                msconvert_output,
            )
        else:
            print(" (-) Execution Status: ", executionStatus)
            print(" (-) Data cannot be copied")


def copy_msgf_identification(
    metadata, dest_root_folder, bucket_source, bucket_destination
):
    msgf_identification_output = dest_root_folder + "msgf_identification_outputs/"
    msgf_identification_calls = metadata["calls"][
        "proteomics_msgfplus.msgf_identification"
    ]

    for x, call_attempt in enumerate(msgf_identification_calls):
        if "stdout" in call_attempt:
            seq_id = call_attempt["inputs"]["sample_id"]
            copy_file_to_new_location(
                call_attempt,
                "stdout",
                bucket_source,
                bucket_destination,
                msgf_identification_output,
                seq_id + "-msgf_identification-stdout.log",
            )

        write_command_to_file(
            metadata=metadata,
            x=x,
            method="proteomics_msgfplus.msgf_identification",
            results_output=msgf_identification_output,
            bucket_destination=bucket_destination,
            file_name="msgf_identification-command.log",
        )

        executionStatus = trim_gs_prefix(
            call_attempt["executionStatus"],
            bucket_source.name,
        )
        if executionStatus == "Done":
            attempt_outputs = call_attempt["outputs"]
            for output in ["rename_mzmlfixed", "mzid_final"]:
                copy_file_to_new_location(
                    attempt_outputs,
                    output,
                    bucket_source,
                    bucket_destination,
                    msgf_identification_output,
                )
        else:
            print(" (-) Execution Status: ", executionStatus)
            print(" (-) Data cannot be copied")


# Copy msgf_sequences results to the same or different bucket
def copy_msgf_sequences(metadata, dest_root_folder, bucket_source, bucket_destination):
    msgf_sequences_output = dest_root_folder + "msgf_sequences_outputs/"
    msgf_sequences_calls = metadata["calls"]["proteomics_msgfplus.msgf_sequences"]

    for x, call_attempt in enumerate(msgf_sequences_calls):
        # # Get and upload the command
        if "commandLine" in call_attempt:
            msgf_sequences_cmd = call_attempt["commandLine"]
            cmd_local_file_name = "command-msgf_sequences.txt"
            cmd_blob_filename = msgf_sequences_output + cmd_local_file_name
            print("- Command: ", cmd_blob_filename)
            upload_string(bucket_destination, msgf_sequences_cmd, cmd_blob_filename)

        write_command_to_file(
            metadata=metadata,
            x=x,
            method="proteomics_msgfplus.msgf_sequences",
            results_output=msgf_sequences_output,
            bucket_destination=bucket_destination,
            file_name="msgf_sequences-command.log",
        )

        executionStatus = trim_gs_prefix(
            call_attempt["executionStatus"],
            bucket_source.name,
        )
        if executionStatus == "Done":
            attempt_outputs = call_attempt["outputs"]
            for output in ["revcat_fasta, sequencedb_files"]:
                copy_file_to_new_location(
                    attempt_outputs,
                    output,
                    bucket_source,
                    bucket_destination,
                    msgf_sequences_output,
                )
        else:
            print(" (-) Execution Status: ", executionStatus)
            print(" (-) Data cannot be copied")


# Copy msgf_tryptic results to the same or different bucket
def copy_msgf_tryptic(metadata, dest_root_folder, bucket_source, bucket_destination):
    msgf_tryptic_output = dest_root_folder + "msgf_tryptic_outputs/"
    msgf_tryptic_calls = metadata["calls"]["proteomics_msgfplus.msgf_tryptic"]

    for x, call_attempt in enumerate(msgf_tryptic_calls):
        # STDOUT, which requires to rename the file
        if "stdout" in call_attempt:
            seq_id = call_attempt["inputs"]["sample_id"]
            copy_file_to_new_location(
                call_attempt,
                "stdout",
                bucket_source,
                bucket_destination,
                msgf_tryptic_output,
                seq_id + "-msgf_tryptic-stdout.log",
            )

        write_command_to_file(
            metadata=metadata,
            x=x,
            method="proteomics_msgfplus.msgf_tryptic",
            results_output=msgf_tryptic_output,
            bucket_destination=bucket_destination,
            file_name="msgf_tryptic-command.log",
        )

        executionStatus = trim_gs_prefix(
            call_attempt["executionStatus"],
            bucket_source.name,
        )
        if executionStatus == "Done":
            call_outputs = call_attempt["outputs"]
            copy_file_to_new_location(
                call_outputs,
                "mzid",
                bucket_source,
                bucket_destination,
                msgf_tryptic_output,
            )
        else:
            print(" (-) Execution Status: ", executionStatus)
            print(" (-) Data cannot be copied")


########################################################################
# WARNING TO DO: THERE MIGHT BE AN EXTRA OUTPUT TO BE ADDED: phrp_log_file
########################################################################
def copy_phrp(metadata, dest_root_folder, bucket_source, bucket_destination):
    phrp_output = dest_root_folder + "phrp_outputs/"
    phrp_calls = metadata["calls"]["proteomics_msgfplus.phrp"]
    # print('- Number of files processed:', phrp_length)

    for x, call_attempt in enumerate(phrp_calls):
        # print('\nBlob-', x, ' ', end = '')
        if "stdout" in call_attempt:
            # WARNING: ID IS COMING FROM THE RAW FILE NAME:
            seq_id = os.path.basename(call_attempt["inputs"]["input_tsv"])
            seq_id = seq_id.replace(".tsv", "")
            copy_file_to_new_location(
                call_attempt,
                "stdout",
                bucket_source,
                bucket_destination,
                phrp_output,
                seq_id + "-phrp-stdout.log",
            )

        write_command_to_file(
            metadata=metadata,
            x=x,
            method="proteomics_msgfplus.phrp",
            results_output=phrp_output,
            bucket_destination=bucket_destination,
            file_name="phrp-command.log",
        )

        executionStatus = trim_gs_prefix(
            call_attempt["executionStatus"],
            bucket_source.name,
        )
        if executionStatus == "Done":
            attempt_outputs = call_attempt["outputs"]
            for output in [
                "syn_ResultToSeqMap",
                "fht",
                "PepToProtMapMTS",
                "syn_ProteinMods",
                "syn_SeqToProteinMap",
                "syn",
                "syn_ModSummary",
                "syn_SeqInfo",
                "syn_ModDetails",
            ]:
                copy_file_to_new_location(
                    attempt_outputs,
                    output,
                    bucket_source,
                    bucket_destination,
                    phrp_output,
                )
        else:
            print(" (-) Execution Status: ", executionStatus)
            print(" (-) Data cannot be copied")


# Copy mzidtotsvconverter results to the same or different bucket
def copy_mzidtotsvconverter(
    metadata, dest_root_folder, bucket_source, bucket_destination
):
    mzidtotsvconverter_output = dest_root_folder + "mzidtotsvconverter_outputs/"
    mzidtotsvconverter_calls = metadata["calls"]["proteomics_msgfplus.mzidtotsvconverter"]

    for x, call_attempt in enumerate(mzidtotsvconverter_calls):
        if "stdout" in call_attempt:
            seq_id = call_attempt["inputs"]["sample_id"]
            copy_file_to_new_location(
                call_attempt,
                "stdout",
                bucket_source,
                bucket_destination,
                mzidtotsvconverter_output,
                seq_id + "-mzidtotsvconverter-stdout.log",
            )

        write_command_to_file(
            metadata=metadata,
            x=x,
            method="proteomics_msgfplus.mzidtotsvconverter",
            results_output=mzidtotsvconverter_output,
            bucket_destination=bucket_destination,
            file_name="mzidtotsvconverter-command.log",
        )

        executionStatus = trim_gs_prefix(
            call_attempt["executionStatus"],
            bucket_source.name,
        )
        if executionStatus == "Done":
            call_outputs = call_attempt["outputs"]
            copy_file_to_new_location(
                call_outputs,
                "tsv",
                bucket_source,
                bucket_destination,
                mzidtotsvconverter_output,
            )
        else:
            print(" (-) Execution Status: ", executionStatus)
            print(" (-) Data cannot be copied")


# Copy wrapper_pp results to the same or different bucket
def copy_wrapper_pp(
    metadata,
    dest_root_folder,
    bucket_source: Bucket,
    bucket_destination: Bucket,
):
    wrapper_results_output = dest_root_folder + "wrapper_results/"

    # Check whether isPTM

    print("+ Proteomics experiment results")
    wrapper_method = "proteomics_msgfplus.wrapper_pp"

    if wrapper_method not in metadata["calls"]:
        print("(-) Plexed piper not available")
        return None

    wrapper_results_calls = metadata["calls"][wrapper_method]

    for x, call_attempt in enumerate(wrapper_results_calls):
        if "stdout" in call_attempt:
            copy_file_to_new_location(
                call_attempt,
                "stdout",
                bucket_source,
                bucket_destination,
                wrapper_results_output,
            )

        write_command_to_file(
            metadata=metadata,
            x=x,
            method=wrapper_method,
            results_output=wrapper_results_output,
            bucket_destination=bucket_destination,
            file_name="wrapper_results-command.log",
        )

        executionStatus = trim_gs_prefix(
            call_attempt["executionStatus"], bucket_source.name
        )
        if executionStatus == "Done":
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
                    wrapper_results_output,
                )
        else:
            print(" (-) Execution Status: ", executionStatus)
            print(" (-) Data cannot be copied")


# Copy wrapper_pp results to the same or different bucket
def copy_ppinputs(
    metadata,
    dest_root_folder,
    bucket_source: Bucket,
    bucket_destination: Bucket,
):
    # Check whether isPTM

    print("+ Proteomics experiment results")
    wrapper_method = "proteomics_msgfplus.wrapper_pp"

    if wrapper_method not in metadata["calls"]:
        print("(-) Plexed piper not available", file=sys.stderr)
        return None

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
    for x, call_attempt in enumerate(wrapper_results_calls):
        executionStatus = trim_gs_prefix(
            call_attempt["executionStatus"], bucket_source.name
        )
        if executionStatus == "Done":
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
            print(" (-) Execution Status: ", executionStatus)
            print(" (-) Data cannot be copied")


# MAXQUANT METHODS----------------------------------------------------
# Copy maxquant results to the same or different bucket
def copy_maxquant(
    metadata: dict,
    dest_root_folder: str,
    bucket_source: Bucket,
    bucket_destination: Bucket,
):
    maxquant_output = dest_root_folder + "maxquant_outputs/"
    maxquant_calls = metadata["calls"]["proteomics_maxquant.maxquant"]

    for x, call_attempt in enumerate(maxquant_calls):
        if "stdout" in call_attempt:
            seq_id = "console"
            copy_file_to_new_location(
                call_attempt,
                "stdout",
                bucket_source,
                bucket_destination,
                maxquant_output,
                seq_id + "-maxquant-stdout.log",
            )

        write_command_to_file(
            metadata=metadata,
            x=x,
            method="proteomics_maxquant.maxquant",
            results_output=maxquant_output,
            bucket_destination=bucket_destination,
            file_name="maxquant-command.log",
        )

        executionStatus = trim_gs_prefix(
            call_attempt["executionStatus"],
            bucket_source.name,
        )
        if executionStatus == "Done":
            attempt_outputs = call_attempt["outputs"]
            for output in [
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
            ]:
                copy_file_to_new_location(
                    attempt_outputs,
                    output,
                    bucket_source,
                    bucket_destination,
                    maxquant_output,
                )

            if "sites" in attempt_outputs:
                for files in attempt_outputs["sites"]:
                    s_file = trim_gs_prefix(files, bucket_source.name)
                    blob_f_sites = bucket_source.get_blob(s_file)
                    new_f_sites = maxquant_output + os.path.basename(s_file)
                    print("- File to:", new_f_sites)
                    bucket_source.copy_blob(blob_f_sites, bucket_destination, new_f_sites)

        else:
            print(" (-) Execution Status: ", executionStatus)
            print(" (-) Data cannot be copied")


def arg_parser():
    parser = argparse.ArgumentParser(
        description="Copy proteomics pipeline output files to a desire location"
    )
    parser.add_argument(
        "-p", "--project", required=True, type=str, help="GCP project name. Required."
    )
    parser.add_argument(
        "-b",
        "--bucket_origin",
        required=True,
        type=str,
        help="Bucket with output files. Required.",
    )
    parser.add_argument(
        "-d",
        "--bucket_destination_name",
        required=False,
        type=str,
        help="Bucket to copy file. Not Required. Default: same as bucket_origin).",
    )
    parser.add_argument(
        "-m",
        "--method_proteomics",
        required=True,
        type=str,
        help="Proteomics Method. Currently supported: msgfplus or maxquant.",
    )
    parser.add_argument(
        "-r",
        "--results_location_path",
        required=True,
        type=str,
        help="Path to the pipeline results. Required "
        "(e.g. results/proteomics_msgfplus/9c6ff6fe-ce7d-4d23-ac18-9935614d6f9b)",
    )
    parser.add_argument(
        "-o",
        "--dest_root_folder",
        required=True,
        type=str,
        help="Folder path to copy the files. Required "
        "(e.g. test/results/input_test_gcp_s6-global-2files-8/)",
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
    parser = arg_parser()
    args = parser.parse_args()

    project_name = args.project.rstrip("/")
    print("\nGCP project:", project_name)

    bucket_origin = args.bucket_origin.rstrip("/")
    print("Bucket origin:", bucket_origin)

    bucket_destination_name = args.bucket_destination_name
    if args.bucket_destination_name is None:
        print(
            "Bucket destination: --bucket_destination_name (-d) is empty. Same as "
            f"original will be used ({bucket_origin})",
            file=sys.stderr,
        )
        if input("Proceed? (y/n) ") != "y":
            sys.exit(1)
        bucket_destination_name = bucket_origin
    else:
        print("Bucket destination: ", bucket_destination_name)

    print("\nOPTIONS:")

    method_proteomics = args.method_proteomics
    print("+ Proteomics Pipeline METHOD: ", method_proteomics)

    results_location_path = args.results_location_path.rstrip("/")
    print("+ Copy files from:", results_location_path)

    dest_root_folder = args.dest_root_folder
    if not dest_root_folder.endswith("/"):
        dest_root_folder += "/"

    print("+ Copy files to: ", dest_root_folder)

    storage_client = storage.Client(project_name)
    bucket_source = storage_client.get_bucket(bucket_origin)
    bucket_destination = storage_client.get_bucket(bucket_destination_name)

    bucket_content_list = storage_client.list_blobs(
        bucket_source, prefix=results_location_path
    )
    metadata = None
    # Get and load the metadata.json file
    for blob in bucket_content_list:
        # print(type(here))
        # print(here)
        m = re.match("(.*.metadata.json)", blob.name)
        if m:
            print("\nMetadata file location: ", m[1])
            metadata = json.loads(blob.download_as_string(client=None))
            break

    if metadata is None:
        print(
            "Error: unable to find metadata.json file in path specified",
            file=sys.stderr,
        )
        sys.exit(1)

    start_time = dateparser.parse(metadata["start"])
    end_time = dateparser.parse(metadata["end"])

    print("Pipeline Running Time: ", end_time - start_time, "\n")

    if method_proteomics == "maxquant":
        print("PROTEOMICS METHOD: maxquant")
        print("+ Copy MAXQUANT outputs-----------------------------\n")
        copy_maxquant(metadata, dest_root_folder, bucket_source, bucket_destination)
    else:
        if args.copy_what == "full":
            print("PROTEOMICS METHOD: msgfplus")

            if "inputs" in metadata:
                is_ptm = metadata["inputs"]["proteomics_msgfplus.isPTM"]
                if is_ptm:
                    print("\n######## PTM PROTEOMICS EXPERIMENT ########\n")
                else:
                    print("\n######## GLOBAL PROTEIN ABUNDANCE EXPERIMENT ########\n")
                print("Ready to copy ALL MSGFplus outputs")

            if "proteomics_msgfplus.ascore" in metadata["calls"]:
                print("\nASCORE OUTPUTS--------------------------------------\n")
                copy_ascore(
                    metadata,
                    dest_root_folder,
                    bucket_source,
                    bucket_destination,
                )

            print("\nMSCONVERT_MZREFINER OUTPUTS-----------------------------\n")
            copy_msconvert_mzrefiner(
                metadata,
                dest_root_folder,
                bucket_source,
                bucket_destination,
            )

            print("\nPPMErrorCharter (ppm_errorcharter)------------------------\n")
            copy_ppm_errorcharter(
                metadata,
                dest_root_folder,
                bucket_source,
                bucket_destination,
            )

            print("\nMASIC OUTPUTS-------------------------------------------\n")
            copy_masic(
                metadata,
                dest_root_folder,
                bucket_source,
                bucket_destination,
            )

            print("\nMSCONVERT OUTPUTS---------------------------------------\n")
            copy_msconvert(
                metadata,
                dest_root_folder,
                bucket_source,
                bucket_destination,
            )

            print("\nMSGF_IDENTIFICATION OUTPUTS-----------------------------\n")
            copy_msgf_identification(
                metadata,
                dest_root_folder,
                bucket_source,
                bucket_destination,
            )

            print("\nMSGF_SEQUENCES OUTPUTS----------------------------------\n")
            copy_msgf_sequences(
                metadata,
                dest_root_folder,
                bucket_source,
                bucket_destination,
            )

            print("\nMSGF_TRYPTIC OUTPUTS------------------------------------\n")
            copy_msgf_tryptic(
                metadata,
                dest_root_folder,
                bucket_source,
                bucket_destination,
            )

            print("\nPHRP OUTPUTS--------------------------------------------\n")
            copy_phrp(
                metadata,
                dest_root_folder,
                bucket_source,
                bucket_destination,
            )

            print("\nMZID to TSV CONVERTER OUTPUTS---------------------------\n")
            copy_mzidtotsvconverter(
                metadata,
                dest_root_folder,
                bucket_source,
                bucket_destination,
            )

            print("\nWRAPPER: PlexedPiper output-------------------------------\n")
            copy_wrapper_pp(metadata, dest_root_folder, bucket_source, bucket_destination)
        elif args.copy_what == "ppinputs":
            if "inputs" in metadata:
                is_ptm = metadata["inputs"]["proteomics_msgfplus.isPTM"]
                if is_ptm:
                    print("\n######## PTM PROTEOMICS EXPERIMENT ########\n")
                else:
                    print("\n######## GLOBAL PROTEIN ABUNDANCE EXPERIMENT ########\n")
                print("Ready to copy ONLY PlexedPiper (RII + Ratio) results")
            print("\nWRAPPER: PlexedPiper output-------------------------------\n")

            copy_ppinputs(metadata, dest_root_folder, bucket_source, bucket_destination)
        else:
            if "inputs" in metadata:
                is_ptm = metadata["inputs"]["proteomics_msgfplus.isPTM"]
                if is_ptm:
                    print("\n######## PTM PROTEOMICS EXPERIMENT ########\n")
                else:
                    print("\n######## GLOBAL PROTEIN ABUNDANCE EXPERIMENT ########\n")
                print("Ready to copy ONLY PlexedPiper (RII + Ratio) results")
            print("\nWRAPPER: PlexedPiper output-------------------------------\n")
            copy_wrapper_pp(metadata, dest_root_folder, bucket_source, bucket_destination)

    print("\n")


if __name__ == "__main__":
    main()
