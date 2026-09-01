// Q3 — single point of failure.
// Services with no known path that routes around the Goldthwaite core.
// Run on a schedule: this stops being a slide bullet and becomes a monitored
// condition that catches new exposure the day a service is re-homed.

MATCH (core:Device {id: 'dev:mx960-gldt'})-[:HAS_PORT]->(:Port)
      <-[:TRAVERSES]-(:ServicePath)<-[:REALIZED_BY]-(svc:Service)
WITH DISTINCT core, svc
WHERE NOT EXISTS {
  MATCH (svc)-[:REALIZED_BY]->(alt:ServicePath)-[:TRAVERSES]->(ap:Port)
        <-[:HAS_PORT]-(other:Device {role: 'core'})
  WHERE other <> core
}
MATCH (svc)-[:DELIVERED_TO]->(sub:Subscriber)

RETURN
  count(DISTINCT svc)                 AS services_with_no_alternate,
  count(DISTINCT sub)                 AS subscribers_exposed,
  collect(DISTINCT sub.service_area)  AS service_areas,
  collect(DISTINCT svc.class)         AS service_classes;
