USE [master]
GO
/****** Object:  Database [BunCha]    Script Date: 9/20/2026 9:00:39 PM ******/
CREATE DATABASE [BunCha]
 CONTAINMENT = NONE
 ON  PRIMARY 
( NAME = N'BunCha', FILENAME = N'/var/opt/mssql/data/BunCha.mdf' , SIZE = 8192KB , MAXSIZE = UNLIMITED, FILEGROWTH = 65536KB )
 LOG ON 
( NAME = N'BunCha_log', FILENAME = N'/var/opt/mssql/data/BunCha_log.ldf' , SIZE = 8192KB , MAXSIZE = 2048GB , FILEGROWTH = 65536KB )
 WITH CATALOG_COLLATION = DATABASE_DEFAULT, LEDGER = OFF
GO
ALTER DATABASE [BunCha] SET COMPATIBILITY_LEVEL = 160
GO
IF (1 = FULLTEXTSERVICEPROPERTY('IsFullTextInstalled'))
begin
EXEC [BunCha].[dbo].[sp_fulltext_database] @action = 'enable'
end
GO
ALTER DATABASE [BunCha] SET ANSI_NULL_DEFAULT OFF 
GO
ALTER DATABASE [BunCha] SET ANSI_NULLS OFF 
GO
ALTER DATABASE [BunCha] SET ANSI_PADDING OFF 
GO
ALTER DATABASE [BunCha] SET ANSI_WARNINGS OFF 
GO
ALTER DATABASE [BunCha] SET ARITHABORT OFF 
GO
ALTER DATABASE [BunCha] SET AUTO_CLOSE OFF 
GO
ALTER DATABASE [BunCha] SET AUTO_SHRINK OFF 
GO
ALTER DATABASE [BunCha] SET AUTO_UPDATE_STATISTICS ON 
GO
ALTER DATABASE [BunCha] SET CURSOR_CLOSE_ON_COMMIT OFF 
GO
ALTER DATABASE [BunCha] SET CURSOR_DEFAULT  GLOBAL 
GO
ALTER DATABASE [BunCha] SET CONCAT_NULL_YIELDS_NULL OFF 
GO
ALTER DATABASE [BunCha] SET NUMERIC_ROUNDABORT OFF 
GO
ALTER DATABASE [BunCha] SET QUOTED_IDENTIFIER OFF 
GO
ALTER DATABASE [BunCha] SET RECURSIVE_TRIGGERS OFF 
GO
ALTER DATABASE [BunCha] SET  ENABLE_BROKER 
GO
ALTER DATABASE [BunCha] SET AUTO_UPDATE_STATISTICS_ASYNC OFF 
GO
ALTER DATABASE [BunCha] SET DATE_CORRELATION_OPTIMIZATION OFF 
GO
ALTER DATABASE [BunCha] SET TRUSTWORTHY OFF 
GO
ALTER DATABASE [BunCha] SET ALLOW_SNAPSHOT_ISOLATION OFF 
GO
ALTER DATABASE [BunCha] SET PARAMETERIZATION SIMPLE 
GO
ALTER DATABASE [BunCha] SET READ_COMMITTED_SNAPSHOT OFF 
GO
ALTER DATABASE [BunCha] SET HONOR_BROKER_PRIORITY OFF 
GO
ALTER DATABASE [BunCha] SET RECOVERY FULL 
GO
ALTER DATABASE [BunCha] SET  MULTI_USER 
GO
ALTER DATABASE [BunCha] SET PAGE_VERIFY CHECKSUM  
GO
ALTER DATABASE [BunCha] SET DB_CHAINING OFF 
GO
ALTER DATABASE [BunCha] SET FILESTREAM( NON_TRANSACTED_ACCESS = OFF ) 
GO
ALTER DATABASE [BunCha] SET TARGET_RECOVERY_TIME = 60 SECONDS 
GO
ALTER DATABASE [BunCha] SET DELAYED_DURABILITY = DISABLED 
GO
ALTER DATABASE [BunCha] SET ACCELERATED_DATABASE_RECOVERY = OFF  
GO
EXEC sys.sp_db_vardecimal_storage_format N'BunCha', N'ON'
GO
ALTER DATABASE [BunCha] SET QUERY_STORE = ON
GO
ALTER DATABASE [BunCha] SET QUERY_STORE (OPERATION_MODE = READ_WRITE, CLEANUP_POLICY = (STALE_QUERY_THRESHOLD_DAYS = 30), DATA_FLUSH_INTERVAL_SECONDS = 900, INTERVAL_LENGTH_MINUTES = 60, MAX_STORAGE_SIZE_MB = 1000, QUERY_CAPTURE_MODE = AUTO, SIZE_BASED_CLEANUP_MODE = AUTO, MAX_PLANS_PER_QUERY = 200, WAIT_STATS_CAPTURE_MODE = ON)
GO
USE [BunCha]
GO
/****** Object:  Table [dbo].[Categories]    Script Date: 9/20/2026 9:00:39 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[Categories](
	[CategoryID] [int] IDENTITY(1,1) NOT NULL,
	[CategoryName] [nvarchar](100) NOT NULL,
PRIMARY KEY CLUSTERED 
(
	[CategoryID] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO
/****** Object:  Table [dbo].[DriverLocations]    Script Date: 9/20/2026 9:00:39 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[DriverLocations](
	[LocationID] [int] IDENTITY(1,1) NOT NULL,
	[DriverID] [int] NOT NULL,
	[Latitude] [float] NOT NULL,
	[Longitude] [float] NOT NULL,
	[UpdatedAt] [datetime] NULL,
PRIMARY KEY CLUSTERED 
(
	[LocationID] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO
/****** Object:  Table [dbo].[Drivers]    Script Date: 9/20/2026 9:00:39 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[Drivers](
	[DriverID] [int] IDENTITY(1,1) NOT NULL,
	[Username] [varchar](50) NULL,
	[Password] [varchar](50) NULL,
	[DriverName] [nvarchar](100) NULL,
	[Phone] [varchar](20) NULL,
	[IsActive] [bit] NULL,
PRIMARY KEY CLUSTERED 
(
	[DriverID] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO
/****** Object:  Table [dbo].[OrderDetails]    Script Date: 9/20/2026 9:00:39 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[OrderDetails](
	[DetailID] [int] IDENTITY(1,1) NOT NULL,
	[OrderID] [int] NULL,
	[ProductName] [nvarchar](100) NULL,
	[Quantity] [int] NULL,
	[Price] [decimal](18, 0) NULL,
PRIMARY KEY CLUSTERED 
(
	[DetailID] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO
/****** Object:  Table [dbo].[Orders]    Script Date: 9/20/2026 9:00:39 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[Orders](
	[OrderID] [int] IDENTITY(1,1) NOT NULL,
	[OrderCode] [varchar](20) NULL,
	[CustomerName] [nvarchar](100) NULL,
	[Phone] [varchar](20) NULL,
	[Address] [nvarchar](255) NULL,
	[Note] [nvarchar](255) NULL,
	[TotalMoney] [decimal](18, 0) NULL,
	[Status] [nvarchar](50) NULL,
	[CreatedDate] [datetime] NULL,
	[DriverID] [int] NULL,
	[CreatedAt] [datetime] NOT NULL,
	[Latitude] [float] NULL,
	[Longitude] [float] NULL,
	[ShippingFee] [float] NULL,
PRIMARY KEY CLUSTERED 
(
	[OrderID] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO
/****** Object:  Table [dbo].[Products]    Script Date: 9/20/2026 9:00:39 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[Products](
	[ProductID] [int] IDENTITY(1,1) NOT NULL,
	[ProductName] [nvarchar](200) NOT NULL,
	[Description] [nvarchar](500) NULL,
	[Price] [decimal](18, 2) NOT NULL,
	[Image] [varchar](500) NULL,
	[CategoryID] [int] NULL,
	[IsActive] [bit] NOT NULL,
PRIMARY KEY CLUSTERED 
(
	[ProductID] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO
/****** Object:  Table [dbo].[ShipperLocations]    Script Date: 9/20/2026 9:00:39 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[ShipperLocations](
	[LocationID] [int] IDENTITY(1,1) NOT NULL,
	[UserID] [int] NOT NULL,
	[Latitude] [float] NOT NULL,
	[Longitude] [float] NOT NULL,
	[UpdatedAt] [datetime] NULL,
PRIMARY KEY CLUSTERED 
(
	[LocationID] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO
/****** Object:  Table [dbo].[Users]    Script Date: 9/20/2026 9:00:39 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[Users](
	[UserID] [int] IDENTITY(1,1) NOT NULL,
	[Username] [varchar](50) NOT NULL,
	[Password] [varchar](255) NOT NULL,
	[FullName] [nvarchar](100) NOT NULL,
	[Role] [varchar](20) NOT NULL,
	[IsActive] [bit] NOT NULL,
	[Phone] [varchar](20) NULL,
PRIMARY KEY CLUSTERED 
(
	[UserID] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO
SET IDENTITY_INSERT [dbo].[Categories] ON 

INSERT [dbo].[Categories] ([CategoryID], [CategoryName]) VALUES (1, N'Món chính')
INSERT [dbo].[Categories] ([CategoryID], [CategoryName]) VALUES (2, N'Combo siêu hời')
INSERT [dbo].[Categories] ([CategoryID], [CategoryName]) VALUES (3, N'Nem & Món ăn kèm')
INSERT [dbo].[Categories] ([CategoryID], [CategoryName]) VALUES (4, N'Đồ uống')
INSERT [dbo].[Categories] ([CategoryID], [CategoryName]) VALUES (1002, N'Món chính')
INSERT [dbo].[Categories] ([CategoryID], [CategoryName]) VALUES (1003, N'Combo siêu hời')
INSERT [dbo].[Categories] ([CategoryID], [CategoryName]) VALUES (1004, N'Nem & Món ăn kèm')
INSERT [dbo].[Categories] ([CategoryID], [CategoryName]) VALUES (1005, N'Đồ uống')
SET IDENTITY_INSERT [dbo].[Categories] OFF
GO
SET IDENTITY_INSERT [dbo].[DriverLocations] ON 

INSERT [dbo].[DriverLocations] ([LocationID], [DriverID], [Latitude], [Longitude], [UpdatedAt]) VALUES (1, 1003, 21.014194157075895, 105.80732018030643, CAST(N'2026-09-17T10:12:58.657' AS DateTime))
INSERT [dbo].[DriverLocations] ([LocationID], [DriverID], [Latitude], [Longitude], [UpdatedAt]) VALUES (2, 1003, 21.014194157075895, 105.80732018030643, CAST(N'2026-09-17T10:14:18.480' AS DateTime))
INSERT [dbo].[DriverLocations] ([LocationID], [DriverID], [Latitude], [Longitude], [UpdatedAt]) VALUES (3, 1003, 21.014225204684031, 105.80732599344813, CAST(N'2026-09-17T10:39:02.490' AS DateTime))
INSERT [dbo].[DriverLocations] ([LocationID], [DriverID], [Latitude], [Longitude], [UpdatedAt]) VALUES (4, 1003, 21.014229053073922, 105.80732007296696, CAST(N'2026-09-17T10:40:52.033' AS DateTime))
INSERT [dbo].[DriverLocations] ([LocationID], [DriverID], [Latitude], [Longitude], [UpdatedAt]) VALUES (5, 1003, 21.014227530206146, 105.80732602747311, CAST(N'2026-09-17T10:42:17.807' AS DateTime))
INSERT [dbo].[DriverLocations] ([LocationID], [DriverID], [Latitude], [Longitude], [UpdatedAt]) VALUES (6, 1003, 21.014227530206146, 105.80732602747311, CAST(N'2026-09-17T10:42:23.100' AS DateTime))
INSERT [dbo].[DriverLocations] ([LocationID], [DriverID], [Latitude], [Longitude], [UpdatedAt]) VALUES (7, 1003, 21.014207689741468, 105.80728616001468, CAST(N'2026-09-17T10:54:05.277' AS DateTime))
INSERT [dbo].[DriverLocations] ([LocationID], [DriverID], [Latitude], [Longitude], [UpdatedAt]) VALUES (8, 1003, 21.014207689741468, 105.80728616001468, CAST(N'2026-09-17T10:54:05.550' AS DateTime))
INSERT [dbo].[DriverLocations] ([LocationID], [DriverID], [Latitude], [Longitude], [UpdatedAt]) VALUES (9, 1003, 21.014207689741468, 105.80728616001468, CAST(N'2026-09-17T10:54:07.550' AS DateTime))
INSERT [dbo].[DriverLocations] ([LocationID], [DriverID], [Latitude], [Longitude], [UpdatedAt]) VALUES (10, 1003, 21.014207689741468, 105.80728616001468, CAST(N'2026-09-17T10:55:25.763' AS DateTime))
INSERT [dbo].[DriverLocations] ([LocationID], [DriverID], [Latitude], [Longitude], [UpdatedAt]) VALUES (11, 1003, 21.014171747431654, 105.80728865946725, CAST(N'2026-09-17T10:55:53.377' AS DateTime))
INSERT [dbo].[DriverLocations] ([LocationID], [DriverID], [Latitude], [Longitude], [UpdatedAt]) VALUES (12, 1003, 21.014171747431654, 105.80728865946725, CAST(N'2026-09-17T10:56:17.440' AS DateTime))
INSERT [dbo].[DriverLocations] ([LocationID], [DriverID], [Latitude], [Longitude], [UpdatedAt]) VALUES (13, 1003, 21.014207689741468, 105.80728616001468, CAST(N'2026-09-17T10:57:52.160' AS DateTime))
INSERT [dbo].[DriverLocations] ([LocationID], [DriverID], [Latitude], [Longitude], [UpdatedAt]) VALUES (14, 1003, 21.014207689741468, 105.80728616001468, CAST(N'2026-09-17T10:57:55.730' AS DateTime))
INSERT [dbo].[DriverLocations] ([LocationID], [DriverID], [Latitude], [Longitude], [UpdatedAt]) VALUES (15, 1003, 21.014207689741468, 105.80728616001468, CAST(N'2026-09-17T10:57:57.950' AS DateTime))
INSERT [dbo].[DriverLocations] ([LocationID], [DriverID], [Latitude], [Longitude], [UpdatedAt]) VALUES (16, 1003, 21.014220179676169, 105.80734894255698, CAST(N'2026-09-17T10:58:39.007' AS DateTime))
INSERT [dbo].[DriverLocations] ([LocationID], [DriverID], [Latitude], [Longitude], [UpdatedAt]) VALUES (17, 1003, 21.014211390642757, 105.8072573558341, CAST(N'2026-09-17T13:24:32.907' AS DateTime))
INSERT [dbo].[DriverLocations] ([LocationID], [DriverID], [Latitude], [Longitude], [UpdatedAt]) VALUES (18, 1003, 21.014211390642757, 105.8072573558341, CAST(N'2026-09-17T13:24:33.287' AS DateTime))
INSERT [dbo].[DriverLocations] ([LocationID], [DriverID], [Latitude], [Longitude], [UpdatedAt]) VALUES (19, 1003, 21.01418463926391, 105.80726658607645, CAST(N'2026-09-17T13:24:44.490' AS DateTime))
INSERT [dbo].[DriverLocations] ([LocationID], [DriverID], [Latitude], [Longitude], [UpdatedAt]) VALUES (20, 1003, 21.014185490792737, 105.80729339736301, CAST(N'2026-09-17T13:26:36.853' AS DateTime))
INSERT [dbo].[DriverLocations] ([LocationID], [DriverID], [Latitude], [Longitude], [UpdatedAt]) VALUES (21, 1003, 21.014227530206146, 105.80732602747311, CAST(N'2026-09-17T13:52:50.263' AS DateTime))
INSERT [dbo].[DriverLocations] ([LocationID], [DriverID], [Latitude], [Longitude], [UpdatedAt]) VALUES (22, 1003, 21.014227530206146, 105.80732602747311, CAST(N'2026-09-17T13:52:52.903' AS DateTime))
INSERT [dbo].[DriverLocations] ([LocationID], [DriverID], [Latitude], [Longitude], [UpdatedAt]) VALUES (23, 1003, 21.014227530206146, 105.80732602747311, CAST(N'2026-09-17T13:52:56.780' AS DateTime))
INSERT [dbo].[DriverLocations] ([LocationID], [DriverID], [Latitude], [Longitude], [UpdatedAt]) VALUES (24, 1003, 21.01422663311379, 105.80729453611796, CAST(N'2026-09-17T13:53:18.490' AS DateTime))
INSERT [dbo].[DriverLocations] ([LocationID], [DriverID], [Latitude], [Longitude], [UpdatedAt]) VALUES (25, 1003, 21.01422663311379, 105.80729453611796, CAST(N'2026-09-17T13:53:23.813' AS DateTime))
INSERT [dbo].[DriverLocations] ([LocationID], [DriverID], [Latitude], [Longitude], [UpdatedAt]) VALUES (1002, 1003, 21.01422663311379, 105.80729453611796, CAST(N'2026-09-18T01:29:02.120' AS DateTime))
INSERT [dbo].[DriverLocations] ([LocationID], [DriverID], [Latitude], [Longitude], [UpdatedAt]) VALUES (1003, 1003, 21.01422663311379, 105.80729453611796, CAST(N'2026-09-18T01:29:53.210' AS DateTime))
INSERT [dbo].[DriverLocations] ([LocationID], [DriverID], [Latitude], [Longitude], [UpdatedAt]) VALUES (1004, 1003, 21.01422663311379, 105.80729453611796, CAST(N'2026-09-18T01:29:55.360' AS DateTime))
INSERT [dbo].[DriverLocations] ([LocationID], [DriverID], [Latitude], [Longitude], [UpdatedAt]) VALUES (1005, 1003, 21.01422663311379, 105.80729453611796, CAST(N'2026-09-18T01:29:58.423' AS DateTime))
SET IDENTITY_INSERT [dbo].[DriverLocations] OFF
GO
SET IDENTITY_INSERT [dbo].[Drivers] ON 

INSERT [dbo].[Drivers] ([DriverID], [Username], [Password], [DriverName], [Phone], [IsActive]) VALUES (1, N'shipper01', N'123456', N'Nguy?n Van Nam', N'0988888888', 1)
SET IDENTITY_INSERT [dbo].[Drivers] OFF
GO
SET IDENTITY_INSERT [dbo].[Orders] ON 

INSERT [dbo].[Orders] ([OrderID], [OrderCode], [CustomerName], [Phone], [Address], [Note], [TotalMoney], [Status], [CreatedDate], [DriverID], [CreatedAt], [Latitude], [Longitude], [ShippingFee]) VALUES (1, N'BCV501209', N'Bui Huy Phu-231230867', N'0329961823', N'594 Duong Lang', N'', CAST(255000 AS Decimal(18, 0)), N'Hoàn thành', CAST(N'2026-08-23T16:06:49.910' AS DateTime), 1002, CAST(N'2026-09-04T00:57:55.233' AS DateTime), NULL, NULL, NULL)
INSERT [dbo].[Orders] ([OrderID], [OrderCode], [CustomerName], [Phone], [Address], [Note], [TotalMoney], [Status], [CreatedDate], [DriverID], [CreatedAt], [Latitude], [Longitude], [ShippingFee]) VALUES (2, N'BCV503474', N'Bui Huy Phu-231230867', N'0329961823', N'594 Duong Lang', N'', CAST(100000 AS Decimal(18, 0)), N'Hoàn thành', CAST(N'2026-08-23T16:44:34.753' AS DateTime), 1003, CAST(N'2026-09-04T00:57:55.233' AS DateTime), NULL, NULL, NULL)
INSERT [dbo].[Orders] ([OrderID], [OrderCode], [CustomerName], [Phone], [Address], [Note], [TotalMoney], [Status], [CreatedDate], [DriverID], [CreatedAt], [Latitude], [Longitude], [ShippingFee]) VALUES (1002, N'BCV484528', N'Đào Văn Tuyến', N'0916083371', N'Đan Phượng', N'ok', CAST(230000 AS Decimal(18, 0)), N'Đang giao', CAST(N'2026-09-04T01:15:28.900' AS DateTime), 1003, CAST(N'2026-09-04T01:15:28.900' AS DateTime), NULL, NULL, NULL)
INSERT [dbo].[Orders] ([OrderID], [OrderCode], [CustomerName], [Phone], [Address], [Note], [TotalMoney], [Status], [CreatedDate], [DriverID], [CreatedAt], [Latitude], [Longitude], [ShippingFee]) VALUES (2002, N'BCV639066', N'Nguyễn Thùy Dương', N'0329961823', N'Ngõ 68 Đường Tân Triều, Triều Khúc, Phường Thanh Liệt, Hà Nội, 10135, Việt Nam', N'168, triều khúc', CAST(85000 AS Decimal(18, 0)), N'Hoàn thành', CAST(N'2026-09-17T09:57:46.160' AS DateTime), 1003, CAST(N'2026-09-17T09:57:46.160' AS DateTime), 20.9809332, 105.8029195, NULL)
INSERT [dbo].[Orders] ([OrderID], [OrderCode], [CustomerName], [Phone], [Address], [Note], [TotalMoney], [Status], [CreatedDate], [DriverID], [CreatedAt], [Latitude], [Longitude], [ShippingFee]) VALUES (2003, N'BCV642606', N'Nguyễn Thùy Dương', N'0329961823', N'Ngõ 68 Đường Tân Triều, Triều Khúc, Phường Thanh Liệt, Hà Nội, 10135, Việt Nam', N'', CAST(85000 AS Decimal(18, 0)), N'Hoàn thành', CAST(N'2026-09-17T10:56:46.407' AS DateTime), 1003, CAST(N'2026-09-17T10:56:46.407' AS DateTime), 21.014171747431654, 105.80728865946725, NULL)
INSERT [dbo].[Orders] ([OrderID], [OrderCode], [CustomerName], [Phone], [Address], [Note], [TotalMoney], [Status], [CreatedDate], [DriverID], [CreatedAt], [Latitude], [Longitude], [ShippingFee]) VALUES (2004, N'BCV651112', N'Bui Huy Phu-231230867', N'0329961823', N'Ngách 594/2 Đường Láng, Láng Hạ, Kẻ Láng, Phường Láng, Hà Nội, 11528, Việt Nam', N'', CAST(60000 AS Decimal(18, 0)), N'Đã tiếp nhận', CAST(N'2026-09-17T13:18:32.123' AS DateTime), NULL, CAST(N'2026-09-17T13:18:32.123' AS DateTime), 21.0142210787561, 105.80729094180562, 15000)
INSERT [dbo].[Orders] ([OrderID], [OrderCode], [CustomerName], [Phone], [Address], [Note], [TotalMoney], [Status], [CreatedDate], [DriverID], [CreatedAt], [Latitude], [Longitude], [ShippingFee]) VALUES (2005, N'BCV651154', N'Bui Huy Phu-231230867', N'0329961823', N'Ngách 594/2 Đường Láng, Láng Hạ, Kẻ Láng, Phường Láng, Hà Nội, 11528, Việt Nam', N'', CAST(60000 AS Decimal(18, 0)), N'Hoàn thành', CAST(N'2026-09-17T13:19:14.357' AS DateTime), 1003, CAST(N'2026-09-17T13:19:14.357' AS DateTime), 21.014211390642757, 105.8072573558341, 15000)
INSERT [dbo].[Orders] ([OrderID], [OrderCode], [CustomerName], [Phone], [Address], [Note], [TotalMoney], [Status], [CreatedDate], [DriverID], [CreatedAt], [Latitude], [Longitude], [ShippingFee]) VALUES (2006, N'BCV651950', N'Bui Huy Phu-231230867', N'0329961823', N'Ngách 594/2 Đường Láng, Láng Hạ, Kẻ Láng, Phường Láng, Hà Nội, 11528, Việt Nam', N'', CAST(170000 AS Decimal(18, 0)), N'Đang giao', CAST(N'2026-09-17T13:32:30.443' AS DateTime), 1003, CAST(N'2026-09-17T13:32:30.443' AS DateTime), 21.014211250000002, 105.807249, 15000)
INSERT [dbo].[Orders] ([OrderID], [OrderCode], [CustomerName], [Phone], [Address], [Note], [TotalMoney], [Status], [CreatedDate], [DriverID], [CreatedAt], [Latitude], [Longitude], [ShippingFee]) VALUES (3004, N'BCV697101', N'Tuyến', N'0329961823', N'Đường Láng, Láng Hạ, Kẻ Láng, Phường Láng, Hà Nội, 11528, Việt Nam', N'', CAST(60000 AS Decimal(18, 0)), N'Đã tiếp nhận', CAST(N'2026-09-18T02:05:01.710' AS DateTime), NULL, CAST(N'2026-09-18T02:05:01.710' AS DateTime), 21.014244257305091, 105.80734513140872, 15000)
SET IDENTITY_INSERT [dbo].[Orders] OFF
GO
SET IDENTITY_INSERT [dbo].[Products] ON 

INSERT [dbo].[Products] ([ProductID], [ProductName], [Description], [Price], [Image], [CategoryID], [IsActive]) VALUES (1, N'Bún chả truyền thống', N'Bún chả Hà Nội chuẩn vị với thịt nướng nạc vai và chả viên nướng than hoa', CAST(45000.00 AS Decimal(18, 2)), N'bun-cha-truyen-thong.jpg', 1, 1)
INSERT [dbo].[Products] ([ProductID], [ProductName], [Description], [Price], [Image], [CategoryID], [IsActive]) VALUES (2, N'Bún chả đặc biệt', N'Suất bún chả đầy đặn gấp đôi chả miếng và chả viên', CAST(60000.00 AS Decimal(18, 2)), N'bun-cha-dac-biet.jpg', 1, 1)
INSERT [dbo].[Products] ([ProductID], [ProductName], [Description], [Price], [Image], [CategoryID], [IsActive]) VALUES (3, N'Combo 1 Người', N'1 Bún chả truyền thống + 1 Nem cua bể + 1 Trà chanh', CAST(85000.00 AS Decimal(18, 2)), N'combo-1-nguoi.jpg', 2, 1)
INSERT [dbo].[Products] ([ProductID], [ProductName], [Description], [Price], [Image], [CategoryID], [IsActive]) VALUES (4, N'Combo 2 Người', N'2 Bún chả đặc biệt + 2 Nem cua bể + 2 Trà chanh', CAST(170000.00 AS Decimal(18, 2)), N'combo-1-nguoi.jpg', 2, 1)
INSERT [dbo].[Products] ([ProductID], [ProductName], [Description], [Price], [Image], [CategoryID], [IsActive]) VALUES (5, N'Nem cua bể (1 chiếc)', N'Nem cua bể Hải Phòng giòn rụm, nhân thịt cua tươi', CAST(35000.00 AS Decimal(18, 2)), N'nem-cua-be.jpg', 3, 1)
INSERT [dbo].[Products] ([ProductID], [ProductName], [Description], [Price], [Image], [CategoryID], [IsActive]) VALUES (6, N'Nem rán truyền thống (3 chiếc)', N'Nem rán nhân thịt, mộc nhĩ, miến thơm giòn', CAST(30000.00 AS Decimal(18, 2)), N'nem-ran.jpg', 3, 1)
INSERT [dbo].[Products] ([ProductID], [ProductName], [Description], [Price], [Image], [CategoryID], [IsActive]) VALUES (7, N'Bún thêm', N'1 Đĩa bún tươi ăn kèm', CAST(5000.00 AS Decimal(18, 2)), N'bun-them.jpg', 3, 1)
INSERT [dbo].[Products] ([ProductID], [ProductName], [Description], [Price], [Image], [CategoryID], [IsActive]) VALUES (8, N'Trà chanh Hà Nội', N'Trà chanh tươi mát lạnh giải ngấy', CAST(15000.00 AS Decimal(18, 2)), N'tra-chanh.jpg', 4, 1)
INSERT [dbo].[Products] ([ProductID], [ProductName], [Description], [Price], [Image], [CategoryID], [IsActive]) VALUES (9, N'Trà tắc xí muội', N'Trà tắc chua ngọt đậm đà', CAST(20000.00 AS Decimal(18, 2)), N'tra-tac.jpg', 4, 1)
INSERT [dbo].[Products] ([ProductID], [ProductName], [Description], [Price], [Image], [CategoryID], [IsActive]) VALUES (10, N'Nước quất mật ong', N'Nước quất thanh mát bồi bổ sức khỏe', CAST(20000.00 AS Decimal(18, 2)), N'quat-mat-ong.jpg', 4, 1)
INSERT [dbo].[Products] ([ProductID], [ProductName], [Description], [Price], [Image], [CategoryID], [IsActive]) VALUES (1002, N'Bún chả truyền thống', N'Bún chả Hà Nội chuẩn vị với thịt nướng nạc vai và chả viên nướng than hoa', CAST(45000.00 AS Decimal(18, 2)), N'bun-cha-truyen-thong.jpg', 1, 0)
INSERT [dbo].[Products] ([ProductID], [ProductName], [Description], [Price], [Image], [CategoryID], [IsActive]) VALUES (1003, N'Bún chả đặc biệt', N'Suất bún chả đầy đặn gấp đôi chả miếng và chả viên', CAST(60000.00 AS Decimal(18, 2)), N'bun-cha-dac-biet.jpg', 1, 0)
INSERT [dbo].[Products] ([ProductID], [ProductName], [Description], [Price], [Image], [CategoryID], [IsActive]) VALUES (1004, N'Combo 1 Người', N'1 Bún chả truyền thống + 1 Nem cua bể + 1 Trà chanh', CAST(85000.00 AS Decimal(18, 2)), N'combo-1-nguoi.jpg', 2, 0)
INSERT [dbo].[Products] ([ProductID], [ProductName], [Description], [Price], [Image], [CategoryID], [IsActive]) VALUES (1005, N'Combo 2 Người', N'2 Bún chả đặc biệt + 2 Nem cua bể + 2 Trà chanh', CAST(170000.00 AS Decimal(18, 2)), N'combo-2-nguoi.jpg', 2, 0)
INSERT [dbo].[Products] ([ProductID], [ProductName], [Description], [Price], [Image], [CategoryID], [IsActive]) VALUES (1006, N'Nem cua bể (1 chiếc)', N'Nem cua bể Hải Phòng giòn rụm, nhân thịt cua tươi', CAST(35000.00 AS Decimal(18, 2)), N'nem-cua-be.jpg', 3, 0)
INSERT [dbo].[Products] ([ProductID], [ProductName], [Description], [Price], [Image], [CategoryID], [IsActive]) VALUES (1007, N'Nem rán truyền thống (3 chiếc)', N'Nem rán nhân thịt, mộc nhĩ, miến thơm giòn', CAST(30000.00 AS Decimal(18, 2)), N'nem-ran.jpg', 3, 0)
INSERT [dbo].[Products] ([ProductID], [ProductName], [Description], [Price], [Image], [CategoryID], [IsActive]) VALUES (1008, N'Bún thêm', N'1 Đĩa bún tươi ăn kèm', CAST(5000.00 AS Decimal(18, 2)), N'bun-them.jpg', 3, 0)
INSERT [dbo].[Products] ([ProductID], [ProductName], [Description], [Price], [Image], [CategoryID], [IsActive]) VALUES (1009, N'Trà chanh Hà Nội', N'Trà chanh tươi mát lạnh giải ngấy', CAST(15000.00 AS Decimal(18, 2)), N'tra-chanh.jpg', 4, 0)
INSERT [dbo].[Products] ([ProductID], [ProductName], [Description], [Price], [Image], [CategoryID], [IsActive]) VALUES (1010, N'Trà tắc xí muội', N'Trà tắc chua ngọt đậm đà', CAST(20000.00 AS Decimal(18, 2)), N'tra-tac.jpg', 4, 0)
INSERT [dbo].[Products] ([ProductID], [ProductName], [Description], [Price], [Image], [CategoryID], [IsActive]) VALUES (1011, N'Nước quất mật ong', N'Nước quất thanh mát bồi bổ sức khỏe', CAST(20000.00 AS Decimal(18, 2)), N'quat-mat-ong.jpg', 4, 0)
INSERT [dbo].[Products] ([ProductID], [ProductName], [Description], [Price], [Image], [CategoryID], [IsActive]) VALUES (2002, N'Combo 3 Người', N'Siêu Ngon', CAST(170000.00 AS Decimal(18, 2)), N'combo-1-nguoi.jpg', 2, 1)
SET IDENTITY_INSERT [dbo].[Products] OFF
GO
SET IDENTITY_INSERT [dbo].[ShipperLocations] ON 

INSERT [dbo].[ShipperLocations] ([LocationID], [UserID], [Latitude], [Longitude], [UpdatedAt]) VALUES (1, 1003, 21.014225556523048, 105.80731963053596, CAST(N'2026-09-14T14:05:16.313' AS DateTime))
SET IDENTITY_INSERT [dbo].[ShipperLocations] OFF
GO
SET IDENTITY_INSERT [dbo].[Users] ON 

INSERT [dbo].[Users] ([UserID], [Username], [Password], [FullName], [Role], [IsActive], [Phone]) VALUES (1, N'admin', N'admin123', N'Quản Lý Cửa Hàng', N'Admin', 1, NULL)
INSERT [dbo].[Users] ([UserID], [Username], [Password], [FullName], [Role], [IsActive], [Phone]) VALUES (2, N'nhanvien1', N'staff123', N'Nhân Viên Thu Ngân', N'Staff', 1, NULL)
INSERT [dbo].[Users] ([UserID], [Username], [Password], [FullName], [Role], [IsActive], [Phone]) VALUES (1002, N'shipper01', N'123456', N'Nguyễn Văn Nam', N'Shipper', 1, N'0329961823')
INSERT [dbo].[Users] ([UserID], [Username], [Password], [FullName], [Role], [IsActive], [Phone]) VALUES (1003, N'shipper02', N'123456', N'Ðinh Xuân Thành', N'Shipper', 1, N'0329941934')
SET IDENTITY_INSERT [dbo].[Users] OFF
GO
SET ANSI_PADDING ON
GO
/****** Object:  Index [UQ__Drivers__536C85E4314ECD14]    Script Date: 9/20/2026 9:00:39 PM ******/
ALTER TABLE [dbo].[Drivers] ADD UNIQUE NONCLUSTERED 
(
	[Username] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, IGNORE_DUP_KEY = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
GO
SET ANSI_PADDING ON
GO
/****** Object:  Index [UQ__Users__536C85E4081C61CE]    Script Date: 9/20/2026 9:00:39 PM ******/
ALTER TABLE [dbo].[Users] ADD UNIQUE NONCLUSTERED 
(
	[Username] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, IGNORE_DUP_KEY = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
GO
ALTER TABLE [dbo].[DriverLocations] ADD  DEFAULT (getdate()) FOR [UpdatedAt]
GO
ALTER TABLE [dbo].[Drivers] ADD  DEFAULT ((1)) FOR [IsActive]
GO
ALTER TABLE [dbo].[Orders] ADD  DEFAULT (getdate()) FOR [CreatedDate]
GO
ALTER TABLE [dbo].[Orders] ADD  DEFAULT (getdate()) FOR [CreatedAt]
GO
ALTER TABLE [dbo].[Products] ADD  DEFAULT ((1)) FOR [IsActive]
GO
ALTER TABLE [dbo].[ShipperLocations] ADD  DEFAULT (getdate()) FOR [UpdatedAt]
GO
ALTER TABLE [dbo].[Users] ADD  DEFAULT ('Staff') FOR [Role]
GO
ALTER TABLE [dbo].[Users] ADD  DEFAULT ((1)) FOR [IsActive]
GO
ALTER TABLE [dbo].[OrderDetails]  WITH CHECK ADD FOREIGN KEY([OrderID])
REFERENCES [dbo].[Orders] ([OrderID])
GO
ALTER TABLE [dbo].[Products]  WITH CHECK ADD FOREIGN KEY([CategoryID])
REFERENCES [dbo].[Categories] ([CategoryID])
GO
USE [master]
GO
ALTER DATABASE [BunCha] SET  READ_WRITE 
GO
