-- Phase 3D.3. Send this single DO as a top-level command on a NEW autocommit connection.
-- No BEGIN wrapper, psql --single-transaction, pipeline or other statements in this request.
DO $migration$
DECLARE
    expected_address text := '__TARGET_SERVER__';
    expected_port integer := 0;
    expected_role text := '__TARGET_ROLE__';
    test_id text := '__TEST_ID__';
    approval text := '__APPROVAL__';
BEGIN
    IF approval IS DISTINCT FROM 'BunChaViet phase3d3 test up approved'
       OR current_setting('server_version_num')::integer NOT BETWEEN 180000 AND 189999
       OR inet_server_addr() NOT IN ('127.0.0.1'::inet,'::1'::inet)
       OR current_database() IS DISTINCT FROM 'bunchaviet_phase3d3_test'
       OR session_user::text IS DISTINCT FROM expected_role
       OR inet_server_addr()::text IS DISTINCT FROM expected_address
       OR inet_server_port() IS DISTINCT FROM expected_port
       OR test_id IS NULL
       OR test_id !~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
       OR NOT EXISTS (SELECT 1 FROM pg_database WHERE datname=current_database()
           AND shobj_description(oid,'pg_database')='BunChaViet migration test:' || test_id) THEN
        RAISE EXCEPTION USING ERRCODE='P3001', MESSAGE='BCV_TEST_TARGET_OR_APPROVAL_REQUIRED';
    END IF;
    -- PostgreSQL itself rejects this COMMIT when invoked in an outer transaction.
    -- Only read-only target checks precede it. No exception subtransaction may surround it.
    COMMIT;
    PERFORM set_config('search_path','pg_catalog,public',true);
    PERFORM set_config('lock_timeout','5s',true);
    PERFORM set_config('statement_timeout','60s',true);
    BEGIN
    LOCK TABLE public."Orders", public."OrderDetails" IN ACCESS EXCLUSIVE MODE;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint con WHERE con.conrelid='public."Orders"'::regclass
        AND con.contype='p' AND con.convalidated
        AND con.conkey=ARRAY[(SELECT attnum FROM pg_attribute WHERE attrelid=con.conrelid AND attname='OrderID')]::smallint[])
       OR NOT EXISTS (SELECT 1 FROM pg_constraint con WHERE con.conrelid='public."OrderDetails"'::regclass
        AND con.contype='p' AND con.convalidated
        AND con.conkey=ARRAY[(SELECT attnum FROM pg_attribute WHERE attrelid=con.conrelid AND attname='DetailID')]::smallint[])
       OR NOT EXISTS (SELECT 1 FROM pg_constraint con WHERE con.conrelid='public."OrderDetails"'::regclass
        AND con.confrelid='public."Orders"'::regclass AND con.contype='f'
        AND con.convalidated AND NOT con.condeferrable AND con.confdeltype='a' AND con.confupdtype='a'
        AND con.conkey=ARRAY[(SELECT attnum FROM pg_attribute WHERE attrelid=con.conrelid AND attname='OrderID')]::smallint[]
        AND con.confkey=ARRAY[(SELECT attnum FROM pg_attribute WHERE attrelid=con.confrelid AND attname='OrderID')]::smallint[])
       OR NOT EXISTS (SELECT 1 FROM pg_class WHERE oid='public."Orders"'::regclass
        AND pg_has_role(current_user,relowner,'USAGE'))
       OR NOT EXISTS (SELECT 1 FROM pg_class WHERE oid='public."OrderDetails"'::regclass
        AND pg_has_role(current_user,relowner,'USAGE')) THEN
        RAISE EXCEPTION USING ERRCODE='P3013', MESSAGE='BCV_PK_FK_OR_OWNERSHIP_DRIFT';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_database WHERE datname=current_database()
        AND datcollate IN ('C.UTF-8','C.utf8') AND datctype IN ('C.UTF-8','C.utf8')
        AND datlocprovider='c'
        AND datcollversion IS NOT DISTINCT FROM pg_database_collation_actual_version(oid))
       OR NOT EXISTS (SELECT 1 FROM pg_attribute a WHERE a.attrelid='public."Orders"'::regclass
        AND a.attname='OrderCode' AND a.atttypid='varchar'::regtype AND a.atttypmod=24
        AND NOT a.attnotnull AND a.attcollation='pg_catalog."default"'::regcollation)
       OR NOT EXISTS (SELECT 1 FROM pg_collation WHERE oid='pg_catalog."default"'::regcollation AND collisdeterministic)
       OR upper('i'::text) <> 'I' OR upper('abc'::text) <> 'ABC'
       OR upper(rtrim('abc '::text)) <> upper(rtrim('ABC'::text)) THEN
        RAISE EXCEPTION USING ERRCODE='P3010', MESSAGE='BCV_COLLATION_OR_CODE_SCHEMA_DRIFT';
    END IF;
    IF EXISTS (SELECT 1 FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid
        WHERE a.attrelid IN ('public."Orders"'::regclass,'public."OrderDetails"'::regclass)
        AND (a.attgenerated<>'' OR c.relkind<>'r' OR c.relispartition OR c.relrowsecurity))
       OR EXISTS (SELECT 1 FROM pg_inherits WHERE inhrelid IN
        ('public."Orders"'::regclass,'public."OrderDetails"'::regclass) OR inhparent IN
        ('public."Orders"'::regclass,'public."OrderDetails"'::regclass))
       OR EXISTS (SELECT 1 FROM pg_trigger WHERE NOT tgisinternal AND tgenabled<>'D'
        AND tgrelid IN ('public."Orders"'::regclass,'public."OrderDetails"'::regclass))
       OR EXISTS (SELECT 1 FROM pg_event_trigger WHERE evtenabled<>'D') THEN
        RAISE EXCEPTION USING ERRCODE='P3011', MESSAGE='BCV_TABLE_FEATURE_OR_TRIGGER_REVIEW';
    END IF;
    IF EXISTS (SELECT 1 FROM pg_attribute a WHERE
        ((a.attrelid='public."Orders"'::regclass AND a.attname='TotalMoney') OR
         (a.attrelid='public."OrderDetails"'::regclass AND a.attname IN ('Price','ProductName')))
        AND (a.atthasdef OR a.attidentity<>'' OR a.attgenerated<>''))
       OR EXISTS (SELECT 1 FROM pg_depend d JOIN pg_attribute a
        ON d.refobjid=a.attrelid AND d.refobjsubid=a.attnum
        WHERE d.refclassid='pg_class'::regclass AND
        ((a.attrelid='public."Orders"'::regclass AND a.attname='TotalMoney') OR
         (a.attrelid='public."OrderDetails"'::regclass AND a.attname IN ('Price','ProductName')))) THEN
        RAISE EXCEPTION USING ERRCODE='P3012', MESSAGE='BCV_COLUMN_DEFAULT_OR_DEPENDENCY_DRIFT';
    END IF;
    IF (SELECT COUNT(*) FROM information_schema.columns WHERE table_schema='public'
        AND table_name='OrderDetails' AND column_name IN ('OrderID','Quantity')
        AND data_type='integer' AND is_nullable='YES') <> 2
       OR (SELECT COUNT(*) FROM information_schema.columns WHERE table_schema='public'
        AND ((table_name='Orders' AND column_name='OrderID') OR
             (table_name='OrderDetails' AND column_name='DetailID'))
        AND data_type='integer' AND is_nullable='NO' AND is_identity='YES') <> 2 THEN
        RAISE EXCEPTION USING ERRCODE='P3013', MESSAGE='BCV_SNAPSHOT_SCHEMA_DRIFT';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public'
        AND table_name = 'Orders' AND column_name = 'TotalMoney'
        AND data_type = 'numeric' AND numeric_precision = 18 AND numeric_scale = 0 AND is_nullable = 'YES')
       OR NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public'
        AND table_name = 'OrderDetails' AND column_name = 'Price'
        AND data_type = 'numeric' AND numeric_precision = 18 AND numeric_scale = 0 AND is_nullable = 'YES')
       OR NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public'
        AND table_name = 'OrderDetails' AND column_name = 'ProductName'
        AND data_type = 'character varying' AND character_maximum_length = 100 AND is_nullable = 'YES')
       OR NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public'
        AND table_name = 'Orders' AND column_name = 'OrderCode'
        AND data_type = 'character varying' AND character_maximum_length = 20 AND is_nullable = 'YES') THEN
        RAISE EXCEPTION USING ERRCODE='P3015', MESSAGE='Unexpected source schema; rerun metadata review.';
    END IF;
    IF to_regclass('public."UX_Orders_OrderCode_NotNull"') IS NOT NULL THEN
        RAISE EXCEPTION USING ERRCODE='P3015', MESSAGE='Target index already exists; do not apply twice.';
    END IF;
    IF EXISTS (SELECT 1 FROM public."Orders" WHERE "OrderCode" IS NOT NULL
        GROUP BY UPPER(RTRIM("OrderCode")) HAVING COUNT(*) > 1) THEN
        RAISE EXCEPTION USING ERRCODE='P3015', MESSAGE='Duplicate normalized order codes; resolve separately.';
    END IF;
    IF EXISTS (SELECT 1 FROM public."Orders" WHERE "OrderCode" IS NOT NULL
        AND "OrderCode" !~ '^[A-Z0-9]+$') THEN
        RAISE EXCEPTION USING ERRCODE='P3015', MESSAGE='Noncanonical order codes; review without automatic cleanup.';
    END IF;

    IF EXISTS (SELECT 1 FROM public."Orders" WHERE "TotalMoney"::text IN ('NaN','Infinity','-Infinity'))
       OR EXISTS (SELECT 1 FROM public."OrderDetails" WHERE "Price"::text IN ('NaN','Infinity','-Infinity')) THEN
        RAISE EXCEPTION USING ERRCODE='P3014', MESSAGE='BCV_NONFINITE_MONEY';
    END IF;
    ALTER TABLE public."Orders" ALTER COLUMN "TotalMoney" TYPE numeric(20,2);
    ALTER TABLE public."OrderDetails" ALTER COLUMN "Price" TYPE numeric(20,2);
    ALTER TABLE public."OrderDetails" ALTER COLUMN "ProductName" TYPE varchar(200);
    -- Match SQL Server case/trailing-space equality for generated ASCII codes.
    CREATE UNIQUE INDEX "UX_Orders_OrderCode_NotNull"
        ON public."Orders" (UPPER(RTRIM("OrderCode"))) WHERE "OrderCode" IS NOT NULL;
    COMMENT ON INDEX public."UX_Orders_OrderCode_NotNull" IS 'phase3d3:OrderCode:v1';
    EXCEPTION
        WHEN SQLSTATE 'P3010' OR SQLSTATE 'P3011' OR SQLSTATE 'P3012'
          OR SQLSTATE 'P3013' OR SQLSTATE 'P3014' OR SQLSTATE 'P3015'
          OR SQLSTATE 'P3020' THEN RAISE;
        WHEN OTHERS THEN
            RAISE EXCEPTION USING ERRCODE='P3099', MESSAGE='BCV_MIGRATION_FAILED';
    END;
END;
$migration$;
