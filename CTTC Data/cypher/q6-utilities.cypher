// Q6 — the two primitives every other query depends on.

// Resolve a name asked in ticket vocabulary to a canonical node
CALL db.index.fulltext.queryNodes('entity_alias', 'Goldthwaite A')
YIELD node, score
RETURN labels(node) AS kind, node.id AS id, node.name AS name,
       node.aliases AS aliases, score
ORDER BY score DESC LIMIT 5;

// Topology as it was at an arbitrary instant — the "what changed" primitive
:param asOf => datetime('2026-05-14T03:10:00Z');
MATCH (d:Device)-[r:HAS_PORT|RUNS|CONTAINS]->(n)
WHERE r.valid_from <= $asOf
  AND (r.valid_to IS NULL OR r.valid_to > $asOf)
RETURN d.name, type(r), labels(n), n.id, r.source, r.confidence;

// Everything that changed on a device in a window — the incident primitive.
// This is the query an engineer actually wants at 2am, and it works because
// edges are closed rather than deleted.
:param device => 'dev:mx304-sang';
:param from   => datetime('2026-04-01T00:00:00Z');
:param to     => datetime('2026-06-01T00:00:00Z');
MATCH (d:Device {id: $device})-[r]-()
WHERE (r.valid_from >= $from AND r.valid_from <= $to)
   OR (r.valid_to   >= $from AND r.valid_to   <= $to)
RETURN type(r) AS change, r.valid_from, r.valid_to, r.source, r.method
ORDER BY coalesce(r.valid_to, r.valid_from);
