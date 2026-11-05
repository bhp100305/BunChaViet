# Phase 3D.2 — kết quả kiểm chứng và quy trình test chờ duyệt

Ngày kiểm tra: 2026-11-04 (Asia/Bangkok).

**Không chạy migration, không tạo DB/Neon branch, không sửa checkout/frontend.**
Đã đọc toàn bộ README và sáu script. Chỉ tạo báo cáo này; không sửa các script SQL.
Thiết kế (20,2), tên chi tiết 200 và unique OrderCode đã được duyệt; việc thực thi
trên bất kỳ database nào chưa được duyệt trong phase này.

## 1. Những kiểm tra thực sự đã thực hiện

| Kiểm tra | Kết quả |
| --- | --- |
| SQL Server hiện tại | SQL Server 2022, major 16, compatibility 160 |
| Neon hiện tại | PostgreSQL 18.6, collation C.UTF-8 |
| preflight_sqlserver.sql | 10 SELECT chạy thành công trên Local |
| preflight_postgres.sql | 12 SELECT chạy thành công trên Neon |
| Cú pháp ba file SQL Server | PASS, Microsoft ScriptDom 161.9142.1, TSql160Parser |
| Cú pháp ba file PostgreSQL | PASS, pglast 8.7 parse_sql; up/down thêm parse_plpgsql |
| ALTER/CREATE/DROP/INSERT/UPDATE/DELETE | Không thực hiện |
| Diễn tập up/down bằng engine | Chưa thực hiện |

Parser được cài trong thư mục tạm, không thêm dependency vào dự án. Parser PASS
không chứng minh quyền DDL, dependency runtime, timeout hoặc rollback trên engine.
Không gửi cả file up/down vào database, kể cả để thử approval flag mặc định.

Nguồn parser: [Microsoft ScriptDom](https://github.com/microsoft/SqlScriptDOM),
[pglast API](https://pglast.readthedocs.io/en/latest/api.html).

## 2. Dữ liệu và dependency vừa đối chiếu lại

- Cả hai: 21 sản phẩm, giá không có phần lẻ, tên dài nhất 30, không tên >100.
- Cả hai: 27 đơn, không mã NULL/rỗng/trùng, không trùng sau chuẩn hóa, không mã
  ngoài ASCII viết hoa/chữ số. Không TotalMoney NULL hoặc âm.
- Cả hai: OrderDetails có 0 dòng, không chi tiết mồ côi hoặc quantity bất thường.
- Neon: không NaN trong Products.Price, Orders.TotalMoney, OrderDetails.Price.
- Metadata OrderDetails: DetailID identity/PK; OrderID nullable và FK đến Orders;
  ProductName nvarchar/varchar(100), Quantity int nullable, Price (18,0) nullable.
- SQL Server: không user-created statistics trên ba cột sẽ đổi; không dependency
  schema-bound được catalog báo cho Orders/OrderDetails; không DDL trigger enabled
  ở cấp database. Các default/FK/index đã được đối chiếu qua preflight.
- PostgreSQL: không view dependency được information_schema báo trên ba cột đổi;
  không event trigger enabled. Thông tin vẫn phụ thuộc quyền nhìn metadata của role.

Không khẳng định đã loại trừ mọi dependency bên ngoài DB: ứng dụng, báo cáo,
dynamic SQL, quyền của role khác hoặc server-level DDL trigger cần kiểm tra riêng
khi lên kế hoạch thực thi. Không xuất giá trị mã đơn, tên món, khách hàng hoặc URL.

## 3. Trạng thái từng script

| File | Trạng thái |
| --- | --- |
| preflight_sqlserver.sql | Dùng được cho kiểm tra chỉ đọc; đã chạy thành công |
| preflight_postgres.sql | Dùng được cho kiểm tra chỉ đọc; đã chạy thành công |
| sqlserver_up.sql | Cú pháp đạt; sẵn sàng review/chuẩn bị diễn tập, chưa được phép chạy |
| postgres_up.sql | SQL và PL/pgSQL đạt; chưa được phép chạy |
| sqlserver_down.sql | Cú pháp đạt; cần gia cố xác minh index trước khi duyệt thực thi |
| postgres_down.sql | SQL và PL/pgSQL đạt; cần gia cố xác minh index trước khi duyệt thực thi |

Không tìm thấy lỗi cú pháp qua parser. Các mục sau là điểm an toàn/diagnostic cần
sửa hoặc chốt trước rehearsal, không phải bằng chứng migration đã thất bại trên DB:

1. **Cần chặn outer transaction trên SQL Server.** README yêu cầu connection riêng
   nhưng script chưa kiểm tra `@@TRANCOUNT = 0` trước BEGIN TRY/BEGIN TRANSACTION,
   chưa bảo đảm `IMPLICIT_TRANSACTIONS OFF`. Nếu chạy trong transaction có sẵn,
   COMMIT có thể chỉ giảm nesting, còn CATCH/ROLLBACK có thể hủy cả công việc của
   caller. Cần từ chối bên ngoài TRY khi đã có transaction; dùng connection mới,
   autocommit và tắt implicit transactions. PostgreSQL cũng phải kiểm tra trạng
   thái IDLE ở client trước khi gửi file BEGIN/COMMIT; không dùng chung connection
   đang có transaction, không bật autocommit để ép commit công việc chưa hoàn tất.
2. **Guard index của down chưa đủ chặt.** SQL Server chỉ kiểm tra tên/unique/filter;
   PostgreSQL kiểm tra tên/table/unique/có predicate. Chưa đối chiếu chính xác key
   column hoặc expression, filter `IS NOT NULL`, số key, trạng thái enabled/valid.
   Có thể DROP nhầm index cùng tên đã bị sửa. Cần xác minh đầy đủ definition trước
   DROP; từ chối nếu drift, không dùng CASCADE hoặc tự sửa index.
3. **Approval flag nên kiểm tra strict true.** Giá trị mặc định false/0 hiện an toàn.
   Tuy nhiên nếu sửa thành NULL, `IF @Approved <> 1` và `IF NOT approved` đều không
   vào nhánh từ chối. Đề xuất `IF ISNULL(@Approved,0) <> 1` và
   `IF approved IS DISTINCT FROM TRUE THEN`.
4. **Bắt lỗi hiện che cả guard.** CATCH/EXCEPTION đổi mọi lỗi thành thông báo chung,
   nên không phân biệt chưa duyệt, schema drift, duplicate hay lossless-down bị
   chặn. Cần mã lỗi cố định cho từng nhóm an toàn, giữ nguyên che nội dung driver
   và dữ liệu duplicate. Không khôi phục ERROR_MESSAGE()/raw exception vào log.
5. **Preflight còn thiếu một số inventory/giá trị đặc biệt.** Nên bổ sung thống kê
   user-created, dependency/view/DDL trigger, PostgreSQL numeric NaN; NaN không bị
   bắt bởi kiểm tra `value <> FLOOR(value)`. Kiểm tra bổ sung lần này đã không thấy
   các vấn đề đó trong phạm vi catalog/role nêu trên, nhưng script cần tự phản ánh.

Không cần thay đổi thiết kế money/name để sửa các guard này. Chưa thay các cờ duyệt.

## 4. NULL, collation và khả năng ghi snapshot

- (18,0) → (20,2) giữ 18 chữ số phần nguyên và thêm 2 số lẻ; toàn bộ số tiền cũ
  hữu hạn đều biểu diễn được chính xác. Không đổi nullable, default hoặc identity.
- SQL Server giữ CI_AS; PostgreSQL index UPPER(RTRIM(OrderCode)) đáp ứng case và
  trailing-space equality cho mã ASCII hiện tại, đã xác minh collation C.UTF-8.
  Không cam kết tương đương cho mọi Unicode/collation.
- Filter `IS NOT NULL` cho phép nhiều NULL. Index không phải CHECK: nó không tự
  cấm mã rỗng, chữ thường hay ký tự không canonical được ghi sau migration.
  Guard chỉ kiểm tra dữ liệu vào thời điểm up; ứng dụng vẫn phải sinh/validate mã.
- Down kiểm tra DATALENGTH >200 byte ở SQL Server để chặn tên không fit
  nvarchar(100), gồm cả trailing spaces; PostgreSQL dùng LENGTH >100.
- Sau up, các cột có thể lưu tên snapshot 200, quantity nguyên và đơn giá 2 số lẻ.
  Cột vẫn nullable nên ứng dụng phải cung cấp đủ dữ liệu và kiểm tra quantity >0.
- Price nên mang nghĩa đơn giá từ DB, không phải thành tiền; ghi một dòng mỗi
  ProductID đã gộp quantity. Đây là hợp đồng ứng dụng cần duyệt khi hoàn thiện 3D.
- Lấy OrderID bằng OUTPUT INSERTED.OrderID / RETURNING "OrderID". Ghi Orders và
  chi tiết cùng connection, một commit; lỗi chi tiết rollback toàn bộ. Chưa chạy
  INSERT thử trên DB hiện tại.

## 5. Ảnh hưởng 27 đơn cũ

Về thiết kế, không có UPDATE/DELETE hoặc backfill; mã/ID/trạng thái/thời gian và
giá trị tiền cũ giữ nguyên. Tổng cũ chỉ biểu diễn thêm `.00`; tên chi tiết chỉ được
mở rộng. Không thể tái tạo chi tiết lịch sử vì bảng đang rỗng.

Đây là phân tích và kiểm tra điều kiện nguồn, **chưa phải kết quả before/after**.
Rehearsal cần chứng minh row count và từng giá trị tiền/ID còn nguyên trên fixture.
DDL có thể rewrite bảng, tăng transaction log/dung lượng và chặn đọc/ghi. Index
unique có thể khiến writer cũ nhận lỗi duplicate; không mở writer cũ không an toàn
chỉ vì schema up thành công. ShippingFee vẫn float/double như thiết kế gốc.

## 6. Trạng thái DB test và cách chuẩn bị

Chưa tìm thấy biến cấu hình test DB riêng trong environment/.env/.env.test hiện
có. Catalog của các endpoint hiện tại không thấy database theo mẫu tên
`BunCha...Test`/`Test...BunCha`. **Không thể từ đó kết luận mọi Neon branch khác đều
không tồn tại. Chưa có đích test nào được xác nhận an toàn.**

Chỉ thực hiện các bước sau sau khi người dùng phê duyệt tạo đích test:

### SQL Server

1. Người vận hành tạo database riêng, ví dụ `BunChaViet_MigrationTest`, bằng SSMS
   trên SQL Server 2022; không dùng BunCha hiện tại, không restore đè DB khác.
2. Dùng Generate Scripts với **Schema only**, đúng dbo, identity, defaults,
   collation, PK/FK/index; cần Categories để FK Products hoạt động.
3. Review script output: không CREATE/USE tên DB thật, không chứa dữ liệu hoặc
   credential. Không chạy nguyên BunchaViet.sql cũ: có dữ liệu tài khoản và target DB.
4. Dùng role chỉ có quyền trong DB test; kiểm tra DB_NAME() khớp đích đã duyệt
   trước mọi ghi/DDL. Không lấy connection fallback từ environment production.

### PostgreSQL

1. Chọn đích riêng: PostgreSQL 18 local cô lập, hoặc **schema-only branch** Neon
   do người dùng tạo sau khi kiểm tra quota/free plan. Không tạo compute trả phí.
2. Copy schema không data, giữ public, quoted identifiers, identity, FK/defaults
   và collation. Không copy token hoặc tài khoản thật.
3. Trên Neon có thể thao tác Console: Branches → New branch → schema-only,
   kiểm tra đúng source và quota trước xác nhận. Tính năng còn beta theo tài liệu.
4. Tạo role/quyền riêng và cấu hình `TEST_POSTGRES_DATABASE_URL` bằng secret ngoài
   repository. Xác minh cả endpoint/branch được duyệt, role và current_database().
   Chỉ tên database không đủ: các Neon branch có thể cùng tên database.

Harness test tương lai phải fail nếu thiếu cấu hình test; tuyệt đối không fallback
sang DATABASE_URL/DB_NAME hiện tại. Chưa tạo harness có thể chạy DDL tự động.
Không chỉ dựa vào hậu tố `_test` để xác nhận một target an toàn.

Tài liệu: [Neon schema-only branches](https://neon.com/docs/guides/branching-schema-only).

## 7. Ma trận rehearsal cần phê duyệt trên DB test

| Ca kiểm thử | Kết quả cần đạt |
| --- | --- |
| Baseline fake 21 sản phẩm, 27 đơn, 0 chi tiết | Không có PII; schema khớp nguồn |
| Approval false/0 và NULL | Bị chặn trước DDL; schema/data không đổi |
| Connection đã có outer transaction / implicit transactions | Phải từ chối, không commit/rollback công việc của caller |
| Up trên schema nguồn chuẩn | 3 cột và đúng index đổi; các phần khác giữ nguyên |
| Up lần hai / sai kiểu cột / index đích có sẵn | Bị chặn, không áp dụng một phần |
| Source có mã trùng hoặc không canonical | Bị chặn; không tự cleanup |
| Source có nhiều NULL OrderCode | Up thành công, NULL được giữ đúng hợp đồng |
| Exact code duplicate sau up | Unique error, rollback, không có dòng thứ hai |
| Code khác case/trailing spaces, gồm I/i | Bị coi là trùng trên cả hai backend |
| Hai connection insert cùng code đồng thời | Chỉ một commit; bên lỗi không để lại chi tiết |
| Đọc lại 27 fixture sau up | ID/code/status/timestamps bằng baseline, tiền bằng Decimal |
| Tiền có 0.01, 123.45, biên +/-999999999999999999.99 | Lưu/đọc chính xác; vượt range bị lỗi |
| Tên Việt 101/200 và vượt 200; UTF-16 supplementary | Fit đúng giới hạn từng backend, không cắt ngầm |
| OrderID OUTPUT/RETURNING và insert nhiều chi tiết | FK đúng; lấy ID của chính transaction |
| Lỗi khi ghi chi tiết thứ hai | Cả Orders và mọi chi tiết rollback; identity gap được chấp nhận |
| Down khi chỉ có tiền nguyên và tên fit 100 | Về schema cũ; không mất giá trị, giữ FK/default/index cũ |
| Down có tiền lẻ, tên dài hoặc numeric NaN | Từ chối; index và schema mới không đổi |
| Down khi index cùng tên sai definition | Phải từ chối sau khi gia cố guard |
| Cố tình gây lỗi DDL giữa migration | Rollback mọi thay đổi trước đó trên DB test |
| Connection khác giữ lock | Timeout; không có migration áp dụng dở dang |

Tất cả fixture dùng dữ liệu giả; không lấy 27 bản ghi thật. Có thể thêm fixture
chi tiết lịch sử giả để kiểm tra bảo toàn; không backfill DB thật. Không tự chạy
matrix này trong 3D.2, kể cả khi đã có DB test. Unique code không kiểm chứng
idempotency checkout; CheckoutRequests vẫn chưa được duyệt triển khai.

## 8. Thứ tự duyệt tiếp theo

1. Duyệt sửa các guard/preflight/diagnostic đã nêu, không đổi thiết kế schema.
2. Duyệt tạo/cung cấp đúng test target cho mỗi backend và fixture/harness cô lập.
3. Duyệt chạy rehearsal up/down và DML test **chỉ trên test targets đó**.
4. Sau khi có bằng chứng rehearsal: duyệt backup, maintenance, timeout, rollback
   và người thực hiện trước khi chạy riêng trên từng database hiện tại.

Chưa có bất kỳ phê duyệt thực thi migration hoặc idempotency nào được suy diễn từ
việc đã đồng ý thiết kế. Các file SQL hiện giữ nguyên và approval flag vẫn false/0.
