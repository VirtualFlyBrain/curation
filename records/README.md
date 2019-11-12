# Image curation overview

This curation system currently only supports adding images with a single specified anatomical entity per image.

Directory structure:

```
/records
   /working    # Records here are checked for syntax only
   /to_submit  # Records here run through the full set of checks, 
                 including loading into test DB. A Jenkins job is used 
                 to load passing records from here into the KB.
   /archive    # Submitted records are archived here
```

Curation file naming: type_DataSetName_YYMMDD

Types:
   -  DataSet: Add new dataset.  [YAML spec](YAML spec)
   -  Common: YAML file specifying common fields for a curation record (e.g. template) - use in combination with Anat, EP, Split.  [YAML spec](YAML spec)
   -  Anat: Add new anatomical image. [YAML spec](YAML spec)
   -  EP: Add new expression pattern image. [YAML spec](YAML spec)
   -  Split: Add new split image. [YAML spec](YAML spec)
   -  Free: Extend annotation on an existing image. [YAML spec](YAML spec)

For me details please see [Curation Guide (wiki)](https://github.com/VirtualFlyBrain/curation/wiki/Curation-wiki--Home)
