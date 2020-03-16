workflow proteomics {

    # MASIC
    Int masic_ncpu
    Int masic_ramGB
    String masic_docker
    String? masic_disk
    Array[File] raw_file = []
    File parameter_masic
    

    scatter (i in range(length(raw_file))) {
        call masic { input:
            ncpu = masic_ncpu,
            ramGB = masic_ramGB,
            docker = masic_docker,
            raw_file = raw_file[i],
            parameter_masic = parameter_masic,
            disks = masic_disk,
            output_masic = "masic_output"
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


