CREATE RETENTION POLICY one_week ON sysmon DURATION 168h REPLICATION 1 DEFAULT;

create_retention_policy("one_week", "168h", 1, database="sysmon")
