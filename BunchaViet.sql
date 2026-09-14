CREATE DATABASE BunChaViet;
GO

USE BunChaViet;
GO
CREATE TABLE Categories
(
    CategoryID INT IDENTITY(1,1) PRIMARY KEY,
    CategoryName NVARCHAR(100) NOT NULL
);
GO

CREATE TABLE Products
(
    ProductID INT IDENTITY(1,1) PRIMARY KEY,
    ProductName NVARCHAR(200) NOT NULL,
    Description NVARCHAR(500),
    Price DECIMAL(18,2) NOT NULL,
    Image VARCHAR(500),
    CategoryID INT,
    IsActive BIT DEFAULT 1,

    FOREIGN KEY (CategoryID)
        REFERENCES Categories(CategoryID)
);
GO

INSERT INTO Categories
(
    CategoryName
)
VALUES
(N'Bún ch?'),
(N'Nem'),
(N'?? u?ng'),
(N'Món ?n kèm');
GO

INSERT INTO Products
(
    ProductName,
    Description,
    Price,
    Image,
    CategoryID
)
VALUES
(
    N'Bún ch? truy?n th?ng',
    N'Bún ch? Hà N?i v?i th?t n??ng, ch? viên và n??c ch?m',
    45000,
    'bun-cha-truyen-thong.jpg',
    1
),
(
    N'Bún ch? ??c bi?t',
    N'Bún ch? ??c bi?t v?i th?t n??ng và ch? viên',
    60000,
    'bun-cha-dac-biet.jpg',
    1
),
(
    N'Nem cua b?',
    N'Nem cua b? giòn th?m',
    35000,
    'nem-cua-be.jpg',
    2
),
(
    N'Trà chanh',
    N'Trà chanh t??i mát',
    15000,
    'tra-chanh.jpg',
    3
);
GO

SELECT *
FROM Products;




DELETE FROM Categories;