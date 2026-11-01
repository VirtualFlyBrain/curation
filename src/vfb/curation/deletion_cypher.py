"""Cypher for newmeta_deletions records.

Kept free of database dependencies so the statements can be generated and
reviewed offline (see src/deletions_to_cypher.py).
"""
import re

# KB edge type for a curation relation, where it differs from the relation name
KB_EDGE = {'is_a': 'INSTANCEOF'}

SHORT_FORM = re.compile(r'^[A-Za-z]+_[A-Za-z0-9]+$')
EDGE_TYPE = re.compile(r'^[A-Za-z_]+$')


def edge_type(relation, relations):
    """KB edge type for a relation, or None if it isn't a known relation."""
    if relation not in relations:
        return None
    edge = KB_EDGE.get(relation, relation)
    return edge if EDGE_TYPE.match(edge) else None


def deletion_statement(individual, edge, cls, delete=False):
    """One statement matching (and optionally deleting) an Individual-Class edge.
    Returns the number of matching edges as `n`."""
    return ("MATCH (i:Individual {short_form: '%s'})-[r:`%s`]->(c:Class {short_form: '%s'}) "
            "%sRETURN count(r) AS n" % (individual, edge, cls, 'DELETE r ' if delete else ''))


def deletion_statements(rows, relations, delete=False):
    """Build statements for deletion rows (dicts with Individual_id, relation, remove).

    Returns (statements, failures): statements is a list of (row_index, cypher);
    failures lists rows that can't be turned into a safe statement, as dicts with
    context_name, message and context (the format the loader reports).
    """
    statements, failures = [], []
    for i, row in enumerate(rows):
        ind = str(row['Individual_id']).strip()
        cls = str(row['remove']).strip()
        rel = str(row['relation']).strip()
        context = '%s %s %s' % (ind, rel, cls)
        if not SHORT_FORM.match(ind):
            failures.append({'context_name': 'Individual_id', 'context': context,
                             'message': 'not a short form: %r' % ind})
            continue
        if not SHORT_FORM.match(cls):
            failures.append({'context_name': 'remove', 'context': context,
                             'message': 'not a short form: %r' % cls})
            continue
        edge = edge_type(rel, relations)
        if not edge:
            failures.append({'context_name': 'relation', 'context': context,
                             'message': 'unknown relation: %r' % rel})
            continue
        statements.append((i, deletion_statement(ind, edge, cls, delete=delete)))
    return statements, failures
