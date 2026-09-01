// Q5 — fleet version drift. Runs against nothing but the inventory seed,
// which is why phase 1 pays for itself.

MATCH (d:Device)-[run:RUNS]->(v:SoftwareVersion)
WHERE run.valid_to IS NULL
WITH d.model AS model, v.train AS train, v.release AS release,
     v.approved AS approved, collect(d.name) AS devices
RETURN model, release, approved, size(devices) AS device_count, devices[..5] AS sample
ORDER BY model, device_count DESC;

// The stragglers: devices not on their model's dominant release
MATCH (d:Device)-[run:RUNS]->(v:SoftwareVersion)
WHERE run.valid_to IS NULL
WITH d.model AS model, v.release AS release, collect(d.name) AS devices
ORDER BY size(devices) DESC
WITH model, collect({release: release, devices: devices}) AS byRelease
WITH model, byRelease, head(byRelease).release AS dominant
UNWIND byRelease AS entry
WITH model, dominant, entry WHERE entry.release <> dominant
RETURN model, dominant, entry.release AS outlier, entry.devices AS devices
ORDER BY model;
