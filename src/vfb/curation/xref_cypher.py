"""Cypher for new_xrefs records.

Kept free of database dependencies so the checks can be generated and tested offline. Xref edges are written by
VFB_neo4j's kb_owl_edge_writer.add_xref (one edge per accession); this module only builds the read-only checks.
"""
import re

SHORT_FORM = re.compile(r'^[A-Za-z]+_[A-Za-z0-9]+$')
SITE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.\-]*$')
ACCESSION = re.compile(r'^[A-Za-z0-9_.\-]+(:[A-Za-z0-9_.\-]+)*$')


def check_statement(individual, site, accession):
    """Counts of the Individual, the Site and existing xref edges with this accession (as i, s, n).

    Loaders write xrefs as hasDbXref edges and the nightly kbw-backup maintenance renames them to
    database_cross_reference (vfb-k8s kbw-backup.yaml), so both types count."""
    return ("OPTIONAL MATCH (i:Individual {short_form: '%s'}) "
            "OPTIONAL MATCH (s:Site {short_form: '%s'}) "
            "OPTIONAL MATCH (i)-[r:database_cross_reference|hasDbXref]->(s) WHERE r.accession = ['%s'] "
            "RETURN count(DISTINCT i) AS i, count(DISTINCT s) AS s, count(r) AS n" % (individual, site, accession))


def xref_rows(rows):
    """Validate rows (dicts with Individual_id, site, accession).

    Returns (checked, failures): checked is a list of (row_index, individual, site, accession, cypher);
    failures lists rows that can't be turned into a safe statement, in the loader's report format.
    """
    checked, failures = [], []
    for i, row in enumerate(rows):
        ind = str(row['Individual_id']).strip()
        site = str(row['site']).strip()
        acc = str(row['accession']).strip()
        context = '%s %s:%s' % (ind, site, acc)
        for name, value, pattern in (('Individual_id', ind, SHORT_FORM), ('site', site, SITE),
                                     ('accession', acc, ACCESSION)):
            if not pattern.match(value):
                failures.append({'context_name': name, 'context': context, 'message': 'not valid: %r' % value})
                break
        else:
            checked.append((i, ind, site, acc, check_statement(ind, site, acc)))
    return checked, failures
