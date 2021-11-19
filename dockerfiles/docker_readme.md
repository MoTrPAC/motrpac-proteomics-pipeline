# DOCKER BUILD, TAG, AND PUSH

## Images used by this proteomics pipeline

Dockerfiles available at the `docker_files/` folder:

- Dockerfile.ascore
- Dockerfile.masic
- Dockerfile.msgfplus
- Dockerfile.mzid2tsv
- Dockerfile.phrp
- Dockerfile.ppmerror
- Dockerfile.plexedpiper

## How to

To build, tag, and push an updated docker image, follow these steps:

1. Change directory to the root folder of this github repo:

```
cd MoTrPAC/motrpac-proteomics-pipeline/
```

2. Execute

```
 scripts/build_push_docker.sh <Docker Name> <Docker Version>
```

where

```
	- <Docker Name> options: [masic, msgfplus, msconvert, ppmerror, mzid2tsv, phrp, ascore, plexedpiper]
	- <Docker Version> format: v#.#_YYYYMMDD (example: v1.1_20200327)
```

## Warnings

- The script must be executed from the root folder of this github repo for the script being able to access the folder `docker_files/` properly)

- Bash version must be `>= 4.0`. If executing the following test: `scripts/build_push_docker.sh testing v12000` does not generate this output:

```
$ scripts/build_push_docker.sh testing v12000

 --------------------------------------------------
  DOCKER IMAGE BUILDER
 --------------------------------------------------
 - Check Docker Name: testing  ---> ERROR!!
	Docker name <testing> is not valid. Valid options:
	- ascore
	- masic
	- msgfplus
	- mzid2tsv
	- phrp
	- ppmerror
 - Check Version format: v12000  ---> ERROR!!
	<docker version> option is not valid
	Please, provide the right format: v#.#_YYYYMMDD
    
```

...then you are likely running a lower bash version


### Latest software versions:

- ascore: https://github.com/PNNL-Comp-Mass-Spec/AScore/releases/download/v1.0.7537/AScore_Program_Debian.zip
- masic: https://github.com/PNNL-Comp-Mass-Spec/MASIC/releases/download/v3.2.7465/MASIC_Console_Program.zip
- msgfplus: https://github.com/MSGFPlus/msgfplus/releases/download/v2020.08.05/MSGFPlus_v20200805.zip
- mzid2tsv: https://github.com/PNNL-Comp-Mass-Spec/Mzid-To-Tsv-Converter/releases/download/v1.4.3/MzidToTsvConverter.zip
- sqlite-netFx: https://github.com/AshleyLab/motrpac-proteomics-pnnl-prototype/raw/master/step06/sqlite-netFx-full-source-1.0.111.0.zip
- phrp: https://github.com/PNNL-Comp-Mass-Spec/PHRP/releases/download/v1.5.7458/PeptideHitResultsProcessor_Debian.zip
- ppmerror: https://github.com/PNNL-Comp-Mass-Spec/PPMErrorCharter/releases/download/v1.2.7458/PPMErrorCharterPython_Program.zip

Latest Update to v1.2_20200901
