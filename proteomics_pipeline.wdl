workflow proteomics {
    
    # RAW INPUT FILES
    Array[File] raw_file = []

    # MASIC
    Int masic_ncpu
    Int masic_ramGB
    String masic_docker
    String? masic_disk
    
    File masic_parameter
    
    # MSCONVERT
    Int msconvert_ncpu
    Int msconvert_ramGB
    String msconvert_docker
    String? msconvert_disk

    # MS-GF+ SHARED OPTIONS
    Int msgf_ncpu
    Int msgf_ramGB
    String msgf_docker
    String? msgf_disk
    File fasta_sequence_db

    # MS-GF+ TRYPTIC
    File msgf_tryptic_parameter

    # MS-GF+ IDENTIFICATION
    File msgf_identification_parameter

    # PPMErrorCharter
    String ppm_errorcharter_docker

    # MzidToTSVConverter
    String mzidtotsvconverter_docker

    # PHRP
    Int phrp_ncpu
    Int phrp_ramGB
    String phrp_docker
    String? phrp_disk

    File phrp_parameter_m
    File phrp_parameter_t
    File phrp_parameter_n
    Float phrp_synpvalue
    Float phrp_synprob

    call msgf_sequences { input:
        ncpu = msgf_ncpu,
        ramGB = msgf_ramGB,
        docker = msgf_docker,
        disks = msgf_disk,
        fasta_sequence_db = fasta_sequence_db
    }

    scatter (i in range(length(raw_file))) {
        call masic { input:
            ncpu = masic_ncpu,
            ramGB = masic_ramGB,
            docker = masic_docker,
            disks = masic_disk,
            raw_file = raw_file[i],
            masic_parameter = masic_parameter,
            output_masic = "masic_output"
        }

        call msconvert { input:
            ncpu = msconvert_ncpu,
            ramGB = msconvert_ramGB,
            docker = msconvert_docker,
            disks = msconvert_disk,
            raw_file = raw_file[i],
            output_msconvert = "msconvert_output"
        }

        call msgf_tryptic { input:
            ncpu = msgf_ncpu,
            ramGB = msgf_ramGB,
            docker = msgf_docker,
            disks = msgf_disk,
            input_mzml = msconvert.mzml,
            fasta_sequence_db = fasta_sequence_db,
            sequencedb_files = msgf_sequences.sequencedb_files,
            msgf_tryptic_parameter = msgf_tryptic_parameter
        }

        call msconvert_mzrefiner { input:
            ncpu = msconvert_ncpu,
            ramGB = msconvert_ramGB,
            docker = msconvert_docker,
            disks = msconvert_disk,
            input_mzml = msconvert.mzml,
            input_mzid = msgf_tryptic.mzid,
            output_msconvert_mzrefiner = "msconvert_mzrefiner_output"
        }

        call ppm_errorcharter { input:
            ncpu = msconvert_ncpu,
            ramGB = msconvert_ramGB,
            docker = ppm_errorcharter_docker,
            disks = msconvert_disk,
            input_fixed_mzml = msconvert_mzrefiner.mzml_fixed,
            input_mzid = msgf_tryptic.mzid
        }

        call msgf_identification { input:
            ncpu = msgf_ncpu,
            ramGB = msgf_ramGB,
            docker = msgf_docker,
            disks = msgf_disk,
            input_fixed_mzml = msconvert_mzrefiner.mzml_fixed,
            fasta_sequence_db = fasta_sequence_db,
            sequencedb_files = msgf_sequences.sequencedb_files,
            msgf_identification_parameter = msgf_identification_parameter
        }

        call mzidtotsvconverter { input:
            ncpu = msconvert_ncpu,
            ramGB = msconvert_ramGB,
            docker = mzidtotsvconverter_docker,
            disks = msconvert_disk,
            input_mzid_final = msgf_identification.mzid_final,
            output_mzidtotsvconverter = "mzidtotsvconverter_output"
        }

        call phrp { input:
            ncpu = phrp_ncpu,
            ramGB = phrp_ramGB,
            docker = phrp_docker,
            disks = phrp_disk,
            input_tsv = mzidtotsvconverter.tsv,
            output_phrp = "phrp_output",
            phrp_parameter_m = phrp_parameter_m,
            phrp_parameter_t = phrp_parameter_t,
            phrp_parameter_n = phrp_parameter_n,
            phrp_synpvalue = phrp_synpvalue,
            phrp_synprob = phrp_synprob,
            input_revcat_fasta = msgf_sequences.revcat_fasta
        }
    }
}

task msgf_sequences {
    Int ncpu
    Int ramGB
    String docker
    String? disks

    File fasta_sequence_db

    String seq_file_id = basename(fasta_sequence_db, ".fasta")
    # String output_full = output_msgf_tryptic + "/" + ouput_name
    
    command {
        echo "PRE-STEP: MSGF+ READY TO PROCES SEQUENCE DB"

        # Generate sequence indexes
        java -Xmx4000M -cp /app/MSGFPlus.jar edu.ucsd.msjava.msdbsearch.BuildSA \
        -d ${fasta_sequence_db} \
        -tda 2 \
        -o sequencedb_folder #test this

        # Compress results
        tar -C sequencedb_folder -zcvf sequencedb_files.tar.gz .
    }

    output {
        File sequencedb_files = "sequencedb_files.tar.gz"
        File revcat_fasta = "sequencedb_folder/${seq_file_id}.revCat.fasta"
    }

    runtime {
        docker: "${docker}"
        memory: "${ramGB} GB"
        cpu: "${ncpu}"
        disks : select_first([disks,"local-disk 100 SSD"])
    }
}

task masic {
    Int ncpu
    Int ramGB
    String docker
    String? disks
    File raw_file
    File masic_parameter
    String output_masic

    command {
        echo "STEP 0: Ready to run MASIC"

        mono /app/masic/MASIC_Console.exe \
        /I:${raw_file} \
        /P:${masic_parameter} \
        /O:${output_masic}
    }

    output {
        File ReporterIons_output_file = glob("${output_masic}/*ReporterIons.txt")[0]
        File DatasetInfo_output_file = glob("${output_masic}/*DatasetInfo.xml")[0]
        File ScanStats_output_file = glob("${output_masic}/*ScanStats.txt")[0]
        File MS_scans_output_file = glob("${output_masic}/*MS_scans.csv")[0]
        File MSMS_scans_output_file = glob("${output_masic}/*MSMS_scans.csv")[0]
        File ScanStatsEx_output_file = glob("${output_masic}/*ScanStatsEx.txt")[0]
        File SICstats_output_file = glob("${output_masic}/*SICstats.txt")[0]
        File ScanStatsConstant_output_file = glob("${output_masic}/*ScanStatsConstant.txt")[0]
        File SICs_output_file = glob("${output_masic}/*SICs.xml")[0]
    }

    runtime {
        docker: "${docker}"
        memory: "${ramGB} GB"
        cpu: "${ncpu}"
        disks : select_first([disks,"local-disk 100 SSD"])
    }
}

task msconvert {
    Int ncpu
    Int ramGB
    String docker
    String? disks
    File raw_file
    String output_msconvert
    
    command {
        echo "STEP 1: MSCONVERT - - - - - - - -"

        wine msconvert ${raw_file} \
        -o ${output_msconvert}
    }

    output {
        File mzml = glob("${output_msconvert}/*.mzML")[0]
    }

    runtime {
        docker: "${docker}"
        memory: "${ramGB} GB"
        cpu: "${ncpu}"
        disks : select_first([disks,"local-disk 100 SSD"])
    }
}

task msgf_tryptic {
    Int ncpu
    Int ramGB
    String docker
    String? disks

    File input_mzml
    File fasta_sequence_db
    File sequencedb_files
    File msgf_tryptic_parameter

    # Create new ouput destination
    String sample_id = basename(input_mzml, ".mzML")
    String seq_file_id = basename(fasta_sequence_db, ".fasta")
    
    command {
        echo "STEP 2: MS-GF+ TRYPTIC SEARCH"
        ls
        echo "COPY FILES - - - - - - - - - -"
        
        cp ${sequencedb_files} .
        ls
        tar xvzf ${sequencedb_files}

        echo "MSGF+ BEGINs - - - - - - - - - -"

        java -Xmx4000M \
        -jar /app/MSGFPlus.jar \
        -s ${input_mzml} \
        -o ${sample_id}.mzid \
        -d ${seq_file_id}.fasta \
        -conf ${msgf_tryptic_parameter}
        
        echo "LIST RESULTS - - - - - - - - - -"
        ls
        echo "ADIOS - - - - - - - - - -"
    }

    output {
        File mzid = "${sample_id}.mzid"
    }

    runtime {
        docker: "${docker}"
        memory: "${ramGB} GB"
        cpu: "${ncpu}"
        disks : select_first([disks,"local-disk 100 SSD"])
    }
}

task msconvert_mzrefiner {
    Int ncpu
    Int ramGB
    String docker
    String? disks
    File input_mzml
    File input_mzid
    String output_msconvert_mzrefiner

    # Create new ouput destination
    String sample_id = basename(input_mzml, ".mzML")
    String ouput_name = sample_id + "_FIXED.mzML"
    String output_full = output_msconvert_mzrefiner + "/" + ouput_name
    
    command {
        echo "STEP 3A: MSCONVERT-MZREFINE"

        wine msconvert ${input_mzml} \
        -o ${output_msconvert_mzrefiner} \
        --outfile ${output_full} \
        --filter "mzRefiner ${input_mzid} thresholdValue=-1e-10 thresholdStep=10 maxSteps=2" \
        --32 --mzML
    }

    output {
        File mzml_fixed = glob("${output_msconvert_mzrefiner}/*_FIXED.mzML")[0]
    }

    runtime {
        docker: "${docker}"
        memory: "${ramGB} GB"
        cpu: "${ncpu}"
        disks : select_first([disks,"local-disk 100 SSD"])
    }
}

task ppm_errorcharter {
    Int ncpu
    Int ramGB
    String docker
    String? disks
    File input_fixed_mzml
    File input_mzid
    
    command {
        echo "STEP 3B: PPMErrorCharter"

        mono /app/PPMErrorCharterPython.exe \
        -I:${input_mzid} \
        -F:${input_fixed_mzml} \
        -EValue:1E-10
    }

    runtime {
        docker: "${docker}"
        memory: "${ramGB} GB"
        cpu: "${ncpu}"
        disks : select_first([disks,"local-disk 100 SSD"])
    }
}


task msgf_identification {
    Int ncpu
    Int ramGB
    String docker
    String? disks

    File input_fixed_mzml
    File fasta_sequence_db
    File sequencedb_files
    File msgf_identification_parameter

    # Create new ouput destination
    String sample_id = basename(input_fixed_mzml, "_FIXED.mzML")
    String seq_file_id = basename(fasta_sequence_db, ".fasta")
    
    command {
        echo "STEP 4: MS-GF+ IDENTIFICATION SEARCH - - - - - - - - - -"
        ls
        echo "COPY FILES - - - - - - - - - -"
        
        cp ${sequencedb_files} .
        ls
        tar xvzf ${sequencedb_files}

        echo "MSGF+ IDENTIFICATION BEGINs - - - - - - - - - -"

        java -Xmx4000M \
        -jar /app/MSGFPlus.jar \
        -s ${input_fixed_mzml} \
        -o ${sample_id}_final.mzid \
        -d ${seq_file_id}.fasta \
        -conf ${msgf_identification_parameter}

        echo "LIST RESULTS - - - - - - - - - -"
        ls
        echo "ADIOS - - - - - - - - - -"
    }

    output {
        File mzid_final = "${sample_id}_final.mzid"
    }

    runtime {
        docker: "${docker}"
        memory: "${ramGB} GB"
        cpu: "${ncpu}"
        disks : select_first([disks,"local-disk 100 SSD"])
    }
}

task mzidtotsvconverter {
    Int ncpu
    Int ramGB
    String docker
    String? disks
    File input_mzid_final
    String output_mzidtotsvconverter

    # Create new ouput destination
    String sample_id = basename(input_mzid_final, "_final.mzid")
    String ouput_name = sample_id + ".tsv"
    String output_full = output_mzidtotsvconverter + "/" + ouput_name
    
    command {
        echo "STEP 5:: MzidToTSVConverter"

        mono /app/mzid2tsv/net462/MzidToTsvConverter.exe \
		-mzid:${input_mzid_final} \
		-tsv:${output_full} \
		-unroll -showDecoy
    }

    output {
        File tsv = glob("${output_mzidtotsvconverter}/*.tsv")[0]
    }

    runtime {
        docker: "${docker}"
        memory: "${ramGB} GB"
        cpu: "${ncpu}"
        disks : select_first([disks,"local-disk 100 SSD"])
    }
}

task phrp {
    Int ncpu
    Int ramGB
    String docker
    String? disks
    
    File input_tsv
    String output_phrp

    File phrp_parameter_m
    File phrp_parameter_t
    File phrp_parameter_n
    Float phrp_synpvalue
    Float phrp_synprob
    
    # Create new ouput destination
    String phrp_logfile = "PHRP_LogFile.txt"
    String output_logfile = output_phrp + "/" + phrp_logfile

    File input_revcat_fasta
    
    command {
        echo "STEP 6: PeptideHitResultsProcRunner"

		mono /app/phrp/PeptideHitResultsProcRunner.exe \
		-I:${input_tsv} \
		-O:${output_phrp} \
		-M:${phrp_parameter_m} \
		-T:${phrp_parameter_t} \
		-N:${phrp_parameter_n} \
		-SynPvalue:${phrp_synpvalue} -SynProb:${phrp_synprob} \
		-L:${output_logfile} \
		-ProteinMods \
		-F:${input_revcat_fasta}
    }

    output {
        File PepToProtMapMTS = glob("${output_phrp}/*_PepToProtMapMTS.txt")[0]
        File fht = glob("${output_phrp}/*_fht.txt")[0]
        File syn = glob("${output_phrp}/*_syn.txt")[0]
        File syn_ModDetails = glob("${output_phrp}/*_syn_ModDetails.txt")[0]
        File syn_ModSummary = glob("${output_phrp}/*_syn_ModSummary.txt")[0]
        File syn_ProteinMods = glob("${output_phrp}/*_syn_ProteinMods.txt")[0]
        File syn_ResultToSeqMap = glob("${output_phrp}/*_syn_ResultToSeqMap.txt")[0]
        File syn_SeqInfo = glob("${output_phrp}/*_syn_SeqInfo.txt")[0]
        File syn_SeqToProteinMap = glob("${output_phrp}/*_syn_SeqToProteinMap.txt")[0]
    }

    runtime {
        docker: "${docker}"
        memory: "${ramGB} GB"
        cpu: "${ncpu}"
        disks : select_first([disks,"local-disk 100 SSD"])
    }
}
