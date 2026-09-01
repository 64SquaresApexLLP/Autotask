// Q4 — intended vs. current path diff.
// A service that is up, billing normally, and quietly riding an unprotected or
// constrained path. Nothing alarms for this today.

MATCH (svc:Service)-[:REALIZED_BY]->(i:ServicePath {kind: 'intended'})
MATCH (svc)-[:REALIZED_BY]->(c:ServicePath {kind: 'current'})
MATCH (i)-[:TRAVERSES]->(ip:Port)
MATCH (c)-[:TRAVERSES]->(cp:Port)
WITH svc, c,
     collect(DISTINCT ip) AS intended,
     collect(DISTINCT cp) AS current
WHERE size([p IN current WHERE NOT p IN intended]) > 0   // it has moved

UNWIND [p IN current WHERE NOT p IN intended] AS newPort
OPTIONAL MATCH (newPort)-[:TERMINATES]->(l:Link)

RETURN
  svc.circuit_id                      AS circuit,
  svc.class                           AS class,
  c.protected                         AS currently_protected,
  collect(DISTINCT newPort.name)      AS now_traversing,
  min(l.capacity_gbps)                AS tightest_link_gbps,
  collect(DISTINCT l.protection_role) AS protection_on_new_hops
ORDER BY tightest_link_gbps ASC;      // most constrained failover first
