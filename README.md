**# NARIS**



**### Network-Assisted Anti-Forensics Detection & Incident Reconstruction System**



[![Version]\(https\://img.shields.io/badge/version-1.0.0-blue)]\(https\://github.com/SN272/NARIS/releases)

[![Status]\(https\://img.shields.io/badge/status-research%20prototype-orange)]\(https\://github.com/SN272/NARIS)



NARIS is a research-oriented digital forensics prototype that

investigates how independent network evidence can support the

reconstruction of cyber incidents when host-based forensic evidence has

been degraded by anti-forensic activity.



The project uses controlled experiments to compare incident

reconstruction from host evidence, network evidence, and their

combination. Its central research question is whether network-side

observations can improve the completeness and reliability of an incident

reconstruction when host artefacts are missing, altered, or otherwise

degraded.



\> **\*\*Research status:\*\*** NARIS v1.0 is an experimental research prototype.

\> Results produced using timestamp-offset adjustment are provisional and

\> must not be interpreted as independently validated final findings.



**## Table of contents**



\-   [Research motivation]\(#research-motivation)

\-   [Objectives]\(#objectives)

\-   [Research approach]\(#research-approach)

\-   [Experimental design]\(#experimental-design)

\-   [Reconstruction modes]\(#reconstruction-modes)

\-   [Evaluation]\(#evaluation)

\-   [Dataset and current status]\(#dataset-and-current-status)

\-   [Dashboard]\(#dashboard)

\-   [Repository contents]\(#repository-contents)

\-   [Installation and execution]\(#installation-and-execution)

\-   [Experimental status and

    limitations]\(#experimental-status-and-limitations)

\-   [Reproducibility]\(#reproducibility)

\-   [Roadmap]\(#roadmap)

\-   [Citation]\(#citation)

\-   [License]\(#license)



**## Research motivation**



Digital forensic investigations often rely on host artefacts such as

file-system metadata, event logs, execution traces, and application

records to establish what happened during a cyber incident.

Anti-forensic actions can remove, alter, or manipulate these artefacts,

making host-only reconstruction incomplete or misleading.



Network activity can provide an independent source of evidence. NARIS

explores the use of network observations alongside surviving host

artefacts to assess whether incident events can be reconstructed more

effectively under controlled host-evidence degradation.



NARIS does not assume that network evidence can replace host forensics;

it studies the additional investigative value and limitations of

combining evidence sources.



**## Objectives**



\-   Establish controlled cyber-incident ground truth for repeatable

    experiments.

\-   Apply defined levels of host-evidence degradation.

\-   Collect host artefacts and independent network evidence.

\-   Reconstruct incidents using host-only, network-only, and combined

    evidence.

\-   Compare reconstructed events against ground truth strictly during

    evaluation.

\-   Quantitatively assess reconstruction quality and evidence coverage.

\-   Visualize experimental results for analysis and reporting.



**## Research approach**



1\.  **\*\*Controlled execution:\*\*** Execute a defined incident scenario in an

    isolated virtual lab and record ground-truth events.

2\.  **\*\*Evidence acquisition:\*\*** Collect host artefacts and network traffic

    associated with the execution.

3\.  **\*\*Anti-forensic degradation:\*\*** Apply controlled degradation to host

    evidence at the selected experimental level.

4\.  **\*\*Evidence processing:\*\*** Analyze surviving host artefacts and

    network observations independently.

5\.  **\*\*Incident reconstruction:\*\*** Generate timelines using the selected

    reconstruction mode.

6\.  **\*\*Evaluation:\*\*** Compare reconstructed events with ground truth and

    calculate evaluation metrics.

7\.  **\*\*Analysis and visualization:\*\*** Aggregate results and generate

    dashboard views and report figures.



Ground truth is used as the evaluation reference. It is not supplied to

the reconstruction process.



**## Experimental design**



**### Scenario S1**



The current documented experimental dataset focuses on \*\*S1:

Unauthorized File Access and Simulated Exfiltration\*\*. The scenario

models a controlled sequence of file creation/access, staging, and

simulated transfer activity in an isolated lab.



The scenario is intended for controlled forensic experimentation and

does not perform real-world data exfiltration.



**### Host-evidence degradation**



The experiment uses five degradation levels:



  Level   Description

  ------- ---------------------------------------

  L0      Baseline / no intentional degradation

  L1      Degradation level 1

  L2      Degradation level 2

  L3      Degradation level 3

  L4      Degradation level 4



The precise operations applied at each level are defined by the

experiment configuration and degradation manifests. Consult those

artefacts when reproducing a particular trial.



**## Reconstruction modes**



  -----------------------------------------------------------------------

  Mode                                Evidence used

  ----------------------------------- -----------------------------------

  Host-only                           Surviving host forensic artefacts



  Network-only                        Captured network evidence



  Combined                            Host evidence with network evidence

                                      used for corroboration and

                                      reconstruction

  -----------------------------------------------------------------------



**## Evaluation**



Reconstructed timelines are evaluated against the experiment's

ground-truth event records. The project tracks:



\-   **\*\*Event precision:\*\*** Proportion of reconstructed events that

    correctly match ground-truth events.

\-   **\*\*Event recall:\*\*** Proportion of ground-truth events recovered by the

    reconstruction.

\-   **\*\*F1-score:\*\*** Harmonic mean of event precision and recall.

\-   **\*\*Reconstruction completeness:\*\*** Coverage of ground-truth incident

    events in the reconstructed timeline.

\-   **\*\*Timestamp error:\*\*** Difference between reconstructed event

    timestamps and corresponding ground-truth timestamps.

\-   **\*\*Event-order accuracy:\*\*** Correctness of the reconstructed

    chronological ordering.

\-   **\*\*Evidence coverage:\*\*** Coverage of relevant events by the available

    evidence sources.



The matching tolerance and metric implementation are defined in the

evaluation code. Results should be interpreted with the corresponding

experiment configuration, evidence availability, and limitations.



**## Dataset and current status**



The current S1 experimental records include:



\-   49 valid trials in the ground-truth dataset, with five ground-truth

    events per trial (245 ground-truth events).

\-   40 L1--L4 trials with host evidence and per-trial network captures

    (10 trials per level).

\-   Nine L0 trials with ground truth but without comparable host/network

    evidence for the current L1--L4 reconstruction analysis.

\-   120 generated reconstruction outputs for the 40 L1--L4 trials across

    three reconstruction modes.



An infrastructure-validation trial is excluded from the valid

experimental-trial count. Availability records may include trial folders

that do not produce a comparable reconstruction output; availability-row

counts should not be interpreted as evaluated trial-mode outputs.



These counts describe the current experimental records and may change as

the dataset is validated and expanded. Refer to the generated CSV and

JSON result files for the exact data used in a particular analysis.



**## Dashboard**



The Streamlit dashboard presents experimental results and visual

summaries.



**\*\*Live dashboard:\*\*** Replace this line with the deployed Streamlit

Community Cloud URL.



Run the dashboard locally using:



\`\`\` bash

python -m streamlit run dashboard.py

\`\`\`



**## Repository contents**



  -------------------------------------------------------------------------

  Path                                  Purpose

  ------------------------------------- -----------------------------------

  \`dashboard.py\`                        Streamlit research dashboard



  \`run_naris_reconstruction.py\`         Reconstruction and evaluation entry

                                        point



  \`naris_pipeline/\`                     Reconstruction and evaluation

                                        implementation



  \`results/naris_v1/\`                   Baseline NARIS v1.0 results



  \`export_naris_figures.py\`             Exports report figures from result

                                        files



  \`results/naris_v1/report_figures/\`    Baseline report figures, when

                                        generated



  \`naris_offset_adjustment.py\`          Separate provisional

                                        timestamp-offset analysis utility



  \`results/naris_v1_offset_adjusted/\`   Provisional offset-adjusted

                                        outputs, separate from baseline

                                        results

  -------------------------------------------------------------------------



Additional directories may contain scenario-specific scripts, experiment

plans, evidence-preparation utilities, and supporting documentation.

Their contents depend on the checked-out repository revision.



**## Installation and execution**



**### Requirements**



\-   Python 3.x

\-   pip

\-   Packages required by the reconstruction and dashboard scripts



Install dependencies from the repository's \`requirements.txt\`:



\`\`\` bash

python -m pip install -r requirements.txt

\`\`\`



If \`requirements.txt\` is not present in the checked-out revision,

install the packages used by the relevant scripts, including:



\`\`\` bash

python -m pip install pandas scapy streamlit

\`\`\`



**### Run reconstruction**



From the repository root:



\`\`\` bash

python run_naris_reconstruction.py --dataset experiment_data/naris_v1/final_dataset --output results/naris_v1

\`\`\`



The dataset path must exist in the local checkout. If your dataset is

stored elsewhere, supply its actual path. Preserve original evidence

when preparing derived analysis outputs.



**### Run dashboard**



\`\`\` bash

python -m streamlit run dashboard.py

\`\`\`



**### Export report figures**



After the corresponding result files have been generated:



\`\`\` bash

python export_naris_figures.py

\`\`\`



Check the script's configured input and output paths before running it

if your results are stored elsewhere.



**## Experimental status and limitations**



NARIS v1.0 is a research prototype. Outputs must be interpreted in the

context of the experiment design and the evidence available for each

trial.



**### Timestamp-offset investigation**



During analysis of the current L1--L4 network captures, a consistent

difference was observed between network-derived transfer timestamps and

corresponding ground-truth timestamps. The observed difference was

approximately 663.4 seconds across the examined trials.



A separate offset-adjusted result set was generated for exploratory

analysis. These outputs are stored under

\`results/naris_v1_offset_adjusted/\` and are **\*\*provisional\*\***. The

underlying timestamp discrepancy has not yet been conclusively explained

or independently validated. Offset-adjusted metrics and figures must not

be presented as final validated findings.



The baseline results under \`results/naris_v1/\` and provisional adjusted

results under \`results/naris_v1_offset_adjusted/\` are separate result

sets and should not be mixed.



**### Evidence availability**



The current L0 records do not provide comparable host and network

evidence for the L1--L4 reconstruction analysis. L0 should not be

treated as having the same evidence coverage or reconstruction basis as

L1--L4.



**### Interpretation**



\-   A reconstructed event is not automatically proof of malicious

    intent.

\-   Network evidence may corroborate particular actions without

    independently recovering every host-side event.

\-   Results depend on the scenario, collection configuration,

    degradation operation, parser behavior, and event-matching rules.

\-   The prototype is intended for controlled research and education, not

    as a production incident-response platform.



**## Reproducibility**



For reproducible experiments:



\-   Preserve original evidence and its hashes.

\-   Keep original and degraded host evidence distinguishable.

\-   Retain trial identifiers, run identifiers, scenario identifiers, and

    degradation-level metadata.

\-   Record the exact software/configuration revision used for each

    experiment.

\-   Keep derived or corrected artefacts separate from original captures.

\-   Use ground truth only for evaluation, not as reconstruction input.

\-   Report missing evidence and excluded trials explicitly.



Do not overwrite original PCAP files, host artefacts, or ground-truth

records when preparing derived outputs.



**## Roadmap**



**### NARIS v1.0**



\-   Controlled experimental framework.

\-   Host and network evidence collection.

\-   Host-only, network-only, and combined reconstruction.

\-   Quantitative evaluation and visualization.

\-   Research prototype and experimental dataset.



**### NARIS v2.0**



Planned future work includes:

- Improved modular architecture and maintainability.
- Enhanced evidence processing and detection.
- More robust event correlation and reconstruction.
- Expanded experimental validation and scenario coverage.
- Improved handling and reporting of timestamp inconsistencies.
- Further dashboard and analysis capabilities.



The roadmap is subject to experimental findings and implementation

progress. Planned capabilities should not be interpreted as features

already delivered in v1.0.

