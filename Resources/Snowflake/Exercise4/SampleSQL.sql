--1) Run SQL Scripts to create sample data

create table demonstration1 (
    id integer,
    array1 array,
    variant1 variant,
    object1 object
    );

insert into demonstration1 (id, array1, variant1, object1) 
  select 
    1, 
    array_construct(1, 2, 3), 
    parse_json(' { "key1": "value1", "key2": "value2" } '),
    parse_json(' { "outer_key1": { "inner_key1A": "1a", "inner_key1B": "1b" }, '
              ||
               '   "outer_key2": { "inner_key2": 2 } } ')
    ;

insert into demonstration1 (id, array1, variant1, object1) 
  select 
    1, 
    array_construct(1, 2, 3, null), 
    parse_json(' { "key1": "value1", "key2": NULL } '),
    parse_json(' { "outer_key1": { "inner_key1A": "1a", "inner_key1B": NULL }, '
              ||
               '   "outer_key2": { "inner_key2": 2 } '
              ||
               ' } ')
  ;

create table demonstration3 (
    id integer,
    variant1 variant);

insert into demonstration3 (id, variant1) 
  select 
    1, 
    parse_json(' { "key1": "value1", "key2": "value2" } ')
    ;

--2) Run Workspace
--3) Review Data in Web Console

--demo table 1
select * 
    from demonstration1;

--FME Table
desc table mydemonstration_1;    

select * 
    from mydemonstration_1;

-- demo table 3
select * 
	from demonstration3;
-- FME Table
desc table mydemonstration_3;

select * 
	from mydemonstration_3;