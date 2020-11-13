
-- 1) The Default output for GEOM column is ‘GeoJSON’

alter session set geography_output_format='GeoJSON';
select "vehicle_id", GEOM from "TEST_DB"."PUBLIC"."ElectricCarTrack"; 

-- 2) Set output to WKT

alter session set geography_output_format='WKT';
select "vehicle_id", GEOM from "TEST_DB"."PUBLIC"."ElectricCarTrack";

-- 3) Set output to WKB (this is the default for FME)

alter session set geography_output_format='WKB';
select "vehicle_id", GEOM from "TEST_DB"."PUBLIC"."ElectricCarTrack";

-- 4) Set output to  EWKT (or EWKB)  introduced by PostGIS (non-standard formats)

alter session set geography_output_format='EWKT';
select "vehicle_id", GEOM from "TEST_DB"."PUBLIC"."ElectricCarTrack";
