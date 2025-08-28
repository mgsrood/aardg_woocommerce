IF OBJECT_ID(N'[dbo].[OrderShipping]', N'U') IS NULL
BEGIN
    CREATE TABLE [dbo].[OrderShipping] (
        [ShippingItemID] INT NOT NULL,
        [OrderID] INT NOT NULL,
        [ShippingMethod] NVARCHAR(255) NOT NULL,
        [ShippingCost] DECIMAL(18,2) NOT NULL,
        [ShippingTax] DECIMAL(18,2) NOT NULL
    );
END;
