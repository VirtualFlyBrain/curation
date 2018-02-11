# Curation records for extending annotation of existing entities in the KB

Curation records take the form of a TSV with columns:

 * Individual_ID: Short_form identifier for an Individual in the KB, e.g. VFB_1234567
 * Relation:  The 'safe name'of a relationship in the KB (label with spaces/special characters replaced by '_').
 * Object: The identifier of an Individual or Class in the KB
 * Mapping_comment: *Optional*.  A free text comment describing the evidence for the annotation being added.
 * Mapping_evidence: *Optional*. A list of one or more evidence terms (This field is currently a placeholder).
 * Mapping_references: A list of IDs (FBrf) of publications supporting the mapping. 
 
