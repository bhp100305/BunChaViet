-- Phase 3D.3: standalone test-only template; prepare.py renders reviewed targets.
DECLARE @ExpectedServer nvarchar(128) = N'__TARGET_SERVER__';
DECLARE @ExpectedDatabase sysname = N'BunChaViet_Phase3D3_Test';
DECLARE @ExpectedPort int = 0;
DECLARE @ExpectedLogin sysname = N'__TARGET_ROLE__';
DECLARE @TestId nvarchar(36) = N'__TEST_ID__';
DECLARE @Approval nvarchar(100) = N'__APPROVAL__';
IF @@TRANCOUNT <> 0 OR (@@OPTIONS & 2) <> 0
    THROW 51200, 'BCV_TRANSACTION_CONTEXT', 1;
IF @Approval IS NULL OR @ExpectedServer IS NULL OR @ExpectedLogin IS NULL OR @TestId IS NULL
    OR @Approval <> N'BunChaViet phase3d3 test up approved'
    OR @ExpectedServer LIKE N'__TARGET%'
    OR TRY_CONVERT(uniqueidentifier, @TestId) IS NULL
    OR TRY_CONVERT(int,SERVERPROPERTY('ProductMajorVersion')) <> 16
    OR CONVERT(int,CONNECTIONPROPERTY('local_tcp_port')) IS NULL
    OR CONVERT(int,CONNECTIONPROPERTY('local_tcp_port')) <> @ExpectedPort
    OR SERVERPROPERTY('ServerName') IS NULL
    OR CONVERT(nvarchar(128), SERVERPROPERTY('ServerName')) COLLATE Latin1_General_100_BIN2
       <> @ExpectedServer COLLATE Latin1_General_100_BIN2
    OR DB_NAME() COLLATE Latin1_General_100_BIN2 <> @ExpectedDatabase COLLATE Latin1_General_100_BIN2
    OR ORIGINAL_LOGIN() COLLATE Latin1_General_100_BIN2 <> @ExpectedLogin COLLATE Latin1_General_100_BIN2
    THROW 51201, 'BCV_TEST_TARGET_OR_APPROVAL_REQUIRED', 1;
IF NOT EXISTS (SELECT 1 FROM sys.extended_properties WHERE class = 0
    AND name = N'BunChaViet_MigrationTestId'
    AND CONVERT(nvarchar(36), value) COLLATE Latin1_General_100_BIN2 = @TestId COLLATE Latin1_General_100_BIN2)
    THROW 51202, 'BCV_TEST_DATABASE_MARKER_REQUIRED', 1;
IF ISNULL(HAS_PERMS_BY_NAME(DB_NAME(), 'DATABASE', 'VIEW DEFINITION'),0) <> 1
    OR ISNULL(HAS_PERMS_BY_NAME(NULL, NULL, 'VIEW ANY DEFINITION'),0) <> 1
    THROW 51203, 'BCV_METADATA_VISIBILITY_REQUIRED', 1;
SET IMPLICIT_TRANSACTIONS OFF;
SET NOCOUNT ON;
SET XACT_ABORT ON;
SET LOCK_TIMEOUT 5000;
SET ANSI_NULLS ON;
SET ANSI_PADDING ON;
SET ANSI_WARNINGS ON;
SET ARITHABORT ON;
SET CONCAT_NULL_YIELDS_NULL ON;
SET QUOTED_IDENTIFIER ON;
SET NUMERIC_ROUNDABORT OFF;

BEGIN TRY
    BEGIN TRANSACTION;
    -- Stop checkout writers first. Lock both tables until every step commits.
    DECLARE @Guard bigint;
    SELECT @Guard = COUNT_BIG(*) FROM dbo.Orders WITH (TABLOCKX, HOLDLOCK);
    SELECT @Guard = COUNT_BIG(*) FROM dbo.OrderDetails WITH (TABLOCKX, HOLDLOCK);


    IF NOT EXISTS (SELECT 1 FROM sys.indexes i JOIN sys.index_columns ic
        ON ic.object_id=i.object_id AND ic.index_id=i.index_id JOIN sys.columns c
        ON c.object_id=ic.object_id AND c.column_id=ic.column_id
        WHERE i.object_id=OBJECT_ID('dbo.Orders') AND i.is_primary_key=1
        AND c.name='OrderID' AND ic.key_ordinal=1 AND
        (SELECT COUNT(*) FROM sys.index_columns k WHERE k.object_id=i.object_id
         AND k.index_id=i.index_id AND k.key_ordinal>0)=1)
       OR NOT EXISTS (SELECT 1 FROM sys.indexes i JOIN sys.index_columns ic
        ON ic.object_id=i.object_id AND ic.index_id=i.index_id JOIN sys.columns c
        ON c.object_id=ic.object_id AND c.column_id=ic.column_id
        WHERE i.object_id=OBJECT_ID('dbo.OrderDetails') AND i.is_primary_key=1
        AND c.name='DetailID' AND ic.key_ordinal=1 AND
        (SELECT COUNT(*) FROM sys.index_columns k WHERE k.object_id=i.object_id
         AND k.index_id=i.index_id AND k.key_ordinal>0)=1)
       OR NOT EXISTS (SELECT 1 FROM sys.foreign_keys fk JOIN sys.foreign_key_columns fc
        ON fc.constraint_object_id=fk.object_id
        WHERE fk.parent_object_id=OBJECT_ID('dbo.OrderDetails')
        AND fk.referenced_object_id=OBJECT_ID('dbo.Orders')
        AND COL_NAME(fc.parent_object_id,fc.parent_column_id)='OrderID'
        AND COL_NAME(fc.referenced_object_id,fc.referenced_column_id)='OrderID'
        AND fk.is_disabled=0 AND fk.is_not_trusted=0
        AND fk.delete_referential_action=0 AND fk.update_referential_action=0
        AND (SELECT COUNT(*) FROM sys.foreign_key_columns k WHERE k.constraint_object_id=fk.object_id)=1)
        THROW 51214, 'BCV_PK_OR_FK_DRIFT', 1;
    -- Fail closed on unreviewed dependencies, including non-schema-bound modules.
    IF EXISTS (SELECT 1 FROM sys.columns c WHERE c.object_id IN
        (OBJECT_ID('dbo.Orders'),OBJECT_ID('dbo.OrderDetails')) AND c.is_computed = 1)
       OR EXISTS (SELECT 1 FROM sys.check_constraints WHERE parent_object_id IN
        (OBJECT_ID('dbo.Orders'),OBJECT_ID('dbo.OrderDetails')))
       OR EXISTS (SELECT 1 FROM sys.sql_expression_dependencies WHERE referenced_id IN
        (OBJECT_ID('dbo.Orders'),OBJECT_ID('dbo.OrderDetails')))
       OR EXISTS (SELECT 1 FROM sys.triggers WHERE is_disabled = 0 AND
        (parent_class = 0 OR parent_id IN (OBJECT_ID('dbo.Orders'),OBJECT_ID('dbo.OrderDetails'))))
       OR EXISTS (SELECT 1 FROM sys.server_triggers WHERE is_disabled = 0)
        THROW 51210, 'BCV_DEPENDENCY_REVIEW_REQUIRED', 1;
    IF EXISTS (SELECT 1 FROM sys.columns c WHERE
        ((c.object_id=OBJECT_ID('dbo.Orders') AND c.name='TotalMoney') OR
         (c.object_id=OBJECT_ID('dbo.OrderDetails') AND c.name IN ('Price','ProductName')))
        AND (c.default_object_id <> 0 OR c.rule_object_id <> 0 OR c.is_identity=1
             OR c.is_computed=1 OR c.generated_always_type <> 0 OR c.is_sparse=1))
       OR EXISTS (SELECT 1 FROM sys.index_columns ic JOIN sys.columns c
        ON c.object_id=ic.object_id AND c.column_id=ic.column_id WHERE
        (c.object_id=OBJECT_ID('dbo.Orders') AND c.name='TotalMoney') OR
        (c.object_id=OBJECT_ID('dbo.OrderDetails') AND c.name IN ('Price','ProductName')))
       OR EXISTS (SELECT 1 FROM sys.stats st JOIN sys.stats_columns sc
        ON sc.object_id=st.object_id AND sc.stats_id=st.stats_id JOIN sys.columns c
        ON c.object_id=sc.object_id AND c.column_id=sc.column_id WHERE st.user_created=1 AND
        ((c.object_id=OBJECT_ID('dbo.Orders') AND c.name='TotalMoney') OR
         (c.object_id=OBJECT_ID('dbo.OrderDetails') AND c.name IN ('Price','ProductName'))))
        THROW 51211, 'BCV_COLUMN_DEPENDENCY_OR_DEFAULT_DRIFT', 1;
    IF EXISTS (SELECT 1 FROM sys.tables WHERE object_id IN
        (OBJECT_ID('dbo.Orders'),OBJECT_ID('dbo.OrderDetails'))
        AND (temporal_type <> 0 OR is_memory_optimized=1 OR is_replicated=1 OR is_tracked_by_cdc=1))
        THROW 51212, 'BCV_UNSUPPORTED_TABLE_FEATURE', 1;
    IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id=OBJECT_ID('dbo.Orders')
        AND name='OrderCode' AND TYPE_NAME(user_type_id)='varchar' AND max_length=20
        AND is_nullable=1 AND collation_name='SQL_Latin1_General_CP1_CI_AS')
       OR NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id=OBJECT_ID('dbo.OrderDetails')
        AND name='Quantity' AND TYPE_NAME(user_type_id)='int' AND is_nullable=1)
       OR NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id=OBJECT_ID('dbo.OrderDetails')
        AND name='OrderID' AND TYPE_NAME(user_type_id)='int' AND is_nullable=1)
       OR NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id=OBJECT_ID('dbo.Orders')
        AND name='OrderID' AND TYPE_NAME(user_type_id)='int' AND is_identity=1 AND is_nullable=0)
       OR NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id=OBJECT_ID('dbo.OrderDetails')
        AND name='DetailID' AND TYPE_NAME(user_type_id)='int' AND is_identity=1 AND is_nullable=0)
        THROW 51213, 'BCV_SNAPSHOT_OR_CODE_SCHEMA_DRIFT', 1;
    IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id = OBJECT_ID('dbo.Orders')
        AND name = 'TotalMoney' AND TYPE_NAME(user_type_id) = 'decimal'
        AND precision = 18 AND scale = 0 AND is_nullable = 1)
       OR NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id = OBJECT_ID('dbo.OrderDetails')
        AND name = 'Price' AND TYPE_NAME(user_type_id) = 'decimal'
        AND precision = 18 AND scale = 0 AND is_nullable = 1)
       OR NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id = OBJECT_ID('dbo.OrderDetails')
        AND name = 'ProductName' AND TYPE_NAME(user_type_id) = 'nvarchar'
        AND max_length = 200 AND is_nullable = 1
        AND collation_name = 'SQL_Latin1_General_CP1_CI_AS')
       OR NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id = OBJECT_ID('dbo.Orders')
        AND name = 'OrderCode' AND TYPE_NAME(user_type_id) = 'varchar'
        AND max_length = 20 AND is_nullable = 1
        AND collation_name = 'SQL_Latin1_General_CP1_CI_AS')
        THROW 51001, 'Unexpected source schema; rerun metadata review.', 1;

    IF EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID('dbo.Orders')
        AND name = 'UX_Orders_OrderCode_NotNull')
        THROW 51002, 'Target index already exists; do not apply twice.', 1;

    IF EXISTS (SELECT 1 FROM dbo.Orders WHERE OrderCode IS NOT NULL
        GROUP BY OrderCode HAVING COUNT_BIG(*) > 1)
        THROW 51003, 'Duplicate non-null order codes; resolve separately.', 1;

    -- Both backends are designed for generated uppercase ASCII codes.
    IF EXISTS (SELECT 1 FROM dbo.Orders WHERE OrderCode IS NOT NULL AND
        (DATALENGTH(OrderCode) = 0 OR
         OrderCode COLLATE Latin1_General_100_BIN2 LIKE '%[^A-Z0-9]%'))
        THROW 51004, 'Noncanonical order codes; review without automatic cleanup.', 1;

    ALTER TABLE dbo.Orders ALTER COLUMN TotalMoney decimal(20,2) NULL;
    ALTER TABLE dbo.OrderDetails ALTER COLUMN Price decimal(20,2) NULL;
    ALTER TABLE dbo.OrderDetails ALTER COLUMN ProductName nvarchar(200)
        COLLATE SQL_Latin1_General_CP1_CI_AS NULL;
    CREATE UNIQUE INDEX UX_Orders_OrderCode_NotNull
        ON dbo.Orders (OrderCode) WHERE OrderCode IS NOT NULL;

    EXEC sys.sp_addextendedproperty @name=N'BunChaVietMigrationOwner',
        @value=N'phase3d3:OrderCode:v1', @level0type=N'SCHEMA', @level0name=N'dbo',
        @level1type=N'TABLE', @level1name=N'Orders',
        @level2type=N'INDEX', @level2name=N'UX_Orders_OrderCode_NotNull';

    -- Existing PKs, FKs, identity, defaults and tracking index are not replaced.
    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    IF ERROR_NUMBER() IN (51001,51002,51003,51004,51101,51103,51210,51211,51212,51213,51214,51220) THROW;
    -- Do not print ERROR_MESSAGE(): duplicate errors can contain order codes.
    THROW 51099, 'Migration failed and was rolled back. Review privately; do not log row values.', 1;
END CATCH;
