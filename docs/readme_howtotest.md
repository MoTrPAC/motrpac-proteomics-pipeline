# How to test the pipeline

## Test data

Download the raw files available in the following bucket of the GCP `motrpac-project-dev` project:

```
cd /the/directory/where/you/want/the/data
gcloud config set project my-project-dev
gsutil cp -r gs://motrpac-test-datasets/proteomics_tmt/raw_light/Global .
```

which contains the following files:

```
MoTrPAC_Pilot_TMT_S3_54_24Jan18_Precious_18-01-05.raw
MoTrPAC_Pilot_TMT_S3_81_24Jan18_Precious_18-01-05.raw
MoTrPAC_Pilot_TMT_S3_88_24Jan18_Precious_18-01-05.raw # this one won't be used for this test
```

**WARNING**: do not download the files using the GCP web interface (it changes the file names)


## JSON configuration file

Details for each parameter of the configuration file are available in [input_config_template.json](../tests/input_config_template.json)

### Local

Use the [input_config_local.json](../tests/input_test_local.json) file available in the `tests` folder as an example (but it will require to replace the "`/full/path/to/`" with your custom values)

We recommend to first test that the MoTrPAC BIC docker container registry (or docker.io) can be accessed (otherwise, contact the BIC ;-). For example:

```
docker pull gcr.io/my-project-dev/motrpac-prot-masic:v1.0_20200122
docker pull docker.io/chambm/pwiz-skyline-i-agree-to-the-vendor-licenses:latest
```

### GCP

Use the [input_config_gcp.json](../tests/input_test_gcp.json) file available in `tests` folder to start the job (see below). It will require you to customize your values.

**Note**: it assumes you have gcp set up [as described here](https://cloud.google.com/container-registry/docs/advanced-authentication)


## Run it!

### Locally

Create a folder and cd:

```
mkdir test_proteomics_local
cd test_proteomics_local
```

and run

```
caper run /full/path/to/motrpac-proteomics-pipeline/proteomics_pipeline.wdl \
-i /full/path/to/motrpac-proteomics-pipeline/tests/input_config_local.json \
-m testrun_metadata_local.json | tee run_masic_local.log
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

and two docker containers should be up an running for a while (the command `docker ps` should display both commands once running)


### GCP

Create a folder and cd:

```
mkdir test_proteomics_gcp
cd test_proteomics_gcp
```

and run

```
caper run /full/path/to/motrpac-proteomics-pipeline/proteomics_pipeline.wdl -i /full/path/to/motrpac-proteomics-pipeline/tests/input_test_gcp.json -b gcp -m testrun_metadata_gcp.json | tee run_masic_gcp.log
```

### Outputs

Once completed, something like this shold be printed in your console (also available in the `run_masic_[local or gcp].log` file):

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
[CaperURI] write to local, target: /path/to/whatever/test_proteomics_gcp/testrun_metadata.json, size: 19673
[Caper] troubleshooting 86786b9a-7467-4c8f-82ef-08e769517fee ...
This workflow ran successfully. There is nothing to troubleshoot
[Caper] run:  0 86786b9a-7467-4c8f-82ef-08e769517fee /path/to/whatever/test_proteomics_gcp/testrun_metadata.json
```

Then the output folder should look like this:

```
test_proteomics_[local or gcp]/
|-- cromwell-workflow-logs
`-- proteomics
    `-- 25127cbd-6ab1-45f2-81d4-9bdc0bca1e45
        `-- call-masic
            |-- shard-0
            |   |-- execution
            |   |   |-- glob-0c83d6906fbe3091d7f9ae5df309e090
            |   |   |-- glob-2066f9e90c242769b62d9866c26b90c0
            |   |   |-- glob-70dc246c20c4fd6400712f99f71d46e7
            |   |   |-- glob-73480eaa13c897bb106798d152550136
            |   |   |-- glob-90594c8d236cc66bb27d666c3b020fa1
            |   |   |-- glob-b069eab7e4d1edec185303ed4920ca86
            |   |   |-- glob-c744e7680f222aceef79f6ff81336630
            |   |   |-- glob-cb375dfd8c40490e7d395e9f60e10b65
            |   |   |-- glob-fc4d11d84f15789a6b364ac1c2ad631a
|           |   |   |-- masic_output
|           |   |   |   |-- MoTrPAC_Pilot_TMT_S3_54_24Jan18_Precious_18-01-05_DatasetInfo.xml
|           |   |   |   |-- MoTrPAC_Pilot_TMT_S3_54_24Jan18_Precious_18-01-05_MSMS_scans.csv
|           |   |   |   |-- MoTrPAC_Pilot_TMT_S3_54_24Jan18_Precious_18-01-05_MS_scans.csv
|           |   |   |   |-- MoTrPAC_Pilot_TMT_S3_54_24Jan18_Precious_18-01-05_ReporterIons.txt
|           |   |   |   |-- MoTrPAC_Pilot_TMT_S3_54_24Jan18_Precious_18-01-05_SICs.xml
|           |   |   |   |-- MoTrPAC_Pilot_TMT_S3_54_24Jan18_Precious_18-01-05_SICstats.txt
|           |   |   |   |-- MoTrPAC_Pilot_TMT_S3_54_24Jan18_Precious_18-01-05_ScanStats.txt
|           |   |   |   |-- MoTrPAC_Pilot_TMT_S3_54_24Jan18_Precious_18-01-05_ScanStatsConstant.txt
|           |   |   |   `-- MoTrPAC_Pilot_TMT_S3_54_24Jan18_Precious_18-01-05_ScanStatsEx.txt
            |   |-- inputs
            |   |   |-- -1036559106
            |   |   `-- 1761609127
            |   `-- tmp.f0f36feb
            `-- shard-1
                |-- execution
                |   |-- glob-0c83d6906fbe3091d7f9ae5df309e090
                |   |-- glob-2066f9e90c242769b62d9866c26b90c0
                |   |-- glob-70dc246c20c4fd6400712f99f71d46e7
                |   |-- glob-73480eaa13c897bb106798d152550136
                |   |-- glob-90594c8d236cc66bb27d666c3b020fa1
                |   |-- glob-b069eab7e4d1edec185303ed4920ca86
                |   |-- glob-c744e7680f222aceef79f6ff81336630
                |   |-- glob-cb375dfd8c40490e7d395e9f60e10b65
                |   |-- glob-fc4d11d84f15789a6b364ac1c2ad631a
|               |   |-- masic_output
|               |   |   |-- MoTrPAC_Pilot_TMT_S3_81_24Jan18_Precious_18-01-05_DatasetInfo.xml
|               |   |   |-- MoTrPAC_Pilot_TMT_S3_81_24Jan18_Precious_18-01-05_MSMS_scans.csv
|               |   |   |-- MoTrPAC_Pilot_TMT_S3_81_24Jan18_Precious_18-01-05_MS_scans.csv
|               |   |   |-- MoTrPAC_Pilot_TMT_S3_81_24Jan18_Precious_18-01-05_ReporterIons.txt
|               |   |   |-- MoTrPAC_Pilot_TMT_S3_81_24Jan18_Precious_18-01-05_SICs.xml
|               |   |   |-- MoTrPAC_Pilot_TMT_S3_81_24Jan18_Precious_18-01-05_SICstats.txt
|               |   |   |-- MoTrPAC_Pilot_TMT_S3_81_24Jan18_Precious_18-01-05_ScanStats.txt
|               |   |   |-- MoTrPAC_Pilot_TMT_S3_81_24Jan18_Precious_18-01-05_ScanStatsConstant.txt
|               |   |   `-- MoTrPAC_Pilot_TMT_S3_81_24Jan18_Precious_18-01-05_ScanStatsEx.txt
				
                |-- inputs
                |   |-- -1036559106
                |   `-- 1761609127
                `-- tmp.4fd0350b
```

if so... congratulations!