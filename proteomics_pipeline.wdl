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

    # MS-GF+ TRYPTIC
    Int msgf_tryptic_ncpu
    Int msgf_tryptic_ramGB
    String msgf_tryptic_docker
    String? msgf_tryptic_disk

    File fasta_sequence_db
    File msgf_tryptic_parameter

    # PPMErrorCharter
    String ppm_errorcharter_docker


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
            ncpu = msgf_tryptic_ncpu,
            ramGB = msgf_tryptic_ramGB,
            docker = msgf_tryptic_docker,
            disks = msgf_tryptic_disk,
            input_mzml = msconvert.mzml,
            fasta_sequence_db = fasta_sequence_db,
            msgf_tryptic_parameter = msgf_tryptic_parameter,
            output_msgf_tryptic = "msgf_tryptic_output"
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
        echo "Ready to run MASIC"

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
        echo "Ready to run MSCONVERT"

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
    File msgf_tryptic_parameter

    String output_msgf_tryptic

    # Create new ouput destination
    String sample_id = basename(input_mzml, ".mzML")
    String ouput_name = sample_id + ".mzid"
    String output_full = output_msgf_tryptic + "/" + ouput_name
    
    command {
        echo "Ready to run MS-GF+ tryptic search:"

        java -Xmx4000M \
        -jar /app/MSGFPlus.jar \
        -s ${input_mzml} \
        -o ${output_full} \
        -d ${fasta_sequence_db} \
        -conf ${msgf_tryptic_parameter}

    }

    output {
        # File revCat_cnlcp = glob("*.revCat.cnlcp")[0]
        # File revCat_csarr = glob("*.revCat.csarr")[0]
        # File revCat_cseq  = glob("*.revCat.cseq")[0]
        # File revCat_canno = glob("*.revCat.canno")[0]
        # File revCat_fasta = glob("*.revCat.fasta")[0]
        File mzid = glob("${output_msgf_tryptic}/*.mzid")[0]
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
        echo "Step 3A: Ready to run MSCONVERT-MZREFINE"

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

    # Create new ouput destination
    String sample_id = basename(input_mzid, ".mzid")
    
    command {
        echo "Step 3B: PPMErrorCharter"

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


