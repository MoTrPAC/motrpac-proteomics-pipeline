# DOCKER BUILD, TAG, AND PUSH

## Images used by this proteomics pipeline

Dockerfiles available at the `docker_files/` folder:

- Dockerfile_ascore
- Dockerfile_masic
- Dockerfile_msgfplus
- Dockerfile_mzid2tsv
- Dockerfile_phrp
- Dockerfile_ppmerror

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
	- ppmerror
	- masic
	- ascore
	- mzid2tsv
	- phrp
	- msgfplus
 - Check Version format: v12000  ---> ERROR!!
	<docker version> option is not valid
	Please, provide the right format: v#.#_YYYYMMDD
    
```

...then you are likely running a lower bash version
