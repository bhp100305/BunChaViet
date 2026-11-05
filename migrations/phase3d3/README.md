# Phase 3D.3 — migration an toàn, chưa thực thi

Ngày 2026-11-05, Asia/Bangkok. Chỉ sửa migration/tài liệu và chạy kiểm tra offline.
Không kết nối database, không tạo DB/Neon branch, không chạy migration/DML,
không sửa ứng dụng, không commit/push/deploy. Mốc 27 Orders / 0 OrderDetails là
chứng cứ của phase trước, không phải kết quả đo mới trong 3D.3.

## File và trạng thái

- Sáu SQL trong `../phase3d1`: đã gia cố, là bản dùng cho review/rehearsal tiếp theo.
- `prepare.py`: công cụ **offline**, mặc định dry-run, không có database driver,
  không đọc `.env`, không nhận DSN/password, không có nhánh execute hoặc `--execute`.
- `test_guards.py`: mock target/approval/transaction và kiểm tra hợp đồng file SQL.
- `.gitignore`: bỏ qua artifact đã điền target, hồ sơ duyệt cục bộ và bytecode.
- README phase3d1: chỉ rõ phần hướng dẫn thực thi mới thay thế hướng dẫn cũ.

UP/DOWN chưa có engine rehearsal. File SQL gốc có placeholder và approval không
hợp lệ; mở file trong IDE không cấp quyền thực thi. Preflight chỉ SELECT và chỉ
xuất metadata/số tổng hợp. Default/filter/constraint/expression tùy ý được xuất
dưới dạng hash để tránh lộ literal nhạy cảm; không xuất code/tên/khách hàng thực.

## Bảo vệ thực thi

Chỉ hỗ trợ **test** ở phase này; production bị từ chối dù sửa environment trong
manifest hoặc bật một biến môi trường. Không có đường chạy production trong công cụ.
Đích cố định:

| Backend | Database duy nhất được phép | Điều kiện bổ sung |
| --- | --- | --- |
| SQL Server | `BunChaViet_Phase3D3_Test` | SQL Server major 16, đúng ServerName, TCP port, ORIGINAL_LOGIN, UUID marker |
| PostgreSQL | `bunchaviet_phase3d3_test` | PostgreSQL major 18, TCP loopback, đúng địa chỉ/port/session_user, UUID marker |

Các DB hiện tại không mang tên này và chưa có marker được cấp. PostgreSQL test
Neon/remote chưa được hỗ trợ: muốn mở phạm vi đó phải có thay đổi được review riêng,
không chỉ sửa manifest. SQL Server có thể dùng instance Local nhưng **database test
riêng**, không được chạy trên BunCha hiện tại. Vai trò test không nên có quyền DDL
trên DB ứng dụng. Guard catalog cần quyền nhìn metadata: SQL Server VIEW DEFINITION
của database và VIEW ANY DEFINITION ở server; PostgreSQL cần ownership/membership
phù hợp trên cả hai bảng. Không hạ guard để né thiếu quyền.

Marker được người vận hành cấp **riêng sau khi duyệt tạo/test target**:

- SQL Server: database-level extended property `BunChaViet_MigrationTestId`, giá trị
  UUID lowercase mới, đúng như hồ sơ target. Không đặt marker trên DB hiện tại.
- PostgreSQL: database comment chính xác `BunChaViet migration test:<UUID>` trên DB
  test mới. Không ghi đè comment của DB không được xác nhận an toàn.

Hai điều kiện độc lập nữa: observation chỉ đọc phải khớp target; hồ sơ approval phải
gắn SHA-256 của manifest và template SQL theo từng UP/DOWN, có reference backup đã
thử restore, preflight và thời hạn có timezone. Công cụ không suy ra duyệt từ tên DB.
Các JSON là hồ sơ quy trình, **không phải chữ ký số**; UUID marker không phải secret.
Guard chống chạy nhầm, không chống DBA cố ý sửa SQL/giả mạo hồ sơ và marker. Thay đổi
source/hash sau review bắt buộc duyệt lại. Mọi artifact vẫn phải được người chạy
kiểm tra target thực ngay trước khi gửi SQL; observation offline không thay được việc đó.

SQL Server từ chối @@TRANCOUNT != 0 hoặc IMPLICIT_TRANSACTIONS ON **trước TRY/BEGIN**,
không rollback transaction caller. Sau đó tự mở một transaction, khóa hai bảng,
chỉ commit khi tất cả thành công. PostgreSQL dùng một DO top-level: kiểm tra target
chỉ đọc, rồi COMMIT trước mọi lock/DDL để engine từ chối nếu đang trong outer
transaction. COMMIT này chỉ kết thúc transaction kiểm tra target của chính DO;
không có dữ liệu/DDL trước nó. Phần migration sau đó là một transaction mới, có
exception subblock; không COMMIT bên trong subblock. Nếu caller cố bọc BEGIN, engine
báo invalid transaction termination; caller phải rollback connection lỗi. Tuyệt đối
không bật autocommit để ép commit một connection đang có transaction.

## Schema, dependency và unique

- Giữ (20,2), tên chi tiết 200, nullable; giữ đủ 18 chữ số phần nguyên. Không đổi
  Products.Price, ShippingFee, dữ liệu cũ, PK/FK/default/identity/index khác.
- Kiểm tra loại/size/precision/scale/NULL/identity của cột cần thiết; kiểm tra PK
  một cột và FK OrderDetails.OrderID → Orders.OrderID đang valid/trusted, no action.
  Default/rule mới trên ba cột đổi type bị chặn, không tự drop/recreate default.
- Dừng nếu có dependency chưa review trên các cột đổi; SQL Server còn chặn module
  tham chiếu bảng, CHECK/computed, statistics tạo bởi user, trigger DDL/DML và tính
  năng bảng đặc biệt. PostgreSQL chặn pg_depend theo column, event/DML trigger,
  partition/inheritance/generated và RLS. Đây là policy bảo thủ, có thể từ chối một
  dependency hợp lệ; phải review riêng, không bỏ đối tượng để ép chạy.
- Catalog không bao quát dynamic SQL, báo cáo và hệ thống ngoài DB. Cần audit của
  người vận hành; mọi writer/DDL khác phải dừng trong cửa sổ migration. Không coi
  preflight hôm trước là bảo đảm tránh race.
- SQL Server unique giữ `SQL_Latin1_General_CP1_CI_AS` cho OrderCode varchar(20),
  không phân biệt case, bỏ qua trailing ASCII spaces. PostgreSQL giữ expression
  `UPPER(RTRIM("OrderCode"))`, yêu cầu default deterministic collation, libc provider,
  C.UTF-8/C.utf8 cho datcollate/datctype và không có version mismatch; kiểm tra i/I
  và case/trailing-space với literal giả. Không tự đổi collation hoặc thêm COLLATE C.
  Giả định này lấy từ VERIFICATION_3D2; test target mới phải xác minh lại.
- Không cam kết tương đương Unicode; ứng dụng phải tạo ASCII uppercase. Unique
  không thay thế CHECK: sau up vẫn có thể ghi mã không canonical/rỗng nếu không
  trùng. Up từ chối dữ liệu không canonical hiện có và duplicate theo đúng biểu
  thức/collation index. Cho phép nhiều NULL để giữ hợp đồng cũ, không tự cleanup.
- SQL Server nvarchar(200) chứa 200 UTF-16 code units, không phải luôn 200 Unicode
  code points; PostgreSQL varchar(200) đếm ký tự. Giới hạn giữ cùng Products của
  từng backend. Quantity vẫn int nullable; ứng dụng phải yêu cầu quantity >0.
- (20,2) có thể làm tròn đầu vào >2 số lẻ. Migration bảo toàn dữ liệu cũ scale 0;
  validation Decimal trước INSERT là việc của checkout phase sau. Không coi DDL
  này là cơ chế từ chối mọi dữ liệu không hợp lệ.

Index mới được gắn marker sở hữu `phase3d3:OrderCode:v1` (extended property ở SQL
Server, index comment ở PostgreSQL). DOWN không nhận index của bản phase3d1 cũ chưa
có marker, dù cùng tên. Không tự nhận quyền sở hữu hoặc sửa index có sẵn.

DOWN yêu cầu đúng schema/table/name/type/key count/sort/unique/filter/state và marker;
PostgreSQL kiểm tra thêm expression canonical, opclass, collation, không constraint,
replica identity hoặc dependent object. SQL Server chặn PK/constraint-backed,
included column thêm và FK tham chiếu index. Canonical deparse được so sánh strict:
engine test trả định dạng khác thì **dừng để review**, không nới lỏng bằng regex.
Tiền lẻ, NaN/Infinity, vượt range cũ hoặc tên quá 100 đều chặn DOWN trước DROP;
SQL Server dùng DATALENGTH để tính cả trailing spaces/surrogate. Không ROUND, LEFT,
DELETE, TRUNCATE hoặc CASCADE. Không thể phục hồi giỏ hàng 27 đơn từ bảng details rỗng.

## Hồ sơ review offline

Sau khi được duyệt target, tạo JSON cục bộ trong `local-review/`, không đưa credential
hay URL vào các file. Mẫu target SQL Server (các giá trị dưới đây chỉ minh họa):

```json
{
  "backend": "sqlserver",
  "environment": "test",
  "server": "TESTHOST\\SQLEXPRESS",
  "port": 1433,
  "database": "BunChaViet_Phase3D3_Test",
  "role": "migration_test",
  "test_id": "12345678-1234-1234-1234-123456789abc"
}
```

PostgreSQL dùng backend `postgres`, server là IP loopback thực tế, port thực tế và
database `bunchaviet_phase3d3_test`. Không dùng UUID minh họa cho môi trường thật.
Observation lặp lại đúng bảy trường target, thêm `marker` bằng
`BunChaViet migration test:<UUID>`, `transaction_state: "IDLE"`, `autocommit: true`.
Người vận hành thu thập bằng connection mới chỉ đọc trên test, không copy từ .env:

- SQL Server: SERVERPROPERTY('ServerName'), CONNECTIONPROPERTY('local_tcp_port'),
  DB_NAME(), ORIGINAL_LOGIN(), @@TRANCOUNT, @@OPTIONS và database extended property.
- PostgreSQL: inet_server_addr(), inet_server_port(), current_database(), session_user,
  shobj_description của database. Client phải kiểm tra transaction status IDLE trước
  bất kỳ query nào và kết thúc transaction kiểm tra trước khi tạo connection chạy.

Từ root repository, lệnh dưới đây chỉ dry-run, không kết nối:

```powershell
.\.venv\Scripts\python.exe migrations/phase3d3/prepare.py
.\.venv\Scripts\python.exe migrations/phase3d3/prepare.py --manifest migrations/phase3d3/local-review/target.json --observation migrations/phase3d3/local-review/observed.json --action up
```

Lệnh thứ hai in hai hash, không in target. Hồ sơ approval dùng đúng hai hash đó:

```json
{
  "approved": true,
  "environment": "test",
  "action": "up",
  "target_sha256": "<hash target đã review>",
  "template_sha256": "<hash template đã review>",
  "approval_reference": "<tham chiếu phê duyệt người dùng>",
  "backup_restore_reference": "<bằng chứng restore test thành công>",
  "preflight_reference": "<báo cáo preflight đích test>",
  "expires_at": "<ISO 8601 có timezone và còn hiệu lực>"
}
```

Chỉ sau khi duyệt, thêm `--approval <file> --output
migrations/phase3d3/prepared/sqlserver_up.sql` để tạo artifact. Công cụ không ghi đè
file có sẵn, không chấp nhận đường dẫn output ngoài prepared và **không chạy SQL**.
DOWN cần approval/hash/action riêng. Approval expiry được kiểm tra lúc tạo artifact;
người chạy phải kiểm tra lại hiệu lực ngay lúc chạy (SQL không xác thực hồ sơ approval).

## Quy trình rehearsal — chỉ sau phê duyệt riêng

1. **Tạo target:** người vận hành tạo DB test mới trên instance/cluster test đúng
   version/locale ở trên, role riêng và marker. Chưa thực hiện trong phase này.
   PostgreSQL dùng TCP loopback; SQL Server dùng TCP đúng port. Không restore đè DB
   khác. Không tạo Neon branch. Không chỉ dựa vào tên có chữ Test.
2. **Schema và fixture:** import schema-only đã review đầy đủ Categories/Products và
   các bảng FK; không chạy nguyên BunchaViet.sql vì chứa context/data thật. Seed 27
   Orders giả, 21 Products giả, ban đầu 0 details; thêm fixture details riêng gồm tiền
   biên/NULL/tên tiếng Việt để kiểm chứng cột Price dù bảng thật hiện rỗng.
3. **Backup:** backup DB test/pg_dump test trước up, thử restore sang đích test phụ
   được duyệt; ghi reference. Snapshot metadata, count và so sánh từng dòng theo PK
   trong test harness. Không xuất dữ liệu thật; không dùng SUM/count làm bằng chứng
   duy nhất bảo toàn. Chuẩn bị phương án giữ schema rộng nếu down không lossless.
4. **Preflight:** chạy đúng file SELECT tương ứng trên connection chỉ đọc. Tất cả
   matches_pre_up_schema phải true; unsafe/nonfinite/duplicate/noncanonical phải 0.
   NULL OrderCode được phép, không ép về 0; NULL tiền/tên giữ nguyên. Rà default,
   FK/PK/index/dependency/collation/permission/version, thu observation và duyệt artifact.
5. **UP:** dừng mọi writer/DDL, kiểm tra target lại ngay trước chạy, dùng connection
   mới autocommit. SQL Server gửi nguyên batch, không GO; dùng command timeout 60s
   ở client (không dùng connection timeout thay command timeout). PostgreSQL gửi một
   DO duy nhất, không BEGIN, pipeline hoặc psql --single-transaction. Đặt session
   statement_timeout=60s và lock_timeout=5s bằng các lệnh riêng đã hoàn tất trước DO;
   SET LOCAL bên trong DO là bổ sung, không thay timeout được đặt trước command.
   Client dừng ngay khi lỗi, chỉ log mã lỗi/primary message cố định; không log SQL
   context, DETAIL, raw driver exception, params hoặc DSN. Rollback/đóng connection lỗi.
6. **Xác minh:** dùng connection mới kiểm tra (20,2)/200/NULL/collation/index marker;
   ID/code/status/time và giá trị số bằng baseline, tiền cũ thêm .00. PK/FK/default,
   sequence/identity và tracking index phải còn nguyên. Kiểm tra snapshot không đổi
   khi menu test thay đổi. Không reseed identity để xóa gap.
7. **Unique/concurrency:** trùng chính xác, abc/ABC, i/I và dấu cách cuối phải bị chặn;
   nhiều NULL được phép; kiểm tra riêng rỗng/space/leading space. Hai connection cùng
   mã: A commit thì B unique-fail; A rollback thì B có thể thành công. Ghi Orders +
   nhiều details cùng transaction, ép lỗi ở detail thứ hai: không còn Orders/details
   của transaction lỗi. Không nhầm unique code với idempotency checkout.
8. **DOWN:** tạo approval riêng; chỉ chạy fixture lossless. Tiền phải nguyên, tên
   fit 100; index giữ nguyên định nghĩa/marker. Kiểm tra về schema cũ và mọi giá trị
   còn nguyên. Up lại từ baseline. Nếu đã có .01, tên dài, NaN hay index drift,
   down phải từ chối và giữ nguyên schema/index/data. Không sửa/xóa fixture để ép
   qua rồi gọi đó là rollback thành công; reset DB test riêng giữa các ca.
9. **Rollback thật trên test:** dùng bản sao artifact có fault injection được review,
   ép lỗi sau ALTER đầu/trước commit; xác minh bằng connection mới không có thay đổi
   từng phần. Giữ lock từ connection thứ hai để thử timeout; thử cancel/disconnect
   và transaction context sai. Sửa hash phải duyệt lại. Kiểm tra down cũng rollback
   index nếu ALTER sau DROP lỗi. Không có fault injection tự động trong bản dùng chạy.

Mỗi backend có transaction riêng; không có distributed commit. Nếu một backend
thất bại, dừng và xác minh trạng thái từng bên, không tiếp tục writer tự động.

## Kiểm tra đã thực hiện và giới hạn

- Static review cả sáu SQL và công cụ offline; không có DML cleanup/backfill/USE.
- Microsoft ScriptDom TSql160Parser: ba file SQL Server parse thành công.
- pglast 8.7: ba file PostgreSQL parse SQL, hai DO parse PL/pgSQL thành công.
- `python -m unittest discover -s migrations/phase3d3 -p 'test_*.py' -v`:
  10 nhóm test offline, bao gồm mock sai server/database/role/marker/transaction,
  production/current names, approval NULL/false/expired/sai action, stale SQL hash,
  injection/remote target và boundary dry-run → artifact.
- Kiểm tra Python syntax và whitespace; không cài dependency vào ứng dụng.

Parser không kiểm chứng binding catalog, format canonical pg_get_expr/filter_definition,
quyền, lock/deadlock, row rewrite, transaction rollback hoặc concurrency của engine.
Mock kiểm chứng policy của công cụ và thứ tự guard trong file, không mô phỏng SQL
Server/PostgreSQL thực thi DDL. Cần engine rehearsal để khẳng định các điều đó.

## Điều kiện còn thiếu / cần duyệt

1. Cung cấp hoặc duyệt tạo đúng hai test target, version/locale/role/marker và fixture.
2. Duyệt backup/restore test, preflight chỉ đọc và hồ sơ observation tương ứng.
3. Review diff/hashes mới, duyệt tạo artifact và **chạy bộ rehearsal chỉ trên test**.
4. Production vẫn bị chặn. Mở khả năng áp dụng lên Local/Neon hiện tại cần phase
   riêng sau bằng chứng engine PASS, backup đã thử restore, maintenance/timeout,
   người chạy và kế hoạch rollback được duyệt. Không suy ra từ duyệt thiết kế.

Không triển khai CheckoutRequests. Dừng chờ duyệt sau Phase 3D.3.

## Nguồn kỹ thuật

- [PostgreSQL DO: transaction control chỉ trong invocation độc lập](https://www.postgresql.org/docs/current/sql-do.html)
- [PostgreSQL PL/pgSQL: COMMIT và exception subtransaction](https://www.postgresql.org/docs/current/plpgsql-transactions.html)
- [Microsoft filtered index: SET options](https://learn.microsoft.com/en-us/sql/t-sql/statements/create-index-transact-sql)
- [Microsoft decimal: precision, storage và rounding](https://learn.microsoft.com/en-us/sql/t-sql/data-types/decimal-and-numeric-transact-sql)
- [PostgreSQL numeric: rounding](https://www.postgresql.org/docs/current/datatype-numeric.html)
