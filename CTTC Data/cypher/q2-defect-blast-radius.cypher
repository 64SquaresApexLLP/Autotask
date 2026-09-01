// Q2 — blast radius of a known defect.
// Which customer services ride hardware running software with an open defect,
// and WHY is that software still there (the change that put it there).

MATCH (d:Device)-[run:RUNS]->(v:SoftwareVersion)-[:AFFECTED_BY]->(k:KnownDefect)
WHERE run.valid_to IS NULL                  // current state only
OPTIONAL MATCH (k)-[:TRACKED_BY]->(vcase:VendorCase)
OPTIONAL MATCH (chg:Change)-[:MOTIVATED_BY]->(k)

MATCH (d)-[:HAS_PORT]->(p:Port)<-[:TRAVERSES]-(path:ServicePath {kind: 'current'})
MATCH (svc:Service)-[:REALIZED_BY]->(path)
MATCH (svc)-[:DELIVERED_TO]->(sub:Subscriber)

RETURN
  d.name                              AS device,
  d.model                             AS model,
  v.release                           AS running,
  k.symptom                           AS defect,
  vcase.case_number                   AS vendor_case,
  chg.outcome                         AS why_this_release,
  count(DISTINCT svc)                 AS services,
  count(DISTINCT sub)                 AS subscribers,
  collect(DISTINCT svc.class)         AS service_classes,
  collect(DISTINCT svc.circuit_id)[..10] AS sample_circuits
ORDER BY subscribers DESC;
