-- 3) Run each of the following SQL’s and review the output each time.
 
desc table "TEST_DB"."PUBLIC"."PostalAddress";
-- output: lists the columns and their data types.


alter session set GEOGRAPHY_OUTPUT_FORMAT='GeoJSON';
-- ensure output will be GeoJSON

select PSTLCITY, LASTUPDATE, GEOM from "TEST_DB"."PUBLIC"."PostalAddress" LIMIT 10;
-- Review the output of the LASTUPDATE (Date) & the GEOM (Geography) columns.