IF OBJECT_ID(N'[dbo].[OrderItems]', N'U') IS NULL
BEGIN
    CREATE TABLE [dbo].[OrderItems] (
        [OrderItemID] INT NOT NULL,
        [OrderID] INT NOT NULL,
        [OrderItemType] NVARCHAR(100) NOT NULL,
        [OrderItemName] NVARCHAR(400) NOT NULL,
        [ProductID] INT NULL,
        [VariationID] INT NULL,
        [SKU] NVARCHAR(255) NULL,
        [Quantity] INT NOT NULL,
        [LineSubtotal] DECIMAL(18,2) NOT NULL,
        [LineSubtotalTax] DECIMAL(18,2) NOT NULL,
        [LineTotal] DECIMAL(18,2) NOT NULL,
        [LineTotalTax] DECIMAL(18,2) NOT NULL,
        [TaxClass] NVARCHAR(100) NULL
    );
END;
