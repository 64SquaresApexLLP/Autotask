// CTTC network ontology — constraints and indexes (Neo4j 5.x)
// Run once before any load. Safe to re-run.

// Uniqueness — one canonical node per real-world thing
CREATE CONSTRAINT site_id   IF NOT EXISTS FOR (n:Site)            REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT device_id IF NOT EXISTS FOR (n:Device)          REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT port_id   IF NOT EXISTS FOR (n:Port)            REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT link_id   IF NOT EXISTS FOR (n:Link)            REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT pon_id    IF NOT EXISTS FOR (n:PONTree)         REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT ont_id    IF NOT EXISTS FOR (n:ONT)             REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT svc_id    IF NOT EXISTS FOR (n:Service)         REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT path_id   IF NOT EXISTS FOR (n:ServicePath)     REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT sub_id    IF NOT EXISTS FOR (n:Subscriber)      REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT sw_id     IF NOT EXISTS FOR (n:SoftwareVersion) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT def_id    IF NOT EXISTS FOR (n:KnownDefect)     REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT case_id   IF NOT EXISTS FOR (n:VendorCase)      REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT chg_id    IF NOT EXISTS FOR (n:Change)          REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT alm_id    IF NOT EXISTS FOR (n:Alarm)           REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT tkt_id    IF NOT EXISTS FOR (n:Ticket)          REQUIRE n.id IS UNIQUE;

// Business keys that must not collide either
CREATE CONSTRAINT svc_circuit IF NOT EXISTS FOR (n:Service) REQUIRE n.circuit_id IS UNIQUE;
CREATE CONSTRAINT ont_serial  IF NOT EXISTS FOR (n:ONT)     REQUIRE n.serial     IS UNIQUE;

// Existence
CREATE CONSTRAINT device_name IF NOT EXISTS FOR (n:Device) REQUIRE n.name IS NOT NULL;

// Lookup indexes for the hot paths
CREATE INDEX device_model  IF NOT EXISTS FOR (n:Device) ON (n.model);
CREATE INDEX device_role   IF NOT EXISTS FOR (n:Device) ON (n.role);
CREATE INDEX port_role     IF NOT EXISTS FOR (n:Port)   ON (n.role);
CREATE INDEX alarm_raised  IF NOT EXISTS FOR (n:Alarm)  ON (n.raised_at);
CREATE INDEX change_window IF NOT EXISTS FOR (n:Change) ON (n.window_start, n.window_end);

// Identity resolution: one full-text index over every human-facing name
CREATE FULLTEXT INDEX entity_alias IF NOT EXISTS
FOR (n:Device|Site|Service|Subscriber|ONT) ON EACH [n.name, n.aliases];
