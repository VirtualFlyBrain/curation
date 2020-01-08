from .peevish import Record, get_recs
from .curation_writer import CurationWriter, NewImageWriter, NewMetaDataWriter
import warnings

def load_recs(path_to_specs, path_to_recs, endpoint, usr, pwd):
    records = [r for r in get_recs(path_to_recs=path_to_recs,
                                   spec_path=path_to_specs) if r]
    stat = True
    if len(records) == 0:
        print("No records to check in: " + path_to_recs)
    else:
        print("Test loading %d record(s)." % len(records))

    for r in records:
        print("Test loading %s" % r.cr.path)
        if r.gross_type == 'new_images':
            niw = NewImageWriter(endpoint, usr, pwd, r)  # niw rolls appropriate dicts
            # roll lookups (from configs)
            print()  # Do stuff
            # Could potentially simplify from here and embed in CurationWriter...
            if type == 'ep':
                print()  # Do stuff
                # Attempt to add split classes
                # load rows
                if not niw.stat: stat = False
            elif type == 'split':
                print()  # Do stuff
                # Attempt to add split classes
                # load rows
                if not niw.stat: stat = False
            elif type == 'anat':
                # Check FlyBase (from configs) & add types if poss
                # load rows
                print()  # Do stuff
                if not niw.stat: stat = False
            else:
                warnings.warn("Unknown record type: %s" % r.type)
                stat = False
        elif r.gross_type == 'new_metadata':
            print()  # Do stuff
            nmw = NewMetaDataWriter(endpoint, usr, pwd, r)  # nmw rolls appropriate dicts
            nmw.write_rows()
            nmw.commit()
            # check relations !!!
            # roll lookups (from configs)
            # Check FlyBase (from configs)
            # load rows (wrap rolling VfbInd)
            if not nmw.stat: stat = False

        elif r.gross_type == 'new_dataset':
            print()  # Do stuff # STUB
        else:
            warnings.warn("Unknown record gross type: %s" % r.gross_type)
            stat = False

    return stat


