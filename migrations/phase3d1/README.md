# Phase 3D.1 — thiết kế migration, chưa được phép thực thi

> Cập nhật Phase 3D.3: sáu script SQL đã được gia cố. Hướng dẫn thực thi/guard mới
> nằm trong [phase3d3/README.md](../phase3d3/README.md) và thay thế mô tả approval
> flag/transaction/index ownership cũ bên dưới. UP/DOWN hiện là template test-only,
> chưa được chạy trên bất kỳ database nào trong phase này. Các số liệu lịch sử bên
> dưới không phải kết quả kiểm tra database mới của Phase 3D.3.

Ngày kiểm tra: **2026-11-04, Asia/Bangkok**. Chỉ chạy SELECT metadata và số liệu
tổng hợp trên SQL Server Local và Neon. Không chạy bất kỳ script up/down nào,
không sửa checkout/frontend, không ghi dữ liệu thật. Snapshot không phải backup
và phải được kiểm tra lại trước khi thực hiện sau này.

## 1. Schema và dữ liệu đã xác minh

| Cột | SQL Server `dbo` | PostgreSQL `public` | NULL |
| --- | --- | --- | --- |
| Products.ProductID | int IDENTITY, PK | integer identity, PK | Không |
| Products.ProductName | nvarchar(200) | varchar(200) | Không |
| Products.Price | decimal(18,2) | numeric(18,2) | Không |
| Orders.OrderID | int IDENTITY, PK | integer identity, PK | Không |
| Orders.OrderCode | varchar(20) | varchar(20) | Có |
| Orders.TotalMoney | decimal(18,0) | numeric(18,0) | Có |
| Orders.ShippingFee | float | double precision | Có |
| OrderDetails.DetailID | int IDENTITY, PK | integer identity, PK | Không |
| OrderDetails.OrderID | int | integer | Có |
| OrderDetails.ProductName | nvarchar(100) | varchar(100) | Có |
| OrderDetails.Quantity | int | integer | Có |
| OrderDetails.Price | decimal(18,0) | numeric(18,0) | Có |

SQL Server báo `max_length` của nvarchar theo **byte**: 200 byte tương ứng
nvarchar(100), 400 byte tương ứng nvarchar(200). Không diễn giải thành số ký tự.
SQL Server đếm sức chứa Unicode theo UTF-16; PostgreSQL varchar giới hạn theo
ký tự. Mở rộng chi tiết theo đúng giới hạn Products của từng backend.

| Kiểm tra dữ liệu | SQL Server | Neon |
| --- | ---: | ---: |
| Sản phẩm | 21 | 21 |
| Giá sản phẩm có phần lẻ | 0 | 0 |
| Giá sản phẩm <= 0 | 0 | 0 |
| Tên sản phẩm > 100 ký tự | 0 | 0 |
| Tên sản phẩm dài nhất | 30 | 30 |
| Đơn hàng | 27 | 27 |
| OrderCode NULL / rỗng | 0 / 0 | 0 / 0 |
| Nhóm mã trùng / trùng sau chuẩn hóa | 0 / 0 | 0 / 0 |
| Mã không đúng ASCII viết hoa/chữ số | 0 | 0 |
| TotalMoney NULL / âm / phần lẻ | 0 / 0 / 0 | 0 / 0 / 0 |
| OrderDetails | 0 | 0 |
| Chi tiết mồ côi, giá NULL, quantity không hợp lệ | 0 | 0 |

Không suy ra rằng giá từng có phần lẻ chưa bị mất: cột tiền cũ đã có scale 0.
Không thể phục hồi phần lẻ hoặc giỏ hàng lịch sử chỉ từ tổng tiền hiện tại.

### Constraint, default, index và identity

- Có PK trên Products.ProductID, Orders.OrderID, OrderDetails.DetailID.
- Có FK OrderDetails.OrderID → Orders.OrderID và Products.CategoryID →
  Categories.CategoryID; không cascade. FK SQL Server đang enabled/trusted.
- Không có unique index/constraint cho Orders.OrderCode ở cả hai backend.
- Local có `IX_Orders_OrderCode_Tracking` không unique, key OrderCode, INCLUDE
  Status/DriverID/Latitude/Longitude. Neon chưa có index tracking tương ứng.
- Orders.CreatedAt và CreatedDate có default GETDATE() / CURRENT_TIMESTAMP.
  Products.IsActive và IsAvailable có default 1 / true.
- Các cột tiền và tên chi tiết dự định đổi không có default; không có index
  riêng trên các cột này trong snapshot.
- Không phát hiện trigger người dùng trên Orders/OrderDetails. Không khẳng định
  đã audit toàn bộ database-level DDL trigger hoặc mọi dependency của view.
- Neon có identity sequence `public."Orders_OrderID_seq"` và
  `public."OrderDetails_DetailID_seq"`. Không reseed/reset sequence trong migration.
- SQL Server OrderCode dùng `SQL_Latin1_General_CP1_CI_AS`: phân biệt dấu,
  không phân biệt hoa/thường; so sánh bỏ qua trailing spaces. Unique PostgreSQL
  thông thường không có cùng hành vi này.

## 2. Migration cơ sở đề xuất

1. Orders.TotalMoney → decimal/numeric(20,2), giữ NULL.
2. OrderDetails.Price → decimal/numeric(20,2), giữ NULL.
3. OrderDetails.ProductName → nvarchar/varchar(200), giữ NULL/collation hiện tại.
4. Thêm `UX_Orders_OrderCode_NotNull`, chỉ áp dụng khi OrderCode khác NULL.

(20,2) giữ **18 chữ số phần nguyên** của kiểu (18,0) và thêm hai số lẻ. Dùng
(18,2) sẽ giảm sức chứa phần nguyên xuống 16 chữ số. Không đổi Products.Price,
ShippingFee, PK, FK, identity, default, index tracking hoặc tính nullable.
ShippingFee vẫn là float/double; các mức phí nguyên hiện tại biểu diễn chính xác,
nhưng nếu sau này hỗ trợ phí lẻ cần đề xuất đổi cột này riêng.

### Unique index và khác biệt collation — cần duyệt

- SQL Server: filtered unique index trên OrderCode, giữ CI_AS hiện tại.
- PostgreSQL: partial unique expression index trên `UPPER(RTRIM("OrderCode"))`.
- Với mã ASCII mới và dữ liệu hiện tại, hai cách đều từ chối khác biệt chỉ ở
  hoa/thường hoặc dấu cách cuối. Không trim đầu, không sửa giá trị được lưu.
- Không cam kết tương đương cho toàn bộ Unicode/collation. Ứng dụng phải tiếp tục
  sinh mã ASCII viết hoa. Mã hiện tại đã đạt kiểm tra canonical.
- Cho phép nhiều NULL để không thay đổi hợp đồng dữ liệu cũ; ứng dụng phải luôn
  sinh mã cho đơn mới. Không thêm NOT NULL hoặc tự sửa mã trùng/rỗng.
- Expression index bảo vệ unique; truy vấn PostgreSQL so sánh cột thô có thể
  không tận dụng nó để tracking. Tối ưu index tracking là việc riêng sau đo đạc.

### Không có backfill chi tiết

create_order hiện chỉ INSERT Orders, không có bước lấy OrderID rồi INSERT
OrderDetails. Hiện cả hai bảng chi tiết đều rỗng. Không đủ thông tin tái tạo
tên món, số lượng hoặc đơn giá của 27 đơn cũ; tuyệt đối không suy đoán/backfill.
Các giá trị tiền cũ được giữ đúng và biểu diễn với `.00`, không tính lại từ menu.

## 3. Lấy OrderID và ghi chi tiết sau khi được duyệt triển khai

SQL Server: `INSERT ... OUTPUT INSERTED.OrderID VALUES (...)`; PostgreSQL:
`INSERT ... VALUES (...) RETURNING "OrderID"`. Đọc ID bằng `fetchone()[0]`.
Snapshot không có trigger nên OUTPUT trực tiếp phù hợp hiện tại. Nếu có trigger
về sau, phải xem lại phương án OUTPUT INTO và result set trước khi áp dụng.
Không dùng MAX(OrderID), @@IDENTITY hoặc SELECT theo mã đơn để tìm lại ID.

Trong **cùng connection/transaction**:

1. Xác thực khách/OTP theo hợp đồng hiện tại.
2. Đọc và kiểm tra Products từ DB, tính Decimal, quantity và phí server.
3. INSERT Orders và lấy ID do DB sinh.
4. INSERT OrderDetails theo snapshot ProductName/Price từ DB và quantity đã
   chuẩn hóa; Price là **đơn giá**, không phải thành tiền dòng — cần duyệt nghĩa này.
5. COMMIT một lần. Bất kỳ chi tiết nào lỗi phải rollback cả đơn và chi tiết.

Chỉ trả thành công sau commit; không sử dụng ID OUTPUT/RETURNING nếu statement
hoặc transaction thất bại, dù driver đã nhận được một result row trước lỗi.

Tên quá giới hạn, số tiền vượt (20,2), hoặc hơn hai số lẻ phải bị từ chối rõ ràng;
không cắt tên/làm tròn ngầm. ID identity/sequence có thể bị bỏ trống sau rollback,
đó không phải dữ liệu mồ côi và không được reseed để bù khoảng trống.

Tài liệu: [SQL Server OUTPUT](https://learn.microsoft.com/en-us/sql/t-sql/queries/output-clause-transact-sql),
[PostgreSQL RETURNING](https://www.postgresql.org/docs/current/dml-returning.html).

## 4. Đề xuất idempotency — tách khỏi migration cơ sở

**Khuyến nghị bảng mới CheckoutRequests**, không thêm cột vào Orders trong đợt
cơ sở. Đây mới là thiết kế, chưa có DDL idempotency hoặc sửa frontend/OTP.

| Trường đề xuất | Mục đích |
| --- | --- |
| CustomerID | FK đến Customers; scope khóa theo khách đăng nhập |
| IdempotencyKey varchar(64) | Khóa ngẫu nhiên do frontend tạo, giữ nguyên khi retry |
| RequestHash char(64) | Hash payload chuẩn hóa; loại giá/tổng/phí client |
| OrderID nullable | FK đến Orders; gán trước commit |
| ResponseStatus + ResponseBody | Lưu response tạo đơn để replay đúng kết quả ban đầu |
| CreatedAt, ExpiresAt | UTC; thời gian giữ đề xuất 24 giờ, cần duyệt |

PK/unique `(CustomerID, IdempotencyKey)` là bắt buộc; có thể thêm unique OrderID
khác NULL. Chọn kiểu JSON response tương ứng SQL Server/PostgreSQL khi thiết kế
chi tiết; không lưu mật khẩu, OTP, token OAuth hoặc raw payload có PII.

Quy trình dự kiến: cùng transaction reserve key → INSERT Orders → INSERT chi tiết
→ gắn OrderID/response vào key → COMMIT. Hai request cùng khóa được điều phối bằng
unique index, không bằng dict/RAM hay cookie session. Khi unique lỗi trên PostgreSQL,
rollback transaction lỗi trước khi đọc record đã commit. Cùng key/hash trả lại kết
quả cũ; cùng key/khác hash trả 409. Request đầu rollback thì reservation cũng mất.
Timeout/deadlock phải trả lỗi có thể retry cùng key, không tự tạo khóa mới.
Hash phải dựa trên request ổn định, không dựa trên giá menu có thể thay đổi sau đó;
replay trả response đã lưu thay vì tính lại tiền. Sau retention, xóa reservation
sẽ mất bảo đảm cho retry quá hạn: cần duyệt chính sách từ chối key hết hạn hoặc
giữ liên kết/tombstone lâu hơn. Chưa có job cleanup hoặc DELETE tự động nào.

Frontend cần gửi `Idempotency-Key` và không đổi khóa khi double-click, timeout,
reload hoặc retry cùng checkout. Một hành động đặt đơn mới phải tạo khóa mới.
Unique OrderCode chỉ chống trùng mã, **không chống hai đơn khác mã cùng giỏ**.

OTP guard hiện chạy before_request và xóa trạng thái xác minh sau thành công.
Vì vậy cần duyệt sửa guard/luồng retry: chỉ cho replay đơn **đã commit** thuộc đúng
khách, cùng key và hash mà không tạo đơn mới; mọi key mới vẫn phải có OTP hợp lệ.
Không tự bỏ OTP để làm idempotency hoạt động. Idempotency không tự giải quyết replay
cookie xác minh với các key khác nhau; đảm bảo OTP dùng một lần tuyệt đối cần state
tiêu thụ OTP phía server và thiết kế riêng. Không mở rộng phần đó trong bước này.

## 5. File và cách thực hiện sau này

- `preflight_sqlserver.sql`, `preflight_postgres.sql`: chỉ SELECT metadata/counts.
- `sqlserver_up.sql`, `postgres_up.sql`: bản migration cơ sở để review.
- `sqlserver_down.sql`, `postgres_down.sql`: rollback có điều kiện, để review.

Mọi up/down đều có **approval flag mặc định false/0**, không tự áp dụng. Không có
runner tự động. Không gọi các script từ get_connection(), startup hay Docker CMD.
Up/down không tự INSERT/UPDATE/DELETE, không tự xóa/truncate dữ liệu hoặc CASCADE.
Các guard kiểm tra kiểu cột nguồn và tên index; chúng không thay thế rà metadata
đầy đủ. Chạy lại up/down trên schema đã đổi sẽ bị chặn thay vì âm thầm bỏ qua.

Quy trình chỉ sau phê duyệt:

1. Backup/snapshot do người vận hành chọn; chuẩn bị DB test riêng, dữ liệu giả.
2. Rehearse up, kiểm tra số dòng/tiền/FK/default/index/identity, ghi đơn+chi tiết,
   rollback khi lỗi, unique/cạnh tranh thật, và down trên DB test.
3. Dừng checkout và mọi writer liên quan, đợi transaction cũ kết thúc. Chạy lại
   preflight ngay trước migration; xử lý dữ liệu bất thường bằng kế hoạch riêng.
4. Dùng connection maintenance riêng, không có outer transaction; không sửa flag
   hoặc chạy script chỉ vì đang mở file trong IDE. Cần quyền ALTER/CREATE INDEX.
5. Chạy migration từng backend, kiểm tra sau commit rồi mới duyệt mở lại writer.
   Hai DB không có distributed transaction; nếu một bên thất bại, giữ maintenance
   và xác định trạng thái từng bên, không giả định cả hai đã đổi.
6. Chỉ rollout checkout dùng giá DB/Decimal/chi tiết khi đủ điều kiện triển khai.

Scripts khóa Orders rồi OrderDetails, timeout chờ khóa 5 giây. PostgreSQL có thêm
statement timeout 60 giây. SQL Server không có statement timeout tương đương trong
script; client maintenance phải đặt command timeout theo kế hoạch đã duyệt.
DDL có thể rewrite bảng, tăng dung lượng/log và chặn đọc/ghi; không hứa zero downtime.
Không dùng CREATE INDEX CONCURRENTLY ở migration này để giữ cùng transaction atomic
cho snapshot nhỏ hiện tại. Nếu dữ liệu tăng lớn, thiết kế lại kế hoạch online.
Xem [PostgreSQL ALTER TABLE](https://www.postgresql.org/docs/current/sql-altertable.html).

## 6. Rollback và ảnh hưởng dữ liệu

- Nếu up lỗi trước commit: rollback transaction trên backend đó; không tiếp tục
  thực hiện các bước khác. Client phải rollback/đóng connection khi nhận lỗi.
- Sau commit: ưu tiên rollback phiên bản ứng dụng tương thích đã duyệt nhưng giữ
  schema mở rộng. Không mở lại checkout cũ không an toàn trên môi trường công khai.
- Chỉ chạy down khi writer đã dừng, metadata đúng và tất cả tiền vẫn nguyên/fits
  decimal(18,0), mọi tên chi tiết còn fit 100 ký tự (SQL Server kiểm tra byte).
- Nếu đã có số lẻ hoặc tên dài: down **phải từ chối**, không ROUND/LEFT hoặc xóa dòng
  để ép qua. Giữ schema mới và sửa tiến; phục hồi backup cần quyết định riêng vì có
  thể mất các đơn phát sinh sau backup.
- Down gỡ index do migration tạo, không gỡ PK/FK hoặc index tracking cũ. Nếu có
  dependency mới, cần review riêng; không dùng CASCADE để ép rollback.
- Việc gỡ unique index làm mất bảo vệ mã đơn; chỉ mở writer khi có kế hoạch phù hợp.

## 7. Cần phê duyệt

1. Kiểu (20,2), tên chi tiết 200 và giữ nullable/default/identity như cũ.
2. Unique index khác NULL với so sánh ASCII case/trailing-space như mô tả.
3. Không backfill chi tiết đơn lịch sử; Price trong chi tiết là đơn giá snapshot.
4. Test DB, backup, maintenance window, timeout và người thực hiện migration.
5. Thiết kế CheckoutRequests, retention, frontend retry và tương tác OTP ở phase riêng.

**Chưa thực thi migration; chưa xác nhận SQL up/down bằng database engine.**
Chỉ kiểm tra tĩnh file, đối chiếu metadata và tài liệu. Không coi đây là kết quả
rehearsal hoặc phê duyệt chạy trên dữ liệu thật.
