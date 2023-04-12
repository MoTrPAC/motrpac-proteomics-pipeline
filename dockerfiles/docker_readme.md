# Docker containers


The MSGF+ proteomics pipelines consists of numerous steps using different software tools (check [here](../docs/readme_msgfplus-details.md) for details). Check the `Dockerfiles` available in the  `motrpac-proteomics-pipeline/dockerfiles` directory to find out more about the software installed in each of them. All docker containers are already built and available at the Motrpac's [Artifact Registry](https://cloud.google.com/artifact-registry). The table below contains the details of the docker file and the corresponding image name available in the registry:

| Dockerfile | Container name on Artifact |
|:------------- |:---------------|
| [Dockerfile.ascore](Dockerfile.ascore) | prot-ascore |
| [Dockerfile.masic](Dockerfile.masic) | prot-masic |
| [Dockerfile.msgfplus](Dockerfile.msgfplus) | prot-msgfplus |
| [Dockerfile.mzid2tsv](Dockerfile.mzid2tsv) | prot-mzid2tsv |
| [Dockerfile.phrp](Dockerfile.phrp) | prot-phrp |
| [Dockerfile.ppmerror](Dockerfile.ppmerror) | prot-ppmerror |
| [Dockerfile.plexedpiper](Dockerfile.plexedpiper) | prot-plexedpiper |

You can pull any of them to your system by running the command:

```
docker pull [artifact.registry].prot-[name]
```


To build any of them, from the `github/MoTrPAC/motrpac-proteomics-pipeline` directory run the following command:

```
docker build -t "prot-msgfplus:v1" -f dockerfiles/Dockerfile.msgfplus .
```


