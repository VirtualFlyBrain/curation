from .peevish import get_recs
from .curation_writer import NewImageWriter, NewMetaDataWriter
import warnings

def load_recs(path_to_specs, path_to_recs, endpoint, usr, pwd, commit=False, verbose=False):
    records = [r for r in get_recs(path_to_recs=path_to_recs,
                                   spec_path=path_to_specs)]
    if False in records:
        stat = False
    else:
        stat = True
    if (len(records) == 0) or (len(records) == 1 and not records[0]):
        print("No valid records to check in: " + path_to_recs)
    else:
        print("Test loading %d record(s)." % len(records))

    for r in records:
        if not r:
            continue
        print("Test loading %s" % r.cr.path)
        if r.gross_type == 'new_images':
            niw = NewImageWriter(endpoint, usr, pwd, r)  # niw rolls appropriate dicts
            if 'Start' in r.y.keys():
                niw.write_rows(start=r.y['Start'], verbose=verbose)
            else:
                niw.write_rows(verbose=verbose)
            if commit:
                niw.commit(verbose=verbose)
            if not niw.stat:
                    stat = False

        elif r.gross_type == 'new_metadata':
            nmw = NewMetaDataWriter(endpoint, usr, pwd, r)  # nmw rolls appropriate dicts
            nmw.write_rows(verbose=verbose)
            if commit:
                nmw.commit(verbose=verbose)
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


