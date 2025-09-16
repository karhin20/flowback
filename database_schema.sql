-- Insight Ops Flow Database Schema
-- Run this script in your Supabase SQL editor to create the required tables

-- Create customers table
CREATE TABLE IF NOT EXISTS customers (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    account_number VARCHAR(50) UNIQUE NOT NULL,
    phone VARCHAR(15) NOT NULL,
    status VARCHAR(20) DEFAULT 'connected' CHECK (status IN ('connected', 'disconnected', 'warned')),
    arrears VARCHAR(50) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create customer_actions table
CREATE TABLE IF NOT EXISTS customer_actions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    customer_id UUID REFERENCES customers(id) ON DELETE CASCADE,
    action VARCHAR(20) NOT NULL CHECK (action IN ('connect', 'disconnect', 'warn', 'sms_sent')),
    performed_by VARCHAR(255) NOT NULL,
    source VARCHAR(20) DEFAULT 'manual' CHECK (source IN ('manual', 'batch')),
    batch_id UUID,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_customers_status ON customers(status);
CREATE INDEX IF NOT EXISTS idx_customers_account_number ON customers(account_number);
CREATE INDEX IF NOT EXISTS idx_customers_phone ON customers(phone);
CREATE INDEX IF NOT EXISTS idx_customers_created_at ON customers(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_customers_arrears ON customers(arrears);
CREATE INDEX IF NOT EXISTS idx_customers_name_search ON customers USING gin(to_tsvector('english', name));

CREATE INDEX IF NOT EXISTS idx_customer_actions_customer_id ON customer_actions(customer_id);
CREATE INDEX IF NOT EXISTS idx_customer_actions_timestamp ON customer_actions(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_customer_actions_batch_id ON customer_actions(batch_id);
CREATE INDEX IF NOT EXISTS idx_customer_actions_action ON customer_actions(action);
CREATE INDEX IF NOT EXISTS idx_customer_actions_source ON customer_actions(source);
CREATE INDEX IF NOT EXISTS idx_customer_actions_performed_by ON customer_actions(performed_by);

-- Composite indexes for common queries
CREATE INDEX IF NOT EXISTS idx_customers_status_created ON customers(status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_actions_customer_timestamp ON customer_actions(customer_id, timestamp DESC);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger for customers table
CREATE TRIGGER update_customers_updated_at 
    BEFORE UPDATE ON customers 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Create or update message_templates table
CREATE TABLE IF NOT EXISTS message_templates (
    action VARCHAR(20) PRIMARY KEY,
    message TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Insert/Update default templates
INSERT INTO message_templates (action, message) VALUES
('connect', 'Your water service has been restored. Thank you for your payment.'),
('disconnect', 'Dear Customer, your water service has been disconnected due to outstanding arrears of {amount}. Please settle it to restore service.'),
('warn', 'Dear Customer, you have outstanding arrears of {amount}. Please settle it to avoid service disconnection. Thank you')
ON CONFLICT (action) DO UPDATE 
SET message = EXCLUDED.message, updated_at = NOW();

-- Insert sample data (optional)
INSERT INTO customers (name, account_number, phone, status, arrears) VALUES
('John Doe', 'ACC001', '1234567890', 'connected', '0.00'),
('Jane Smith', 'ACC002', '0987654321', 'warned', '150.50'),
('Bob Johnson', 'ACC003', '1122334455', 'disconnected', '300.75')
ON CONFLICT (account_number) DO NOTHING;

-- Insert sample actions (optional)
INSERT INTO customer_actions (customer_id, action, performed_by, source) 
SELECT 
    c.id,
    'warn',
    'system',
    'manual'
FROM customers c 
WHERE c.status = 'warned'
ON CONFLICT DO NOTHING;
