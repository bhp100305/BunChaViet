-- READ ONLY. Metadata and counts only; no customer, order-code or name values.
SELECT t.name AS TableName, c.name AS ColumnName, ty.name AS DataType,
    c.max_length AS MaxBytes, c.precision AS NumericPrecision, c.scale AS NumericScale,
    c.is_nullable, c.is_identity, CASE WHEN dc.object_id IS NULL THEN 0 ELSE 1 END AS HasDefault,
    CONVERT(varchar(64),HASHBYTES('SHA2_256',dc.definition),2) AS DefaultHash,
    c.collation_name, c.is_computed, c.generated_always_type, c.is_sparse
FROM sys.tables t
JOIN sys.schemas s ON s.schema_id = t.schema_id
JOIN sys.columns c ON c.object_id = t.object_id
JOIN sys.types ty ON ty.user_type_id = c.user_type_id
LEFT JOIN sys.default_constraints dc ON dc.object_id = c.default_object_id
WHERE s.name = 'dbo' AND t.name IN ('Products', 'Orders', 'OrderDetails')
ORDER BY t.name, c.column_id;

SELECT COUNT_BIG(*) AS ProductCount,
    COALESCE(SUM(CASE WHEN Price <> FLOOR(Price) THEN 1 ELSE 0 END),0) AS FractionalPrices,
    COALESCE(SUM(CASE WHEN LEN(ProductName) > 100 THEN 1 ELSE 0 END),0) AS NamesOver100,
    COALESCE(MAX(LEN(ProductName)),0) AS MaxNameLength
FROM dbo.Products;

SELECT COUNT_BIG(*) AS OrderCount,
    COALESCE(SUM(CASE WHEN OrderCode IS NULL THEN 1 ELSE 0 END),0) AS NullCodes,
    COALESCE(SUM(CASE WHEN OrderCode IS NOT NULL AND LTRIM(RTRIM(OrderCode)) = '' THEN 1 ELSE 0 END),0) AS BlankCodes,
    COALESCE(SUM(CASE WHEN TotalMoney IS NULL THEN 1 ELSE 0 END),0) AS NullTotals,
    COALESCE(SUM(CASE WHEN TotalMoney < 0 THEN 1 ELSE 0 END),0) AS NegativeTotals
FROM dbo.Orders;

SELECT COUNT_BIG(*) AS DuplicateGroups FROM (
    SELECT OrderCode FROM dbo.Orders WHERE OrderCode IS NOT NULL
    GROUP BY OrderCode HAVING COUNT_BIG(*) > 1
) d;
SELECT COUNT_BIG(*) AS NormalizedDuplicateGroups FROM (
    SELECT UPPER(RTRIM(OrderCode)) AS k FROM dbo.Orders WHERE OrderCode IS NOT NULL
    GROUP BY UPPER(RTRIM(OrderCode)) HAVING COUNT_BIG(*) > 1
) d;

SELECT COUNT_BIG(*) AS NoncanonicalCodes FROM dbo.Orders WHERE OrderCode IS NOT NULL
    AND (DATALENGTH(OrderCode) = 0 OR OrderCode COLLATE Latin1_General_100_BIN2 LIKE '%[^A-Z0-9]%');

SELECT COUNT_BIG(*) AS DetailCount,
    COALESCE(SUM(CASE WHEN d.Price <> FLOOR(d.Price) THEN 1 ELSE 0 END),0) AS FractionalPrices,
    COALESCE(SUM(CASE WHEN d.Price IS NULL THEN 1 ELSE 0 END),0) AS NullPrices,
    COALESCE(SUM(CASE WHEN DATALENGTH(d.ProductName) > 200 THEN 1 ELSE 0 END),0) AS NamesNotFittingNvarchar100,
    COALESCE(SUM(CASE WHEN d.OrderID IS NULL THEN 1 ELSE 0 END),0) AS NullOrderIDs,
    COALESCE(SUM(CASE WHEN d.OrderID IS NOT NULL AND o.OrderID IS NULL THEN 1 ELSE 0 END),0) AS OrphanDetails,
    COALESCE(SUM(CASE WHEN d.Quantity IS NULL OR d.Quantity <= 0 THEN 1 ELSE 0 END),0) AS InvalidQuantities
FROM dbo.OrderDetails d LEFT JOIN dbo.Orders o ON o.OrderID = d.OrderID;

SELECT t.name AS TableName, i.name AS IndexName, i.is_unique, i.is_primary_key,
    CONVERT(varchar(64),HASHBYTES('SHA2_256',i.filter_definition),2) AS FilterHash,
    i.is_disabled, i.is_hypothetical, i.type_desc, c.name AS ColumnName, ic.key_ordinal, ic.is_included_column
FROM sys.tables t JOIN sys.schemas s ON s.schema_id = t.schema_id
JOIN sys.indexes i ON i.object_id = t.object_id
JOIN sys.index_columns ic ON ic.object_id = i.object_id AND ic.index_id = i.index_id
JOIN sys.columns c ON c.object_id = ic.object_id AND c.column_id = ic.column_id
WHERE s.name = 'dbo' AND t.name IN ('Products', 'Orders', 'OrderDetails')
ORDER BY t.name, i.name, ic.key_ordinal;

SELECT OBJECT_NAME(f.parent_object_id) AS ChildTable, f.name AS ConstraintName,
    OBJECT_NAME(f.referenced_object_id) AS ParentTable, f.is_disabled, f.is_not_trusted,
    f.delete_referential_action_desc, f.update_referential_action_desc
FROM sys.foreign_keys f WHERE f.parent_object_id IN
    (OBJECT_ID('dbo.Products'), OBJECT_ID('dbo.Orders'), OBJECT_ID('dbo.OrderDetails'))
    OR f.referenced_object_id IN
    (OBJECT_ID('dbo.Products'), OBJECT_ID('dbo.Orders'), OBJECT_ID('dbo.OrderDetails'));

SELECT OBJECT_NAME(parent_id) AS TableName, name AS TriggerName, is_disabled
FROM sys.triggers WHERE parent_id IN (OBJECT_ID('dbo.Orders'), OBJECT_ID('dbo.OrderDetails'));

-- Additional 3D.3 inventory. Definitions are hashed: no arbitrary literal values printed.
SELECT CONVERT(varchar(30),SERVERPROPERTY('ProductVersion')) AS EngineVersion,
    d.compatibility_level, d.collation_name,
    HAS_PERMS_BY_NAME(DB_NAME(),'DATABASE','VIEW DEFINITION') AS CanViewDatabase,
    HAS_PERMS_BY_NAME(NULL,NULL,'VIEW ANY DEFINITION') AS CanViewServerMetadata
FROM sys.databases d WHERE d.database_id=DB_ID();
SELECT CASE WHEN 'i' COLLATE SQL_Latin1_General_CP1_CI_AS = 'I' THEN 1 ELSE 0 END AS EqualI,
    CASE WHEN 'abc ' COLLATE SQL_Latin1_General_CP1_CI_AS = 'ABC' THEN 1 ELSE 0 END AS EqualCaseAndTrailingSpace;
SELECT COUNT_BIG(*) AS ProductNamesNotFittingOldDetail,
    COALESCE(MAX(DATALENGTH(ProductName)),0) AS MaxProductNameBytes
FROM dbo.Products WHERE DATALENGTH(ProductName)>200;
SELECT COUNT_BIG(*) AS UnsafeOrderTotals FROM dbo.Orders
WHERE TotalMoney <> TRY_CONVERT(decimal(20,2),TotalMoney)
   OR (TotalMoney IS NOT NULL AND TRY_CONVERT(decimal(20,2),TotalMoney) IS NULL);
SELECT COUNT_BIG(*) AS UnsafeDetailValues FROM dbo.OrderDetails
WHERE (Price IS NOT NULL AND TRY_CONVERT(decimal(20,2),Price) IS NULL)
   OR Price <> TRY_CONVERT(decimal(20,2),Price) OR DATALENGTH(ProductName)>400;
SELECT OBJECT_NAME(parent_object_id) AS TableName,name,is_disabled,is_not_trusted,
    CONVERT(varchar(64),HASHBYTES('SHA2_256',definition),2) AS DefinitionHash
FROM sys.check_constraints WHERE parent_object_id IN
    (OBJECT_ID('dbo.Orders'),OBJECT_ID('dbo.OrderDetails'));
SELECT OBJECT_NAME(referencing_id) AS ReferencingObject,referencing_minor_id,
    OBJECT_NAME(referenced_id) AS ReferencedObject,referenced_minor_id,is_schema_bound_reference
FROM sys.sql_expression_dependencies WHERE referenced_id IN
    (OBJECT_ID('dbo.Orders'),OBJECT_ID('dbo.OrderDetails'));
SELECT OBJECT_NAME(st.object_id) AS TableName,st.name,st.user_created,st.auto_created,
    c.name AS ColumnName FROM sys.stats st JOIN sys.stats_columns sc
    ON sc.object_id=st.object_id AND sc.stats_id=st.stats_id JOIN sys.columns c
    ON c.object_id=sc.object_id AND c.column_id=sc.column_id
WHERE st.object_id IN (OBJECT_ID('dbo.Orders'),OBJECT_ID('dbo.OrderDetails'));
SELECT name,is_disabled FROM sys.triggers WHERE parent_class=0;
SELECT name,is_disabled FROM sys.server_triggers;
SELECT name,temporal_type,is_memory_optimized,is_replicated,is_tracked_by_cdc
FROM sys.tables WHERE object_id IN (OBJECT_ID('dbo.Orders'),OBJECT_ID('dbo.OrderDetails'));

-- Source schema readiness: missing columns are reported as mismatches, not hidden.
SELECT e.TableName,e.ColumnName,
    CASE WHEN c.column_id IS NOT NULL AND TYPE_NAME(c.user_type_id)=e.TypeName
        AND c.is_nullable=e.Nullable AND c.is_identity=e.IdentityExpected
        AND (e.MaxBytes IS NULL OR c.max_length=e.MaxBytes)
        AND (e.PrecisionExpected IS NULL OR c.precision=e.PrecisionExpected)
        AND (e.ScaleExpected IS NULL OR c.scale=e.ScaleExpected)
        AND (e.NoDefault=0 OR (c.default_object_id=0 AND c.rule_object_id=0))
        THEN 1 ELSE 0 END AS MatchesPreUpSchema
FROM (VALUES
    ('Orders','OrderID','int',0,1,NULL,NULL,NULL,0),
    ('Orders','OrderCode','varchar',1,0,20,NULL,NULL,0),
    ('Orders','TotalMoney','decimal',1,0,NULL,18,0,1),
    ('OrderDetails','DetailID','int',0,1,NULL,NULL,NULL,0),
    ('OrderDetails','OrderID','int',1,0,NULL,NULL,NULL,0),
    ('OrderDetails','ProductName','nvarchar',1,0,200,NULL,NULL,1),
    ('OrderDetails','Quantity','int',1,0,NULL,NULL,NULL,0),
    ('OrderDetails','Price','decimal',1,0,NULL,18,0,1)
) e(TableName,ColumnName,TypeName,Nullable,IdentityExpected,MaxBytes,PrecisionExpected,ScaleExpected,NoDefault)
LEFT JOIN sys.columns c ON c.object_id=OBJECT_ID('dbo.'+e.TableName) AND c.name=e.ColumnName;
SELECT COUNT_BIG(*) AS LossyDownTotals FROM dbo.Orders
WHERE TotalMoney <> FLOOR(TotalMoney) OR TotalMoney < -999999999999999999 OR TotalMoney > 999999999999999999;
