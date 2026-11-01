"""Cypher for newmeta_deletions records.

Kept free of database dependencies so the statements can be generated and
reviewed offline (see src/deletions_to_cypher.py).

Edges are identified as the newmeta loader writes them: is_a is an INSTANCEOF
edge; any other relation is an edge carrying the property's short_form from
relations_spec.yaml (e.g. has_soma_location -> r.short_form 'RO_0002100').
The edge type name is not used, as it doesn't always match the relation name
(has_presynaptic_terminal_in is stored as has_presynaptic_terminals_in). The
object can be any node (Class, Individual, Feature...) with that short_form.
"""
import re

SHORT_FORM = re.compile(r'^[A-Za-z]+_[A-Za-z0-9]+$')


def edge_pattern(relation, relations):
    """Cypher relationship pattern + condition for a relation, or None if the
    relation isn't in the relations spec (dict of relation name -> spec)."""
    spec = relations.get(relation)
    if spec is None:
        return None
    if relation == 'is_a':
        return '[r:INSTANCEOF]', ''
    prop = str(spec.get('short_form', ''))
    if not SHORT_FORM.match(prop):
        return None
    return '[r]', "WHERE r.short_form = '%s' " % prop


def deletion_statement(individual, pattern, cls, delete=False):
    """One statement matching (and optionally deleting) an edge from an Individual.
    Returns the number of matching edges as `n`."""
    rel, where = pattern
    return ("MATCH (i:Individual {short_form: '%s'})-%s->(o {short_form: '%s'}) %s"
            "%sRETURN count(r) AS n" % (individual, rel, cls, where, 'DELETE r ' if delete else ''))


def deletion_statements(rows, relations, delete=False):
    """Build statements for deletion rows (dicts with Individual_id, relation, remove).

    relations is the relations spec (dict). Returns (statements, failures):
    statements is a list of (row_index, cypher); failures lists rows that can't
    be turned into a safe statement, as dicts with context_name, message and
    context (the format the loader reports).
    """
    statements, failures = [], []
    for i, row in enumerate(rows):
        ind = str(row['Individual_id']).strip()
        obj = str(row['remove']).strip()
        rel = str(row['relation']).strip()
        context = '%s %s %s' % (ind, rel, obj)
        if not SHORT_FORM.match(ind):
            failures.append({'context_name': 'Individual_id', 'context': context,
                             'message': 'not a short form: %r' % ind})
            continue
        if not SHORT_FORM.match(obj):
            failures.append({'context_name': 'remove', 'context': context,
                             'message': 'not a short form: %r' % obj})
            continue
        pattern = edge_pattern(rel, relations)
        if not pattern:
            failures.append({'context_name': 'relation', 'context': context,
                             'message': 'unknown relation: %r' % rel})
            continue
        statements.append((i, deletion_statement(ind, pattern, obj, delete=delete)))
    return statements, failures
