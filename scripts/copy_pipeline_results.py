import argparse
import getopt
from google.cloud import storage
import json
import os
import pathlib
import re # regular expressions
import sys
import warnings
import dateparser
warnings.filterwarnings("ignore", "Your application has authenticated using end user credentials")


# Removes the bucket name from a string
def remove_gsbucket( str , bucket_name ):
    gs_bucket_name = 'gs://' + bucket_name + '/'
    new_str = str.replace(gs_bucket_name, '')
    return new_str

# Not used, but just in case
def upload_file(bucket_destination, source_file_name, destination_blob_name):
#   """Uploads a file to the bucket."""
#   storage_client = storage.Client()
    blob = bucket_destination.blob(destination_blob_name)
    blob.upload_from_filename(source_file_name)
    print('File {} uploaded to {}.'.format(
        source_file_name,
        destination_blob_name))
    # Use it like this
    # f = open( cmd_local_file_name, 'w' )
    # f.write( msconvert_mzrefiner_cmd )
    # f.close()
    # upload_file(bucket_destination, cmd_local_file_name, msconvert_mzrefiner_cmd_blob_filename)

def upload_string(bucket_destination, str_content, destination_blob_name):
    b = bucket_destination.blob(destination_blob_name)
    b.upload_from_string(str_content)

# Copy ascore results to the same or different bucket
def copy_ascore( metadata, dest_root_folder, bucket_source, bucket_origin, bucket_destination ):

    ascore_output = dest_root_folder + 'ascore_outputs/'
    ascore_length = (len(metadata['calls']['proteomics_msgfplus.ascore']))
    # print('- Number of files processed:', ascore_length)

    for x in range(ascore_length):
        # print('\nBlob-', x, ' ', end = '')
        # # STDOUT, which requires to rename the file
        if 'stdout' in metadata['calls']['proteomics_msgfplus.ascore'][x]:
            seq_id = metadata['calls']['proteomics_msgfplus.ascore'][x]["inputs"]['seq_file_id'] 
            ascore_stdout = metadata['calls']['proteomics_msgfplus.ascore'][x]["stdout"]
            ascore_stdout_clean = remove_gsbucket( ascore_stdout, bucket_origin)
            ascore_stdout_rename =  ascore_output  + seq_id + '-ascore-stdout.log'
            print('- Log to:', ascore_stdout_rename)
            blob_stdout = bucket_source.get_blob(ascore_stdout_clean)
            bucket_source.copy_blob(blob_stdout, bucket_destination, ascore_stdout_rename)
        
        # ascore_output_length = len(metadata['calls']['proteomics_msgfplus.ascore'][x]['outputs'])
        # print('(Number of outputs:', ascore_output_length, ')')

        # # Get and upload the command
        if 'commandLine' in metadata['calls']['proteomics_msgfplus.ascore'][x]:
            ascore_cmd = metadata['calls']['proteomics_msgfplus.ascore'][x]["commandLine"]
            # print('The Command line:\n', ascore_cmd)
            cmd_local_file_name = 'command-ascore.txt'
            cmd_blob_filename = ascore_output + cmd_local_file_name
            print('- Command: ', cmd_blob_filename)
            upload_string(bucket_destination, ascore_cmd, cmd_blob_filename)

        executionStatus = remove_gsbucket( metadata['calls']['proteomics_msgfplus.ascore'][x]['executionStatus'], bucket_origin )
        if executionStatus == 'Done':
            syn_plus_ascore = remove_gsbucket( metadata['calls']['proteomics_msgfplus.ascore'][x]['outputs']['syn_plus_ascore'], bucket_origin )
            syn_ascore = remove_gsbucket( metadata['calls']['proteomics_msgfplus.ascore'][x]['outputs']['syn_ascore'], bucket_origin )
            syn_ascore_proteinmap = remove_gsbucket( metadata['calls']['proteomics_msgfplus.ascore'][x]['outputs']['syn_ascore_proteinmap'], bucket_origin )
            output_ascore_logfile = remove_gsbucket( metadata['calls']['proteomics_msgfplus.ascore'][x]['outputs']['output_ascore_logfile'], bucket_origin )

            blob_syn_plus_ascore = bucket_source.get_blob(syn_plus_ascore)
            blob_syn_ascore = bucket_source.get_blob(syn_ascore)
            blob_syn_ascore_proteinmap = bucket_source.get_blob(syn_ascore_proteinmap)
            blob_output_ascore_logfile = bucket_source.get_blob(output_ascore_logfile)

            new_syn_plus_ascore = ascore_output + os.path.basename(syn_plus_ascore)
            new_syn_ascore = ascore_output + os.path.basename(syn_ascore)
            new_syn_ascore_proteinmap = ascore_output + os.path.basename(syn_ascore_proteinmap)
            new_output_ascore_logfile = ascore_output + os.path.basename(output_ascore_logfile)

            print('- File to:', new_syn_plus_ascore)
            print('- File to:', new_syn_ascore)
            print('- File to:', new_syn_ascore_proteinmap)
            print('- File to:', new_output_ascore_logfile)

            bucket_source.copy_blob(blob_syn_plus_ascore, bucket_destination, new_syn_plus_ascore)
            bucket_source.copy_blob(blob_syn_ascore, bucket_destination, new_syn_ascore)
            bucket_source.copy_blob(blob_syn_ascore_proteinmap, bucket_destination, new_syn_ascore_proteinmap)
            bucket_source.copy_blob(blob_output_ascore_logfile, bucket_destination, new_output_ascore_logfile)
        else:
            print(' (-) Execution Status: ', executionStatus)
            print(' (-) Data cannot be copied')


# Copy msconvert_mzrefiner results to the same or different bucket
def copy_msconvert_mzrefiner( metadata, dest_root_folder, bucket_source, bucket_origin, bucket_destination):

    msconvert_mzrefiner_output = dest_root_folder + 'msconvert_mzrefiner_outputs/'
    msconvert_mzrefiner_length = (len(metadata['calls']['proteomics_msgfplus.msconvert_mzrefiner']))
    # print('- Number of files processed:', msconvert_mzrefiner_length)

    for x in range(msconvert_mzrefiner_length):
        # print('\nBlob-', x, ' ', end = '')
        if 'stdout' in metadata['calls']['proteomics_msgfplus.msconvert_mzrefiner'][x]:
            # STDOUT, which requires to rename the file
            seq_id = metadata['calls']['proteomics_msgfplus.msconvert_mzrefiner'][x]["inputs"]['sample_id'] 
            msconvert_mzrefiner_stdout = metadata['calls']['proteomics_msgfplus.msconvert_mzrefiner'][x]["stdout"]
            msconvert_mzrefiner_stdout_clean = remove_gsbucket( msconvert_mzrefiner_stdout, bucket_origin)
            msconvert_mzrefiner_stdout_rename =  msconvert_mzrefiner_output  + seq_id + '-msconvert_mzrefiner-stdout.log'
            # print('Stdout: ', msconvert_mzrefiner_stdout_rename)
            print('- Log to:', msconvert_mzrefiner_stdout_rename)
            blob_stdout = bucket_source.get_blob(msconvert_mzrefiner_stdout_clean)
            bucket_source.copy_blob(blob_stdout, bucket_destination, msconvert_mzrefiner_stdout_rename)
        
        if 'commandLine' in metadata['calls']['proteomics_msgfplus.msconvert_mzrefiner'][x]:
            # Get and upload the command
            msconvert_mzrefiner_cmd = metadata['calls']['proteomics_msgfplus.msconvert_mzrefiner'][x]["commandLine"]
            # print('The Command line:\n', msconvert_mzrefiner_cmd)
            cmd_local_file_name = 'command-msconvert_mzrefiner.txt'
            cmd_blob_filename = msconvert_mzrefiner_output + cmd_local_file_name
            upload_string(bucket_destination, msconvert_mzrefiner_cmd, cmd_blob_filename)
            # print('- Command: ', cmd_blob_filename)

        # msconvert_mzrefiner_output_length = len(metadata['calls']['proteomics_msgfplus.msconvert_mzrefiner'][x]['outputs'])
        # print(' (number of outputs:', msconvert_mzrefiner_output_length, ')')

        executionStatus = remove_gsbucket( metadata['calls']['proteomics_msgfplus.msconvert_mzrefiner'][x]['executionStatus'], bucket_origin )
        
        if executionStatus == 'Done':
            mzml_fixed = remove_gsbucket( metadata['calls']['proteomics_msgfplus.msconvert_mzrefiner'][x]['outputs']['mzml_fixed'], bucket_origin )
            blob_mzml_fixed = bucket_source.get_blob(mzml_fixed)
            new_mzml_fixed = msconvert_mzrefiner_output + os.path.basename(mzml_fixed)
            print('- File to:', new_mzml_fixed)
            bucket_source.copy_blob(blob_mzml_fixed, bucket_destination, new_mzml_fixed)
        else:
            print(' (-) Execution Status: ', executionStatus)
            print(' (-) Data cannot be copied')

def copy_ppm_errorcharter( metadata, dest_root_folder, bucket_source, bucket_origin, bucket_destination):

    ppm_errorcharter_output = dest_root_folder + 'output_ppm_errorcharter/'
    ppm_errorcharter_length = (len(metadata['calls']['proteomics_msgfplus.ppm_errorcharter']))
    # print('- Number of files processed:', ppm_errorcharter_length)

    for x in range(ppm_errorcharter_length):
        # print('\nBlob-', x, ' ', end = '')
        if 'stdout' in metadata['calls']['proteomics_msgfplus.ppm_errorcharter'][x]:
            # STDOUT, which requires to rename the file
            seq_id = metadata['calls']['proteomics_msgfplus.ppm_errorcharter'][x]["inputs"]['sample_id'] 
            ppm_errorcharter_stdout = metadata['calls']['proteomics_msgfplus.ppm_errorcharter'][x]["stdout"]
            ppm_errorcharter_stdout_clean = remove_gsbucket( ppm_errorcharter_stdout, bucket_origin)
            ppm_errorcharter_stdout_rename =  ppm_errorcharter_output  + seq_id + '-ppm_errorcharter-stdout.log'
            print('- Log to:', ppm_errorcharter_stdout_rename)
            blob_stdout = bucket_source.get_blob(ppm_errorcharter_stdout_clean)
            bucket_source.copy_blob(blob_stdout, bucket_destination, ppm_errorcharter_stdout_rename)

        # # Get and upload the command
        if 'commandLine' in metadata['calls']['proteomics_msgfplus.ppm_errorcharter'][x]:
            ppm_errorcharter_cmd = metadata['calls']['proteomics_msgfplus.ppm_errorcharter'][x]["commandLine"]
            # print('The Command line:\n', ppm_errorcharter_cmd)
            cmd_local_file_name = 'command-ppm_errorcharter.txt'
            cmd_blob_filename = ppm_errorcharter_output + cmd_local_file_name
            print('- Command: ', cmd_blob_filename)
            upload_string(bucket_destination, ppm_errorcharter_cmd, cmd_blob_filename)

        executionStatus = remove_gsbucket( metadata['calls']['proteomics_msgfplus.ppm_errorcharter'][x]['executionStatus'], bucket_origin )
        if executionStatus == 'Done':
            ppm_masserror_png = remove_gsbucket( metadata['calls']['proteomics_msgfplus.ppm_errorcharter'][x]['outputs']['ppm_masserror_png'], bucket_origin )
            blob_ppm_masserror_png = bucket_source.get_blob(ppm_masserror_png)
            new_ppm_masserror_png = ppm_errorcharter_output + os.path.basename(ppm_masserror_png)

            ppm_histogram_png = remove_gsbucket( metadata['calls']['proteomics_msgfplus.ppm_errorcharter'][x]['outputs']['ppm_histogram_png'], bucket_origin )
            blob_ppm_histogram_png = bucket_source.get_blob(ppm_histogram_png)
            new_ppm_histogram_png = ppm_errorcharter_output + os.path.basename(ppm_histogram_png)

            print('- File to:', new_ppm_masserror_png)
            print('- File to:', new_ppm_histogram_png)
            bucket_source.copy_blob(blob_ppm_masserror_png, bucket_destination, new_ppm_masserror_png)
            bucket_source.copy_blob(blob_ppm_histogram_png, bucket_destination, new_ppm_histogram_png)
        else:
            print(' (-) Execution Status: ', executionStatus)
            print(' (-) Data cannot be copied')

# WARNING: ID IS COMING FROM THE RAW FILE NAME:
def copy_masic( metadata, dest_root_folder, bucket_source, bucket_origin, bucket_destination):

    masic_output = dest_root_folder + 'masic_outputs/'
    masic_length = (len(metadata['calls']['proteomics_msgfplus.masic']))
    # print('- Number of files processed:', masic_length)

    for x in range(masic_length):
        # print('\nBlob-', x, ' ', end = '')
        if 'stdout' in metadata['calls']['proteomics_msgfplus.masic'][x]:
            # WARNING: ID IS COMING FROM THE RAW FILE NAME:
            seq_id = os.path.basename(metadata['calls']['proteomics_msgfplus.masic'][x]["inputs"]['raw_file']) 
            seq_id = seq_id.replace('.raw', '')
            masic_stdout = metadata['calls']['proteomics_msgfplus.masic'][x]["stdout"]
            masic_stdout_clean = remove_gsbucket( masic_stdout, bucket_origin)
            masic_stdout_rename =  masic_output  + seq_id + '-masic-stdout.log'
            print('- Log to:', masic_stdout_rename)
            blob_stdout = bucket_source.get_blob(masic_stdout_clean)
            bucket_source.copy_blob(blob_stdout, bucket_destination, masic_stdout_rename)

        # Get and upload the command
        if 'commandLine' in metadata['calls']['proteomics_msgfplus.masic'][x]:
            masic_cmd = metadata['calls']['proteomics_msgfplus.masic'][x]["commandLine"]
            # print('The Command line:\n', masic_cmd)
            cmd_local_file_name = 'command-masic.txt'
            cmd_blob_filename = masic_output + cmd_local_file_name
            print('- Command: ', cmd_blob_filename)
            upload_string(bucket_destination, masic_cmd, cmd_blob_filename)

        # masic_output_length = len(metadata['calls']['proteomics_msgfplus.masic'][x]['outputs'])
        # print('(Number of outputs:', masic_output_length, ')')

        executionStatus = remove_gsbucket( metadata['calls']['proteomics_msgfplus.masic'][x]['executionStatus'], bucket_origin )
        if executionStatus == 'Done':
            ReporterIons_output_file = remove_gsbucket( metadata['calls']['proteomics_msgfplus.masic'][x]['outputs']['ReporterIons_output_file'], bucket_origin )
            MSMS_scans_output_file = remove_gsbucket( metadata['calls']['proteomics_msgfplus.masic'][x]['outputs']['MSMS_scans_output_file'], bucket_origin )
            SICs_output_file = remove_gsbucket( metadata['calls']['proteomics_msgfplus.masic'][x]['outputs']['SICs_output_file'], bucket_origin )
            MS_scans_output_file = remove_gsbucket( metadata['calls']['proteomics_msgfplus.masic'][x]['outputs']['MS_scans_output_file'], bucket_origin )
            SICstats_output_file = remove_gsbucket( metadata['calls']['proteomics_msgfplus.masic'][x]['outputs']['SICstats_output_file'], bucket_origin )
            ScanStatsConstant_output_file = remove_gsbucket( metadata['calls']['proteomics_msgfplus.masic'][x]['outputs']['ScanStatsConstant_output_file'], bucket_origin )
            ScanStatsEx_output_file = remove_gsbucket( metadata['calls']['proteomics_msgfplus.masic'][x]['outputs']['ScanStatsEx_output_file'], bucket_origin )
            ScanStats_output_file = remove_gsbucket( metadata['calls']['proteomics_msgfplus.masic'][x]['outputs']['ScanStats_output_file'], bucket_origin )
            DatasetInfo_output_file = remove_gsbucket( metadata['calls']['proteomics_msgfplus.masic'][x]['outputs']['DatasetInfo_output_file'], bucket_origin )

            blob_ReporterIons_output_file = bucket_source.get_blob(ReporterIons_output_file)
            blob_MSMS_scans_output_file = bucket_source.get_blob(MSMS_scans_output_file)
            blob_SICs_output_file = bucket_source.get_blob(SICs_output_file)
            blob_MS_scans_output_file = bucket_source.get_blob(MS_scans_output_file)
            blob_SICstats_output_file = bucket_source.get_blob(SICstats_output_file)
            blob_ScanStatsConstant_output_file = bucket_source.get_blob(ScanStatsConstant_output_file)
            blob_ScanStatsEx_output_file = bucket_source.get_blob(ScanStatsEx_output_file)
            blob_ScanStats_output_file = bucket_source.get_blob(ScanStats_output_file)
            blob_DatasetInfo_output_file = bucket_source.get_blob(DatasetInfo_output_file)

            new_ReporterIons_output_file = masic_output + os.path.basename(ReporterIons_output_file)
            new_MSMS_scans_output_file = masic_output + os.path.basename(MSMS_scans_output_file)
            new_SICs_output_file = masic_output + os.path.basename(SICs_output_file)
            new_MS_scans_output_file = masic_output + os.path.basename(MS_scans_output_file)
            new_SICstats_output_file = masic_output + os.path.basename(SICstats_output_file)
            new_ScanStatsConstant_output_file = masic_output + os.path.basename(ScanStatsConstant_output_file)
            new_ScanStatsEx_output_file = masic_output + os.path.basename(ScanStatsEx_output_file)
            new_ScanStats_output_file = masic_output + os.path.basename(ScanStats_output_file)
            new_DatasetInfo_output_file = masic_output + os.path.basename(DatasetInfo_output_file)

            # COPY FILES TO NEW LOCATION
            print('- File to:', new_ReporterIons_output_file)
            print('- File to:', new_MSMS_scans_output_file)
            print('- File to:', new_SICs_output_file)
            print('- File to:', new_MS_scans_output_file)
            print('- File to:', new_SICstats_output_file)
            print('- File to:', new_ScanStatsConstant_output_file)
            print('- File to:', new_ScanStatsEx_output_file)
            print('- File to:', new_ScanStats_output_file)
            print('- File to:', new_DatasetInfo_output_file)

            bucket_source.copy_blob(blob_ReporterIons_output_file, bucket_destination, new_ReporterIons_output_file)
            bucket_source.copy_blob(blob_MSMS_scans_output_file, bucket_destination, new_MSMS_scans_output_file)
            bucket_source.copy_blob(blob_SICs_output_file, bucket_destination, new_SICs_output_file)
            bucket_source.copy_blob(blob_MS_scans_output_file, bucket_destination, new_MS_scans_output_file)
            bucket_source.copy_blob(blob_SICstats_output_file, bucket_destination, new_SICstats_output_file)
            bucket_source.copy_blob(blob_ScanStatsConstant_output_file, bucket_destination, new_ScanStatsConstant_output_file)
            bucket_source.copy_blob(blob_ScanStatsEx_output_file, bucket_destination, new_ScanStatsEx_output_file)
            bucket_source.copy_blob(blob_ScanStats_output_file, bucket_destination, new_ScanStats_output_file)
            bucket_source.copy_blob(blob_DatasetInfo_output_file, bucket_destination, new_DatasetInfo_output_file)
        else:
            print(' (-) Execution Status: ', executionStatus)
            print(' (-) Data cannot be copied')


# Copy msconvert results to the same or different bucket
def copy_msconvert( metadata, dest_root_folder, bucket_source, bucket_origin, bucket_destination):

    msconvert_output = dest_root_folder + 'msconvert_outputs/'
    msconvert_length = (len(metadata['calls']['proteomics_msgfplus.msconvert']))
    # print('- Number of files processed:', msconvert_length)

    for x in range(msconvert_length):
        # print('\nBlob-', x, ' ', end = '')
        if 'stdout' in metadata['calls']['proteomics_msgfplus.msconvert'][x]:
            seq_id = os.path.basename(metadata['calls']['proteomics_msgfplus.msconvert'][x]["inputs"]['raw_file']) 
            # print("seq_id ", seq_id)
            seq_id = seq_id.replace('.raw', '')
            # print("seq_id ", seq_id)
            msconvert_stdout = metadata['calls']['proteomics_msgfplus.msconvert'][x]["stdout"]
            # print("msconvert_stdout", msconvert_stdout)
            msconvert_stdout_clean = remove_gsbucket( msconvert_stdout, bucket_origin)
            msconvert_stdout_rename =  msconvert_output  + seq_id + '-msconvert-stdout.log'
            blob_stdout = bucket_source.get_blob(msconvert_stdout_clean)
            print('- Log to:', msconvert_stdout_rename)
            if not blob_stdout is None:
                bucket_source.copy_blob(blob_stdout, bucket_destination, msconvert_stdout_rename)
            else:
                print('WARNING: stdout blob available in metadata file, but not available in bucket')

        # Get and upload the command
        if 'commandLine' in metadata['calls']['proteomics_msgfplus.msconvert'][x]:
            msconvert_cmd = metadata['calls']['proteomics_msgfplus.msconvert'][x]["commandLine"]
            # print('The Command line:\n', msconvert_cmd)
            cmd_local_file_name = 'command-msconvert.txt'
            cmd_blob_filename = msconvert_output + cmd_local_file_name
            print('- Command: ', cmd_blob_filename)
            upload_string(bucket_destination, msconvert_cmd, cmd_blob_filename)

        # msconvert_output_length = len(metadata['calls']['proteomics_msgfplus.msconvert'][x]['outputs'])
        # print(' (number of outputs:', msconvert_output_length, ')')

        executionStatus = remove_gsbucket( metadata['calls']['proteomics_msgfplus.msconvert'][x]['executionStatus'], bucket_origin )
        if executionStatus == 'Done':
            mzml = remove_gsbucket( metadata['calls']['proteomics_msgfplus.msconvert'][x]['outputs']['mzml'], bucket_origin )
            # print('mzml:', mzml)
            blob_mzml = bucket_source.get_blob(mzml)
            new_mzml = msconvert_output + os.path.basename(mzml)

            print('- File to:', new_mzml)
            bucket_source.copy_blob(blob_mzml, bucket_destination, new_mzml)
        else:
            print(' (-) Execution Status: ', executionStatus)
            print(' (-) Data cannot be copied')

def copy_msgf_identification( metadata, dest_root_folder, bucket_source, bucket_origin, bucket_destination):

    msgf_identification_output = dest_root_folder + 'msgf_identification_outputs/'
    msgf_identification_length = (len(metadata['calls']['proteomics_msgfplus.msgf_identification']))
    # print('- Number of files processed:', msgf_identification_length)

    for x in range(msgf_identification_length):
        # print('\nBlob-', x, ' ', end = '')
        if 'stdout' in metadata['calls']['proteomics_msgfplus.msgf_identification'][x]:
            # STDOUT, which requires to rename the file
            seq_id = metadata['calls']['proteomics_msgfplus.msgf_identification'][x]["inputs"]['sample_id'] 
            msgf_identification_stdout = metadata['calls']['proteomics_msgfplus.msgf_identification'][x]["stdout"]
            msgf_identification_stdout_clean = remove_gsbucket( msgf_identification_stdout, bucket_origin)
            msgf_identification_stdout_rename =  msgf_identification_output  + seq_id + '-msgf_identification-stdout.log'
            print('- Log to:', msgf_identification_stdout_rename)
            blob_stdout = bucket_source.get_blob(msgf_identification_stdout_clean)
            bucket_source.copy_blob(blob_stdout, bucket_destination, msgf_identification_stdout_rename)

        # # Get and upload the command
        if 'commandLine' in metadata['calls']['proteomics_msgfplus.msgf_identification'][x]:
            msgf_identification_cmd = metadata['calls']['proteomics_msgfplus.msgf_identification'][x]["commandLine"]
            # print('The Command line:\n', msgf_identification_cmd)
            cmd_local_file_name = 'command-msgf_identification.txt'
            cmd_blob_filename = msgf_identification_output + cmd_local_file_name
            print('- Command: ', cmd_blob_filename)
            upload_string(bucket_destination, msgf_identification_cmd, cmd_blob_filename)

        executionStatus = remove_gsbucket( metadata['calls']['proteomics_msgfplus.msgf_identification'][x]['executionStatus'], bucket_origin )
        if executionStatus == 'Done':
            rename_mzmlfixed = remove_gsbucket( metadata['calls']['proteomics_msgfplus.msgf_identification'][x]['outputs']['rename_mzmlfixed'], bucket_origin )
            blob_rename_mzmlfixed = bucket_source.get_blob(rename_mzmlfixed)
            new_rename_mzmlfixed = msgf_identification_output + os.path.basename(rename_mzmlfixed)

            mzid_final = remove_gsbucket( metadata['calls']['proteomics_msgfplus.msgf_identification'][x]['outputs']['mzid_final'], bucket_origin )
            blob_mzid_final = bucket_source.get_blob(mzid_final)
            new_mzid_final = msgf_identification_output + os.path.basename(mzid_final)

            print('- File to:', new_rename_mzmlfixed)
            print('- File to:', new_mzid_final)
            bucket_source.copy_blob(blob_rename_mzmlfixed, bucket_destination, new_rename_mzmlfixed)
            bucket_source.copy_blob(blob_mzid_final, bucket_destination, new_mzid_final)
        else:
            print(' (-) Execution Status: ', executionStatus)
            print(' (-) Data cannot be copied')

# Copy msgf_sequences results to the same or different bucket
def copy_msgf_sequences( metadata, dest_root_folder, bucket_source, bucket_origin, bucket_destination):

    msgf_sequences_output = dest_root_folder + 'msgf_sequences_outputs/'
    msgf_sequences_length = (len(metadata['calls']['proteomics_msgfplus.msgf_sequences']))
    # print('- Number of files processed:', msgf_sequences_length)

    for x in range(msgf_sequences_length):
        # print('\nBlob-', x, ' ', end = '')
        # # UNFORTUNATELY THE STDOUT HERE IS WRONG! It is listed as available but then the file is not available on GCP
        # if 'stdout' in metadata['calls']['proteomics_msgfplus.msgf_sequences'][x]:
        #     seq_id = os.path.basename(metadata['calls']['proteomics_msgfplus.msgf_sequences'][x]["inputs"]['seq_file_id']) 
        #     msgf_sequences_stdout = metadata['calls']['proteomics_msgfplus.msgf_sequences'][x]["stdout"]
        #     msgf_sequences_stdout_clean = remove_gsbucket( msgf_sequences_stdout, bucket_origin)
        #     msgf_sequences_stdout_rename =  msgf_sequences_output  + seq_id + '-msgf_sequences-stdout.log'
        #     print('- Log to:', msgf_sequences_stdout_rename)
        #     blob_stdout = bucket_source.get_blob(msgf_sequences_stdout_clean)
        #     bucket_source.copy_blob(blob_stdout, bucket_destination, msgf_sequences_stdout_rename)

        # # Get and upload the command
        if 'commandLine' in metadata['calls']['proteomics_msgfplus.msgf_sequences'][x]:
            msgf_sequences_cmd = metadata['calls']['proteomics_msgfplus.msgf_sequences'][x]["commandLine"]
            # print('The Command line:\n', msgf_sequences_cmd)
            cmd_local_file_name = 'command-msgf_sequences.txt'
            cmd_blob_filename = msgf_sequences_output + cmd_local_file_name
            print('- Command: ', cmd_blob_filename)
            upload_string(bucket_destination, msgf_sequences_cmd, cmd_blob_filename)

        executionStatus = remove_gsbucket( metadata['calls']['proteomics_msgfplus.msgf_sequences'][x]['executionStatus'], bucket_origin )
        if executionStatus == 'Done':
            revcat_fasta = remove_gsbucket( metadata['calls']['proteomics_msgfplus.msgf_sequences'][x]['outputs']['revcat_fasta'], bucket_origin )
            blob_revcat_fasta = bucket_source.get_blob(revcat_fasta)
            new_revcat_fasta = msgf_sequences_output + os.path.basename(revcat_fasta)

            sequencedb_files = remove_gsbucket( metadata['calls']['proteomics_msgfplus.msgf_sequences'][x]['outputs']['sequencedb_files'], bucket_origin )
            blob_sequencedb_files = bucket_source.get_blob(sequencedb_files)
            new_sequencedb_files = msgf_sequences_output + os.path.basename(sequencedb_files)

            print('- File to:', new_revcat_fasta)
            print('- File to:', new_sequencedb_files)
            bucket_source.copy_blob(blob_revcat_fasta, bucket_destination, new_revcat_fasta)
            bucket_source.copy_blob(blob_sequencedb_files, bucket_destination, new_sequencedb_files)
        else:
            print(' (-) Execution Status: ', executionStatus)
            print(' (-) Data cannot be copied')

# Copy msgf_tryptic results to the same or different bucket
def copy_msgf_tryptic( metadata, dest_root_folder, bucket_source, bucket_origin, bucket_destination):

    msgf_tryptic_output = dest_root_folder + 'msgf_tryptic_outputs/'
    msgf_tryptic_length = (len(metadata['calls']['proteomics_msgfplus.msgf_tryptic']))
    # print('- Number of files processed:', msgf_tryptic_length)

    for x in range(msgf_tryptic_length):
        # print('\nBlob-', x, ' ', end = '')
        
        # STDOUT, which requires to rename the file
        if 'stdout' in metadata['calls']['proteomics_msgfplus.msgf_tryptic'][x]:
            seq_id = metadata['calls']['proteomics_msgfplus.msconvert_mzrefiner'][x]["inputs"]['sample_id'] 
            msgf_tryptic_stdout = metadata['calls']['proteomics_msgfplus.msgf_tryptic'][x]["stdout"]
            msgf_tryptic_stdout_clean = remove_gsbucket( msgf_tryptic_stdout, bucket_origin)
            msgf_tryptic_stdout_rename =  msgf_tryptic_output  + seq_id + '-msgf_tryptic-stdout.log'
            print('- Log to:', msgf_tryptic_stdout_rename)
            blob_stdout = bucket_source.get_blob(msgf_tryptic_stdout_clean)
            bucket_source.copy_blob(blob_stdout, bucket_destination, msgf_tryptic_stdout_rename)

        # # Get and upload the command
        if 'commandLine' in metadata['calls']['proteomics_msgfplus.msgf_tryptic'][x]:
            msgf_tryptic_cmd = metadata['calls']['proteomics_msgfplus.msgf_tryptic'][x]["commandLine"]
            # print('The Command line:\n', msgf_tryptic_cmd)
            cmd_local_file_name = 'command-msgf_tryptic.txt'
            cmd_blob_filename = msgf_tryptic_output + cmd_local_file_name
            print('- Command: ', cmd_blob_filename)
            upload_string(bucket_destination, msgf_tryptic_cmd, cmd_blob_filename)

        # msgf_tryptic_output_length = len(metadata['calls']['proteomics_msgfplus.msgf_tryptic'][x]['outputs'])
        # print(' (number of outputs:', msgf_tryptic_output_length, ')')

        executionStatus = remove_gsbucket( metadata['calls']['proteomics_msgfplus.msgf_tryptic'][x]['executionStatus'], bucket_origin )
        if executionStatus == 'Done':
            mzid = remove_gsbucket( metadata['calls']['proteomics_msgfplus.msgf_tryptic'][x]['outputs']['mzid'], bucket_origin )
            blob_mzid = bucket_source.get_blob(mzid)
            new_mzid = msgf_tryptic_output + os.path.basename(mzid)

            print('- File to:', new_mzid)
            bucket_source.copy_blob(blob_mzid, bucket_destination, new_mzid)
        else:
            print(' (-) Execution Status: ', executionStatus)
            print(' (-) Data cannot be copied')

########################################################################
# WARNING TO DO: THERE MIGHT BE AN EXTRA OUTPUT TO BE ADDED: phrp_log_file
########################################################################
def copy_phrp( metadata, dest_root_folder, bucket_source, bucket_origin, bucket_destination):

    phrp_output = dest_root_folder + 'phrp_outputs/'
    phrp_length = (len(metadata['calls']['proteomics_msgfplus.phrp']))
    # print('- Number of files processed:', phrp_length)

    for x in range(phrp_length):
        # print('\nBlob-', x, ' ', end = '')
        if 'stdout' in metadata['calls']['proteomics_msgfplus.phrp'][x]:
            # WARNING: ID IS COMING FROM THE RAW FILE NAME:
            seq_id = os.path.basename(metadata['calls']['proteomics_msgfplus.phrp'][x]["inputs"]['input_tsv']) 
            seq_id = seq_id.replace('.tsv', '')
            phrp_stdout = metadata['calls']['proteomics_msgfplus.phrp'][x]["stdout"]
            phrp_stdout_clean = remove_gsbucket( phrp_stdout, bucket_origin)
            phrp_stdout_rename =  phrp_output  + seq_id + '-phrp-stdout.log'
            print('- Log to:', phrp_stdout_rename)
            blob_stdout = bucket_source.get_blob(phrp_stdout_clean)
            bucket_source.copy_blob(blob_stdout, bucket_destination, phrp_stdout_rename)

        # Get and upload the command
        if 'commandLine' in metadata['calls']['proteomics_msgfplus.phrp'][x]:
            phrp_cmd = metadata['calls']['proteomics_msgfplus.phrp'][x]["commandLine"]
            # print('The Command line:\n', phrp_cmd)
            cmd_local_file_name = 'command-phrp.txt'
            cmd_blob_filename = phrp_output + cmd_local_file_name
            print('- Command: ', cmd_blob_filename)
            upload_string(bucket_destination, phrp_cmd, cmd_blob_filename)

        # phrp_output_length = len(metadata['calls']['proteomics_msgfplus.phrp'][x]['outputs'])
        # print('(Number of outputs:', phrp_output_length, ')')

        executionStatus = remove_gsbucket( metadata['calls']['proteomics_msgfplus.phrp'][x]['executionStatus'], bucket_origin )
        if executionStatus == 'Done':
            syn_ResultToSeqMap = remove_gsbucket( metadata['calls']['proteomics_msgfplus.phrp'][x]['outputs']['syn_ResultToSeqMap'], bucket_origin )
            fht = remove_gsbucket( metadata['calls']['proteomics_msgfplus.phrp'][x]['outputs']['fht'], bucket_origin )
            PepToProtMapMTS = remove_gsbucket( metadata['calls']['proteomics_msgfplus.phrp'][x]['outputs']['PepToProtMapMTS'], bucket_origin )
            syn_ProteinMods = remove_gsbucket( metadata['calls']['proteomics_msgfplus.phrp'][x]['outputs']['syn_ProteinMods'], bucket_origin )
            syn_SeqToProteinMap = remove_gsbucket( metadata['calls']['proteomics_msgfplus.phrp'][x]['outputs']['syn_SeqToProteinMap'], bucket_origin )
            syn = remove_gsbucket( metadata['calls']['proteomics_msgfplus.phrp'][x]['outputs']['syn'], bucket_origin )
            syn_ModSummary = remove_gsbucket( metadata['calls']['proteomics_msgfplus.phrp'][x]['outputs']['syn_ModSummary'], bucket_origin )
            syn_SeqInfo = remove_gsbucket( metadata['calls']['proteomics_msgfplus.phrp'][x]['outputs']['syn_SeqInfo'], bucket_origin )
            syn_ModDetails = remove_gsbucket( metadata['calls']['proteomics_msgfplus.phrp'][x]['outputs']['syn_ModDetails'], bucket_origin )

            blob_syn_ResultToSeqMap = bucket_source.get_blob(syn_ResultToSeqMap)
            blob_fht = bucket_source.get_blob(fht)
            blob_PepToProtMapMTS = bucket_source.get_blob(PepToProtMapMTS)
            blob_syn_ProteinMods = bucket_source.get_blob(syn_ProteinMods)
            blob_syn_SeqToProteinMap = bucket_source.get_blob(syn_SeqToProteinMap)
            blob_syn = bucket_source.get_blob(syn)
            blob_syn_ModSummary = bucket_source.get_blob(syn_ModSummary)
            blob_syn_SeqInfo = bucket_source.get_blob(syn_SeqInfo)
            blob_syn_ModDetails = bucket_source.get_blob(syn_ModDetails)

            new_syn_ResultToSeqMap = phrp_output + os.path.basename(syn_ResultToSeqMap)
            new_fht = phrp_output + os.path.basename(fht)
            new_PepToProtMapMTS = phrp_output + os.path.basename(PepToProtMapMTS)
            new_syn_ProteinMods = phrp_output + os.path.basename(syn_ProteinMods)
            new_syn_SeqToProteinMap = phrp_output + os.path.basename(syn_SeqToProteinMap)
            new_syn = phrp_output + os.path.basename(syn)
            new_syn_ModSummary = phrp_output + os.path.basename(syn_ModSummary)
            new_syn_SeqInfo = phrp_output + os.path.basename(syn_SeqInfo)
            new_syn_ModDetails = phrp_output + os.path.basename(syn_ModDetails)

            print('- File to:', new_syn_ResultToSeqMap)
            print('- File to:', new_fht)
            print('- File to:', new_PepToProtMapMTS)
            print('- File to:', new_syn_ProteinMods)
            print('- File to:', new_syn_SeqToProteinMap)
            print('- File to:', new_syn)
            print('- File to:', new_syn_ModSummary)
            print('- File to:', new_syn_SeqInfo)
            print('- File to:', new_syn_ModDetails)

            bucket_source.copy_blob(blob_syn_ResultToSeqMap, bucket_destination, new_syn_ResultToSeqMap)
            bucket_source.copy_blob(blob_fht, bucket_destination, new_fht)
            bucket_source.copy_blob(blob_PepToProtMapMTS, bucket_destination, new_PepToProtMapMTS)
            bucket_source.copy_blob(blob_syn_ProteinMods, bucket_destination, new_syn_ProteinMods)
            bucket_source.copy_blob(blob_syn_SeqToProteinMap, bucket_destination, new_syn_SeqToProteinMap)
            bucket_source.copy_blob(blob_syn, bucket_destination, new_syn)
            bucket_source.copy_blob(blob_syn_ModSummary, bucket_destination, new_syn_ModSummary)
            bucket_source.copy_blob(blob_syn_SeqInfo, bucket_destination, new_syn_SeqInfo)
            bucket_source.copy_blob(blob_syn_ModDetails, bucket_destination, new_syn_ModDetails)
        else:
            print(' (-) Execution Status: ', executionStatus)
            print(' (-) Data cannot be copied')


# Copy mzidtotsvconverter results to the same or different bucket
def copy_mzidtotsvconverter( metadata, dest_root_folder, bucket_source, bucket_origin, bucket_destination):

    mzidtotsvconverter_output = dest_root_folder + 'mzidtotsvconverter_outputs/'
    mzidtotsvconverter_length = (len(metadata['calls']['proteomics_msgfplus.mzidtotsvconverter']))
    # print('- Number of files processed:', mzidtotsvconverter_length)

    for x in range(mzidtotsvconverter_length):
        # print('\nBlob-', x, ' ', end = '')
        if 'stdout' in metadata['calls']['proteomics_msgfplus.mzidtotsvconverter'][x]:
            seq_id = metadata['calls']['proteomics_msgfplus.mzidtotsvconverter'][x]["inputs"]['sample_id'] 
            mzidtotsvconverter_stdout = metadata['calls']['proteomics_msgfplus.mzidtotsvconverter'][x]["stdout"]
            mzidtotsvconverter_stdout_clean = remove_gsbucket( mzidtotsvconverter_stdout, bucket_origin)
            mzidtotsvconverter_stdout_rename =  mzidtotsvconverter_output  + seq_id + '-mzidtotsvconverter-stdout.log'
            print('- Log to:', mzidtotsvconverter_stdout_rename)
            blob_stdout = bucket_source.get_blob(mzidtotsvconverter_stdout_clean)
            bucket_source.copy_blob(blob_stdout, bucket_destination, mzidtotsvconverter_stdout_rename)
        
        # mzidtotsvconverter_output_length = len(metadata['calls']['proteomics_msgfplus.mzidtotsvconverter'][x]['outputs'])
        # print(' (number of outputs:', mzidtotsvconverter_output_length, ')')

        if 'commandLine' in metadata['calls']['proteomics_msgfplus.mzidtotsvconverter'][x]:
            # Get and upload the command
            mzidtotsvconverter_cmd = metadata['calls']['proteomics_msgfplus.mzidtotsvconverter'][x]["commandLine"]
            # print('The Command line:\n', mzidtotsvconverter_cmd)
            cmd_local_file_name = 'command-mzidtotsvconverter.txt'
            cmd_blob_filename = mzidtotsvconverter_output + cmd_local_file_name
            print('- Command: ', cmd_blob_filename)
            upload_string(bucket_destination, mzidtotsvconverter_cmd, cmd_blob_filename)

        executionStatus = remove_gsbucket( metadata['calls']['proteomics_msgfplus.mzidtotsvconverter'][x]['executionStatus'], bucket_origin )
        if executionStatus == 'Done':
            tsv = remove_gsbucket( metadata['calls']['proteomics_msgfplus.mzidtotsvconverter'][x]['outputs']['tsv'], bucket_origin )
            blob_tsv = bucket_source.get_blob(tsv)
            new_tsv = mzidtotsvconverter_output + os.path.basename(tsv)
            
            print('- File to:', new_tsv)
            bucket_source.copy_blob(blob_tsv, bucket_destination, new_tsv)
        else:
            print(' (-) Execution Status: ', executionStatus)
            print(' (-) Data cannot be copied')

# Copy wrapper_pp results to the same or different bucket
def copy_wrapper_pp( metadata, dest_root_folder, bucket_source, bucket_origin, bucket_destination):

    wrapper_results_output = dest_root_folder + 'wrapper_results/'

    # Check whether isPTM
    is_ptm = metadata['inputs']['proteomics_msgfplus.isPTM']

    wrapper_method = ""

    if is_ptm:
        ptm_type = metadata['inputs']['proteomics_msgfplus.isPTM']
        print("+ PTM proteomics experiment: ", ptm_type)
        wrapper_method = "proteomics_msgfplus.wrapper_pp_ptm"
    else:
        print("+ Global proteomics experiment results")
        wrapper_method = "proteomics_msgfplus.wrapper_pp"

    if not wrapper_method in metadata['calls']:
        print('(-) Plexed piper not available')
        return None

    wrapper_results_length = (len(metadata['calls'][wrapper_method]))

    for x in range(wrapper_results_length):
        # print('\nBlob-', x, ' ', end = '')

        if 'stdout' in metadata['calls'][wrapper_method][x]:
            wrapper_results_stdout = metadata['calls'][wrapper_method][x]["stdout"]
            wrapper_results_stdout_clean = remove_gsbucket( wrapper_results_stdout, bucket_origin)
            wrapper_results_stdout_rename =  wrapper_results_output  + 'wrapper_results-stdout.log'
            print('- Log to:', wrapper_results_stdout_rename)
            blob_stdout = bucket_source.get_blob(wrapper_results_stdout_clean)
            bucket_source.copy_blob(blob_stdout, bucket_destination, wrapper_results_stdout_rename)
        
        # wrapper_results_output_length = len(metadata['calls'][wrapper_method][x]['outputs'])
        # print('(Number of outputs:', wrapper_results_output_length, ')')
        
        if 'commandLine' in metadata['calls'][wrapper_method][x]:
            wrapper_results_cmd = metadata['calls'][wrapper_method][x]["commandLine"]
            # print('The Command line:\n', wrapper_results_cmd)
            cmd_local_file_name = 'command-wrapper_results.txt'
            cmd_blob_filename = wrapper_results_output + cmd_local_file_name
            print('- Command: ', cmd_blob_filename)
            upload_string(bucket_destination, wrapper_results_cmd, cmd_blob_filename)

        executionStatus = remove_gsbucket( metadata['calls'][wrapper_method][x]['executionStatus'], bucket_origin )
        if executionStatus == 'Done':
            results_ratio = remove_gsbucket( metadata['calls'][wrapper_method][x]['outputs']['results_ratio'], bucket_origin )
            results_rii = remove_gsbucket( metadata['calls'][wrapper_method][x]['outputs']['results_rii'], bucket_origin )

            blob_results_ratio = bucket_source.get_blob(results_ratio)
            blob_results_rii = bucket_source.get_blob(results_rii)

            new_results_ratio = wrapper_results_output + os.path.basename(results_ratio)
            new_results_rii = wrapper_results_output + os.path.basename(results_rii)

            print('- File to:', new_results_ratio)
            print('- File to:', new_results_rii)
            bucket_source.copy_blob(blob_results_ratio, bucket_destination, new_results_ratio)
            bucket_source.copy_blob(blob_results_rii, bucket_destination, new_results_rii)
        else:
            print(' (-) Execution Status: ', executionStatus)
            print(' (-) Data cannot be copied')

def arg_parser():
    parser = argparse.ArgumentParser(description='Copy proteomics pipeline output files to a desire location')
    parser.add_argument('-p', '--project', required=True, type=str, help='GCP project name. Required.')
    parser.add_argument('-b', '--bucket_origin', required=True, type=str, help='Bucket with output files. Required.')
    parser.add_argument('-d', '--bucket_destination_name', required=False, type=str, help='Bucket to copy file. Not Required. Default: same as bucket_origin).')
    parser.add_argument('-r', '--results_location_path', required=True, type=str, help='Path to the pipeline results. Required (e.g. results/proteomics_msgfplus/9c6ff6fe-ce7d-4d23-ac18-9935614d6f9b)')
    parser.add_argument('-o', '--dest_root_folder', required=True, help='Folder path to copy the files. Required (e.g. test/results/input_test_gcp_s6-global-2files-8/)')
    return parser


def main():
    parser = arg_parser()
    args = parser.parse_args()
    
    print('')

    project_name = args.project
    print('GCP project:', project_name)

    bucket_origin = args.bucket_origin
    print('Bucket origin:', bucket_origin)

    bucket_destination_name = args.bucket_destination_name
    if args.bucket_destination_name is None:
        print("Bucket destination: --bucket_destination_name (-d) is empty. Same as original will be used (", bucket_origin, ")")
        bucket_destination_name = bucket_origin
    else:
        print('Bucket destination: ', bucket_destination_name)

    print('\nOPTIONS:\n')

    results_location_path = args.results_location_path
    print('+ Copy files from:',results_location_path)

    dest_root_folder = args.dest_root_folder
    if not dest_root_folder.endswith("/"):
        dest_root_folder = dest_root_folder + "/"
    
    print('+ Copy files to: ', dest_root_folder)
    
    storage_client = storage.Client(project_name)
    bucket_source = storage_client.get_bucket(bucket_origin)
    bucket_destination = storage_client.get_bucket(bucket_destination_name)

    bucket_content_list = storage_client.list_blobs(bucket_origin, prefix = results_location_path)

    # Get and load the metadata.json file
    for blob in bucket_content_list:
        here = blob.name
        #print(type(here))
        #print(here) 
        reg = re.compile("(.*.metadata.json)")
        m = reg.match(here)
        if m:
            print('\nMetadata file location: ', m[1])
            metadata = json.loads(blob.download_as_string(client=None))
            #print(json.dumps(metadata, sort_keys=True, indent=4))

    start_time = dateparser.parse(metadata['start'])
    end_time = dateparser.parse(metadata['end'])

    print('\nPipeline Running Time: ',end_time - start_time)

    if 'inputs' in metadata:
        is_ptm = metadata['inputs']['proteomics_msgfplus.isPTM']
        if is_ptm:
            print('\n######## PTM PROTEOMICS EXPERIMENT ########\n')
        else:
            print('\n######## GLOBAL PROTEIN ABUNDANCE EXPERIMENT ########\n')

    if 'proteomics_msgfplus.ascore' in metadata['calls']:
        print('\nASCORE OUTPUTS--------------------------------------\n')
        copy_ascore( metadata, dest_root_folder, bucket_source, bucket_origin, bucket_destination)

    print('\nMSCONVERT_MZREFINER OUTPUTS-----------------------------\n')
    copy_msconvert_mzrefiner( metadata, dest_root_folder, bucket_source, bucket_origin, bucket_destination)

    print('\nPPMErrorCharter (ppm_errorcharter)------------------------\n')
    copy_ppm_errorcharter( metadata, dest_root_folder, bucket_source, bucket_origin, bucket_destination)

    print('\nMASIC OUTPUTS-------------------------------------------\n')
    copy_masic( metadata, dest_root_folder, bucket_source, bucket_origin, bucket_destination)

    print('\nMSCONVERT OUTPUTS---------------------------------------\n')
    copy_msconvert( metadata, dest_root_folder, bucket_source, bucket_origin, bucket_destination)

    print('\nMSGF_IDENTIFICATION OUTPUTS-----------------------------\n')
    copy_msgf_identification( metadata, dest_root_folder, bucket_source, bucket_origin, bucket_destination)

    print('\nMSGF_SEQUENCES OUTPUTS----------------------------------\n')
    copy_msgf_sequences( metadata, dest_root_folder, bucket_source, bucket_origin, bucket_destination)

    print('\nMSGF_TRYPTIC OUTPUTS------------------------------------\n')
    copy_msgf_tryptic( metadata, dest_root_folder, bucket_source, bucket_origin, bucket_destination)

    print('\nPHRP OUTPUTS--------------------------------------------\n')
    copy_phrp( metadata, dest_root_folder, bucket_source, bucket_origin, bucket_destination)

    print('\nMZID to TSV CONVERTER OUTPUTS---------------------------\n')
    copy_mzidtotsvconverter( metadata, dest_root_folder, bucket_source, bucket_origin, bucket_destination)

    print('\nWRAPPER: PlexedPiper output-------------------------------\n')
    copy_wrapper_pp( metadata, dest_root_folder, bucket_source, bucket_origin, bucket_destination)

    print('\n')

if __name__ == "__main__":
    main()
