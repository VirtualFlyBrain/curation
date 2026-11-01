from uk.ac.ebi.vfb.neo4j.neo4j_tools import neo4j_connect
from .deletion_cypher import deletion_statements
from .peevish import Record
import logging


class NewMetaDeletionWriter:
    """Checks and deletes the KB edges listed in a newmeta_deletions record."""

    def __init__(self, endpoint, usr, pwd, record: Record):
        self.nc = neo4j_connect(endpoint, usr, pwd)
        self.record = record
        self.rows = record.tsv.to_dict('records')
        self.relations = record.rel_spec.keys()
        self.stat = True
        self.failures = []
        self.to_delete = []  # row indexes whose edge exists

    def _run(self, statements, chunk_length=1000):
        """Run (row_index, cypher) statements; return {row_index: matched edge count}."""
        counts = {}
        for start in range(0, len(statements), chunk_length):
            chunk = statements[start:start + chunk_length]
            results = self.nc.commit_list([s for _, s in chunk])
            if not results:
                self.stat = False
                logging.warning("Query failed for %s, rows %d-%d"
                                % (self.record.cr.path, start, start + len(chunk) - 1))
                continue
            for (i, _), res in zip(chunk, results):
                counts[i] = res['data'][0]['row'][0] if res['data'] else 0
        return counts

    def check(self, allow_duplicates=False, verbose=False):
        """Check each row's edge exists. Rows that can't be checked, or whose
        edge is missing, are recorded as failures and skipped on commit; a
        missing edge is only reported when allow_duplicates is set."""
        statements, self.failures = deletion_statements(self.rows, self.relations)
        counts = self._run(statements)
        for i, n in counts.items():
            row = self.rows[i]
            if n:
                self.to_delete.append(i)
                continue
            context = '%s %s %s' % (row['Individual_id'], row['relation'], row['remove'])
            if allow_duplicates:
                logging.info("Edge not in KB (already removed?): %s" % context)
            else:
                self.failures.append({'context_name': 'remove', 'context': context,
                                      'message': 'edge not in KB'})
        if verbose:
            print("%d of %d edge(s) found for deletion in %s"
                  % (len(self.to_delete), len(self.rows), self.record.cr.path))

    def commit(self, verbose=False):
        """Delete the edges found by check()."""
        wanted = [self.rows[i] for i in self.to_delete]
        statements, _ = deletion_statements(wanted, self.relations, delete=True)
        counts = self._run(statements)
        deleted = sum(counts.values())
        print("Deleted %d edge(s) for %s" % (deleted, self.record.cr.path))
        if len(counts) < len(statements):
            self.stat = False
        return self.stat
