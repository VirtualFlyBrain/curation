# Curation records for removing edges from individuals in the KB

The counterpart of `new_metadata`: each row names an existing edge from an Individual to a Class that should be deleted (for example a broad or wrong typing superseded by a newmeta record). Files are TSVs named `deletions_<dataset>_<date>.tsv` with columns (see [deletions_spec.yaml](deletions_spec.yaml)):

 * Individual_id: short form of the Individual, e.g. VFB_jrmc2zmq
 * relation: relation of the edge, as in newmeta records. `is_a` removes the `INSTANCEOF` edge; other relations remove the edge of that type.
 * remove: short form of the Class at the other end, e.g. FBbt_00052753
 * subject_name, remove_label, superseded_by: *optional*, for review only

No YAML file is needed. Connectome deletions files are written in this format by `vfb-curation run` in connectome-curation.

Loading works like `new_metadata`:
 * `working/`: file names and columns are checked.
 * `to_submit/`: the Test job also checks every edge exists in the KB; the Run job deletes them. Run loads `new_metadata` before deletions, so replacement assertions go in first.
 * A row whose edge is not in the KB is reported and fails the run (as an already-loaded newmeta row does), unless `--allow_duplicates` is set.

To review the Cypher a file will run: `cd src && python deletions_to_cypher.py ../records/newmeta_deletions/to_submit/<file>.tsv`
