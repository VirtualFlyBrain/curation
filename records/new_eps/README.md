# Curation records for expression pattern classes of single drivers

Each row adds the expression pattern class of one driver (a GAL4, LexA, QF... transposon or insertion), with no image. Use it when VFB needs the class but FlyBase has no expression curation for the driver, so the data release's FlyBase expression import doesn't make it: e.g. RNA-seq samples of cells sorted by the driver (vfb-EPseq-ontology), which are instances of the class. Split lines go in `new_splits`; images of a driver's expression pattern in `new_images` (`ep_*` records), which add the class themselves.

Files are TSVs named `ep_<dataset>_<date>.tsv` with columns (see [ep_spec.yaml](ep_spec.yaml)):

 * driver_id: FlyBase id of the driver, FBtp (or FBti where FlyBase has no transposon), e.g. FBtp0131830
 * driver: FlyBase name of the driver, e.g. P{NPFR-GAL4.T}; give driver_id or driver, or both (they must agree)
 * comment: *optional*, for review only

No YAML file is needed.

The class is made by the same code as the FlyBase expression import (VFB_neo4j `FeatureMover.generate_expression_patterns`), so it is the same node the import would make if FlyBase later curates the driver's expression:

 * `VFBexp_<FBid>` (:Class:Expression_pattern), label `<driver> expression pattern`, synonyms from the driver's FlyBase synonyms
 * SUBCLASSOF expression pattern (CARO_0030002); `expresses` the driver
 * the driver as a :Feature (FlyBase label, synonyms, SO type)

The import also links a curated driver's FlyBase alleles and genes, in the production database only; like the classes `new_images` adds, these classes don't have those links.

Loading works like `new_splits`: any row that can't be loaded (driver not in FlyBase or not an FBtp/FBti, name and id disagree, the class label already used by another class) fails the whole record before anything is written. A class already in the KB is merged, so resubmitting a record changes nothing. Classes load before `new_images`.
