from uk.ac.ebi.vfb.neo4j.neo4j_tools import neo4j_connect
from uk.ac.ebi.vfb.neo4j.KB_tools import kb_owl_edge_writer
from .xref_cypher import xref_rows, check_statement
from .peevish import Record
import logging


class NewXrefWriter:
    """Checks and adds the xrefs listed in a new_xrefs record."""

    def __init__(self, endpoint, usr, pwd, record: Record):
        self.endpoint, self.usr, self.pwd = endpoint, usr, pwd
        self.nc = neo4j_connect(endpoint, usr, pwd)
        self.record = record
        self.rows = record.tsv.to_dict('records')
        self.stat = True
        self.failures = []
        self.to_add = []  # (individual, site, accession) not yet in the KB

    def check(self, allow_duplicates=False, verbose=False, chunk_length=1000):
        """Check each row's Individual and Site exist and whether the xref is already there.
        Missing entities are failures; an existing xref is a failure unless allow_duplicates."""
        checked, self.failures = xref_rows(self.rows)
        for start in range(0, len(checked), chunk_length):
            chunk = checked[start:start + chunk_length]
            results = self.nc.commit_list([c[4] for c in chunk])
            if not results:
                self.stat = False
                logging.warning("Query failed for %s, rows %d-%d"
                                % (self.record.cr.path, start, start + len(chunk) - 1))
                continue
            for (_, ind, site, acc, _), res in zip(chunk, results):
                i, s, n = res['data'][0]['row']
                context = '%s %s:%s' % (ind, site, acc)
                if not i:
                    self.failures.append({'context_name': 'Individual_id', 'context': context,
                                          'message': 'Individual not in KB'})
                elif not s:
                    self.failures.append({'context_name': 'site', 'context': context, 'message': 'Site not in KB'})
                elif n:
                    if not allow_duplicates:
                        self.failures.append({'context_name': 'accession', 'context': context,
                                              'message': 'xref already in KB'})
                else:
                    self.to_add.append((ind, site, acc))
        if verbose:
            print("%d of %d xref(s) to add in %s" % (len(self.to_add), len(self.rows), self.record.cr.path))

    def commit(self, verbose=False):
        """Add the xrefs found missing by check()."""
        ew = kb_owl_edge_writer(self.endpoint, self.usr, self.pwd)
        for ind, site, acc in self.to_add:
            ew.add_xref(s=ind, xref='%s:%s' % (site, acc), stype=':Individual')
        if self.to_add:
            ew.commit(verbose=verbose)
        # commit() resets the writer's log, so check the result in the KB itself
        missing = self._missing(self.to_add)
        if missing:
            self.stat = False
            for ind, site, acc in missing[:25]:
                logging.warning("xref not added: %s %s:%s" % (ind, site, acc))
        print("Added %d of %d xref(s) for %s" % (len(self.to_add) - len(missing), len(self.to_add),
                                                 self.record.cr.path))
        return self.stat

    def _missing(self, triples, chunk_length=1000):
        """The (individual, site, accession) triples with no xref edge in the KB."""
        missing = []
        for start in range(0, len(triples), chunk_length):
            chunk = triples[start:start + chunk_length]
            results = self.nc.commit_list([check_statement(*t) for t in chunk])
            if not results:
                return list(triples)
            missing += [t for t, res in zip(chunk, results) if not res['data'][0]['row'][2]]
        return missing
