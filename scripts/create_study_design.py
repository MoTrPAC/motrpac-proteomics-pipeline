#!/usr/bin/env python3

import argparse
import glob
import logging
import os
import re
from datetime import datetime

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(message)s")


def validate_batch(input_results_folder: str) -> str:
    """Extract BATCH_YYYYMMDD folder from input folder path.

    :param input_results_folder: input_results_folder path
    :returns: BATCH_YYYYMMDD folder name
    :raises: ValueError: If batch folder is not recognized
    """
    # Try different patterns to be more flexible
    # First try the original pattern
    batch_match = re.search(r".*/?(BATCH\d{1,2}_\d{8})", input_results_folder)

    if not batch_match:
        # Try alternative pattern without requiring a path before BATCH
        batch_match = re.search(r"(BATCH\d{1,2}_\d{8})", input_results_folder)

    if not batch_match:
        msg = "`BATCH#_YYYYMMDD` folder is not recognized in the folder structure."
        raise ValueError(msg)

    return batch_match.group(1)


def validate_phase(
    input_results_folder: str, *, return_phase: bool = True
) -> str | None:
    """Extract PHASE from input folder path.

    :param input_results_folder: input_results_folder path
    :param return_phase: return the phase only if True (default)
    :returns: PHASE code
    :raises: ValueError: If phase is not found in the folder structure
    """
    phase = re.search(
        r"(PASS1A-06|PASS1A-18|PASS1B-06|PASS1B-18|PASS1C-06|PASS1C-18|PASS1AC-06|HUMAN|HUMAN-PRECOVID|HUMAN-MAIN-TR(?:0[1-9]|1[0-5]))",
        input_results_folder,
    )

    if not phase:
        msg = (
            "- (-) Project phase is not found in the folder structure. "
            "Please check the MoTrPAC control vocabulary guidelines"
        )
        raise ValueError(msg)

    if return_phase:
        return phase.group(1)

    return None


def validate_assay(input_results_folder: str) -> str:
    """Extract ASSAY from input folder path.

    :param input_results_folder: input_results_folder path
    :returns: ASSAY code
    :raises: ValueError: If assay is not found
    """
    assay = re.search(
        r"(?<=T\d{2}/)(IONPNEG|RPNEG|RPPOS|HILICPOS|LRPPOS|LRPNEG|3HIB|AA|AC_DUKE|ACOA|BAIBA|CER_DUKE|KA|NUC|OA|SPHM|OXYLIPNEG|ETAMIDPOS|AC_MAYO|AMINES|CER_MAYO|TCA|LAB_GLC|LAB_INS|PROT_PH|PROT_PR|PROT_AC|PROT_UB|PROT_OL|PROT_OX|LAB_CK|LAB_CRT|LAB_CONV)",
        input_results_folder,
    )

    if not assay:
        msg = "ASSAY not found in the folder structure"
        raise ValueError(msg)

    return assay.group(0)


def validate_tissue(input_results_folder: str) -> str:
    """Extract and validate TISSUE CODE from input folder path.

    :param input_results_folder: input_results_folder path
    :returns: Tissue code
    :raises: ValueError: If tissue code is not valid
    """
    # Define the list of valid tissue codes as in bic_animal_tissue_code$bic_tissue_code
    bic_tissue_codes = [
        "T01",
        "T02",
        "T03",
        "T04",
        "T05",
        "T06",
        "T07",
        "T08",
        "T09",
        "T10",
        "T11",
        "T12",
        "T13",
        "T14",
        "T15",
        "T16",
        "T17",
        "T18",
        "T19",
        "T20",
        "T21",
        "T30",
        "T31",
        "T32",
        "T33",
        "T34",
        "T35",
        "T36",
        "T37",
        "T38",
        "T39",
        "T40",
        "T41",
        "T42",
        "T43",
        "T44",
        "T45",
        "T46",
        "T47",
        "T48",
        "T49",
        "T50",
        "T51",
        "T52",
        "T53",
        "T54",
        "T55",
        "T56",
        "T57",
        "T58",
        "T59",
        "T60",
        "T61",
        "T62",
        "T63",
        "T64",
        "T65",
        "T66",
        "T67",
        "T68",
        "T69",
        "T70",
        "T77",
        "T99",
    ]

    # Extract tissue code using regex similar to gsub in R
    match = re.search(r"(.*)(T[0-9]{2,3})(.*)", input_results_folder)
    if not match:
        msg = "Tissue code not found in the folder structure"
        raise ValueError(msg)

    tissue_code = match.group(2)

    if tissue_code not in bic_tissue_codes:
        msg = (
            f"tissue_code: `{tissue_code}` is not valid. Must be one of the following codes "
            f"(check data object `MotrpacBicQC::bic_animal_tissue_code`):\n- "
            f"{', '.join(bic_tissue_codes)}",
        )
        raise ValueError(msg)

    return tissue_code


def find_unique_tmt_channel(tempcol: list[str] | np.ndarray | pd.Series) -> str:
    """Find unique TMT channel name in a list based on a specified pattern.

    :param tempcol: A list of potential TMT channel names.
    :returns: The matching TMT channel name if exactly one match is found.
        Raises error if no matches or multiple matches are found.
    """
    # Check that input is a list/array-like
    if not isinstance(tempcol, (list, np.ndarray, pd.Series)):
        msg = "Input must be a list-like object."
        raise TypeError(msg)

    # Regular expression to find matches
    pattern = r"^tmt(\d{2})?_channel$"

    # Find matches
    matches = [col for col in tempcol if re.match(pattern, col)]

    # Check the number of matches
    if len(matches) == 1:
        # Return the matching variable
        return matches[0]
    if len(matches) > 1:
        msg = "Error: More than one matching element found."
        raise ValueError(msg)
    msg = "Error: No matching elements found."
    raise ValueError(msg)


def check_tmt_channels(
    tmt_type: str,
    tmt_expected: list[str],
    temp: pd.DataFrame,
    tmt_col: str,
    tmt_details: str,
) -> None:
    """Check TMT channel consistency and provide detailed comparison.

    :param tmt_type: Type of TMT experiment
    :param tmt_expected: List of expected TMT channels
    :param temp: DataFrame with TMT data
    :param tmt_col: Column name containing TMT channels
    :param tmt_details: Path to TMT details file for error reporting
    :raises: ValueError if channel mismatch is detected
    """
    actual_channels = sorted(temp[tmt_col].tolist())
    expected_channels = sorted(tmt_expected)

    if expected_channels != actual_channels:
        # Find differences and intersections
        shared_channels = set(expected_channels).intersection(set(actual_channels))
        missed_in_actual = set(expected_channels).difference(set(actual_channels))
        extra_in_actual = set(actual_channels).difference(set(expected_channels))

        # Build error message
        error_message = (
            f"Something is wrong: the expected `{tmt_type}` channels and the `{tmt_type}` "
            f"channels available in the `{os.path.basename(tmt_details)}` file do not match."
            f"\nThis likely means that there is a mismatch between the tmt specified as argument and the actual channels available in the data files.\n"
        )

        if shared_channels:
            error_message += f"\nShared channels: {', '.join(shared_channels)}"
        if missed_in_actual:
            error_message += f"\nMissing in actual data: {', '.join(missed_in_actual)}"
        if extra_in_actual:
            error_message += f"\nExtra in actual data: {', '.join(extra_in_actual)}"

        raise ValueError(error_message)


def fix_duplicates(meta: pd.DataFrame) -> pd.DataFrame:
    """Fix duplicated vial_labels by making them unique."""
    if meta["vial_label"].duplicated().any():
        logger.warning("Duplicate vial_label ids found. Making unique ids.")
        # Equivalent to R's make.unique
        seen = {}
        unique_names = []
        for name in meta["vial_label"]:
            if name in seen:
                seen[name] += 1
                unique_names.append(f"{name}.{seen[name]}")
            else:
                seen[name] = 0
                unique_names.append(name)
        meta["vial_label"] = unique_names
    return meta


def cli_args() -> argparse.Namespace:
    """Set up command line argument parser."""
    parser = argparse.ArgumentParser(
        description="Generate PlexedPiper study_design files",
    )
    parser.add_argument(
        "-f",
        "--file_vial_metadata",
        type=str,
        default="generate",
        help="File <-vial_metadata.txt> or type <generate> if it does not exist",
    )
    parser.add_argument(
        "-b",
        "--batch_folder",
        type=str,
        required=True,
        help="Full path to the BATCH folder (from the PHASE folder)",
    )
    parser.add_argument("-c", "--cas", type=str, required=True, help="CAS: BI or PN)")
    parser.add_argument(
        "-s",
        "--raw_source",
        type=str,
        default="folder",
        help="Source to get the raw files: `manifest` from manifest file or `folder` to list them from the bucket raw folders",
    )
    parser.add_argument(
        "-t",
        "--tmt",
        type=str,
        required=True,
        help="One of the following options: tmt11, tmt16, tmt18",
    )
    parser.add_argument("-p", "--phase", type=str, required=True, help="MOTRPAC PHASE")
    # Parse arguments
    return parser.parse_args()


def process_manifest(raw_folder: str) -> pd.DataFrame:
    """Get fractions from file manifest files."""
    fractions = None
    logger.info("(from processing manifest files):")
    file_manifest = glob.glob(
        os.path.join(raw_folder, "**/*metadata_file.txt"),
        recursive=True,
    )
    file_manifest.extend(
        glob.glob(
            os.path.join(raw_folder, "**/*raw_metadata_file*"),
            recursive=True,
        ),
    )
    # Sort the file paths to ensure they are in the correct order
    file_manifest.sort()
    for i, manifest_file in enumerate(file_manifest, 1):
        logger.info("\t%s. File: %s", i, os.path.basename(manifest_file))

        manifest = pd.read_csv(manifest_file, sep="\t")

        manifest = manifest[["file_name"]]
        manifest = manifest.rename(columns={"file_name": "Dataset"})

        manifest["PlexID"] = f"S{i}"

        if fractions is None:
            fractions = manifest
        else:
            fractions = pd.concat([fractions, manifest], ignore_index=True)

    return fractions


def process_folder(raw_folder: str) -> pd.DataFrame:
    """Get fractions from raw files in the folder."""
    logger.info("(from listing raw files in folder)")
    # Check subfolders
    raw_subfolders = [
        f
        for f in glob.glob(os.path.join(raw_folder, "**/"))
        if re.search(r".*/\d{2}.*", f)
    ]
    raw_subfolders.sort()
    if not raw_subfolders:
        msg = "The number of subfolders with raw data is equal to 0, which might mean that this submission is not according to MoTrPAC guidelines"
        raise ValueError(msg)
    fr_list = []
    for sf, subfolder in enumerate(raw_subfolders, 1):
        raw_files = glob.glob(os.path.join(subfolder, "**/*.raw"), recursive=True)

        # Check and exclude empty *raw files
        non_empty_raw_files = []
        empty_raw_files = []

        for raw_file in raw_files:
            try:
                with open(raw_file, "rb") as f:  # binary mode just in case
                    first_line = f.readline()
                    if first_line.strip():  # non-empty
                        non_empty_raw_files.append(raw_file)
                    else:
                        empty_raw_files.append(os.path.basename(raw_file))
            except Exception as err:
                logger.warning("⚠️ Could not read %s", raw_file, exc_info=err)
                empty_raw_files.append(os.path.basename(raw_file))

        if empty_raw_files:
            logger.warning(
                "🚨 Warning: The following raw files in %s appears to be empty: %s\n"
                "Please inspect for issues. Analysis will continue with non-empty files.\n",
                subfolder,
                "\n".join(empty_raw_files),
            )

        # Use only non-empty files going forward
        raw_files = non_empty_raw_files

        if raw_files:
            invalid_files = [
                f
                for f in raw_files
                if not re.search(r"_f\d{2,3}\.raw$", os.path.basename(f))
            ]
            if invalid_files:
                msg = f"The following raw files do not follow the format of proposed file name: {'\n'.join(invalid_files)}. \n\nPlease check the MoTrPAC control vocabulary guidelines.\n"
                raise ValueError(msg)

            # Extract fraction numbers from filenames
            fraction_nums = []
            for f in raw_files:
                match = re.search(r"_f(\d{2,3})\.raw$", os.path.basename(f))
                if match:
                    fraction_nums.append(int(match.group(1)))

            if fraction_nums:
                min_frac = min(fraction_nums)
                max_frac = max(fraction_nums)
                expected_fracs = set(range(min_frac, max_frac + 1))
                actual_fracs = set(fraction_nums)
                missing_fracs = sorted(expected_fracs - actual_fracs)

                if missing_fracs:
                    all_basenames = {os.path.basename(f) for f in raw_files}
                    expected_names = {
                        f"{os.path.splitext(os.path.basename(f))[0].split('_f')[0]}_f{str(i).zfill(2)}.raw"
                        for i in range(min_frac, max_frac + 1)
                    }
                    missing_names = sorted(expected_names - all_basenames)

                    logger.warning(
                        "🚨 Warning: Missing fraction files in %s. Expected fractions from f%s to f%s."
                        "Missing files:\n %s \nContinuing with available files.\n",
                        subfolder,
                        str(min_frac).zfill(2),
                        str(max_frac).zfill(2),
                        "\n ".join(missing_names),
                    )

            fr_temp = pd.DataFrame(
                {"Dataset": [os.path.basename(f) for f in raw_files]},
            )
            fr_temp["PlexID"] = f"S{sf}"
            fr_list.append(fr_temp)

        else:
            msg = f"Raw files not found in this folder: {subfolder}"
            raise ValueError(msg)

    return pd.concat(fr_list, ignore_index=True)


def main():
    args = cli_args()

    # Extract arguments for easier access
    file_vial_metadata = args.file_vial_metadata
    batch_folder = args.batch_folder
    cas = args.cas
    raw_source = args.raw_source
    tmt = args.tmt
    phase = args.phase

    # Debug information
    logger.debug("\n# GENERATE PlexedPiper study_design FILES")
    logger.debug("-f: Vial metadata: %s", file_vial_metadata)
    logger.debug("-c: Bach folder: %s", batch_folder)
    logger.debug("-u: Get the raw files from: %s", raw_source)
    logger.debug("-t: tmt experiment: %s", tmt)
    logger.debug("-------------------------------------")

    # Collect and Generate metadata
    _batch = validate_batch(batch_folder)
    _phase_folder = validate_phase(
        batch_folder
    )  # Placeholder for actual implementation
    assay = validate_assay(batch_folder)  # Placeholder for actual implementation
    assay = re.sub(r"(PROT_)(.*)", r"\2", assay)
    tissue = validate_tissue(batch_folder)  # Placeholder for actual implementation

    valid_cas = ["PN", "BI", "PNBI"]
    if cas not in valid_cas:
        msg = f"<cas> must be one of this: {','.join(valid_cas)}"
        raise ValueError(msg)

    date = datetime.now().strftime("%Y%m%d")

    # Process batch folder
    batch_folder = os.path.abspath(batch_folder)

    # Get RAW files folder name
    raw_folders = glob.glob(os.path.join(batch_folder, "RAW*"))

    # if There is no raw folder, then use BATCH folder
    raw_folder = batch_folder if not raw_folders else raw_folders[0]

    # Details about the tmt experiment
    if tmt == "tmt11":
        ecolnames = ["tmt_plex", "tmt11_channel", "vial_label"]
        tmt_channels = [
            "126C",
            "127N",
            "127C",
            "128N",
            "128C",
            "129N",
            "129C",
            "130N",
            "130C",
            "131N",
            "131C",
        ]
    elif tmt == "tmt16":
        ecolnames = ["tmt_plex", "tmt16_channel", "vial_label"]
        tmt_channels = [
            "126C",
            "127N",
            "127C",
            "128N",
            "128C",
            "129N",
            "129C",
            "130N",
            "130C",
            "131N",
            "131C",
            "132N",
            "132C",
            "133N",
            "133C",
            "134N",
        ]
    elif tmt == "tmt18":
        ecolnames = ["tmt_plex", "tmt18_channel", "vial_label"]
        tmt_channels = [
            "126C",
            "127N",
            "127C",
            "128N",
            "128C",
            "129N",
            "129C",
            "130N",
            "130C",
            "131N",
            "131C",
            "132N",
            "132C",
            "133N",
            "133C",
            "134N",
            "134C",
            "135N",
        ]
    else:
        msg = "<tmt> must be one of this: tmt11, tmt16, tmt18"
        raise ValueError(msg)

    # List all details.txt files recursively from the raw_folder
    tmt_details_files = glob.glob(
        os.path.join(raw_folder, "**/*details.txt"),
        recursive=True,
    )

    # Sort the file paths to ensure they are in the correct order
    tmt_details_files.sort()

    # Initialize an empty list to store data
    nm_list = []

    if file_vial_metadata == "generate":
        logger.info("+ Generate vial metadata file")

        # Process each file
        for i, tmt_details in enumerate(tmt_details_files, 1):
            try:
                temp = pd.read_csv(tmt_details, sep="\t")
            except pd.errors.EmptyDataError as err:
                msg = f"'{tmt_details}' is empty. Please validate file integrity."
                raise ValueError(msg) from err

            if temp.empty or temp.shape[1] == 0:
                msg = (
                    f"'{tmt_details}' contains no data. Please validate file integrity."
                )
                raise ValueError(msg)

            tmt_col = find_unique_tmt_channel(temp.columns.tolist())

            # Check TMT channels based on tmt type
            check_tmt_channels(tmt, tmt_channels, temp, tmt_col, tmt_details)

            # Add custom labels
            temp["tmt_plex"] = f"S{i}"
            temp["vial_label"] = temp["vial_label"].apply(
                lambda x: f"Ref_S{i}" if "Ref" in str(x) else x,
            )

            nm_list.append(temp)

        vial_metadata = pd.concat(nm_list, ignore_index=True)
        file_vial_metadata = (
            f"MOTRPAC_{phase}_{tissue}_{assay}_{cas}_{date}_vial_metadata.txt"
        )

    else:
        logger.info("+ Reading file vial metadata")
        try:
            vial_metadata = pd.read_csv(file_vial_metadata, sep="\t")
            if vial_metadata.empty:
                msg = f"{file_vial_metadata} is empty. Please use generate option to generate vial metadata file."
                raise ValueError(msg)
        except pd.errors.EmptyDataError as err:
            msg = f"{file_vial_metadata} is empty. Please use generate option to generate vial metadata file."
            raise ValueError(msg) from err

        file_vial_metadata = (
            f"MOTRPAC_{phase}_{tissue}_{assay}_{cas}_{date}_vial_metadata.txt"
        )

    logger.info("File name: %s", file_vial_metadata)

    # Make adjustments: make sure that the Reference channel is "Ref_S#"
    vial_metadata.columns = vial_metadata.columns.str.lower()
    vial_metadata["vial_label"] = vial_metadata.apply(
        lambda row: f"Ref_{row['tmt_plex']}"
        if re.match(r"^ref", str(row["vial_label"]), re.IGNORECASE)
        else row["vial_label"],
        axis=1,
    )

    # Check if there are any "Ref" samples
    has_ref = any(
        vial_metadata["vial_label"].str.contains(r"^Ref", case=False, regex=True),
    )

    if not all(col in vial_metadata.columns for col in ecolnames):
        missing = [col for col in ecolnames if col not in vial_metadata.columns]
        msg = (
            f"Vial Metadata. The expected column names...\n\t{', '.join(ecolnames)}\n"
            f"are not available in vial_metadata: \n\t{', '.join(vial_metadata.columns)}\n"
            f"Missing columns: {', '.join(missing)}",
        )
        raise ValueError(msg)

    # Remove white spaces (known issue for pnnl submissions)
    vial_metadata["vial_label"] = vial_metadata["vial_label"].str.replace(" ", "")

    # Fix duplicated vial_labels
    vial_metadata = fix_duplicates(meta=vial_metadata)

    # Generate samples.txt
    logger.info("+ Generate samples.txt... ")

    if tmt == "tmt11":
        samples = vial_metadata.copy()
        samples["PlexID"] = samples["tmt_plex"]
        samples["QuantBlock"] = 1
        samples["ReporterName"] = samples["tmt11_channel"]
        samples["ReporterAlias"] = samples["vial_label"]
        samples["MeasurementName"] = samples["vial_label"]
        samples = samples.drop(["tmt_plex", "tmt11_channel", "vial_label"], axis=1)
    elif tmt == "tmt16":
        samples = vial_metadata.copy()
        samples["PlexID"] = samples["tmt_plex"]
        samples["QuantBlock"] = 1
        samples["ReporterName"] = samples["tmt16_channel"]
        samples["ReporterAlias"] = samples["vial_label"]
        samples["MeasurementName"] = samples["vial_label"]
        samples = samples.drop(["tmt_plex", "tmt16_channel", "vial_label"], axis=1)
    elif tmt == "tmt18":
        samples = vial_metadata.copy()
        samples["PlexID"] = samples["tmt_plex"]
        samples["QuantBlock"] = 1
        samples["ReporterName"] = samples["tmt18_channel"]
        samples["ReporterAlias"] = samples["vial_label"]
        samples["MeasurementName"] = samples["vial_label"]
        samples = samples.drop(["tmt_plex", "tmt18_channel", "vial_label"], axis=1)
    else:
        msg = "<tmt> must be one of this: tmt11, tmt16, tmt18"
        raise ValueError(msg)

    # adjustments
    samples["ReporterName"] = samples["ReporterName"].str.replace("126C", "126")

    if has_ref:
        samples["MeasurementName"] = samples["ReporterAlias"]
        ref_mask = samples["ReporterAlias"].str.contains(
            r"^ref",
            case=False,
            regex=True,
        )
        samples.loc[ref_mask, "MeasurementName"] = None

    # Select only required columns
    samples = samples[
        ["PlexID", "QuantBlock", "ReporterName", "ReporterAlias", "MeasurementName"]
    ]

    logger.info("done")

    # Generate references.txt
    logger.info("+ Generate references... ")

    # Conditional operation based on the presence of "Ref" samples
    if has_ref:
        references = samples[
            samples["ReporterAlias"].str.contains(r"^\+?Ref", regex=True)
        ].copy()
        references = references.drop(["ReporterName", "MeasurementName"], axis=1)
        references = references.rename(columns={"ReporterAlias": "Reference"})
    else:
        logger.warning(
            "(no references available: value 1 would be added instead) ", end=""
        )
        references = samples[["PlexID", "QuantBlock"]].copy()
        references["Reference"] = 1

    logger.info("done")

    # Generate fractions.txt
    logger.info("+ Generate fractions.txt file")

    if raw_source == "manifest":
        fractions = process_manifest(raw_folder)

    elif raw_source == "folder":
        fractions = process_folder(raw_folder)
    else:
        msg = "The -s argument is not right. It should be either `manifest` or `folder`"
        raise ValueError(msg)

    fractions["Dataset"] = fractions["Dataset"].str.replace(".raw", "")

    logger.info("+ Checking PlexID notations")
    # Extract unique and sorted values from each data frame's relevant variable
    unique_fractions = sorted(fractions["PlexID"].unique())
    unique_samples = sorted(samples["PlexID"].unique())
    unique_references = sorted(references["PlexID"].unique())
    unique_vial_metadata = sorted(vial_metadata["tmt_plex"].unique())

    # Compare all vectors for equality
    are_equal = (
        unique_fractions == unique_samples
        and unique_samples == unique_references
        and unique_references == unique_vial_metadata
    )

    # Output the result
    if are_equal:
        logger.info("+ Validations: All PlexID lists are identical.")
    else:
        logger.error("Not all PlexID lists are identical. Detailed comparison needed.")
        logger.error("Fractions PlexID: %s", ",".join(unique_fractions))
        logger.error("Samples PlexID: %s", ",".join(unique_samples))
        logger.error("References PlexID: %s", ",".join(unique_references))
        logger.error("Vial Metadata tmt_plex: %s", ",".join(unique_vial_metadata))
        msg = "Fix PlexID before printing out files"
        raise ValueError(msg)

    # Print out files
    # The study_design folder should be in the RAW folder, but given that in
    # some cases the RAW files were not given in the RAW folder, it might be
    # located in the BATCH folder.
    output_viallabel_name = os.path.join(raw_folder, "study_design")

    if not os.path.exists(output_viallabel_name):
        os.makedirs(output_viallabel_name, exist_ok=True)

    fractions_path = os.path.join(os.path.join(output_viallabel_name, "fractions.txt"))
    fractions.to_csv(fractions_path, sep="\t", index=False)

    references_path = os.path.join(
        os.path.join(output_viallabel_name, "references.txt"),
    )
    references.to_csv(references_path, sep="\t", index=False)

    samples_path = os.path.join(output_viallabel_name, "samples.txt")
    samples.to_csv(samples_path, sep="\t", index=False)

    vial_metadata_path = os.path.join(output_viallabel_name, file_vial_metadata)
    vial_metadata.to_csv(vial_metadata_path, sep="\t", index=False)

    logger.info("All files are out! Check them out at: %s", output_viallabel_name)


if __name__ == "__main__":
    main()
