# MoTrPAC Proteomics Pipeline

***MoTrPAC Proteomics Data Analysis Pipeline***

## Overview

This mass-spectrometry based-proteomics data analysis pipeline uses the programming language [WDL](https://openwdl.org/) for describing workflows. The pipeline is run using [caper](https://github.com/ENCODE-DCC/caper), a wrapper Python package for using the workflow management system [Cromwell](https://github.com/broadinstitute/cromwell). It currently supports two different software for the peptide identication and quantification: MSGF+ and MaxQuant.

## Details

### Proteomics Pipelines

Two different software/pipelines are currently supported for the peptide identification and quantification:

- MS-GF+ pipeline: it uses [MASIC](https://github.com/PNNL-Comp-Mass-Spec/MASIC) to extract reporter ion peaks from MS2 spectra and create selected ion chromatograms for each MS/MS parent ion, and [MS-GF+](https://github.com/MSGFPlus/msgfplus) for the peptide identification. Details of the pipeline can be found [here](docs/readme_msgfplus-details.md). All MoTrPAC datasets are analyzed with this pipeline
- [MaxQuant](https://www.maxquant.org/): a quantitative proteomics software package designed for analyzing large mass-spectrometric data sets. Originally developed for running only on Windows operating system, recent updates allows the [execution on Linux platforms](https://www.nature.com/articles/s41592-018-0018-y). The user must download and accept the terms on their local computers to generate the required configuration file, that will be used to run MaxQuant on the cloud, increasing speed and performance.

### GCP set-up

The WDL/Cromwell framework is optimized to run pipelines in high-performance computing environments. The MoTrPAC Bioinformatics Center runs pipelines on Google Cloud Platform (GCP). We used a number of fantastic tools developed by our colleagues from the [ENCODE project](https://github.com/ENCODE-DCC) to run pipelines on GCP (and other HPC platforms).

A brief summary of the steps to set-up a VM to run the Motrpac pipelines on GCP (**for details, please, check the [caper repo](https://github.com/ENCODE-DCC/caper/blob/master/scripts/gcp_caper_server/README.md)**):
- Create a GCP account.
- Enable cloud APIs. 
- Install the [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) (Software Development Kit) on your local machine.    
- Create a service account and download the key file to your local computer (e.g  “`service-account-191919.json`”)
- Create a bucket for pipeline inputs and outputs (e.g. gs://pipelines/). Note: a GCP bucket is similar to a folder on your computer or a storage unit, but it is stored on Google's servers in the cloud instead of on your local computer.
- Set up a VM on GCP: create a Virtual Machine (VM) instance from where the pipelines will be run. We recommend the script available in the [caper repo](https://github.com/ENCODE-DCC/caper). For that, clone the repo on your local machine and run the following command:

```
$ bash create_instance.sh [INSTANCE_NAME] [PROJECT_ID] [GCP_SERVICE_ACCOUNT_KEY_JSON_FILE] [GCP_OUT_DIR]

# Example for the pipeline:
./create_instance.sh pipeline-instance your-gcp-project-name service-account-191919.json gs://pipelines/results/
```

- Install [`gcsfuse`](https://github.com/GoogleCloudPlatform/gcsfuse) to mount the bucket on the VM. To mount the bucket on the VM run:

```
gcsfuse --implicit-dirs pipelines pipelines
```

- Finally, clone this repo

### Software / Dockerfiles

Several software packages are required to run the proteomics pipelines. All of them are pre-installed in docker containers, which are publicly available in the [Artifact Registry](https://cloud.google.com/artifact-registry). To find out more about this containers, check the [readme](dockerfiles/docker_readme.md)


### Parameters

Each step of the MSGF+ pipeline has a parameter file with multiple options. The default options are recommended, but users can adjust them. The final parameter folder must be copied to the pipeline  bucket (`gs://pipeline/parameters`)


### Configuration files

A configuration file (in JSON format) is required to analyze a particular dataset in the pipeline. This configuration file contains several key-value pairs that specify the inputs and outputs of the workflow, the location of the input files, pipeline paramenters, sequence database, docker containers, the execution environment, and other parameters needed for execution. 

The optimal way to generate the configuration files is to run  the `create_config_[software].py` script. [Check this link to find out more](scripts/scripts_readme.md). 

### Run the pipeline

Connect to the VM and submit a job by running the command:

```
caper run motrpac-proteomics-pipeline/wdl/proteomics_msgfplus.wdl -i pipeline/config-file.json
```

and check job status by running:

```
caper list
```

### Other utilities

A number of scripts are available in this repo providing additional functionality to interact with GCP. Please, [check this file](scripts/scripts_readme.md) to find out more. 
