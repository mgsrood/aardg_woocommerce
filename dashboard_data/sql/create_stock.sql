CREATE TABLE [dbo].[Stock] (
    [StockID] INT IDENTITY(1,1) PRIMARY KEY,
    [ProductSKU] NVARCHAR(255) NOT NULL,
    [ProductName] NVARCHAR(400) NULL,
    [StandardisedProduct] NVARCHAR(100) NULL,
    [ProductID] INT NULL,
    [StockDate] DATE NOT NULL,
    
    -- Monta Stock Velden (gebaseerd op echte API response)
    [StockAll] INT NOT NULL DEFAULT 0,
    [StockAvailable] INT NOT NULL DEFAULT 0,
    [StockReserved] INT NOT NULL DEFAULT 0,
    [StockInTransit] INT NOT NULL DEFAULT 0,
    [StockBlocked] INT NOT NULL DEFAULT 0,
    [StockQuarantaine] INT NOT NULL DEFAULT 0,
    [StockPicking] INT NOT NULL DEFAULT 0,
    [StockOpen] INT NOT NULL DEFAULT 0,
    [StockInWarehouse] INT NOT NULL DEFAULT 0,
    [StockInboundForecasted] INT NOT NULL DEFAULT 0,
    [StockInboundHistory] INT NOT NULL DEFAULT 0,
    [StockWholeSaler] INT NOT NULL DEFAULT 0,
    
    -- Timestamps
    [LastUpdated] DATETIME2(0) NOT NULL DEFAULT GETDATE(),
    [CreatedAt] DATETIME2(0) NOT NULL DEFAULT GETDATE())

-- Indexen voor efficiënte queries
CREATE INDEX IX_Stock_SKU_Date ON [dbo].[Stock] (ProductSKU, StockDate);
CREATE INDEX IX_Stock_Date ON [dbo].[Stock] (StockDate);
CREATE INDEX IX_Stock_ProductID ON [dbo].[Stock] (ProductID) WHERE ProductID IS NOT NULL;

