# Curation records for adding xrefs to existing individuals in the KB

Each row adds one database cross-reference (a `hasDbXref` edge with an accession) from an existing Individual to an existing Site, e.g. a NeuronBridge link for a connectome neuron. Files are TSVs named `xrefs_<dataset>_<date>.tsv` with columns (see [xrefs_spec.yaml](xrefs_spec.yaml)):

 * Individual_id: short form of the Individual, e.g. VFB_jrmc2zmq
 * site: short form of the Site, e.g. neuronbridge
 * accession: the identifier in that Site, e.g. male-cns:166793 (may contain `:`)
 * subject_name, comment: *optional*, for review only

No YAML file is needed. An Individual can carry several accessions to one Site; each is its own edge (VFB_neo4j#323).

Loading works like `newmeta_deletions`:
 * `working/`: file names and columns are checked.
 * `to_submit/`: the Test job also checks every Individual and Site exists and reports rows whose xref is already in the KB; the Run job adds the rest. Xrefs load last, after `new_images` and `new_splits`, so they can point at entities added in the same run.
 * A row whose Individual or Site is missing, or whose xref is already in the KB, is reported and fails the run, unless `--allow_duplicates` is set (already-loaded rows are then skipped quietly).
