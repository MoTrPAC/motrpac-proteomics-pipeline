#!/usr/local/bin/bash

# DESCRIPTION
# - - -- - - - - -- - - - -- - - -- - - -- - - -- - - -
# Build a new version of a docker file
# - - -- - - - - -- - - - -- - - -- - - -- - - -- - - -

if [ "$#" -ne 2 ]; then

    printf "\n- e r r o r -----------------------------------------\n"
    printf " Error: Illegal number of parameters\n"
    printf " Usage: $0 <Docker Name> <Docker Version>\n" 1>&2
    printf "\t- <Docker Name> valid options: [masic, msgfplus, msconvert, ppmerror, mzid2tsv, phrp, ascore, plexedpiper]\n"
    printf "\t- <Docker Version> format: v#.#_YYYYMMDD (example: v1.1_20200327)\n\n"
    exit "Try again when ready"
fi

printf "\n --------------------------------------------------\n"
printf "  DOCKER IMAGE BUILDER\n"
printf " --------------------------------------------------\n"

DOCKERFILE=$1
VERSION=$2

declare -A arr_dockercontainer

arr_dockercontainer+=( 
    ["ascore"]=motrpac-prot-ascore
    ["masic"]=motrpac-prot-masic
    ["msgfplus"]=motrpac-prot-msgfplus
    ["mzid2tsv"]=motrpac-prot-mzid2tsv
    ["phrp"]=motrpac-prot-phrp 
    ["ppmerror"]=motrpac-prot-ppmerror 
)

declare -A arr_dockerregistry

arr_dockerregistry+=( 
    ["ascore"]=gcr.io/my-project-dev/motrpac-prot-ascore
    ["masic"]=gcr.io/my-project-dev/motrpac-prot-masic
    ["msgfplus"]=gcr.io/my-project-dev/motrpac-prot-msgfplus
    ["mzid2tsv"]=gcr.io/my-project-dev/motrpac-prot-mzid2tsv
    ["phrp"]=gcr.io/my-project-dev/motrpac-prot-phrp 
    ["ppmerror"]=gcr.io/my-project-dev/motrpac-prot-ppmerror 
)

declare -A arr_dockerfile

arr_dockerfile+=( 
    ["ascore"]=docker_files/Dockerfile_ascore
    ["masic"]=docker_files/Dockerfile_masic
    ["msgfplus"]=docker_files/Dockerfile_msgfplus
    ["mzid2tsv"]=docker_files/Dockerfile_mzid2tsv
    ["phrp"]=docker_files/Dockerfile_phrp
    ["ppmerror"]=docker_files/Dockerfile_ppmerror
)

printf " - Check Docker Name: ${DOCKERFILE} "
if [ -v arr_dockercontainer[$DOCKERFILE] ]
then
    printf " ---> correct format\n"
else
    printf " ---> ERROR!!\n"
    printf "\tDocker name <${DOCKERFILE}> is not valid. Valid options:\n"
    for i in "${!arr_dockercontainer[@]}"
    do   
        echo -e "\t- $i"
    done
fi

# CHECK NEW DOCKER VERSION FORMAT
printf " - Check Version format: ${VERSION} "

if [[ ${VERSION} =~ ^v[0-9]{1}.[0-9]{1}_[0-9]{8}$ ]]
then
    printf " ---> correct format\n"
else
    printf " ---> ERROR!!\n"
    printf "\t<docker version> option is not valid\n"
    printf "\tPlease, provide the right format: v#.#_YYYYMMDD\n\n"
    exit 1
fi

# CHECK NEW DOCKER VERSION FORMAT
NEWTAG=${arr_dockercontainer[${DOCKERFILE}]}":"${VERSION}
NEWREG=${arr_dockerregistry[${DOCKERFILE}]}":"${VERSION}
LOCATION=${arr_dockerfile[$DOCKERFILE]}

printf " - New full docker tag: ${NEWTAG}\n\n"

printf "Running: docker build -t \""${NEWTAG}"\" -f ${LOCATION} .\n"
docker build -t "${NEWTAG}" -f ${LOCATION} .

printf "\nRunning: docker tag ${NEWTAG} ${NEWREG}\n"
docker tag ${NEWTAG} ${NEWREG}

printf "\nRunning: docker push ${NEWREG}\n"
docker push ${NEWREG}

printf "\nDONE!\n"


