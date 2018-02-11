# Image curation overview

This curation system currently only supports adding images with a single specified anatomical entity per image.

Images are curated as pairs of files with the same name but different extensions:

* \<some curation filename\>.yaml: General information applicable to all entries in partner tsv files.
  * Key names: 
    * 'Imaging_type': the label of an imaging type from FBbi.  Currently supported imaging types are: 
      "computer graphic"; "confocal micropcopy"; ""; "schematic"
    * 'Template': The name (label) of a template in the KB to which the image is registered.
    * 'DataSet': The name (label) of a DataSet in the KB
    * 'Site': The name of a third-party site with pages for entites specified in curation
    
* \<some curation filename\>.tsv: A TSV file specifying details of depicted entities.
  * Values:  Where an ontology ID is specified, please use the OWL-style short_form identifier.  Multiple entries should be separated with a '|'.
  * Header names: 
    * label: *Compulsory*. The primary label for the 
    * anatomical_types: *Compulsory*. A single anatomical that classifies the depicted entity.
    * Reasons for classification: "A free text comment recording reasons for classification."
    * part_of: *Compulsory*. One or more FBbt identifiers for anatomical entities the depicted entity is part of.
    * expresses: *Optional*. One or more FlyBase identifiers for markers whose expression is depicted in the image and which mark the depicted entity. 
    * overlaps: *Optional*. One or more FBbt identifiers for entities which which the depicted entity overlaps.
    * has_synaptic_terminal_in: *Optional*. One or more FBbt identifiers for entities which which the depicted entity has synaptic terminals in.
    * has_postsynaptic_terminal_in: *Optional*. One or more FBbt identifiers for entities which which the depicted entity has postsynaptic terminals in.
    * has_presynaptic_terminal_in: *Optional*. One or more FBbt identifiers for entities which which the depicted entity has presynaptic terminals in.
    * develops_from: *Optional*. One or more FBbt identifiers for entities which which the depicted entity develops from.
    * accession: Optional. An accession that can be used to roll a link to this entity on 'Site'.
    * centre_point: *Optional*. The x,y,z co-ordinated of the centre-point of the entity depicted. Co-ordinates refer to the stack to which the entity is registered.
    * voxel_volume: *Optional*.  The number of voxels (segmented) corresponding to the depicted entity in a the image.  Voxel numbers correspond to those of the stack to which the entity is registered.
    
    
    
