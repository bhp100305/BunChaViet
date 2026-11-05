# Phase 3D.2 — kiểm chứng trước khi áp dụng

Ngày: 2026-11-05, Asia/Bangkok. **Chưa được phép thực thi migration.**

Đã đọc toàn bộ README và sáu script SQL của phase3d1. Chỉ kết nối driver trực tiếp,
SELECT số liệu tổng hợp/catalog; rollback và đóng connection. Không gọi
`database.get_connection()` vì nhánh Local có `_ensure_product_availability_column()`
có thể ALTER Products và commit. Không chạy up/down, kể cả với flag false.
Không sửa các script phase3d1, checkout, frontend, dữ liệu thật hoặc CheckoutRequests.

## Kết quả và giới hạn chứng cứ

| Kiểm tra trực tiếp hôm nay | SQL Server Local | PostgreSQL hiện cấu hình |
| --- | --- | --- |
| Orders | 27 | 27 |
| OrderDetails | 0 | 0 |
| Nhóm OrderCode trùng | 0, so sánh cột theo collation SQL Server | 0, UPPER(RTRIM) |
| Database có tên chứa test hoặc phase3d trong catalog nhìn thấy | 0 | 0 |

Đây không phải chứng minh không tồn tại DB test: tên có thể khác, quyền nhìn catalog
có thể giới hạn, Neon branch/project khác không được liệt kê bởi pg_database.
**Chưa có database test được xác nhận an toàn.** Không tạo database/branch nào.
Không đọc hoặc in bản ghi khách hàng, OrderCode, credential hay URL kết nối.

Metadata OrderDetails thực tế ở hai backend:

| Cột | SQL Server | PostgreSQL | NULL |
| --- | --- | --- | --- |
| DetailID | int identity | integer identity | Không |
| OrderID | int | integer | Có |
| ProductName | nvarchar(100), 200 byte, SQL_Latin1_General_CP1_CI_AS | varchar(100), collation_name NULL (dùng mặc định) | Có |
| Quantity | int | integer | Có |
| Price | decimal(18,0) | numeric(18,0) | Có |

Cấu trúc đủ lưu snapshot tên món, quantity, đơn giá sau mở rộng; không có ProductID
trong snapshot và không tự thêm cột này. NULL và quantity <= 0 chưa được migration
cấm. Ứng dụng tương lai phải kiểm tra tên/giá/quantity, ghi Price với nghĩa đơn giá.
`main.py:create_order` hiện chỉ ghi Orders; migration không tự kích hoạt ghi chi tiết.

FK/default/index/trigger và Orders.TotalMoney được mô tả trong snapshot phase3d1
ngày 2026-11-04; chưa tái audit đầy đủ những đối tượng đó hôm nay. Phải chạy lại
toàn bộ preflight và bổ sung dependency/collation trước rehearsal và production.

## Trạng thái từng script

| Script phase3d1 | Kết luận |
| --- | --- |
| preflight_sqlserver.sql | Sẵn sàng dùng cho kiểm tra chỉ đọc; cần bổ sung phạm vi bên dưới |
| preflight_postgres.sql | Sẵn sàng dùng cho kiểm tra chỉ đọc; cần bổ sung phạm vi bên dưới |
| sqlserver_up.sql | Không thấy lỗi cú pháp khi review tĩnh; chỉ đủ làm ứng viên rehearsal sau hardening |
| postgres_up.sql | Không thấy lỗi cú pháp khi review tĩnh; cần xác minh locale/collation |
| sqlserver_down.sql | Chưa sẵn sàng chạy: guard xác nhận index chưa đủ chặt |
| postgres_down.sql | Chưa sẵn sàng chạy: guard xác nhận index chưa đủ chặt |

Chưa parse/compile/thực thi DDL bằng engine test. Không coi review tĩnh là PASS engine.

## SQL, constraint, index, NULL và rollback

1. (18,0) → (20,2) giữ đủ 18 chữ số nguyên, không mất giá trị tiền cũ; tên 100 → 200
   là mở rộng. Hai cột tiền giữ NULL. SQL Server ghi rõ COLLATE và NULL; PostgreSQL
   ALTER TYPE không yêu cầu đổi NULL/default/collation. Không có DML/backfill/reseed.
2. Filtered unique index SQL Server và partial expression index PostgreSQL có cú pháp
   phù hợp. SQL Server đã đặt đủ SET options cho filtered index. Phải kiểm tra cả
   SET options của connection ứng dụng khi ghi sau này, không chỉ connection migration.
3. Hai index cho phép nhiều NULL; không cấm mã rỗng hoặc mã không canonical ở các lần
   ghi tương lai. Up chỉ kiểm tra canonical dữ liệu tại thời điểm chạy.
4. PostgreSQL UPPER/RTRIM phụ thuộc locale/collation. `collation_name IS NULL` không
   chứng minh đang dùng C hay quy tắc tương đương CI_AS. Cần ghi nhận version engine,
   database locale/provider, collation thực tế của OrderCode và thử cả chữ i/I,
   hoa/thường, trailing ASCII spaces. Không cam kết tương đương Unicode. Nếu yêu cầu
   ASCII độc lập locale, đề xuất expression COLLATE "C" với approval riêng cho sửa
   định nghĩa; không âm thầm đổi collation. Index expression không thay đổi tracking
   query so sánh cột thô và không bảo đảm query đó sử dụng index.
5. Up SQL Server khóa Orders rồi OrderDetails, dùng XACT_ABORT + TRY/CATCH rollback.
   PostgreSQL khóa ACCESS EXCLUSIVE trong transaction, lỗi làm transaction abort;
   client phải dừng và rollback/đóng connection, không tiếp tục batch sau lỗi.
   Query cancel/timeout cũng cần xử lý tại client; không dựa riêng EXCEPTION handler.
6. Down chặn phần lẻ, tiền vượt ±999999999999999999 và tên vượt giới hạn cũ.
   SQL Server DATALENGTH > 200 kiểm tra đúng UTF-16 và trailing spaces;
   PostgreSQL LENGTH > 100 kiểm tra theo ký tự. Không ROUND/LEFT/DELETE/CASCADE.
7. **Cần sửa guard down trước thực thi:** hiện chỉ xác nhận tên/table, unique và có
   predicate. Một index cùng tên nhưng khác key/expression/filter vẫn có thể bị DROP.
   SQL Server cần kiểm tra đúng OrderCode là key duy nhất, predicate IS NOT NULL,
   trạng thái enabled, không hypothetical và đúng loại index. PostgreSQL cần kiểm tra
   expression UPPER(RTRIM(OrderCode)), predicate, key count, collation/opclass,
   indisvalid/indisready và không phải constraint-backed index. Metadata khác thì dừng.
8. **Cần bổ sung guard target và transaction:** approval flag không xác nhận đang ở
   DB test. Runner phải allowlist đúng server/database/backend đã duyệt và từ chối
   URL hiện tại. SQL Server nên từ chối @@TRANCOUNT <> 0 trước BEGIN; PostgreSQL dùng
   connection mới autocommit, không gửi script vào outer transaction. Nếu lồng SQL
   Server transaction, CATCH rollback có thể rollback cả transaction của caller.
9. Tiền >2 số lẻ có thể bị engine làm tròn khi ép vào (20,2). README yêu cầu từ chối
   phải được hiểu là validation ứng dụng trước bind/INSERT, không phải đảm bảo của DDL.
   Tương tự không dùng explicit varchar cast để kiểm tra tên quá dài vì có thể cắt tên.
10. Preflight cần thêm collation, CHECK constraints, computed/generated columns,
    view/schema-bound dependencies, user statistics/index dependencies, DDL/event
    triggers, quyền, version engine và default. SQL Server LEN tên Products bỏ qua
    trailing spaces: bổ sung DATALENGTH để đánh giá sức chứa nvarchar chính xác.
    PostgreSQL kiểm tra convalidated và collation provider/version khi có.
    Guard hiện tại không thay thế audit này.

## Ảnh hưởng 27 đơn cũ

Theo script, up chỉ đổi biểu diễn TotalMoney thành .00, thêm index và mở rộng cột
chi tiết rỗng. Không đổi OrderID, OrderCode, trạng thái, khách, ngày hoặc tổng tiền
theo giá trị số; không tính lại từ menu. Không có dữ liệu để khôi phục chi tiết 27
đơn. Không backfill suy đoán. Đây là kết luận thiết kế; chưa có rehearsal chứng minh
trước/sau. DDL có thể rewrite/log/block cả bảng; số dòng ít không loại bỏ dependency
hay lock contention. SQL Server decimal precision 18 → 20 tăng storage 9 → 13 byte.

## Chuẩn bị database test — chỉ hướng dẫn, chưa thực hiện

1. Người vận hành chọn hai target riêng: ví dụ SQL Server `BunChaViet_Phase3D2_Test`
   trên instance test; PostgreSQL `bunchaviet_phase3d2_test` trên cluster test riêng.
   Ưu tiên instance/container riêng để tách tài nguyên. Không tự tạo Neon branch.
2. Sau duyệt, SQL Server dùng SSMS tạo DB với collation tương ứng nguồn, tạo login
   test chỉ có quyền DB test. PostgreSQL dùng công cụ quản trị tạo DB từ template0,
   đúng encoding/locale/provider/version nguồn và role test riêng. Không chọn locale
   mặc định tùy tiện. CREATE DATABASE là bước riêng, ngoài transaction migration.
   Nếu muốn Neon test, người vận hành phải duyệt project/branch, chi phí và xử lý
   dữ liệu trước; ưu tiên schema + dữ liệu giả, không clone PII mặc định.
3. Xuất **schema-only** nguồn bằng công cụ tương ứng, review nội dung trước import
   vào target. Không chạy nguyên BunchaViet.sql vì có dữ liệu seed thật và ngữ cảnh
   database riêng. Dựng PK/FK/default/identity/index/trigger giống nguồn; thêm các bảng
   FK cần thiết. Seed 27 đơn giả, 21 sản phẩm giả và 0 chi tiết cho baseline; thêm
   fixture chi tiết riêng để thật sự kiểm tra chuyển đổi Price/ProductName.
4. Lưu thông tin kết nối test riêng ở secret store/session, không thay .env ứng dụng,
   không commit secret. Xác minh backend + identity target bằng SELECT và đối chiếu
   allowlist chính xác. Không dùng tên chứa 'test' làm bằng chứng duy nhất.
5. Dùng direct driver; tắt mọi startup hook, email, background job và writer ứng dụng.
   PostgreSQL rehearsal chỉ có giá trị collation nếu khớp nguồn. Nếu không khớp,
   ghi rõ giới hạn và chưa duyệt production dựa trên kết quả đó.

## Ma trận kiểm thử sau khi được duyệt chạy trên test

| Bài thử | Kết quả bắt buộc |
| --- | --- |
| Approval false/0; sai target; sai schema; index tên đã tồn tại | Từ chối; schema và dữ liệu không đổi |
| Up baseline 27 đơn giả + fixture chi tiết | Đúng (20,2)/200/NULL; so sánh mọi dòng theo PK và mọi giá trị trước/sau, không chỉ SUM/count |
| Biên tiền cũ ±999999999999999999 và NULL | Bảo toàn; không overflow khi up |
| Metadata trước/sau | PK/FK/default/identity/collation/tracking index giữ nguyên; chỉ index mới và ba type thay đổi |
| Ghi snapshot sau up | Tên tiếng Việt, 100/101/200 ký tự; UTF-16 supplementary riêng ở SQL Server; đơn giá .01/.99 và quantity hợp lệ lưu đúng |
| Đổi menu sau ghi trên test | Snapshot tên/giá đơn cũ không đổi |
| Unique INSERT và UPDATE | Trùng chính xác, abc/ABC, i/I, mã + dấu cách cuối bị từ chối theo hợp đồng; mã khác được chấp nhận |
| NULL/rỗng/space/leading space | Nhiều NULL được phép; ghi rõ rỗng/space không bị cấm toàn diện, không tự trim đầu |
| Hai connection cùng mã | Nếu A commit, B thất bại unique; nếu A rollback, B có thể thành công; không có hai mã tương đương cùng commit |
| Orders + nhiều details cùng transaction | Lấy ID bằng OUTPUT/RETURNING; lỗi FK/overflow tại detail sau → rollback cả Orders và mọi detail; không trả thành công trước commit |
| Lỗi sau ALTER nhưng trước COMMIT (bản test có fault injection) | Toàn bộ schema/index/data trở về baseline; kiểm tra bằng connection mới |
| Lock timeout/cancel/deadlock | Runner rollback/đóng connection; không báo thành công; đối chiếu trạng thái bằng connection mới |
| Up rồi down khi lossless, rồi up lại | Khôi phục type cũ; chỉ index migration bị gỡ; PK/FK/tracking/data còn nguyên |
| Down khi có .01, tên >100 hoặc index bị đổi định nghĩa | Từ chối, giữ nguyên schema mới/index/dữ liệu; không sửa dữ liệu để ép PASS |
| Down gặp dependency mới | Dừng an toàn; không CASCADE; transaction rollback |
| >2 số lẻ hoặc tên >giới hạn | Ghi nhận hành vi engine; ứng dụng tương lai phải từ chối trước INSERT, không coi DDL là validation đầy đủ |

Các case phá hoại fixture dùng database test disposable đã duyệt; reset về baseline
giữa case. Không dùng down làm cách dọn dữ liệu thật. Sequence/identity có thể tăng
dù transaction rollback; không reseed để ép liên tục.

Runner SQL Server gửi nguyên batch, không GO, command timeout đã duyệt. PostgreSQL
psql dùng ON_ERROR_STOP hoặc driver dừng ngay ở lỗi. Không bọc script tự BEGIN/COMMIT
bằng outer transaction. Lưu báo cáo PASS/FAIL theo backend, không log tham số/row/DSN.

## Điều kiện trước production và các phê duyệt còn thiếu

Thiết kế (20,2), tên 200 và unique tương thích đã được người dùng đồng ý; không hỏi
lại những quyết định này. Các việc sau cần được duyệt trước bước thực thi tương ứng:

1. Sửa guard/runner theo các phát hiện trên và review lại diff; chưa tự sửa SQL.
2. Target test cụ thể, phương án tạo DB/instance, quyền, locale và dữ liệu giả.
3. Cho phép thực thi up/down và fault/concurrency tests **chỉ trên target test**.
4. Sau khi test PASS: backup đã thử restore, audit dependency đầy đủ, maintenance
   window, dừng toàn bộ writer, timeout/log capacity và người chạy. Chạy preflight
   lại ngay trước migration; không dùng số 27 như điều kiện cố định nếu có đơn mới.
5. Phê duyệt riêng việc áp dụng từng backend thật và hậu kiểm trước mở writer.
   Hai backend không có transaction chung; nếu một bên lỗi giữ maintenance, xác minh
   trạng thái riêng. Down sau commit là quyết định riêng và chỉ khi lossless; ưu tiên
   giữ schema mở rộng nếu đã có dữ liệu mới. Restore backup có thể mất đơn mới nên
   không tự động thực hiện.

Không cần duyệt/triển khai CheckoutRequests trong phase này. Dừng chờ duyệt.

## Tài liệu đối chiếu

- [Microsoft: filtered index và SET options](https://learn.microsoft.com/en-us/sql/t-sql/statements/create-index-transact-sql)
- [Microsoft: decimal, scale, storage và rounding](https://learn.microsoft.com/en-us/sql/t-sql/data-types/decimal-and-numeric-transact-sql)
- [PostgreSQL: numeric và rounding](https://www.postgresql.org/docs/current/datatype-numeric.html)
- [PostgreSQL: index collation](https://www.postgresql.org/docs/current/indexes-collations.html)
- [PostgreSQL: CREATE DATABASE, template và locale](https://www.postgresql.org/docs/current/sql-createdatabase.html)
