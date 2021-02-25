workflow proteomics_maxquant {

    meta {
        author: "David Jimenez-Morales"
        version: "v0.0.1"
    }

    # RAW INPUT FILES
    Array[File] raw_file = []

    # MAXQUANT
    Int mq_ncpu
    Int mq_ramGB
    String mq_docker
    String? mq_disk
    
    File mq_parameters
    File fasta_sequence_db

    call maxquant { input:
        ncpu = mq_ncpu,
        ramGB = mq_ramGB,
        docker = mq_docker,
        disks = mq_disk,
        mq_parameters = mq_parameters ,
        fasta_sequence_db = fasta_sequence_db,
        raw_file = raw_file
    }
}

task maxquant {
    Int ncpu
    Int ramGB
    String docker
    String? disks
    File mq_parameters
    File fasta_sequence_db
    File raw_file

    command {
        echo "STEP 1: Copy RAW files to mqdata folder"

        mkdir -p mqdata
        
        for file in ${sep=' ' raw_file}; 
            do cp $file mqdata/
        done

        echo "STEP 2: Copy SEQUENCE DB to mqdata folder"

        cp ${fasta_sequence_db} mqdata/

        echo "STEP 3: Run Maxquant"

        mono /app/maxquant1660/bin/MaxQuantCmd.exe ${mq_parameters}
    }

    output {
        #File OxidationSites = "mqdata/combined/txt/Oxidation\ \(M\)Sites.txt"
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
    }

    runtime {
        docker: "${docker}"
        memory: "${ramGB} GB"
        cpu: "${ncpu}"
        disks : select_first([disks,"local-disk 100 SSD"])
    }
}

