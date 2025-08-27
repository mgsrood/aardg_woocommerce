-- =====================================================
-- Azure SQL Database Tabellen voor Webhook Monitoring
-- =====================================================

-- Tabel voor webhook status monitoring
IF OBJECT_ID(N'[dbo].[WebhookMonitoring]', N'U') IS NULL
BEGIN
    CREATE TABLE [dbo].[WebhookMonitoring] (
        [LogID] BIGINT IDENTITY(1,1) PRIMARY KEY,
        [CheckedAt] DATETIME2(0) NOT NULL DEFAULT GETDATE(),
        [WebhookID] INT NOT NULL,
        [WebhookName] NVARCHAR(255) NOT NULL,
        [WebhookURL] NVARCHAR(MAX) NULL,
        [PreviousStatus] NVARCHAR(50) NULL,
        [CurrentStatus] NVARCHAR(50) NOT NULL,
        [StatusChanged] BIT NOT NULL DEFAULT 0,
        [ActionTaken] NVARCHAR(100) NULL,  -- 'reactivated', 'already_active', 'failed_to_reactivate'
        [ErrorMessage] NVARCHAR(MAX) NULL,
        [ResponseTime] INT NULL,  -- API response time in ms
        [Environment] NVARCHAR(50) NOT NULL DEFAULT 'development'
    );
    
    -- Indexes
    CREATE INDEX [IX_WebhookMonitoring_CheckedAt] ON [dbo].[WebhookMonitoring] ([CheckedAt] DESC);
    CREATE INDEX [IX_WebhookMonitoring_WebhookName] ON [dbo].[WebhookMonitoring] ([WebhookName]);
    CREATE INDEX [IX_WebhookMonitoring_Status] ON [dbo].[WebhookMonitoring] ([CurrentStatus]);
    CREATE INDEX [IX_WebhookMonitoring_StatusChanged] ON [dbo].[WebhookMonitoring] ([StatusChanged]);
END;

-- Tabel voor system monitoring (app, VM, performance)
IF OBJECT_ID(N'[dbo].[SystemMonitoring]', N'U') IS NULL
BEGIN
    CREATE TABLE [dbo].[SystemMonitoring] (
        [LogID] BIGINT IDENTITY(1,1) PRIMARY KEY,
        [MonitoredAt] DATETIME2(0) NOT NULL DEFAULT GETDATE(),
        [MonitorType] NVARCHAR(50) NOT NULL,  -- 'webhook_app', 'vm_health', 'api_health'
        [Status] NVARCHAR(50) NOT NULL,      -- 'healthy', 'warning', 'critical', 'unknown'
        [Message] NVARCHAR(MAX) NULL,
        
        -- VM Metrics
        [CPUUsagePercent] DECIMAL(5,2) NULL,
        [MemoryUsagePercent] DECIMAL(5,2) NULL,
        [DiskUsagePercent] DECIMAL(5,2) NULL,
        [NetworkLatency] INT NULL,  -- in ms
        
        -- App Metrics  
        [AppResponseTime] INT NULL,  -- in ms
        [ActiveConnections] INT NULL,
        [ErrorRate] DECIMAL(5,2) NULL,  -- percentage
        
        -- API Health
        [APIEndpoint] NVARCHAR(255) NULL,
        [APIResponseCode] INT NULL,
        [APIResponseTime] INT NULL,  -- in ms
        
        -- Additional Info
        [Hostname] NVARCHAR(255) NULL,
        [ProcessID] INT NULL,
        [Details] NVARCHAR(MAX) NULL,  -- JSON with extra metrics
        [Environment] NVARCHAR(50) NOT NULL DEFAULT 'development'
    );
    
    -- Indexes
    CREATE INDEX [IX_SystemMonitoring_MonitoredAt] ON [dbo].[SystemMonitoring] ([MonitoredAt] DESC);
    CREATE INDEX [IX_SystemMonitoring_Type_Status] ON [dbo].[SystemMonitoring] ([MonitorType], [Status]);
    CREATE INDEX [IX_SystemMonitoring_Status] ON [dbo].[SystemMonitoring] ([Status]);
END;

-- Tabel voor monitoring events en alerts
IF OBJECT_ID(N'[dbo].[MonitoringAlerts]', N'U') IS NULL
BEGIN
    CREATE TABLE [dbo].[MonitoringAlerts] (
        [AlertID] BIGINT IDENTITY(1,1) PRIMARY KEY,
        [TriggeredAt] DATETIME2(0) NOT NULL DEFAULT GETDATE(),
        [AlertType] NVARCHAR(100) NOT NULL,  -- 'webhook_down', 'vm_critical', 'app_error', 'api_failure'
        [Severity] NVARCHAR(20) NOT NULL,    -- 'low', 'medium', 'high', 'critical'
        [Title] NVARCHAR(255) NOT NULL,
        [Description] NVARCHAR(MAX) NULL,
        [Source] NVARCHAR(100) NULL,         -- Webhook name, VM hostname, etc.
        [IsResolved] BIT NOT NULL DEFAULT 0,
        [ResolvedAt] DATETIME2(0) NULL,
        [ResolutionNotes] NVARCHAR(MAX) NULL,
        [Environment] NVARCHAR(50) NOT NULL DEFAULT 'development'
    );
    
    -- Indexes
    CREATE INDEX [IX_MonitoringAlerts_TriggeredAt] ON [dbo].[MonitoringAlerts] ([TriggeredAt] DESC);
    CREATE INDEX [IX_MonitoringAlerts_AlertType] ON [dbo].[MonitoringAlerts] ([AlertType]);
    CREATE INDEX [IX_MonitoringAlerts_Severity] ON [dbo].[MonitoringAlerts] ([Severity]);
    CREATE INDEX [IX_MonitoringAlerts_IsResolved] ON [dbo].[MonitoringAlerts] ([IsResolved]);
END;
