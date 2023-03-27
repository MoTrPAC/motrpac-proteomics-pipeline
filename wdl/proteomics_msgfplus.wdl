version 1.0

workflow proteomics_msgfplus {

    meta {
        author: "David Jimenez-Morales"
        version: "v0.4.0"

        task_labels: {
            msgf_sequences: {
                task_name: 'MSGF+ Process Sequence DB',
                description: 'Preprocess the sequence database for MSGF+'
            },
            masic: {
                task_name: 'MASIC',
                description: 'Extract reporter ion peaks from MS2 spectra and create Selected Ion'
            },
            msconvert: {
                task_name: 'MSConvert',
                description: 'Convert Thermo .raw files to .mzML files (standard XML file format for MS data)'
            },
            msgf_tryptic: {
                task_name: 'MSGF+ Full Tryptic Search',
                description: 'Full tryptic search (for speed). Used in mzrefiner filter in MSConvert and PPMErrorCharter'
            },
            msconvert_mzrefiner: {
                task_name: 'MSConvert (MZRefiner filter)',
                description: 'Use mass error histograms to re-calibrate the m/z values in the .mzML file'
            },
            ppm_errorcharter: {
                task_name: 'PPMErrorCharter',
                description: 'Plot the mass error histograms before and after in silico recalibration'
            },
            msgf_identification: {
                task_name: 'MS-GF+ Partial Tryptic Search',
                description: 'Identify peptides using a partially tryptic search'
            },
            mzidtotsvconverter: {
                task_name: 'mzID to TSV Converter',
                description: 'Create a tab-separated value file listing peptide IDs required for PeptideHitResultsProcessor'
            },
            phrp: {
                task_name: 'PeptideHitResultsProcessor',
                description: 'Create tab-delimited files required for Ascore; files contain peptide IDs, unique sequence info, and residue modification details'
            },
            ascore: {
                task_name: 'AScore',
                description: 'Localize the position of Phosphorylation on S, T, and Y residues in phosphopeptides'
            },
            wrapper_pp: {
                task_name: 'PlexedPiper',
                description: 'Process isobaric labeling (e.g. TMT) proteomics data'
            }
        }
    }

    input {    # Quantification method
        String quant_method

        # RAW INPUT FILES
        Array[File] raw_file = []
        String results_prefix
        String species

        # MASIC
        Int masic_ncpu
        Int masic_ramGB
        String masic_docker
        Int? masic_disk
        File masic_parameter

        # MSCONVERT
        Int msconvert_ncpu
        Int msconvert_ramGB
        String msconvert_docker
        Int? msconvert_disk

        # MS-GF+ SHARED OPTIONS
        Int msgf_ncpu
        Int msgf_ramGB
        String msgf_docker
        Int? msgf_disk
        File fasta_sequence_db
        String sequence_db_name

        # MS-GF+ TRYPTIC
        File msgf_tryptic_mzrefinery_parameter

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
        Int? phrp_disk

        File phrp_parameter_m
        File phrp_parameter_t
        File phrp_parameter_n
        Float phrp_synpvalue
        Float phrp_synprob

        # ASCORE (ONLY PTMs)
        Boolean isPTM
        String? proteomics_experiment
        Int? ascore_ncpu
        Int? ascore_ramGB
        String? ascore_docker
        Int? ascore_disk
        File? ascore_parameter_p

        # WRAPPER (PlexedPiper)
        Int? wrapper_ncpu
        Int? wrapper_ramGB
        String? wrapper_docker
        Int? wrapper_disk
        File? sd_fractions
        File? sd_references
        File? sd_samples
        File? pr_ratio #prioritized inference
        Boolean? unique_only # Unique peptides only (default FALSE)
        Boolean? refine_prior # Refine prior probabilities (default TRUE)
    }

    call msgf_sequences {
        input:
            ncpu = msgf_ncpu,
            ramGB = msgf_ramGB,
            docker = msgf_docker,
            disks = msgf_disk,
            fasta_sequence_db = fasta_sequence_db
    }

    scatter (i in range(length(raw_file))) {
        call masic {
            input:
                ncpu = masic_ncpu,
                ramGB = masic_ramGB,
                docker = masic_docker,
                disks = masic_disk,
                raw_file = raw_file[i],
                masic_parameter = masic_parameter,
                quant_method = quant_method
        }

        call msconvert {
            input:
                ncpu = msconvert_ncpu,
                ramGB = msconvert_ramGB,
                docker = msconvert_docker,
                disks = msconvert_disk,
                raw_file = raw_file[i]
        }

        call msgf_tryptic {
            input:
                ncpu = msgf_ncpu,
                ramGB = msgf_ramGB,
                docker = msgf_docker,
                disks = msgf_disk,
                input_mzml = msconvert.mzml,
                fasta_sequence_db = fasta_sequence_db,
                sequencedb_files = msgf_sequences.sequencedb_files,
                msgf_tryptic_mzrefinery_parameter = msgf_tryptic_mzrefinery_parameter
        }

        call msconvert_mzrefiner {
            input:
                ncpu = msconvert_ncpu,
                ramGB = msconvert_ramGB,
                docker = msconvert_docker,
                disks = msconvert_disk,
                input_mzml = msconvert.mzml,
                input_mzid = msgf_tryptic.mzid
        }

        call ppm_errorcharter {
            input:
                ncpu = msconvert_ncpu,
                ramGB = msconvert_ramGB,
                docker = ppm_errorcharter_docker,
                disks = msconvert_disk,
                input_fixed_mzml = msconvert_mzrefiner.mzml_fixed,
                input_mzid = msgf_tryptic.mzid
        }

        call msgf_identification {
            input:
                ncpu = msgf_ncpu,
                ramGB = msgf_ramGB,
                docker = msgf_docker,
                disks = msgf_disk,
                input_fixed_mzml = msconvert_mzrefiner.mzml_fixed,
                fasta_sequence_db = fasta_sequence_db,
                sequencedb_files = msgf_sequences.sequencedb_files,
                msgf_identification_parameter = msgf_identification_parameter
        }

        call mzidtotsvconverter {
            input:
                ncpu = msconvert_ncpu,
                ramGB = msconvert_ramGB,
                docker = mzidtotsvconverter_docker,
                disks = msconvert_disk,
                input_mzid_final = msgf_identification.mzid_final
        }

        call phrp {
            input:
                ncpu = phrp_ncpu,
                ramGB = phrp_ramGB,
                docker = phrp_docker,
                disks = phrp_disk,
                input_tsv = mzidtotsvconverter.tsv,
                phrp_parameter_m = phrp_parameter_m,
                phrp_parameter_t = phrp_parameter_t,
                phrp_parameter_n = phrp_parameter_n,
                phrp_synpvalue = phrp_synpvalue,
                phrp_synprob = phrp_synprob,
                input_revcat_fasta = msgf_sequences.revcat_fasta
        }

        if (isPTM) {
            call ascore {
                input:
                    ncpu = select_first([ascore_ncpu]),
                    ramGB = select_first([ascore_ramGB]),
                    docker = select_first([ascore_docker]),
                    disks = ascore_disk,
                    input_syn = phrp.syn,
                    input_fixed_mzml = msgf_identification.rename_mzmlfixed,
                    ascore_parameter_p = select_first([ascore_parameter_p]),
                    fasta_sequence_db = fasta_sequence_db,
                    syn_ModSummary = phrp.syn_ModSummary
            }
        }
    }

    if (quant_method == "tmt") {
        call wrapper_pp {
            input:
                ncpu = select_first([wrapper_ncpu]),
                ramGB = select_first([wrapper_ramGB]),
                docker = select_first([wrapper_docker]),
                disks = wrapper_disk,
                fractions = select_first([sd_fractions]),
                references = select_first([sd_references]),
                samples = select_first([sd_samples]),
                fasta_sequence_db = fasta_sequence_db,
                sequence_db_name = sequence_db_name,
                proteomics_experiment = select_first([proteomics_experiment]),
                ReporterIons_output_file = masic.ReporterIons_output_file,
                SICstats_output_file = masic.SICstats_output_file,
                syn = phrp.syn,
                syn_ascore = ascore.syn_ascore,
                results_prefix = results_prefix,
                pr_ratio = pr_ratio,
                species = species,
                unique_only = select_first([unique_only]),
                refine_prior = select_first([refine_prior]),
                isPTM = isPTM
        }
    }
}

task msgf_sequences {
    input {
        Int ncpu
        Int ramGB
        String docker
        Int? disks

        File fasta_sequence_db
        String seq_file_id = basename(fasta_sequence_db, ".fasta")
    }

    # String output_full = output_msgf_tryptic + "/" + output_name

    command <<<
        echo "PRE-STEP: MSGF+ READY TO PROCES SEQUENCE DB"

        # Generate sequence indexes
        java -Xmx4000M -cp /app/MSGFPlus.jar edu.ucsd.msjava.msdbsearch.BuildSA \
        -d ~{fasta_sequence_db} \
        -tda 2 \
        -o sequencedb_folder

        # Compress results
        tar -C sequencedb_folder -zcvf sequencedb_files.tar.gz .
    >>>

    output {
        File sequencedb_files = "sequencedb_files.tar.gz"
        File revcat_fasta = "sequencedb_folder/${seq_file_id}.revCat.fasta"
    }

    runtime {
        docker: "${docker}"
        memory: "${ramGB} GB"
        cpu: "${ncpu}"
        disks : "local-disk ${select_first([disks, 100])} HDD"
    }

    parameter_meta {
        seq_file_id: {
            type: "id"
        }
        fasta_sequence_db: {
            type: "sequence_db"
        }
    }
}

task masic {
    input {
        Int ncpu
        Int ramGB
        Int? disks
        String docker

        File masic_parameter
        File raw_file
        File? null

        String quant_method
        String sample_id = basename(raw_file, ".raw")
    }

    command <<<
        echo "STEP 0: Ready to run MASIC"

        mono /app/masic/MASIC_Console.exe \
        /I:~{raw_file} \
        /P:~{masic_parameter} \
        /O:output_masic
    >>>

    output {
        File? ReporterIons_output_file = if (quant_method == "tmt") then "output_masic/${sample_id}_ReporterIons.txt" else null
        File? RepIonObsRate_output_png_file = if (quant_method == "tmt") then "output_masic/${sample_id}_RepIonObsRate.png" else null
        File? RepIonObsRate_output_txt_file = if (quant_method == "tmt") then "output_masic/${sample_id}_RepIonObsRate.txt" else null
        File? RepIonObsRateHighAbundance_output_file = if (quant_method == "tmt") then "output_masic/${sample_id}_RepIonObsRateHighAbundance.png" else null
        File? RepIonStats_output_file = if (quant_method == "tmt") then "output_masic/${sample_id}_RepIonStats.txt" else null
        File? RepIonStatsHighAbundance_output_file = if (quant_method == "tmt") then "output_masic/${sample_id}_RepIonStatsHighAbundance.png" else null

        File PeakAreaHistogram_output_file = "output_masic/${sample_id}_PeakAreaHistogram.png"
        File PeakWidthHistogram_output_file = "output_masic/${sample_id}_PeakWidthHistogram.png"
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
        disks: "local-disk ${select_first([disks, 100])} HDD"
    }

    parameter_meta {
        sample_id: {
            type: "id"
        }
        masic_parameter : {
            type: "parameter",
            label: "MASIC Parameter File"
        }
        raw_file: {
            label: ".RAW File"
        }
    }
}

task msconvert {
    input {
        Int ncpu
        Int ramGB
        Int? disks
        String docker

        File raw_file
        String sample_id = basename(raw_file, ".raw")
    }

    command <<<
        echo "STEP 1: MSCONVERT - - - - - - - -"

        wine msconvert ~{raw_file} \
        --zlib \
        --filter "peakPicking true 2-" \
        -o output_msconvert
    >>>

    output {
        File mzml = "output_msconvert/${sample_id}.mzML"
    }

    runtime {
        docker: "${docker}"
        memory: "${ramGB} GB"
        cpu: "${ncpu}"
        disks : "local-disk ${select_first([disks, 100])} HDD"
    }

    parameter_meta {
        sample_id: {
            type: "id"
        }
        raw_file: {
            label: ".RAW File"
        }
    }
}

task msgf_tryptic {
    input {
        Int ncpu
        Int ramGB
        String docker
        Int? disks

        File input_mzml
        File fasta_sequence_db
        File sequencedb_files
        File msgf_tryptic_mzrefinery_parameter

        String sample_id = basename(input_mzml, ".mzML")
    }

    String seq_file_id = basename(fasta_sequence_db, ".fasta")

    command <<<
        echo "STEP 2: MS-GF+ TRYPTIC SEARCH"
        ls
        echo "COPY FILES - - - - - - - - - -"

        cp ~{sequencedb_files} .
        ls
        tar xvzf ~{sequencedb_files}

        echo "MSGF+ BEGINs - - - - - - - - - -"

        java -Xmx4000M \
        -jar /app/MSGFPlus.jar \
        -s ~{input_mzml} \
        -o output_msgf_tryptic/~{sample_id}.mzid \
        -d ~{seq_file_id}.fasta \
        -conf ~{msgf_tryptic_mzrefinery_parameter}

        echo "LIST RESULTS - - - - - - - - - -"
        ls
        echo "ADIOS - - - - - - - - - -"
    >>>

    output {
        File mzid = "output_msgf_tryptic/${sample_id}.mzid"
    }

    runtime {
        docker: "${docker}"
        memory: "${ramGB} GB"
        cpu: "${ncpu}"
        disks : "local-disk ${select_first([disks, 100])} HDD"
    }

    parameter_meta {
        sample_id: {
            type: "id"
        }
        input_mzml: {
            label: "mzML File"
        }
        fasta_sequence_db: {
            type: "sequence_db"
        }
        sequencedb_files: {
            label: "Processed Sequence Database Files"
        }
        msgf_tryptic_mzrefinery_parameter: {
            type: "parameter",
            label: "MzRefinery Parameter File"
        }
    }
}

task msconvert_mzrefiner {
    input {
        Int ncpu
        Int ramGB
        String docker
        Int? disks

        File input_mzml
        File input_mzid

        String sample_id = basename(input_mzml, ".mzML")
        # Create new output destination
        String output_name = sample_id + "_FIXED.mzML"
    }

    command <<<
        echo "STEP 3A: MSCONVERT-MZREFINE"

        wine msconvert ~{input_mzml} \
        -o output_msconvert_mzrefiner \
        --outfile output_msconvert_mzrefiner/~{output_name} \
        --filter "mzRefiner ~{input_mzid} thresholdValue=-1e-10 thresholdStep=10 maxSteps=2" \
        --zlib

        # Check if the output_name exists. If it doesn't, create a copy of the input file with the output_name.
        if [ ! -f output_msconvert_mzrefiner/~{output_name} ]; then
            cp ~{input_mzml} output_msconvert_mzrefiner/~{output_name}
        fi
    >>>

    output {
        File mzml_fixed = "output_msconvert_mzrefiner/${output_name}"
    }

    runtime {
        docker: "${docker}"
        memory: "${ramGB} GB"
        cpu: "${ncpu}"
        disks : "local-disk ${select_first([disks, 100])} HDD"
    }

    parameter_meta {
        sample_id: {
            type: "id"
        }
        input_mzml: {
            label: "mzML file"
        }
        input_mzid: {
            label: "mzID file"
        }
    }
}

task ppm_errorcharter {
    input {
        Int ncpu
        Int ramGB
        String docker
        Int? disks

        File input_fixed_mzml
        File input_mzid

        String sample_id = basename(input_mzid, ".mzid")
    }


    command <<<
        echo "STEP 3B: PPMErrorCharter"

        mono /app/PPMErrorCharterPython.exe \
        -I:~{input_mzid} \
        -F:~{input_fixed_mzml} \
        -EValue:1E-10 \
        -HistogramPlot:output_ppm_errorcharter/~{sample_id}-histograms.png \
        -MassErrorPlot:output_ppm_errorcharter/~{sample_id}-masserrors.png \
        -Python
    >>>

    output {
       File ppm_histogram_png = "output_ppm_errorcharter/${sample_id}-histograms.png"
       File ppm_masserror_png = "output_ppm_errorcharter/${sample_id}-masserrors.png"
    }

    runtime {
        docker: "${docker}"
        memory: "${ramGB} GB"
        cpu: "${ncpu}"
        disks : "local-disk ${select_first([disks, 100])} HDD"
    }

    parameter_meta {
        sample_id: {
            type: "id"
        }
        input_fixed_mzml: {
            label: "Fixed mzML file"
        }
        input_mzid: {
            label: "mzID file"
        }
    }
}


task msgf_identification {
    input {
        Int ncpu
        Int ramGB
        String docker
        Int? disks

        File input_fixed_mzml
        File fasta_sequence_db
        File sequencedb_files
        File msgf_identification_parameter
    }

    # Create new output destination
    String sample_id = basename(input_fixed_mzml, "_FIXED.mzML")
    String seq_file_id = basename(fasta_sequence_db, ".fasta")

    command <<<
        echo "STEP 4: MS-GF+ IDENTIFICATION SEARCH - - - - - - - - - -"
        ls
        echo "COPY FILES - - - - - - - - - -"

        cp ~{sequencedb_files} .
        ls
        tar xvzf ~{sequencedb_files}

        echo "Rename *_FIXED.mzML to *.mzML"

        cp ~{input_fixed_mzml} ~{sample_id}.mzML

        echo "MSGF+ IDENTIFICATION BEGINs - - - - - - - - - -"

        java -Xmx4000M \
        -jar /app/MSGFPlus.jar \
        -s ~{sample_id}.mzML \
        -o output_msgf_identification/~{sample_id}_final.mzid \
        -d ~{seq_file_id}.fasta \
        -conf ~{msgf_identification_parameter}

        cp ~{sample_id}.mzML output_msgf_identification/~{sample_id}.mzML

        echo "LIST RESULTS - - - - - - - - - -"
        ls -lR
        echo "ADIOS - - - - - - - - - -"
    >>>

    output {
        File mzid_final = "output_msgf_identification/${sample_id}_final.mzid"
        File rename_mzmlfixed = "output_msgf_identification/${sample_id}.mzML"
    }

    runtime {
        docker: "${docker}"
        memory: "${ramGB} GB"
        cpu: "${ncpu}"
        disks : "local-disk ${select_first([disks, 100])} HDD"
    }

    parameter_meta {
        input_fixed_mzml: {
            label: "Fixed mzML file"
        }
        fasta_sequence_db: {
            type: "sequence_db"
        }
        sequencedb_files: {
            label: "Processed Sequence Database Files"
        }
        msgf_identification_parameter: {
            type: "parameter",
            label: "MSGF+ Identification Parameter File"
        }
    }
}

task mzidtotsvconverter {
    input {
        Int ncpu
        Int ramGB
        String docker
        Int? disks

        File input_mzid_final

        String sample_id = basename(input_mzid_final, "_final.mzid")
    }

    # Create new output destination
    String output_name = sample_id + ".tsv"

    command <<<
        echo "STEP 5:: MzidToTSVConverter"

        mono /app/mzid2tsv/net462/MzidToTsvConverter.exe \
        -mzid:~{input_mzid_final} \
        -tsv:output_mzidtotsvconverter/~{output_name} \
        -unroll -showDecoy
    >>>

    output {
        File tsv = "output_mzidtotsvconverter/${sample_id}.tsv"
    }

    runtime {
        docker: "${docker}"
        memory: "${ramGB} GB"
        cpu: "${ncpu}"
        disks : "local-disk ${select_first([disks, 100])} HDD"
    }

    parameter_meta {
        sample_id: {
            type: "id"
        }
        input_mzid_final: {
            label: "mzID file"
        }
    }
}

task phrp {
    input {
        Int ncpu
        Int ramGB
        String docker
        Int? disks

        File input_tsv

        File phrp_parameter_m
        File phrp_parameter_t
        File phrp_parameter_n
        Float phrp_synpvalue
        Float phrp_synprob

        File input_revcat_fasta

        String sample_id = basename(input_tsv, ".tsv")
    }

    # Create new output destination
    String phrp_logfile = sample_id + "_PHRP_LogFile.txt"

    command <<<
        echo "STEP 6: PeptideHitResultsProcRunner"

        mono /app/phrp/PeptideHitResultsProcRunner.exe \
        -I:~{input_tsv} \
        -O:output_phrp \
        -M:~{phrp_parameter_m} \
        -T:~{phrp_parameter_t} \
        -N:~{phrp_parameter_n} \
        -SynPvalue:~{phrp_synpvalue} \
        -SynProb:~{phrp_synprob} \
        -L:output_phrp/~{phrp_logfile} \
        -ProteinMods \
        -F:~{input_revcat_fasta}
    >>>

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
        disks: "local-disk ${select_first([disks, 100])} HDD"
    }

    parameter_meta {
        sample_id: {
            type: "id"
        }
        input_tsv: {
            label: "Processed TSV File"
        }
        input_revcat_fasta: {
            label: "RevCat FASTA File"
        }
        phrp_parameter_m: {
            type: "parameter",
            label: "PHRP Parameter File"
        }
        phrp_parameter_t: {
            type: "parameter",
            label: "PHRP Parameter File"
        }
        phrp_parameter_n: {
            type: "parameter",
            label: "PHRP Parameter File"
        }
        phrp_synpvalue: {
            type: "parameter",
            label: "PHRP Parameter File"
        }
        phrp_synprob: {
            type: "parameter",
            label: "PHRP Parameter File"
        }
    }
}

task ascore {
    input {
        Int ncpu
        Int ramGB
        String docker
        Int? disks

        File input_syn
        File input_fixed_mzml
        File ascore_parameter_p
        File fasta_sequence_db

        File syn_ModSummary
    }

    # Create new output destination
    String seq_file_id = basename(input_syn, "_syn.txt")
    String ascore_logfile = "${seq_file_id}_ascore_LogFile.txt"

    command <<<
        echo "STEP 7 (PTM): Ascore"

        mono /app/ascore/AScore_Console.exe \
        -T:msgfplus \
        -F:~{input_syn} \
        -D:~{input_fixed_mzml} \
        -MS:~{syn_ModSummary} \
        -P:~{ascore_parameter_p} \
        -U:~{seq_file_id}_syn_plus_ascore.txt \
        -O:output_ascore \
        -Fasta:~{fasta_sequence_db} \
        -L:output_ascore/~{ascore_logfile}
    >>>

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
        disks : "local-disk ${select_first([disks, 100])} HDD"
    }

    parameter_meta {
        input_syn: {
            label: "PHRP Syn File"
        }
        input_fixed_mzml: {
            label: "Fixed MZML File"
        }
        ascore_parameter_p: {
            type: "parameter",
            label: "AScore Parameter File"
        }
        fasta_sequence_db: {
            type: "sequnce_db"
        }
        syn_ModSummary: {
            type: "parameter",
            label: "AScore Parameter File"
        }
    }
}

task wrapper_pp {
    input {
        File? null
        Int ncpu
        Int ramGB
        String docker
        Int? disks

        Boolean isPTM

        File samples
        File fractions
        File references

        File fasta_sequence_db
        String sequence_db_name

        String proteomics_experiment
        String results_prefix
        File? pr_ratio
        String species
        Boolean unique_only
        Boolean refine_prior

        # MASIC
        Array[File?] ReporterIons_output_file = []
        Array[File] SICstats_output_file = []

        # #PHRP
        Array[File] syn = []

        # #ASCORE
        Array[File?] syn_ascore = []
    }

    command <<<
        echo "FINAL-STEP: COPY ALL THE FILES TO THE SAME PLACE"

        echo "MASIC"

        mkdir final_output_masic

        cp ~{sep=" " ReporterIons_output_file} final_output_masic
        cp ~{sep=" " SICstats_output_file} final_output_masic

        tar -C final_output_masic -zcvf final_output_masic.tar.gz .

        echo "PHRP"

        mkdir final_output_phrp

        cp ~{sep=" " syn} final_output_phrp

        tar -C final_output_phrp -zcvf final_output_phrp.tar.gz .

        if ~{isPTM}
        then
            echo "ASCORE"
            mkdir final_output_ascore
            cp ~{sep=" " syn_ascore} final_output_ascore
            tar -C final_output_ascore -zcvf final_output_ascore.tar.gz .
        fi

        echo "STUDY DESIGN FOLDER"
        mkdir study_design

        cp ~{samples} study_design
        cp ~{fractions} study_design
        cp ~{references} study_design

        if ~{isPTM}; then

            Rscript /app/pp.R \
            -p ~{proteomics_experiment} \
            -i final_output_phrp \
            -a final_output_ascore \
            -j final_output_masic \
            -f ~{fasta_sequence_db} \
            -d ~{sequence_db_name} \
            -s study_design \
            -o output_plexedpiper \
            -g ~{default="no-prior" pr_ratio} \
            -n ~{results_prefix} \
            -c "~{species}" \
            -u ~{unique_only} \
            -r ~{refine_prior}
        else
            Rscript /app/pp.R \
            -p ~{proteomics_experiment} \
            -i final_output_phrp \
            -j final_output_masic \
            -f ~{fasta_sequence_db} \
            -d ~{sequence_db_name} \
            -s study_design \
            -o output_plexedpiper \
            -n ~{results_prefix} \
            -c "~{species}" \
            -u ~{unique_only} \
            -r ~{refine_prior}
        fi

        echo "-------------------"
        echo "End of PlexedPiper"
        echo "List files--------"
        echo "- Study design -----"
        ls study_design
        echo "- output_plexedpiper -----"
        ls output_plexedpiper
    >>>

    output {
        File final_output_masic_tar = "final_output_masic.tar.gz"
        File final_output_phrp_tar = "final_output_phrp.tar.gz"
        File? final_output_ascore = if (isPTM == true) then "final_output_ascore.tar.gz" else null
        File results_rii = glob("output_plexedpiper/*RII-peptide.txt")[0]
        File results_ratio = glob("output_plexedpiper/*ratio.txt")[0]
    }

    runtime {
        docker: "${docker}"
        memory: "${ramGB} GB"
        cpu: "${ncpu}"
        disks : "local-disk ${select_first([disks, 100])} HDD"
    }

    parameter_meta {
        samples: {
            type: "parameter",
            label: "Samples File"
        }
        fractions: {
            type: "parameter",
            label: "Fractions File"
        }
        references: {
            type: "parameter",
            label: "References File"
        }
        fasta_sequence_db: {
            type: "sequnce_db"
        }
        ReporterIons_output_file: {
            label: "MASIC ReporterIons Output Files"
        }
        SICstats_output_file: {
            label: "MASIC SICstats Output Files"
        }
        syn: {
            label: "PHRP Syn Files"
        }
        syn_ascore: {
            label: "ASCORE Syn Files"
        }
        pr_ratio: {
            type: "parameter",
            label: "PR Ratio File"
        }
    }
}
