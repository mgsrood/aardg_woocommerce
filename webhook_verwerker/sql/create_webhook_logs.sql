IF OBJECT_ID(N'[dbo].[WebhookLogs]', N'U') IS NULL
BEGIN
    CREATE TABLE [dbo].[WebhookLogs] (
        [LogID] BIGINT IDENTITY(1,1) PRIMARY KEY,
        [ProcessedAt] DATETIME2(0) NOT NULL DEFAULT GETDATE(),
        [Route] NVARCHAR(255) NOT NULL,
        [Source] NVARCHAR(100) NOT NULL,
        [ScriptName] NVARCHAR(255) NOT NULL,
        [Status] NVARCHAR(50) NOT NULL,
        [Message] NVARCHAR(MAX) NULL,
        [ProcessingTimeMs] INT NULL,
        [RequestID] NVARCHAR(100) NULL,
        [RetryCount] INT NOT NULL DEFAULT 0,
        
        -- Webhook data
        [BillingEmail] NVARCHAR(320) NULL,
        [BillingFirstName] NVARCHAR(255) NULL,
        [BillingLastName] NVARCHAR(255) NULL,
        [OrderID] INT NULL,
        [SubscriptionID] INT NULL,
        [ProductIDs] NVARCHAR(MAX) NULL,  -- JSON array of product IDs
        [ProductNames] NVARCHAR(MAX) NULL,  -- JSON array of product names
        [OrderTotal] DECIMAL(18,2) NULL,
        [Currency] NVARCHAR(10) NULL,
        [PaymentMethod] NVARCHAR(100) NULL,
        
        -- Error details
        [ErrorType] NVARCHAR(255) NULL,
        [ErrorDetails] NVARCHAR(MAX) NULL,
        
        -- Environment
        [Environment] NVARCHAR(50) NOT NULL DEFAULT 'development'
    );
    
    -- Indexes voor performance
    CREATE INDEX [IX_WebhookLogs_ProcessedAt] ON [dbo].[WebhookLogs] ([ProcessedAt] DESC);
    CREATE INDEX [IX_WebhookLogs_Route_Status] ON [dbo].[WebhookLogs] ([Route], [Status]);
    CREATE INDEX [IX_WebhookLogs_BillingEmail] ON [dbo].[WebhookLogs] ([BillingEmail]);
    CREATE INDEX [IX_WebhookLogs_OrderID] ON [dbo].[WebhookLogs] ([OrderID]);
    CREATE INDEX [IX_WebhookLogs_SubscriptionID] ON [dbo].[WebhookLogs] ([SubscriptionID]);
END;
