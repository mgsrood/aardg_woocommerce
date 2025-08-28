IF OBJECT_ID(N'[dbo].[Subscriptions]', N'U') IS NULL
BEGIN
    CREATE TABLE [dbo].[Subscriptions] (
        [SubscriptionID] INT NOT NULL,
        [Status] NVARCHAR(50) NOT NULL,
        [CustomerID] INT NULL,
        [BillingEmail] NVARCHAR(320) NULL,
        [BillingInterval] INT NOT NULL,
        [BillingPeriod] NVARCHAR(32) NOT NULL,
        [StartDate] DATETIME2(0) NOT NULL,
        [NextPaymentDate] DATETIME2(0) NULL,
        [EndDate] DATETIME2(0) NULL
    );
END;
