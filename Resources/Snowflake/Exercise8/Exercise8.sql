--#### Ex8.0 - Part 1 Web Console ####
DESC TABLE PRD_PARKINGTICKETS;
DESC TABLE STG_PARKINGTICKETS;
-- both should return the data types for the tables.

-- End of Ex8.0

--##### Ex8.1 - Part 2 Web Console  ####
select * from PRD_PARKINGTICKETS;  -- should return 10 records
select * from STG_PARKINGTICKETS;  -- should return zero records

--Table Stages are created when the table is created
LIST '@%"PRD_PARKINGTICKETS"';  -- should list the file that was loaded to the tempoary stage table
LIST '@%"STG_PARKINGTICKETS"';  -- should not have any files listed


-- Ex8.1 - Part 3 Web Console
select * from STG_PARKINGTICKETS;  -- should return 15 records
LIST '@%"STG_PARKINGTICKETS"';  -- should list the file that was loaded to the tempoary stage table
select * from PRD_PARKINGTICKETS;  -- should return 11 records

-- End of Ex8.1

--#### Ex8.2 - Part 1 Web Console ####

