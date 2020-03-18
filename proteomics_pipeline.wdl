workflow proteomics {
    
    # RAW INPUT FILES
    Array[File] raw_file = []

    # MASIC
    Int masic_ncpu
    Int masic_ramGB
    String masic_docker
    String? masic_disk
    
    File parameter_masic
    
    # MSCONVERT
    Int msconvert_ncpu
    Int msconvert_ramGB
    String msconvert_docker
    String? msconvert_disk
    

    scatter (i in range(length(raw_file))) {
        call masic { input:
            ncpu = masic_ncpu,
            ramGB = masic_ramGB,
            docker = masic_docker,
            disks = masic_disk,
            raw_file = raw_file[i],
            parameter_masic = parameter_masic,
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
    }

}

task masic {
    Int ncpu
    Int ramGB
    String docker
    String? disks
    File raw_file
    File parameter_masic
    String output_masic
    
    command {
        echo "Ready to run MASIC"

        mono /app/masic/MASIC_Console.exe \
        /I:${raw_file} \
        /P:${parameter_masic} \
        /O:${output_masic}
    }

    output {
        File ReporterIons_output_file = glob("masic_output/*ReporterIons.txt")[0]
        File DatasetInfo_output_file = glob("masic_output/*DatasetInfo.xml")[0]
        File ScanStats_output_file = glob("masic_output/*ScanStats.txt")[0]
        File MS_scans_output_file = glob("masic_output/*MS_scans.csv")[0]
        File MSMS_scans_output_file = glob("masic_output/*MSMS_scans.csv")[0]
        File ScanStatsEx_output_file = glob("masic_output/*ScanStatsEx.txt")[0]
        File SICstats_output_file = glob("masic_output/*SICstats.txt")[0]
        File ScanStatsConstant_output_file = glob("masic_output/*ScanStatsConstant.txt")[0]
        File SICs_output_file = glob("masic_output/*SICs.xml")[0]
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
        File msconvert_output_file = glob("msconvert_output/*.mzML")[0]
    }

    runtime {
        docker: "${docker}"
        memory: "${ramGB} GB"
        cpu: "${ncpu}"
        disks : select_first([disks,"local-disk 100 SSD"])
    }
}



