# MoTrPAC Proteomics Pipeline

***MoTrPAC Proteomics Data Analysis Pipeline***

---

# Overview

WDL implementation of a MS-GF+ based proteomics data analysis pipeline based on a pipeline language ([WDL](https://openwdl.org/)) and tools that orchestrate the execution (`caper`/`crownwell`). A prototype version of this pipeline with the details of every step can be found in this [repository](https://github.com/AshleyLab/motrpac-proteomics-pnnl-prototype)


# Installations

Only works locally on Mac OS X (>10.14)

## Caper

Direct usage of the execution engine `Cromwell` features complicated backend configuration, workflow options and command line parameters. [Caper](https://github.com/ENCODE-DCC/caper) (developed and mantain by the ENCODE project) hides the complexity and consolidates configuration in one file. `Caper` is available in PyPI and it is installed by running:

```
$ pip install caper
```

Note that conda run mode that is described in caper documentation is not supported by this pipeline.

## Java 8

Java is required to run execution engine `Cromwell` that `caper` uses under the hood. To check which Java version you already have, run:

```
$ java -version
```

You are looking for 1.8 or higher. If the requirement is not fulfilled follow installation instructions for [mac](https://java.com/en/download/help/mac_install.xml) or use your favorite installation method.

## Docker

Pipeline code is packaged and distributed in Docker containers, and thus Docker installation is needed. Follow instructions for [mac](https://docs.docker.com/docker-for-mac/install/). (Docker Desktop recommended)

<sub><sup>
**Note**: When configuring Docker, don't forget to "share" the local folders where the source code of this project, data files, and the output are available. Check out the [file sharing](https://docs.docker.com/docker-for-mac/#file-sharing) section of the manual to find out more. In *Docker Desktop*: "Preferences" > "Resources" > "File Sharing" and use the "+" to add the directories.
</sub></sup>


## Cromwell (optional)

We recommend using `caper` for running the pipeline, although it is possible to use Cromwell directly (you have to figure it out by yourself ;-)

# How to run it

## Test data

Download the raw files available in the following bucket of the 
GCP `motrpac-project-dev` project:

```
project: motrpac-project-dev
bucket: gs://motrpac-test-datasets/proteomics_tmt/raw_light/Global/
```

which contains the following files:

```
MoTrPAC_Pilot_TMT_S3_54_24Jan18_Precious_18-01-05.raw
MoTrPAC_Pilot_TMT_S3_81_24Jan18_Precious_18-01-05.raw
MoTrPAC_Pilot_TMT_S3_88_24Jan18_Precious_18-01-05.raw # this one won't be used for this test
```

## JSON configuration file

Use the [input_config.json] file available in the `tests` folder, which looks like this:

```
{
  "proteomics.masic_ncpu": "2",
  "proteomics.masic_ramGB": "2",
  "proteomics.masic_docker": "gcr.io/motrpac-portal-dev/motrpac-prot-masic@sha256:c4957d438ad59bf52485220a0bec8746110d83d9f7a93ae7f6b38b46f8bd2bc3",
  "proteomics.raw_file": ["/path/to/Global/MoTrPAC_Pilot_TMT_S3_54_24Jan18_Precious_18-01-05.raw", "/path/to/Global/MoTrPAC_Pilot_TMT_S3_81_24Jan18_Precious_18-01-05.raw"],
  "proteomics.parameter_masic": "/path/to/motrpac-proteomics-pipeline/parameters/TMT10_LTQ-FT_10ppm_ReporterTol0.003Da_2014-08-06.xml"
}
```

where

- `"proteomics.masic_docker"`: is the docker container. Give it a try first to make sure you have access to the MoTrPAC BIC docker container registry (otherwise, contact Karen ;-):

```
docker pull gcr.io/motrpac-portal-dev/motrpac-prot-masic@sha256:c4957d438ad59bf52485220a0bec8746110d83d9f7a93ae7f6b38b46f8bd2bc3
```

- `"proteomics.parameter_masic"`: is the path to `parameters` folder of this repo.


## Run it!

Create a folder and cd:

```
mkdir test_proteomics
cd test_proteomics
```

and run

```
caper run /full/path/to/motrpac-proteomics-pipeline/proteomics_pipeline.wdl \
-i /full/path/to/motrpac-proteomics-pipeline/tests/input_config.json \
-m testrun_metadata.json | tee run_masic.log
```

and everything was done correctly, you should see something like this...

```
Success!
[CaperURI] read from local, src: /path/to/whatever/github/MoTrPAC/motrpac-proteomics-pipeline/input_test.json
[CaperURI] copying from url to local, src: https://github.com/broadinstitute/cromwell/releases/download/47/cromwell-47.jar
[CaperURI] file already exists. skip downloading and ignore HTTP_ERR 416
[CaperURI] copying skipped, target: /path/to/whatever/.caper/cromwell_jar/cromwell-47.jar
[CaperURI] copying from url to local, src: https://github.com/broadinstitute/cromwell/releases/download/47/womtool-47.jar
[CaperURI] file already exists. skip downloading and ignore HTTP_ERR 416
[CaperURI] copying skipped, target: /path/to/whatever/.caper/womtool_jar/womtool-47.jar
[Caper] Validating WDL/input JSON with womtool...
[Caper] cmd:  ['java', '-Xmx3G', '-XX:ParallelGCThreads=1', '-DLOG_LEVEL=INFO', '-DLOG_MODE=standard', '-jar',
etc
etc
etc
```

Running this step should take some time (5 to 10 minutes depending on your computer). After a minute or so, if it doesn't crash, open a terminal and run:

```
docker ps
```

and two beautiful docker containers should be up an running for a while.

Once completed, something like this will be printed in your console (also available in the `run_masic.log` file):

```
.
.
.
2020-03-06 15:25:07,635  INFO  - ServiceRegistryActor stopped
2020-03-06 15:25:07,659  INFO  - Shutting down connection pool: curAllocated=0 idleQueues.size=0 waitQueue.size=0 maxWaitQueueLimit=256 closed=false
2020-03-06 15:25:07,659  INFO  - Shutting down connection pool: curAllocated=0 idleQueues.size=0 waitQueue.size=0 maxWaitQueueLimit=256 closed=false
2020-03-06 15:25:07,659  INFO  - Shutting down connection pool: curAllocated=0 idleQueues.size=0 waitQueue.size=0 maxWaitQueueLimit=256 closed=false
2020-03-06 15:25:07,659  INFO  - Shutting down connection pool: curAllocated=0 idleQueues.size=0 waitQueue.size=0 maxWaitQueueLimit=256 closed=false
2020-03-06 15:25:07,661  INFO  - Database closed
2020-03-06 15:25:07,662  INFO  - Stream materializer shut down
2020-03-06 15:25:07,663  INFO  - WDL HTTP import resolver closed
[CaperURI] write to local, target: /path/to/whatever/temp/proteomics_pipeline_test/test_david_light_all/testrun_metadata.json, size: 19673
[Caper] troubleshooting 86786b9a-7467-4c8f-82ef-08e769517fee ...
This workflow ran successfully. There is nothing to troubleshoot
[Caper] run:  0 86786b9a-7467-4c8f-82ef-08e769517fee /path/to/whatever/temp/proteomics_pipeline_test/test_david_light_all/testrun_metadata.json
```

Then the output folder should look like this:

```
test_david_light_all/
|-- cromwell-workflow-logs
`-- proteomics
    `-- 86786b9a-7467-4c8f-82ef-08e769517fee
        `-- call-masic
            |-- shard-0
            |   |-- execution
            |   |-- inputs
            |   |   |-- -2147115843
            |   |   `-- 236662465
			|   |       |-- MoTrPAC_Pilot_TMT_S3_54_24Jan18_Precious_18-01-05.raw
			|   |       |-- MoTrPAC_Pilot_TMT_S3_54_24Jan18_Precious_18-01-05_DatasetInfo.xml
			|   |       |-- MoTrPAC_Pilot_TMT_S3_54_24Jan18_Precious_18-01-05_MSMS_scans.csv
			|   |       |-- MoTrPAC_Pilot_TMT_S3_54_24Jan18_Precious_18-01-05_MS_scans.csv
			|   |       |-- MoTrPAC_Pilot_TMT_S3_54_24Jan18_Precious_18-01-05_ReporterIons.txt
			|   |       |-- MoTrPAC_Pilot_TMT_S3_54_24Jan18_Precious_18-01-05_SICs.xml
			|   |       |-- MoTrPAC_Pilot_TMT_S3_54_24Jan18_Precious_18-01-05_SICstats.txt
			|   |       |-- MoTrPAC_Pilot_TMT_S3_54_24Jan18_Precious_18-01-05_ScanStats.txt
			|   |       |-- MoTrPAC_Pilot_TMT_S3_54_24Jan18_Precious_18-01-05_ScanStatsConstant.txt
			|   |       `-- MoTrPAC_Pilot_TMT_S3_54_24Jan18_Precious_18-01-05_ScanStatsEx.txt
            |   `-- tmp.2f0d2009
            |-- shard-1
            |   |-- execution

            |   |-- inputs
            |   |   |-- -2147115843
            |   |   `-- 236662465
			|   |       |-- MoTrPAC_Pilot_TMT_S3_81_24Jan18_Precious_18-01-05.raw
			|   |       |-- MoTrPAC_Pilot_TMT_S3_81_24Jan18_Precious_18-01-05_DatasetInfo.xml
			|   |       |-- MoTrPAC_Pilot_TMT_S3_81_24Jan18_Precious_18-01-05_MSMS_scans.csv
			|   |       |-- MoTrPAC_Pilot_TMT_S3_81_24Jan18_Precious_18-01-05_MS_scans.csv
			|   |       |-- MoTrPAC_Pilot_TMT_S3_81_24Jan18_Precious_18-01-05_ReporterIons.txt
			|   |       |-- MoTrPAC_Pilot_TMT_S3_81_24Jan18_Precious_18-01-05_SICs.xml
			|   |       |-- MoTrPAC_Pilot_TMT_S3_81_24Jan18_Precious_18-01-05_SICstats.txt
			|   |       |-- MoTrPAC_Pilot_TMT_S3_81_24Jan18_Precious_18-01-05_ScanStats.txt
			|   |       |-- MoTrPAC_Pilot_TMT_S3_81_24Jan18_Precious_18-01-05_ScanStatsConstant.txt
			|   |       `-- MoTrPAC_Pilot_TMT_S3_81_24Jan18_Precious_18-01-05_ScanStatsEx.txt
            |   `-- tmp.c52ed690
```

if so... congratulations!