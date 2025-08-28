IF OBJECT_ID(N'[dbo].[Products]', N'U') IS NULL
BEGIN
    CREATE TABLE [dbo].[Products] (
        [ProductID] INT NOT NULL,
        [Name] NVARCHAR(400) NOT NULL,
        [Status] NVARCHAR(50) NOT NULL,
        [ProductTypeTaxonomyID] INT NULL,
        [SKU] NVARCHAR(255) NULL,
        [RegularPrice] DECIMAL(18,2) NOT NULL,
        [SalePrice] DECIMAL(18,2) NULL,
        [TaxClass] NVARCHAR(100) NULL,
        [CreatedDate] DATETIME2(0) NOT NULL,
        [ModifiedDate] DATETIME2(0) NOT NULL,
        [ProductType] NVARCHAR(50) NULL
    );
END;
