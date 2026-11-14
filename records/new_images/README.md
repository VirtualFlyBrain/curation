# Image curation overview

This curation system currently only supports adding images with a single specified anatomical entity per image.

Directory structure:

```
/records
    /new_images
        /working    # Records here are checked for syntax only
        /to_submit  # Records here run through the full set of checks, 
                       including loading into test DB. A Jenkins job is used 
                       to load passing records from here into the KB.
        /archive    # Submitted records are archived here
```

Curation file naming: type_DataSetName_YYMMDD

Types:
   -  *Common:* YAML file specifying common fields for a curation record (e.g. template) - use in combination with Anat, EP, Split.  [YAML spec](https://github.com/VirtualFlyBrain/curation/blob/master/records/new_images/common_fields_spec.yaml)
   -  *Anat:* Add new anatomical image. [YAML spec](https://github.com/VirtualFlyBrain/curation/blob/master/records/new_images/anat_spec.yaml)
   -  *EP:* Add new expression pattern image. [YAML spec](https://github.com/VirtualFlyBrain/curation/blob/master/records/new_images/ep_spec.yaml)
   -  *Split:* Add new split image. [YAML spec](https://github.com/VirtualFlyBrain/curation/blob/master/records/new_images/split_spec.yaml)
   -  *Free:* Extend annotation on an existing image. [YAML spec](YAML spec)

For more details please see [Curation Guide (wiki)](https://github.com/VirtualFlyBrain/curation/wiki/Curation--Manual-Wiki)

## Reruns and partly loaded records

`src/assign_ids.py` writes each row's `anat_id` into the record before anything is loaded, so a rerun reuses the same ids. On a rerun, `NewImageWriter.find_already_loaded` looks up the record's ids in the KB:

- **id not in the KB:** loaded as normal.
- **id in the KB with this record's DataSet (`has_source`):** treated as loaded and skipped.
- **id in the KB with no DataSet, or another DataSet:** the row fails ("cannot be reused").

A load writes all of a record's nodes first, then its edges one type at a time across the whole record (INSTANCEOF, then sources, xrefs, part_of, channel edges...). A run stopped during the commit (connection drop, workflow time limit) therefore leaves **every** image node in the KB with only some of its edges, often without `has_source`. No row is loaded completely, so there are no "loaded rows" to separate out.

To finish a partly loaded record:
1. Check the record's images in the KB: node, label and every expected edge, per row.
2. Rows complete in the KB can be moved out to an archived copy; leave the rest in `to_submit/` (a new file name with today's date is fine), **keeping their `anat_id`s**.
3. Rerun with `--allow_duplicates` (Argo `-p allow-duplicates=true`). Ids with this record's DataSet or no DataSet are then written again rather than skipped or rejected. Every node and edge write is a MERGE, so this only adds the missing edges. An id with another DataSet still fails.

Do not blank the `anat_id`s to get round the check: the rerun would mint new ids and leave the half-written images in the KB as duplicates. Do not repair edges with ad hoc Cypher.

Without `--allow_duplicates`, a row whose image already has `has_source` is skipped even if later edge types are missing, so after a run stopped during its commit, always rerun with `--allow_duplicates`.
