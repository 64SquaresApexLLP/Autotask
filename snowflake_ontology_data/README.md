# Snowflake Data Schema & Pipeline for AutoTask Network Ontology

This folder contains relational table exports and SQL DDL scripts generated from the **CTTC Network Ontology** datasets (`cttc.json` and `viz.json`), structured for **Snowflake Database** analytics and AutoTask integration.

---

## 📁 Included Files

| File | Description | Rows / Records |
| :--- | :--- | :--- |
| **`DIM_SITES.csv`** | Central offices, aggregation sites, coordinates, and operational status. | 5+ Sites |
| **`DIM_NETWORK_DEVICES.csv`** | Core, Aggregation, and Access routers with firmware release, defect count, and services delivered. | 83+ Devices |
| **`DIM_PORTS.csv`** | Physical interfaces, port speeds (10G/100G), optics, and operational state. | 1,000+ Ports |
| **`FACT_TOPOLOGY_LINKS.csv`** | Physical link trunks, protected/unprotected rings, and SPOF risk markers. | 1,511+ Links |
| **`DIM_SERVICES.csv`** | End-to-end customer circuits (Cell-Backhaul EVPN, DIA Enterprise). | 100+ Services |
| **`DIM_SUBSCRIBERS.csv`** | Enterprise accounts, wholesale mobile carriers, and delivered bandwidth. | 100+ Subscribers |
| **`DIM_KNOWN_DEFECTS.csv`** | Vendor bugs (EVPN QinQ), SPOF topology findings, and version drift outliers. | 4 Critical Findings |
| **`FACT_INCIDENTS_TICKETS.csv`**| Operational AutoTask incident tickets mapped to blast radius and affected devices. | Pre-linked Tickets |
| **`FACT_GRAPH_EDGES.csv`** | General knowledge graph edges with native Snowflake `VARIANT` properties. | 1,511 Edges |
| **`SNOWFLAKE_SCHEMA_DDL.sql`**| Complete SQL script with `CREATE TABLE`, Primary/Foreign keys, and `COPY INTO` commands. | Full Schema |
| **`generate_snowflake_data.py`**| Python pipeline script to regenerate or update CSVs from raw JSON anytime. | Pipeline Tool |

---

## 🚀 How to Ingest into Snowflake

1. **Run DDL**:
   Open Snowflake Worksheets and execute `SNOWFLAKE_SCHEMA_DDL.sql` to create all tables and file formats.

2. **Upload CSVs to Snowflake Stage**:
   ```sql
   PUT file://c:/Autotask/snowflake_ontology_data/*.csv @ONTOLOGY_STAGE AUTO_COMPRESS=FALSE;
   ```

3. **Copy into Tables**:
   ```sql
   COPY INTO DIM_SITES FROM @ONTOLOGY_STAGE/DIM_SITES.csv FILE_FORMAT = (FORMAT_NAME = CSV_ONTOLOGY_FORMAT);
   COPY INTO DIM_NETWORK_DEVICES FROM @ONTOLOGY_STAGE/DIM_NETWORK_DEVICES.csv FILE_FORMAT = (FORMAT_NAME = CSV_ONTOLOGY_FORMAT);
   COPY INTO DIM_PORTS FROM @ONTOLOGY_STAGE/DIM_PORTS.csv FILE_FORMAT = (FORMAT_NAME = CSV_ONTOLOGY_FORMAT);
   COPY INTO FACT_TOPOLOGY_LINKS FROM @ONTOLOGY_STAGE/FACT_TOPOLOGY_LINKS.csv FILE_FORMAT = (FORMAT_NAME = CSV_ONTOLOGY_FORMAT);
   COPY INTO DIM_SERVICES FROM @ONTOLOGY_STAGE/DIM_SERVICES.csv FILE_FORMAT = (FORMAT_NAME = CSV_ONTOLOGY_FORMAT);
   COPY INTO DIM_SUBSCRIBERS FROM @ONTOLOGY_STAGE/DIM_SUBSCRIBERS.csv FILE_FORMAT = (FORMAT_NAME = CSV_ONTOLOGY_FORMAT);
   COPY INTO DIM_KNOWN_DEFECTS FROM @ONTOLOGY_STAGE/DIM_KNOWN_DEFECTS.csv FILE_FORMAT = (FORMAT_NAME = CSV_ONTOLOGY_FORMAT);
   COPY INTO FACT_INCIDENTS_TICKETS FROM @ONTOLOGY_STAGE/FACT_INCIDENTS_TICKETS.csv FILE_FORMAT = (FORMAT_NAME = CSV_ONTOLOGY_FORMAT);
   COPY INTO FACT_GRAPH_EDGES FROM @ONTOLOGY_STAGE/FACT_GRAPH_EDGES.csv FILE_FORMAT = (FORMAT_NAME = CSV_ONTOLOGY_FORMAT);
   ```

---

## 🔄 Re-generating Data
To re-extract or update the CSVs from fresh JSON source files:
```powershell
python c:\Autotask\snowflake_ontology_data\generate_snowflake_data.py
```
