workflow proteomics_msgfplus {

    meta {
        author: "David Jimenez-Morales"
        version: "v0.3.1"
    }

    # Quantification method
    String quant_method

    # RAW INPUT FILES
    Array[File] raw_file = []
    String results_prefix

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

    # ASCORE (ONLY PTMs)
    Boolean isPTM
    String? ptm_type
    Int? ascore_ncpu
    Int? ascore_ramGB
    String? ascore_docker
    String? ascore_disk
    File? ascore_parameter_p

    # WRAPPER (PlexedPiper)
    Int wrapper_ncpu
    Int wrapper_ramGB
    String wrapper_docker
    String? wrapper_disk
    File sd_fractions
    File sd_references
    File sd_samples
    File? pr_ratio #prioritized inference

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
            quant_method = quant_method
        }

        call msconvert { input:
            ncpu = msconvert_ncpu,
            ramGB = msconvert_ramGB,
            docker = msconvert_docker,
            disks = msconvert_disk,
            raw_file = raw_file[i]
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
            input_mzid = msgf_tryptic.mzid
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
            input_mzid_final = msgf_identification.mzid_final
        }

        call phrp { input:
            ncpu = phrp_ncpu,
            ramGB = phrp_ramGB,
            docker = phrp_docker,
            disks = phrp_disk,
            isPTM = isPTM,
            input_tsv = mzidtotsvconverter.tsv,
            phrp_parameter_m = phrp_parameter_m,
            phrp_parameter_t = phrp_parameter_t,
            phrp_parameter_n = phrp_parameter_n,
            phrp_synpvalue = phrp_synpvalue,
            phrp_synprob = phrp_synprob,
            input_revcat_fasta = msgf_sequences.revcat_fasta
        }

        if(isPTM){
            call ascore { input:
                ncpu = ascore_ncpu,
                ramGB = ascore_ramGB,
                docker = ascore_docker,
                disks = ascore_disk,
                input_syn = phrp.syn,
                input_fixed_mzml = msgf_identification.rename_mzmlfixed,
                ascore_parameter_p = ascore_parameter_p,
                fasta_sequence_db = fasta_sequence_db,
                syn_ModSummary = phrp.syn_ModSummary
            }
        }
    }

    if(isPTM){

        if(defined(pr_ratio)){
            call wrapper_pp_ptm_inference { input:
                ncpu = wrapper_ncpu,
                ramGB = wrapper_ramGB,
                docker = wrapper_docker,
                disks = wrapper_disk,
                fractions =  sd_fractions,
                references = sd_references,
                samples = sd_samples,
                fasta_sequence_db = fasta_sequence_db,
                ptm_type = ptm_type,
                ReporterIons_output_file = masic.ReporterIons_output_file,
                SICstats_output_file = masic.SICstats_output_file,
                syn = phrp.syn,
                syn_ascore = ascore.syn_ascore,
                results_prefix = results_prefix,
                pr_ratio = pr_ratio
            }
        }

        if(!defined(pr_ratio)){
            call wrapper_pp_ptm { input:
                ncpu = wrapper_ncpu,
                ramGB = wrapper_ramGB,
                docker = wrapper_docker,
                disks = wrapper_disk,
                fractions =  sd_fractions,
                references = sd_references,
                samples = sd_samples,
                fasta_sequence_db = fasta_sequence_db,
                ptm_type = ptm_type,
                ReporterIons_output_file = masic.ReporterIons_output_file,
                SICstats_output_file = masic.SICstats_output_file,
                syn = phrp.syn,
                syn_ascore = ascore.syn_ascore,
                results_prefix = results_prefix
            }
        }
    }

    if(!isPTM){
        call wrapper_pp { input:
            ncpu = wrapper_ncpu,
            ramGB = wrapper_ramGB,
            docker = wrapper_docker,
            disks = wrapper_disk,
            fractions =  sd_fractions,
            references = sd_references,
            samples = sd_samples,
            fasta_sequence_db = fasta_sequence_db,
            ReporterIons_output_file = masic.ReporterIons_output_file,
            SICstats_output_file = masic.SICstats_output_file,
            syn = phrp.syn,
            results_prefix = results_prefix
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
        -o sequencedb_folder

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

    File? null
    Int ncpu
    Int ramGB
    String docker
    String? disks
    File raw_file
    File masic_parameter
    String quant_method
    String sample_id = basename(raw_file, ".raw")

    command {
        echo "STEP 0: Ready to run MASIC"

        mono /app/masic/MASIC_Console.exe \
        /I:${raw_file} \
        /P:${masic_parameter} \
        /O:output_masic
    }

    output {
        File? ReporterIons_output_file = if (quant_method == "label-free") then "output_masic/${sample_id}_ReporterIons.txt" else null
        File DatasetInfo_output_file = "output_masic/${sample_id}_DatasetInfo.xml"
        File ScanStats_output_file = "output_masic/${sample_id}_ScanStats.txt"
        File MS_scans_output_file = "output_masic/${sample_id}_MS_scans.csv"
        File MSMS_scans_output_file = "output_masic/${sample_id}_MSMS_scans.csv"
        File ScanStatsEx_output_file = "output_masic/${sample_id}_ScanStatsEx.txt"
        File SICstats_output_file = "output_masic/${sample_id}_SICstats.txt"
        File ScanStatsConstant_output_file = "output_masic/${sample_id}_ScanStatsConstant.txt"
        File SICs_output_file = "output_masic/${sample_id}_SICs.xml"
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

    String sample_id = basename(raw_file, ".raw")
    
    command {
        echo "STEP 1: MSCONVERT - - - - - - - -"

        wine msconvert ${raw_file} \
        --zlib \
        --filter "peakPicking true 2-" \
        -o output_msconvert
    }

    output {
        File mzml = "output_msconvert/${sample_id}.mzML"
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
        -o output_msgf_tryptic/${sample_id}.mzid \
        -d ${seq_file_id}.fasta \
        -conf ${msgf_tryptic_parameter}
        
        echo "LIST RESULTS - - - - - - - - - -"
        ls
        echo "ADIOS - - - - - - - - - -"
    }

    output {
        File mzid = "output_msgf_tryptic/${sample_id}.mzid"
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

    # Create new ouput destination
    String sample_id = basename(input_mzml, ".mzML")
    String ouput_name = sample_id + "_FIXED.mzML"
    #String output_full = output_msconvert_mzrefiner + "/" + ouput_name
    
    command {
        echo "STEP 3A: MSCONVERT-MZREFINE"

        wine msconvert ${input_mzml} \
        -o output_msconvert_mzrefiner \
        --outfile output_msconvert_mzrefiner/${ouput_name} \
        --filter "mzRefiner ${input_mzid} thresholdValue=-1e-10 thresholdStep=10 maxSteps=2" \
        --zlib
    }

    output {
        File mzml_fixed = "output_msconvert_mzrefiner/${ouput_name}"
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

    String sample_id = basename(input_mzid, ".mzid")
    
    command {
        echo "STEP 3B: PPMErrorCharter"

        mono /app/PPMErrorCharterPython.exe \
        -I:${input_mzid} \
        -F:${input_fixed_mzml} \
        -EValue:1E-10 \
        -HistogramPlot:output_ppm_errorcharter/${sample_id}-histograms.png \
        -MassErrorPlot:output_ppm_errorcharter/${sample_id}-masserrors.png \
        -Python
    }

    output {
       File ppm_histogram_png = "output_ppm_errorcharter/${sample_id}-histograms.png"
       File ppm_masserror_png = "output_ppm_errorcharter/${sample_id}-masserrors.png"
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

        echo "Rename _FIXED.mzML to .mzML"
    
        cp ${input_fixed_mzml} ${sample_id}.mzML

        echo "(check that it worked)"
        ls *.mzid

        echo "MSGF+ IDENTIFICATION BEGINs - - - - - - - - - -"

        java -Xmx4000M \
        -jar /app/MSGFPlus.jar \
        -s ${sample_id}.mzML \
        -o output_msgf_identification/${sample_id}_final.mzid \
        -d ${seq_file_id}.fasta \
        -conf ${msgf_identification_parameter}

        cp ${sample_id}.mzML output_msgf_identification/${sample_id}.mzML

        echo "LIST RESULTS - - - - - - - - - -"
        ls -lR
        echo "ADIOS - - - - - - - - - -"
    }

    output {
        File mzid_final = "output_msgf_identification/${sample_id}_final.mzid"
        File rename_mzmlfixed = "output_msgf_identification/${sample_id}.mzML"
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

    # Create new ouput destination
    String sample_id = basename(input_mzid_final, "_final.mzid")
    String ouput_name = sample_id + ".tsv"
    #String output_full = output_mzidtotsvconverter + "/" + ouput_name
    
    command {
        echo "STEP 5:: MzidToTSVConverter"

        mono /app/mzid2tsv/net462/MzidToTsvConverter.exe \
		-mzid:${input_mzid_final} \
		-tsv:output_mzidtotsvconverter/${ouput_name} \
		-unroll -showDecoy
    }

    output {
        File tsv = "output_mzidtotsvconverter/${sample_id}.tsv"
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

    Boolean isPTM
    
    File input_tsv
    String sample_id = basename(input_tsv, ".tsv")

    File phrp_parameter_m
    File phrp_parameter_t
    File phrp_parameter_n
    Float phrp_synpvalue
    Float phrp_synprob
    
    # Create new ouput destination
    String phrp_logfile = sample_id + "_PHRP_LogFile.txt"
    #String output_logfile = output_phrp + "/" + phrp_logfile

    File input_revcat_fasta
    
    command {
        echo "STEP 6: PeptideHitResultsProcRunner"

		mono /app/phrp/PeptideHitResultsProcRunner.exe \
		-I:${input_tsv} \
		-O:output_phrp \
		-M:${phrp_parameter_m} \
		-T:${phrp_parameter_t} \
		-N:${phrp_parameter_n} \
		-SynPvalue:${phrp_synpvalue} \
        -SynProb:${phrp_synprob} \
		-L:output_phrp/${phrp_logfile} \
		-ProteinMods \
		-F:${input_revcat_fasta}
    }

    output {
        File PepToProtMapMTS = "output_phrp/${sample_id}_PepToProtMapMTS.txt"
        File fht = "output_phrp/${sample_id}_fht.txt"
        File syn = "output_phrp/${sample_id}_syn.txt"
        File syn_ModDetails = "output_phrp/${sample_id}_syn_ModDetails.txt"
        File syn_ModSummary = "output_phrp/${sample_id}_syn_ModSummary.txt"
        File syn_ProteinMods = "output_phrp/${sample_id}_syn_ProteinMods.txt"
        File syn_ResultToSeqMap = "output_phrp/${sample_id}_syn_ResultToSeqMap.txt"
        File syn_SeqInfo = "output_phrp/${sample_id}_syn_SeqInfo.txt"
        File syn_SeqToProteinMap = "output_phrp/${sample_id}_syn_SeqToProteinMap.txt"
        File phrp_log_file = "output_phrp/${phrp_logfile}"
    }

    runtime {
        docker: "${docker}"
        memory: "${ramGB} GB"
        cpu: "${ncpu}"
        disks : select_first([disks, "local-disk 100 SSD"])
    }
}

task ascore {
    Int ncpu
    Int ramGB
    String docker
    String? disks
    
    File input_syn
    File input_fixed_mzml

    File ascore_parameter_p

    File fasta_sequence_db

    File syn_ModSummary
    
    # Create new ouput destination
    String seq_file_id = basename(input_syn, "_syn.txt")
    String ascore_logfile = "${seq_file_id}_ascore_LogFile.txt"
    
    command {
        echo "STEP 7 (PTM): Ascore"

        mono /app/ascore/AScore_Console.exe \
        -T:msgfplus \
        -F:${input_syn} \
        -D:${input_fixed_mzml} \
        -MS:${syn_ModSummary} \
        -P:${ascore_parameter_p} \
        -U:${seq_file_id}_syn_plus_ascore.txt \
        -O:output_ascore \
        -Fasta:${fasta_sequence_db} \
        -L:output_ascore/${ascore_logfile}
    }

    output {
        File syn_ascore = "output_ascore/${seq_file_id}_syn_ascore.txt"
        File syn_plus_ascore = "output_ascore/${seq_file_id}_syn_plus_ascore.txt"
        File syn_ascore_proteinmap = "output_ascore/${seq_file_id}_syn_ascore_ProteinMap.txt"
        File output_ascore_logfile = "output_ascore/${ascore_logfile}"
    }

    runtime {
        docker: "${docker}"
        memory: "${ramGB} GB"
        cpu: "${ncpu}"
        disks : select_first([disks,"local-disk 100 SSD"])
    }
}

task wrapper_pp_ptm {
    Int ncpu
    Int ramGB
    String docker
    String? disks

    File samples
    File fractions
    File references

    File fasta_sequence_db

    String ptm_type
    String results_prefix

    # MASIC
    Array[File] ReporterIons_output_file = []
    Array[File] SICstats_output_file = []

    # #PHRP
    Array[File] syn = []

    # #ASCORE
    Array[File?] syn_ascore = []

    command {
        echo "FINAL-STEP: COPY ALL THE FILES TO THE SAME PLACE"

        echo "MASIC"

        mkdir final_output_masic

        cp ${sep=' ' ReporterIons_output_file} final_output_masic
        cp ${sep=' ' SICstats_output_file} final_output_masic

        tar -C final_output_masic -zcvf final_output_masic.tar.gz .

        echo "PHRP"

        mkdir final_output_phrp

        cp ${sep=' ' syn} final_output_phrp

        tar -C final_output_phrp -zcvf final_output_phrp.tar.gz .

        echo "ASCORE"

        mkdir final_output_ascore

        cp ${sep=' ' syn_ascore} final_output_ascore

        tar -C final_output_ascore -zcvf final_output_ascore.tar.gz .

        echo "STUDY DESIGN FOLDER"

        mkdir study_design

        cp ${samples} study_design
        cp ${fractions} study_design
        cp ${references} study_design

        Rscript /app/pp_ptm.R \
        -p ${ptm_type} \
        -i final_output_phrp \
        -a final_output_ascore \
        -j final_output_masic \
        -f ${fasta_sequence_db} \
        -s study_design \
        -o output_plexedpiper \
        -n ${results_prefix}

        echo "-------------------"
        echo "End of PlexedPiper"
        echo "List files"
        ls
        ls output_plexedpiper
    }

    output {
        File final_output_masic_tar = "final_output_masic.tar.gz"
        File final_output_phrp_tar = "final_output_phrp.tar.gz"
        File final_output_ascore = "final_output_ascore.tar.gz"
        File results_rii = glob("output_plexedpiper/*RII-peptide.txt")[0]
        File results_ratio = glob("output_plexedpiper/*ratio.txt")[0]
    }

    runtime {
        docker: "${docker}"
        memory: "${ramGB} GB"
        cpu: "${ncpu}"
        disks : select_first([disks,"local-disk 100 SSD"])
    }
}

task wrapper_pp_ptm_inference {
    Int ncpu
    Int ramGB
    String docker
    String? disks

    File samples
    File fractions
    File references

    File fasta_sequence_db

    String ptm_type
    String results_prefix
    File pr_ratio

    # MASIC
    Array[File] ReporterIons_output_file = []
    Array[File] SICstats_output_file = []

    # #PHRP
    Array[File] syn = []

    # #ASCORE
    Array[File?] syn_ascore = []

    command {
        echo "FINAL-STEP: COPY ALL THE FILES TO THE SAME PLACE"

        echo "MASIC"

        mkdir final_output_masic

        cp ${sep=' ' ReporterIons_output_file} final_output_masic
        cp ${sep=' ' SICstats_output_file} final_output_masic

        tar -C final_output_masic -zcvf final_output_masic.tar.gz .

        echo "PHRP"

        mkdir final_output_phrp

        cp ${sep=' ' syn} final_output_phrp

        tar -C final_output_phrp -zcvf final_output_phrp.tar.gz .

        echo "ASCORE"

        mkdir final_output_ascore

        cp ${sep=' ' syn_ascore} final_output_ascore

        tar -C final_output_ascore -zcvf final_output_ascore.tar.gz .

        echo "STUDY DESIGN FOLDER"

        mkdir study_design

        cp ${samples} study_design
        cp ${fractions} study_design
        cp ${references} study_design

        Rscript /app/pp_ptm.R \
        -p ${ptm_type} \
        -i final_output_phrp \
        -a final_output_ascore \
        -j final_output_masic \
        -f ${fasta_sequence_db} \
        -s study_design \
        -o output_plexedpiper \
        -g ${pr_ratio} \
        -n ${results_prefix}

        echo "-------------------"
        echo "End of PlexedPiper"
        echo "List files--------"
        echo "- Study design -----"
        ls study_design
        echo "- output_plexedpiper -----"
        ls output_plexedpiper
    }

    output {
        File final_output_masic_tar = "final_output_masic.tar.gz"
        File final_output_phrp_tar = "final_output_phrp.tar.gz"
        File final_output_ascore = "final_output_ascore.tar.gz"
        File results_rii = glob("output_plexedpiper/*RII-peptide.txt")[0]
        File results_ratio = glob("output_plexedpiper/*ratio.txt")[0]
    }

    runtime {
        docker: "${docker}"
        memory: "${ramGB} GB"
        cpu: "${ncpu}"
        disks : select_first([disks,"local-disk 100 SSD"])
    }
}

task wrapper_pp {
    Int ncpu
    Int ramGB
    String docker
    String? disks
    String results_prefix

    File samples
    File fractions
    File references

    File fasta_sequence_db

    # MASIC
    Array[File] ReporterIons_output_file = []
    Array[File] SICstats_output_file = []

    # #PHRP
    Array[File] syn = []

    command {
        echo "FINAL-STEP: COPY ALL THE FILES TO THE SAME PLACE"

        echo "MASIC"

        mkdir final_output_masic

        cp ${sep=' ' ReporterIons_output_file} final_output_masic
        cp ${sep=' ' SICstats_output_file} final_output_masic

        tar -C final_output_masic -zcvf final_output_masic.tar.gz .

        echo "PHRP"

        mkdir final_output_phrp

        cp ${sep=' ' syn} final_output_phrp

        tar -C final_output_phrp -zcvf final_output_phrp.tar.gz .

        echo "STUDY DESIGN FOLDER"

        mkdir study_design

        cp ${samples} study_design
        cp ${fractions} study_design
        cp ${references} study_design
        
        Rscript /app/pp.R \
        -i final_output_phrp \
        -j final_output_masic \
        -f ${fasta_sequence_db} \
        -s study_design \
        -o output_plexedpiper \
        -n ${results_prefix}

        echo "-------------------"
        echo "End of PlexedPiper"
        echo "List files"
        ls
        ls output_plexedpiper
    }

    output {
        File final_output_masic_tar = "final_output_masic.tar.gz"
        File final_output_phrp_tar = "final_output_phrp.tar.gz"
        File results_rii = glob("output_plexedpiper/*RII-peptide.txt")[0]
        File results_ratio = glob("output_plexedpiper/*ratio.txt")[0]
    }

    runtime {
        docker: "${docker}"
        memory: "${ramGB} GB"
        cpu: "${ncpu}"
        disks: select_first([disks,"local-disk 100 SSD"])
    }
}
