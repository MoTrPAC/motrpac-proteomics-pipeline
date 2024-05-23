#!/usr/bin/env Rscript

suppressWarnings(suppressPackageStartupMessages(library(optparse)))
suppressWarnings(suppressPackageStartupMessages(library(dplyr, warn.conflicts = FALSE)))
suppressWarnings(suppressPackageStartupMessages(library(stringr, warn.conflicts = FALSE)))
library(MotrpacBicQC)

option_list <- list(
  make_option(c("-f", "--file_vial_metadata"), 
              type="character", 
              default="generate", 
              help="File <-vial_metadata.txt> or type <generate> if it does not exist", 
              metavar="character"),
  make_option(c("-b", "--batch_folder"), 
              type="character", 
              help="Full path to the BATCH folder (from the PHASE folder)", 
              metavar="character"),
  make_option(c("-c", "--cas"), 
              type="character", 
              help="CAS: BI or PN)", 
              metavar="character"),
  make_option(c("-s", "--raw_source"), 
              type="character", 
              default="folder", 
              help="Source to get the raw files: `manifest` from manifest file or `folder` to list them from the bucket raw folders", 
              metavar="character"),
  make_option(c("-t", "--tmt"),
              type="character",
              help="One of the following options: tmt11, tmt16, tmt18",
              metavar="character"),
  make_option(c("-p", "--phase"),
              type="character",
              help="MOTRPAC PHASE",
              metavar="character")
)

opt_parser <- OptionParser(option_list = option_list)
opt <- parse_args(opt_parser)

if (is.null(opt$file_vial_metadata) |
    is.null(opt$batch_folder) |
    is.null(opt$cas) |
    is.null(opt$raw_source) |
    is.null(opt$tmt) | 
    is.null(opt$phase)){
  print_help(opt_parser)
  stop("6 arguments are required", call.=FALSE)
}

validate_batch <- function(input_results_folder){
  batch_folder <- stringr::str_extract(string = input_results_folder, 
                                       pattern = "(BATCH\\d*\\_\\d{8})")
  
  if(is.na(batch_folder)){
    stop("`BATCH#_YYYYMMDD` folder is not recognized in the folder structure.")
  }else{
    return(batch_folder)
  }
}

# To facilitate debugging
file_vial_metadata <- opt$file_vial_metadata
batch_folder <- opt$batch_folder
cas <- opt$cas
raw_source <- opt$raw_source
tmt <- opt$tmt
phase <- opt$phase

# DEBUG-----
message("\n# GENERATE PlexedPiper study_design FILES")
message("-f: Vial metadata: ", file_vial_metadata)
message("-c: Bach folder: ", batch_folder)
message("-u: Get the raw files from: ", raw_source)
message("-t: tmt experiment: ", tmt)
message("-------------------------------------")

# Collect and Generate metadata-----
# Collect information to potentially generate the vial label file (if not provided)
batch <- validate_batch(batch_folder)
phase_folder <- MotrpacBicQC::validate_phase(batch_folder)
assay <- MotrpacBicQC::validate_assay(batch_folder)
assay <- gsub("(PROT_)(.*)", "\\2", assay)
tissue <- MotrpacBicQC::validate_tissue(batch_folder)
valid_cas <- c("PN", "BI", "PNBI")
if(!any(cas %in% valid_cas)){
  stop("<cas> must be one of this: ", paste(valid_cas, collapse = ","))
}
date <- Sys.Date()
date <- gsub("-", "", date)

# Process batch folder
batch_folder <- normalizePath(batch_folder)

# Get RAW files folder name
raw_folder <- list.files(batch_folder, pattern = "RAW*", full.names = TRUE)

if(length(raw_folder) == 0){
  # if There is no raw folder, then use BATCH folder
  raw_folder <- batch_folder
}

# Details about the tmt experiment
if(tmt == "tmt11") {
  ecolnames <- c("tmt_plex", "tmt11_channel", "vial_label")
  tmt11 <- c("126C", "127N", "127C", "128N", "128C", "129N", "129C", "130N", "130C", "131N", "131C")
}else if(tmt == "tmt16") {
  ecolnames <- c("tmt_plex", "tmt16_channel", "vial_label")
  tmt16 <- c("126C", "127N", "127C", "128N", "128C", "129N", "129C", "130N", "130C", "131N", "131C", "132N", "132C", "133N", "133C", "134N")
}else if(tmt == "tmt18") {
  ecolnames <- c("tmt_plex", "tmt18_channel", "vial_label")
  tmt18 <- c("126C", "127N", "127C", "128N", "128C", "129N", "129C", "130N", "130C", "131N", "131C", "132N", "132C", "133N", "133C", "134N", "134C", "135N")
}else{
  stop("<tmt> must be one of this: tmt11, tmt16, tmt18")
}

# Vial_metadata file ------
#' Find Unique TMT Channel
#'
#' This function identifies a unique TMT channel name in a vector based on a specified pattern.
#' It ensures exactly one match is found and throws an error if there are none or multiple matches.
#'
#' @param tempcol A character vector of potential TMT channel names.
#' Expected channel names are "tmt_channel", "tmt11_channel", "tmt16_channel", etc.
#'
#' @return The matching TMT channel name if exactly one match is found.
#'         Throws an error if no matches or multiple matches are found.
#'
#' @examples
#' channels <- c("tmt_channel", "a", "b", "c")
#' find_unique_tmt_channel(channels)  # Returns "tmt_channel"
#'
#' channels_error <- c("tmt_channel", "tmt11_channel")
#' find_unique_tmt_channel(channels_error)  # Error: More than one matching element found.
#'
#' @details
#' The function uses a regex to filter entries that start with "tmt", optionally followed by
#' two digits and "_channel". It checks for one exact match and handles errors accordingly.
find_unique_tmt_channel <- function(tempcol) {
  # Check that input is a vector
  if (!is.vector(tempcol)) {
    stop("Input must be a vector.")
  }
  
  # Regular expression to find matches
  pattern <- "^tmt(\\d{2})?_channel$"
  
  # Find matches
  matches <- grepl(pattern, tempcol)
  
  # Check the number of matches
  if (sum(matches) == 1) {
    # Return the matching variable
    return(tempcol[matches])
  } else if (sum(matches) > 1) {
    stop("Error: More than one matching element found.")
  } else {
    stop("Error: No matching elements found.")
  }
}

# Helper function to check TMT channel consistency and provide detailed comparison
check_tmt_channels <- function(tmt_type, tmt_expected, temp, tmt_col, tmt_details) {
  actual_channels <- sort(temp[[tmt_col]])
  expected_channels <- sort(tmt_expected)
  
  if (!identical(expected_channels, actual_channels)) {
    # Find differences and intersections
    shared_channels <- intersect(expected_channels, actual_channels)
    missed_in_actual <- setdiff(expected_channels, actual_channels)
    extra_in_actual <- setdiff(actual_channels, expected_channels)
    
    # Build error message
    error_message <- paste0(
      "Something is wrong: the expected `", tmt_type, "` channels and the `", tmt_type, 
      "` channels available in the `", basename(tmt_details), "` file do not match.",
      "\nThis likely means that there is a mismatch between the tmt specified as argument and the actual channels available in the data files.\n",
      if (length(shared_channels) > 0) paste("\nShared channels:", paste(shared_channels, collapse = ", ")) else "",
      if (length(missed_in_actual) > 0) paste("\nMissing in actual data:", paste(missed_in_actual, collapse = ", ")) else "",
      if (length(extra_in_actual) > 0) paste("\nExtra in actual data:", paste(extra_in_actual, collapse = ", ")) else ""
    )
    
    stop(error_message)
  }
}


# List all details.txt files recursively from the raw_folder
tmt_details_files <- list.files(path = raw_folder,
                                pattern = "details\\.txt",
                                ignore.case = TRUE,
                                full.names = TRUE,
                                recursive = TRUE)

# Sort the file paths to ensure they are in the correct order
tmt_details_files <- sort(tmt_details_files)

# Initialize an empty list to store data
nm_list <- list()

if (file_vial_metadata == "generate") {
  message("+ Generate vial metadata file")
  
  # Process each file
  for (i in seq_along(tmt_details_files)) {
    tmt_details <- tmt_details_files[i]
    
    temp <- read.delim(tmt_details)
    
    tmt_col <- find_unique_tmt_channel(colnames(temp))
    
    # if (tmt == "tmt11") {
    #   if(!identical(sort(tmt11), sort(temp[[tmt_col]]) )){
    #     stop("Something is wrong: the expected tmt11 channels and the tmt11 channels available in the ", 
    #          print(tmt_details), 
    #          " file do not match\n- the expected channels: ", message(paste(tmt11, sep = ",")))
    #   }
    # } else if (tmt == "tmt16") {
    #   if(!identical(sort(tmt16), sort(temp[[tmt_col]]) )){
    #     stop("Something is wrong: the expected tmt16 channels and the tmt16 channels available in the ", 
    #          print(tmt_details), 
    #          " file do not match\n- the expected channels: ", message(paste(tmt16, sep = ",")))
    #   }
    # } else if (tmt == "tmt18") {
    #   if(!identical(sort(tmt18), sort(temp[[tmt_col]]) )){
    #     stop("Something is wrong: the expected tmt18 channels and the tmt18 channels available in the ", 
    #          print(tmt_details), 
    #          " file do not match\n- the expected channels: ", message(paste(tmt16, sep = ",")))
    #   }
    # } else {
    #   stop(paste(tmt, ": this tmt type not supported yet"))
    # }
    
    if (tmt %in% c("tmt11", "tmt16", "tmt18")) {
      tmt_expected <- get(paste0(tmt))  # Assumes tmt11, tmt16, tmt18 are defined somewhere accessible
      check_tmt_channels(tmt, tmt_expected, temp, tmt_col, tmt_details)
    } else {
      stop(paste(tmt, ": this tmt type not supported yet"))
    }
    
    # Add custom labels
    temp$tmt_plex <- paste0("S", i)
    temp$vial_label <- ifelse(grepl("Ref", temp$vial_label), paste0("Ref_S", i), temp$vial_label)
    
    nm_list[[i]] <- temp
  }
  
  vial_metadata <- dplyr::bind_rows(nm_list)
  file_vial_metadata <- paste0("MOTRPAC_", phase, "_", tissue, "_", assay, "_", cas, "_", date, "_vial_metadata.txt")
} else {
  message("+ Reading file vial metadata")
  vial_metadata <- read.delim(file_vial_metadata, stringsAsFactors = FALSE)
  file_vial_metadata <- paste0("MOTRPAC_", phase, "_", tissue, "_", assay, "_", cas, "_", date, "_vial_metadata.txt")
}

message("\t - File name: ", file_vial_metadata)

# Make adjustments: make sure that the Reference channel is "Ref_S#"
colnames(vial_metadata) <- tolower(colnames(vial_metadata))
vial_metadata$vial_label <- ifelse(grepl("^ref", vial_metadata$vial_label, ignore.case = TRUE), paste0("Ref_", vial_metadata$tmt_plex), vial_metadata$vial_label)

# Check if there are any "Ref" samples
has_ref <- any(grepl("^Ref", vial_metadata$vial_label, ignore.case = TRUE))

if( !all(ecolnames %in% colnames(vial_metadata)) ){
  stop("Vial Metadata. The expeted column names...\n\t", 
       paste(ecolnames, collapse = ", "), 
       "\nare not availble in vial_metadata: \n\t", 
       paste(colnames(vial_metadata), collapse = ", "))
}

# Remove white spaces (known issue for pnnl submissions)
vial_metadata$vial_label <- gsub(" ", "", vial_metadata$vial_label)

## Fix duplicated vial_labels-----
fix_duplicates <- function(meta) {
  if (anyDuplicated(meta$vial_label, incomparables = NA)) {
    warning("Duplicate vial_label ids found. Making unique ids.")
    meta$vial_label <- make.unique(meta$vial_label)
  }
  return(meta)
}

vial_metadata <- fix_duplicates(meta = vial_metadata)

# Generate samples.txt-----
message("+ Generate samples.txt... ", appendLF = FALSE)
if(tmt == "tmt11"){
  samples <- vial_metadata %>%
    mutate(PlexID = tmt_plex,
           QuantBlock = 1,
           ReporterName = tmt11_channel,
           ReporterAlias = vial_label,
           MeasurementName = vial_label) %>%
    dplyr::select(-tmt_plex, -tmt11_channel, -vial_label)
}else if(tmt == "tmt16"){
  samples <- vial_metadata %>%
    mutate(PlexID = tmt_plex,
           QuantBlock = 1,
           ReporterName = tmt16_channel,
           ReporterAlias = vial_label,
           MeasurementName = vial_label) %>%
    dplyr::select(-tmt_plex, -tmt16_channel, -vial_label)
}else if(tmt == "tmt18"){
  samples <- vial_metadata %>%
    mutate(PlexID = tmt_plex,
           QuantBlock = 1,
           ReporterName = tmt18_channel,
           ReporterAlias = vial_label,
           MeasurementName = vial_label) %>%
    dplyr::select(-tmt_plex, -tmt18_channel, -vial_label)
}

# adjustments
samples$ReporterName <- gsub("126C", "126", samples$ReporterName)

if(has_ref){
  samples$MeasurementName <- samples$ReporterAlias  
  samples$MeasurementName[grepl("^ref", samples$ReporterAlias, ignore.case = TRUE)] <- NA
}

# Select only required columns
samples <- samples[c("PlexID", "QuantBlock", "ReporterName", "ReporterAlias", "MeasurementName")]

message(" done")

# Generate references.txt-----
message("+ Generate references... ", appendLF = FALSE)

# Conditional operation based on the presence of "Ref" samples
references <- if(has_ref) {
  samples %>%
    filter(grepl("^+Ref", ReporterAlias)) %>%
    dplyr::select(-ReporterName, -MeasurementName) %>%
    dplyr::rename(Reference = ReporterAlias)
} else {
  message(" (no references available: value 1 would be added instead) ", appendLF = FALSE)
  samples %>%
    dplyr::select(-ReporterName, -MeasurementName, -ReporterAlias) %>%
    mutate(Reference = 1)
}

message(" done")

# Generate fractions.txt-----
message("+ Generate fractions.txt file ", appendLF = FALSE)
fractions <- NULL
if(raw_source == "manifest"){
  message("(from processing manifest files):")
  file_manifest <- list.files(file.path(raw_folder),
                              pattern="metadata_file.txt|raw_metadata_file",
                              ignore.case = TRUE,
                              full.names=TRUE,
                              recursive = TRUE)
  # Sort the file paths to ensure they are in the correct order
  file_manifest <- sort(file_manifest)
  
  for (i in 1:length(file_manifest) ){
    message("\t", i, ". File: ", basename(file_manifest[i]))

    manifest <- read.delim(file_manifest[i], stringsAsFactors = FALSE)
    
    manifest <- manifest[c('file_name')]
    manifest <- rename(manifest, Dataset=file_name)
    
    manifest$PlexID <- paste0("S", i)
    
    if(is.null(fractions)){
      fractions <- manifest
    }else{
      fractions <- rbind(fractions, manifest)
    }
  }
}else if(raw_source == "folder"){
  message("(from listing raw files in folder)")
  
  # Check subfolders-----
  raw_subfolders <- list.dirs(raw_folder)
  raw_subfolders <- sort(raw_subfolders)
  raw_subfolders <- raw_subfolders[grepl(".*/\\d{2}.*", raw_subfolders)]
  if(length(raw_subfolders) == 0){
    stop("The number of subfolders with raw data is equal to 0, which might mean that this submission is not according to MoTrPAC guidelines")
  }
  
  fr_list <- list()
  for(sf in 1:length(raw_subfolders)){
    fr_temp <- as.data.frame(list.files(file.path(raw_subfolders[sf]),
                                        pattern="*.raw$",
                                        ignore.case = TRUE,
                                        full.names=TRUE,
                                        recursive = TRUE))
    
    if(dim(fr_temp)[1] > 0){
      colnames(fr_temp) <- c("Dataset")
      fr_temp$PlexID <- paste0("S", sf)
      fr_temp$Dataset <- basename(fr_temp$Dataset)
      fr_list[[sf]] <- fr_temp
    }else{
      stop("\n\nRaw files not found in this folder:\n", raw_subfolders[sf])
    }
  }
  fractions <- dplyr::bind_rows(fr_list)
  
}else{
  stop("The -s argument is not right. It should be either `manifest` or `folder`")
}

fractions$Dataset <- gsub(".raw", "", fractions$Dataset)

message("+ Checking PlexID notations")
# Check points------

# Extract unique and sorted values from each data frame's relevant variable
# Convert to character and sort unique values
unique_fractions <- unique(as.character(fractions$PlexID))
unique_samples <- unique(as.character(samples$PlexID))
unique_references <- unique(as.character(references$PlexID))
unique_vial_metadata <- unique(as.character(vial_metadata$tmt_plex))

# Compare all vectors for equality
are_equal <- identical(unique_fractions, unique_samples) &&
  identical(unique_samples, unique_references) &&
  identical(unique_references, unique_vial_metadata)

# Output the result
if (are_equal) {
  message("+ Validations: All PlexID lists are identical.")
} else {
  message("Not all PlexID lists are identical. Detailed comparison needed.")
  message("Fractions PlexID: ", paste(unique_fractions, collapse = ","))
  message("Samples PlexID: ", paste(unique_samples, collapse = ","))
  message("References PlexID: ", paste(unique_references, collapse = ","))
  message("Vial Metadata tmt_plex: ", paste(unique_vial_metadata, collapse = ","))
  stop("Fix PlexID before printing out files")
}


# Print out files -----
# The study_design folder should be in the RAW folder, but given that in 
# some cases the RAW files where not given in the RAW folder, it might be 
# located in the BATCH folder.
output_viallabel_name <- file.path(raw_folder, "study_design")

if(!dir.exists(file.path(output_viallabel_name))){
  dir.create(output_viallabel_name, recursive = TRUE)
}

write.table(fractions,
            file = file.path(output_viallabel_name, "fractions.txt"),
            row.names = FALSE, sep = "\t", quote = FALSE)

write.table(references, 
            file = file.path(output_viallabel_name, "references.txt"),
            row.names = FALSE, sep = "\t", quote = FALSE)

write.table(samples, 
            file = file.path(output_viallabel_name, "samples.txt"),
            row.names = FALSE, sep = "\t", quote = FALSE)

write.table(vial_metadata, 
            file = file.path(output_viallabel_name, file_vial_metadata),
            row.names = FALSE, sep = "\t", quote = FALSE)


message("\nAll files are out! Check them out at:\n", file.path(output_viallabel_name))


