# Bún Chả Việt - Live Shipper Map

## 1. Chạy SQL tối ưu

Mở SQL Server Management Studio và chạy `MAP_UPGRADE.sql` một lần trên database hiện tại.

---

## 2. Quy ước tọa độ

- `Orders.Latitude` / `Orders.Longitude`: tọa độ khách hàng, là điểm giao hàng.
- `DriverLocations.Latitude` / `DriverLocations.Longitude`: tọa độ GPS riêng của từng shipper theo `DriverID`.
- Không dùng `Orders.Latitude` / `Orders.Longitude` làm vị trí xe máy.
- Không dùng `ShipperLocations` cho luồng Live Map mới.

---

## 3. Luồng test

1. Admin giao đơn cho shipper.
2. Shipper đăng nhập bằng điện thoại.
3. Shipper bật ca và cho phép trình duyệt truy cập Location.
4. Shipper bấm `Đã lấy món`.
5. Shipper bấm `Bắt đầu giao`.
6. Trang shipper hiển thị map từ GPS hiện tại tới vị trí khách.
7. Khách mở `/track-order` và nhập số điện thoại của đơn.
8. Trang khách gọi API tracking khoảng 3 giây/lần.
9. Khi điện thoại shipper di chuyển, icon xe máy của khách sẽ chạy theo vị trí mới.

---

## 4. Điều kiện GPS trên điện thoại

`navigator.geolocation` cần secure context.

Khi test trên điện thoại thật nên chạy website bằng HTTPS.

`localhost` là ngoại lệ.

Địa chỉ dạng:

```text
http://192.168.x.x:5000