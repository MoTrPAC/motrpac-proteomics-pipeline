version 1.0

workflow proteomics_maxquant {

    meta {
        author: "David Jimenez-Morales"
        version: "v0.0.1"
    }
input {
    # MaxQuant input files and parameters
    Array[File] raw_file = []
    File mq_parameters
    File fasta_sequence_db

    # Docker details
    Int mq_ncpu
    Int mq_ramGB
    Int? mq_disk
    String mq_docker
}
    call maxquant {
        input:
            ncpu = mq_ncpu,
            ramGB = mq_ramGB,
            docker = mq_docker,
            disks = mq_disk,
            mq_parameters = mq_parameters,
            fasta_sequence_db = fasta_sequence_db,
            raw_file = raw_file
    }
}

task maxquant {
    input {
        Int ncpu
        Int ramGB
        Int? disks
        String docker
        File mq_parameters
        File fasta_sequence_db
        Array[File] raw_file
    }

    command <<<
        echo "STEP 1: Copy RAW files to mqdata folder"

        mkdir -p mqdata
        
        for file in ~{sep=' ' raw_file}; 
            do cp $file mqdata/
        done

        echo "STEP 2: Copy SEQUENCE DB to mqdata folder"

        cp ~{fasta_sequence_db} mqdata/

        echo "-----List file content----"

        ls -lhtr mqdata

        echo "STEP 3: CHANGE THE FULL PATH OF FILES IN XML FILE"

        cd mqdata || exit

        sed -i "s|mqdata|$PWD|g" ~{mq_parameters}

        echo "STEP 4: Run Maxquant"

        mono /app/MaxQuant/bin/MaxQuantCmd.exe ~{mq_parameters}
    >>>

    output {
        File allPeptides = "mqdata/combined/txt/allPeptides.txt"
        File evidence = "mqdata/combined/txt/evidence.txt"
        File libraryMatch = "mqdata/combined/txt/libraryMatch.txt"
        File matchedFeatures = "mqdata/combined/txt/matchedFeatures.txt"
        File modificationSpecificPeptides = "mqdata/combined/txt/modificationSpecificPeptides.txt"
        File ms3Scans = "mqdata/combined/txt/ms3Scans.txt"
        File msms = "mqdata/combined/txt/msms.txt"
        File msmsScans = "mqdata/combined/txt/msmsScans.txt"
        File mzRange = "mqdata/combined/txt/mzRange.txt"
        File parameters = "mqdata/combined/txt/parameters.txt"
        File peptides = "mqdata/combined/txt/peptides.txt"
        File proteinGroups = "mqdata/combined/txt/proteinGroups.txt"
        File summary = "mqdata/combined/txt/summary.txt"
        File runningTimes = "mqdata/combined/proc/#runningTimes.txt"
        Array[File] sites = glob("mqdata/combined/txt/*Sites.txt")
    }

    runtime {
        docker: "${docker}"
        memory: "${ramGB} GB"
        cpu: "${ncpu}"
        disks: "local-disk ${select_first([disks, 100])} HDD"
    }
    
    parameter_meta {
        mq_parameters: {
            type: "parameter",
            label: "MaxQuant Parameter File"
        }
        fasta_sequence_db: {
            type: "sequence_db"
        }
        raw_file: {
            label: ".RAW File"
        }
    }
}

