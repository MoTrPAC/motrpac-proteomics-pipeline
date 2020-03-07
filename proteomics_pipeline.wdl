workflow proteomics {

    # MASIC
    Int masic_ncpu
    Int masic_ramGB
    String masic_docker
    Array[File] raw_file = []
    File parameter_masic

    scatter (i in range(length(raw_file))) {
        call masic { input:
            ncpu = masic_ncpu,
            ramGB = masic_ramGB,
            docker = masic_docker,
            raw_file = raw_file[i],
            parameter_masic = parameter_masic
        }
    }

}

task masic {
    Int ncpu
    Int ramGB
    String docker
    File raw_file
    File parameter_masic
    
    command {
        echo "Ready to run MASIC"

        mono /app/masic/MASIC_Console.exe \
        /I:${raw_file} \
        /P:${parameter_masic}
    }

    output {
        Array[File] DatasetInfo_output_file = glob("*_DatasetInfo.xml")
        Array[File] MSMS_scans_output_file = glob("*_MSMS_scans.csv")
        Array[File] MS_scans_output_file = glob("*_MS_scans.csv")
        Array[File] ReporterIons_output_file = glob("*_ReporterIons.txt")
        Array[File] SICs_output_file = glob("*_SICs.xml")
        Array[File] SICstats_output_file = glob("*_SICstats.txt")
        Array[File] ScanStats_output_file = glob("*_ScanStats.txt")
        Array[File] ScanStatsConstant_output_file = glob("*_ScanStatsConstant.txt")
        Array[File] ScanStatsEx_output_file = glob("*_ScanStatsEx.txt")
    }

    runtime {
        docker: "${docker}"
        memory: "${ramGB} GB"
        cpu: "${ncpu}"
    }
}


