from .peevish import get_recs
from .curation_writer import NewImageWriter, NewMetaDataWriter
import warnings

def load_recs(path_to_specs, path_to_recs, endpoint, usr, pwd, commit=False, verbose=False, import_filepath='', allow_duplicates=False):
    records = [r for r in get_recs(path_to_recs=path_to_recs, spec_path=path_to_specs)]
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
            if verbose:
                print(f"Initializing NewImageWriter for {r.cr.path}")
            niw = NewImageWriter(endpoint, usr, pwd, r, import_file_path=import_filepath)  # niw rolls appropriate dicts
            if not niw.stat:
                stat = False
                warnings.warn("%s is not a valid record, not attempting to write" % str(r.cr))
                continue
            if 'Start' in r.y.keys():
                if verbose:
                    print(f"Writing rows starting from {r.y['Start']} for {r.cr.path}")
                niw.write_rows(start=r.y['Start'], verbose=verbose, allow_duplicates=allow_duplicates)
            else:
                if verbose:
                    print(f"Writing rows for {r.cr.path}")
                niw.write_rows(verbose=verbose, allow_duplicates=allow_duplicates)
            if not niw.stat:
                stat = False
                continue
            if commit:
                if verbose:
                    print(f"Committing changes for {r.cr.path}")
                niw.commit(verbose=verbose)
            if not niw.stat:
                stat = False

        elif r.gross_type == 'new_metadata':
            if verbose:
                print(f"Initializing NewMetaDataWriter for {r.cr.path}")
            nmw = NewMetaDataWriter(endpoint, usr, pwd, r)  # nmw rolls appropriate dicts
            if not nmw.stat:
                stat = False
                warnings.warn("%s is not a valid record, not attempting to write" % str(r.cr))
                continue
            if verbose:
                print(f"Writing metadata rows for {r.cr.path}")
            nmw.write_rows(verbose=verbose, allow_duplicates=allow_duplicates)
            if not nmw.stat:
                stat = False
                continue
            if commit:
                if verbose:
                    print(f"Committing changes for {r.cr.path}")
                nmw.commit(verbose=verbose)
            if not nmw.stat:
                stat = False

        elif r.gross_type == 'new_dataset':
            if verbose:
                print(f"Processing new dataset for {r.cr.path}")
            # Placeholder for future dataset processing logic
        else:
            warnings.warn("Unknown record gross type: %s" % r.gross_type)
            stat = False

    return stat
