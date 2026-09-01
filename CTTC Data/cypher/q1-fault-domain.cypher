// Q1 — narrow a fault domain from an alarm cluster.
// Returns the OLT, the shared PON, the count, the uplink, and the two counts
// that should be ZERO. Negative evidence is what narrows the domain.

// 1. Open ONT alarms in the last 10 minutes, grouped by the PON they share
MATCH (a:Alarm)-[:RAISED_BY]->(o:ONT)
WHERE a.raised_at > datetime() - duration('PT10M') AND a.cleared_at IS NULL
MATCH (pon:PONTree)-[:FEEDS*1..2]->(o)
WITH pon, collect(DISTINCT o) AS onts, collect(DISTINCT a) AS alarms
WHERE size(onts) >= 5                       // a cluster, not a one-off

// 2. Walk up to the OLT and its uplink
MATCH (olt:Device)-[:HAS_PORT]->(ponPort:Port)-[:SERVES]->(pon)
MATCH (olt)-[:HAS_PORT]->(up:Port {role: 'uplink'})

// 3. Positive evidence — did the uplink misbehave just before the cluster?
OPTIONAL MATCH (up)<-[:RAISED_BY]-(ua:Alarm)
  WHERE ua.raised_at > datetime() - duration('PT15M')

// 4. Negative evidence — rule out the alternatives
OPTIONAL MATCH (chg:Change)-[:TARGETS]->(olt)
  WHERE chg.window_start <= datetime() AND chg.window_end >= datetime()
OPTIONAL MATCH (oltAlarm:Alarm)-[:RAISED_BY]->(olt)
  WHERE oltAlarm.cleared_at IS NULL

RETURN
  olt.name                          AS olt,
  pon.id                            AS pon,
  size(onts)                        AS onts_down,
  head([x IN alarms | x.raised_at]) AS first_alarm,
  up.name                           AS uplink,
  count(DISTINCT ua)                AS uplink_alarms,   // supports
  count(DISTINCT chg)               AS open_changes,    // rules out
  count(DISTINCT oltAlarm)          AS olt_alarms,      // rules out
  CASE WHEN count(DISTINCT ua) > 0 AND count(DISTINCT oltAlarm) = 0
       THEN 'uplink / aggregation interface'
       ELSE 'unresolved — widen search' END             AS narrowed_to
ORDER BY onts_down DESC;
