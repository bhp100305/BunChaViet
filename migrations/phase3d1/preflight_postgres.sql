-- READ ONLY. Metadata and aggregate counts; never output actual row values.
SELECT table_name, column_name, data_type, character_maximum_length,
    numeric_precision, numeric_scale, is_nullable, is_identity, column_default IS NOT NULL AS has_default,
    md5(column_default) AS default_hash, collation_name, is_generated
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name IN ('Products', 'Orders', 'OrderDetails')
ORDER BY table_name, ordinal_position;

SELECT COUNT(*) AS "ProductCount",
    COUNT(*) FILTER (WHERE "Price" <> FLOOR("Price")) AS "FractionalPrices",
    COUNT(*) FILTER (WHERE LENGTH("ProductName") > 100) AS "NamesOver100",
    COALESCE(MAX(LENGTH("ProductName")),0) AS "MaxNameLength"
FROM public."Products";

SELECT COUNT(*) AS "OrderCount",
    COUNT(*) FILTER (WHERE "OrderCode" IS NULL) AS "NullCodes",
    COUNT(*) FILTER (WHERE "OrderCode" IS NOT NULL AND BTRIM("OrderCode") = '') AS "BlankCodes",
    COUNT(*) FILTER (WHERE "TotalMoney" IS NULL) AS "NullTotals",
    COUNT(*) FILTER (WHERE "TotalMoney" < 0) AS "NegativeTotals"
FROM public."Orders";

SELECT COUNT(*) AS "DuplicateGroups" FROM (
    SELECT "OrderCode" FROM public."Orders" WHERE "OrderCode" IS NOT NULL
    GROUP BY "OrderCode" HAVING COUNT(*) > 1
) d;
SELECT COUNT(*) AS "NormalizedDuplicateGroups" FROM (
    SELECT UPPER(RTRIM("OrderCode")) FROM public."Orders" WHERE "OrderCode" IS NOT NULL
    GROUP BY UPPER(RTRIM("OrderCode")) HAVING COUNT(*) > 1
) d;
SELECT COUNT(*) AS "NoncanonicalCodes" FROM public."Orders"
WHERE "OrderCode" IS NOT NULL AND "OrderCode" !~ '^[A-Z0-9]+$';

SELECT COUNT(*) AS "DetailCount",
    COUNT(*) FILTER (WHERE d."Price" <> FLOOR(d."Price")) AS "FractionalPrices",
    COUNT(*) FILTER (WHERE d."Price" IS NULL) AS "NullPrices",
    COUNT(*) FILTER (WHERE LENGTH(d."ProductName") > 100) AS "NamesOver100",
    COUNT(*) FILTER (WHERE d."OrderID" IS NULL) AS "NullOrderIDs",
    COUNT(*) FILTER (WHERE d."OrderID" IS NOT NULL AND o."OrderID" IS NULL) AS "OrphanDetails",
    COUNT(*) FILTER (WHERE d."Quantity" IS NULL OR d."Quantity" <= 0) AS "InvalidQuantities"
FROM public."OrderDetails" d LEFT JOIN public."Orders" o ON o."OrderID" = d."OrderID";

SELECT tablename, indexname, md5(indexdef) AS definition_hash FROM pg_indexes
WHERE schemaname = 'public' AND tablename IN ('Products', 'Orders', 'OrderDetails')
ORDER BY tablename, indexname;
SELECT c.relname AS table_name, con.conname, con.contype, con.convalidated, md5(pg_get_constraintdef(con.oid)) AS definition_hash
FROM pg_constraint con JOIN pg_class c ON c.oid = con.conrelid
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public' AND c.relname IN ('Products', 'Orders', 'OrderDetails');
SELECT c.relname AS child_table, con.conname, con.convalidated, md5(pg_get_constraintdef(con.oid)) AS definition_hash
FROM pg_constraint con JOIN pg_class c ON c.oid = con.conrelid
WHERE con.contype = 'f' AND con.confrelid IN
    ('public."Orders"'::regclass, 'public."OrderDetails"'::regclass, 'public."Products"'::regclass);
SELECT c.relname AS table_name, t.tgname, t.tgenabled FROM pg_trigger t
JOIN pg_class c ON c.oid = t.tgrelid WHERE NOT t.tgisinternal
AND t.tgrelid IN ('public."Orders"'::regclass, 'public."OrderDetails"'::regclass);
SELECT pg_get_serial_sequence('public."Orders"','OrderID') AS order_sequence,
    pg_get_serial_sequence('public."OrderDetails"','DetailID') AS detail_sequence;

-- Additional 3D.3 metadata; no row values or raw expression literals.
SELECT current_setting('server_version') AS engine_version,
    datcollate,datctype,datlocprovider,datcollversion,
    pg_database_collation_actual_version(oid) AS actual_collation_version
FROM pg_database WHERE datname=current_database();
SELECT a.attname,c.relname,coll.collname,coll.collprovider,coll.collisdeterministic,
    coll.collversion,CASE WHEN coll.collprovider<>'d' THEN pg_collation_actual_version(coll.oid) END AS actual_version
FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid
JOIN pg_collation coll ON coll.oid=a.attcollation
WHERE a.attrelid IN ('public."Orders"'::regclass,'public."OrderDetails"'::regclass)
    AND a.attnum>0 AND NOT a.attisdropped;
SELECT upper('i')='I' AS uppercase_i,upper(rtrim('abc '))=upper(rtrim('ABC')) AS normalized_equal;
SELECT COUNT(*) FILTER (WHERE "TotalMoney"::text IN ('NaN','Infinity','-Infinity')) AS nonfinite,
    COUNT(*) FILTER (WHERE "TotalMoney" < -999999999999999999.99 OR "TotalMoney" > 999999999999999999.99) AS outside_target,
    COUNT(*) FILTER (WHERE "TotalMoney" <> trunc("TotalMoney",2)) AS would_round
FROM public."Orders";
SELECT COUNT(*) FILTER (WHERE "Price"::text IN ('NaN','Infinity','-Infinity')) AS nonfinite,
    COUNT(*) FILTER (WHERE "Price" < -999999999999999999.99 OR "Price" > 999999999999999999.99) AS outside_target,
    COUNT(*) FILTER (WHERE "Price" <> trunc("Price",2)) AS would_round,
    COUNT(*) FILTER (WHERE length("ProductName")>200) AS outside_target_name
FROM public."OrderDetails";
SELECT c.relname,a.attname,d.classid::regclass::text AS dependent_catalog,d.objid,d.objsubid,d.deptype
FROM pg_depend d JOIN pg_attribute a ON d.refobjid=a.attrelid AND d.refobjsubid=a.attnum
JOIN pg_class c ON c.oid=a.attrelid WHERE d.refclassid='pg_class'::regclass
AND a.attrelid IN ('public."Orders"'::regclass,'public."OrderDetails"'::regclass);
SELECT evtname,evtevent,evtenabled FROM pg_event_trigger;
SELECT c.relname,c.relkind,c.relispartition,c.relrowsecurity,c.relforcerowsecurity,
    pg_has_role(current_user,c.relowner,'USAGE') AS owns_table
FROM pg_class c WHERE c.oid IN ('public."Orders"'::regclass,'public."OrderDetails"'::regclass);
SELECT i.indexrelid::regclass::text AS index_name,i.indisunique,i.indisvalid,i.indisready,
    i.indislive,i.indnkeyatts,i.indnatts,i.indkey::text AS key_numbers,
    i.indclass::text AS operator_classes,i.indcollation::text AS collations,
    md5(pg_get_expr(i.indexprs,i.indrelid,false)) AS expression_hash,
    md5(pg_get_expr(i.indpred,i.indrelid,false)) AS predicate_hash,
    obj_description(i.indexrelid,'pg_class')='phase3d3:OrderCode:v1' AS migration_owned
FROM pg_index i WHERE i.indrelid='public."Orders"'::regclass;

SELECT e.table_name,e.column_name,
    COALESCE(c.data_type=e.type_name AND c.is_nullable=e.nullable
        AND c.is_identity=e.identity_expected
        AND (e.max_length IS NULL OR c.character_maximum_length=e.max_length)
        AND (e.precision_expected IS NULL OR c.numeric_precision=e.precision_expected)
        AND (e.scale_expected IS NULL OR c.numeric_scale=e.scale_expected)
        AND (NOT e.no_default OR c.column_default IS NULL),false) AS matches_pre_up_schema
FROM (VALUES
    ('Orders','OrderID','integer','NO','YES',NULL::integer,NULL::integer,NULL::integer,false),
    ('Orders','OrderCode','character varying','YES','NO',20,NULL,NULL,false),
    ('Orders','TotalMoney','numeric','YES','NO',NULL,18,0,true),
    ('OrderDetails','DetailID','integer','NO','YES',NULL,NULL,NULL,false),
    ('OrderDetails','OrderID','integer','YES','NO',NULL,NULL,NULL,false),
    ('OrderDetails','ProductName','character varying','YES','NO',100,NULL,NULL,true),
    ('OrderDetails','Quantity','integer','YES','NO',NULL,NULL,NULL,false),
    ('OrderDetails','Price','numeric','YES','NO',NULL,18,0,true)
) e(table_name,column_name,type_name,nullable,identity_expected,max_length,precision_expected,scale_expected,no_default)
LEFT JOIN information_schema.columns c ON c.table_schema='public'
    AND c.table_name=e.table_name AND c.column_name=e.column_name;
SELECT COUNT(*) AS lossy_down_totals FROM public."Orders"
WHERE "TotalMoney"::text IN ('NaN','Infinity','-Infinity') OR "TotalMoney" <> trunc("TotalMoney")
    OR "TotalMoney" < -999999999999999999 OR "TotalMoney" > 999999999999999999;
