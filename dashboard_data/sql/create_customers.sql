IF OBJECT_ID(N'[dbo].[Customers]', N'U') IS NULL
BEGIN
    CREATE TABLE [dbo].[Customers] (
        [CustomerID] INT NULL,
        [Email] NVARCHAR(320) NOT NULL,
        [FirstName] NVARCHAR(255) NULL,
        [LastName] NVARCHAR(255) NULL,
        [Phone] NVARCHAR(64) NULL,
        [Company] NVARCHAR(255) NULL,
        [DateRegistered] DATETIME2(0) NOT NULL
    );
END;
