# Installations

## Caper

Direct usage of the execution engine `Cromwell` features complicated backend configuration, workflow options and command line parameters. [Caper](https://github.com/ENCODE-DCC/caper) (developed and mantain by the ENCODE project) hides the complexity and consolidates configuration in one file. `Caper` is available in PyPI and it is installed by running:

```
$ pip install caper
```

Note that conda run mode that is described in caper documentation is not supported by this pipeline.

***About caper config file***

Once `caper` is installed, the following config file should be available:

```
/Users/[[mac_user]]/.caper/default.conf
```

(please, create otherwise)

Edit the config file and add the following options in order to be able to run it on GCP

```
backend=local

# Caper stores all important temp files and cached big data files here
tmp-dir=/Users/[[mac_user]]/temp/caper_temp

# GCP options
# GCP Project name
gcp-prj=[[your-gcp-project-here]]
# GCP output bucket
out-gcs-bucket=gs://[[your-bucket-location]]/proteomics_tests_gcp
```


## Java 8

Java is required to run execution engine `Cromwell` that `caper` uses under the hood. To check which Java version you already have, run:

```
$ java -version
```

You are looking for 1.8 or higher. If the requirement is not fulfilled follow installation instructions for [mac](https://java.com/en/download/help/mac_install.xml) or use your favorite installation method.

## Docker (only locally)

Pipeline code is packaged and distributed in Docker containers, and thus Docker installation is needed. Follow instructions for [mac](https://docs.docker.com/docker-for-mac/install/). (Docker Desktop recommended)


**Note**: When configuring Docker, don't forget to "share" the local folders where the source code of this project, data files, and the output are available. Check out the [file sharing](https://docs.docker.com/docker-for-mac/#file-sharing) section of the manual to find out more. In *Docker Desktop*: "Preferences" > "Resources" > "File Sharing" and use the "+" to add the directories.

To build, tag, and push docker images used in this repo, [check here](docker_files/docker_readme.md).


## Cromwell (optional)

We recommend using `caper` for running the pipeline, although it is possible to use Cromwell directly (you have to figure it out by yourself ;-)