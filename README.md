# Insight Ops Flow Backend

A FastAPI backend for the Insight Ops Flow application that manages customer data, actions, and SMS notifications with Supabase integration.

## Features

- **Customer Management**: CRUD operations for customer data
- **Action Tracking**: Log and track customer actions (connect, disconnect, warn)
- **SMS Integration**: Send SMS notifications with arrears information
- **Batch Upload**: Process Excel files for bulk operations
- **Dashboard Data**: Provide statistics and analytics
- **Supabase Integration**: Database operations through Supabase

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Environment Configuration

Copy `env.example` to `.env` and configure your environment variables:

```bash
cp env.example .env
```

Update the following variables in `.env`:

- `SUPABASE_URL`: Your Supabase project URL
- `SUPABASE_KEY`: Your Supabase anon key
- `SUPABASE_SERVICE_KEY`: Your Supabase service key (for elevated permissions)
- `ARKESEL_API_KEY`: Your Arkesel V2 API key
- `ARKESEL_SENDER_ID`: Your SMS sender ID for Arkesel
- `SECRET_KEY`: A secret key for JWT tokens
- `ALLOWED_ORIGINS`: Comma-separated list of allowed CORS origins

### 3. Database Schema

Create the following tables in your Supabase database:

#### Customers Table
```sql
CREATE TABLE customers (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    account_number VARCHAR(50) UNIQUE NOT NULL,
    phone VARCHAR(15) NOT NULL,
    status VARCHAR(20) DEFAULT 'connected' CHECK (status IN ('connected', 'disconnected', 'warned')),
    arrears VARCHAR(50) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### Customer Actions Table
```sql
CREATE TABLE customer_actions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    customer_id UUID REFERENCES customers(id) ON DELETE CASCADE,
    action VARCHAR(20) NOT NULL CHECK (action IN ('connect', 'disconnect', 'warn', 'sms_sent')),
    performed_by VARCHAR(255) NOT NULL,
    source VARCHAR(20) DEFAULT 'manual' CHECK (source IN ('manual', 'batch')),
    batch_id UUID,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### Indexes
```sql
CREATE INDEX idx_customers_status ON customers(status);
CREATE INDEX idx_customers_account_number ON customers(account_number);
CREATE INDEX idx_customer_actions_customer_id ON customer_actions(customer_id);
CREATE INDEX idx_customer_actions_timestamp ON customer_actions(timestamp DESC);
CREATE INDEX idx_customer_actions_batch_id ON customer_actions(batch_id);
```

### 4. Run the Application

```bash
# Development
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Production
uvicorn main:app --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

## API Documentation

Once the server is running, you can access:
- **Interactive API docs**: `http://localhost:8000/docs`
- **ReDoc documentation**: `http://localhost:8000/redoc`

## API Endpoints

### Customers
- `GET /api/customers/` - Get customers with filters and pagination
- `POST /api/customers/` - Create a new customer
- `GET /api/customers/{customer_id}` - Get a specific customer
- `PUT /api/customers/{customer_id}` - Update a customer
- `DELETE /api/customers/{customer_id}` - Delete a customer
- `GET /api/customers/dashboard/data` - Get dashboard statistics

### Actions
- `GET /api/actions/` - Get customer actions with pagination
- `POST /api/actions/` - Create a new action
- `GET /api/actions/customer/{customer_id}` - Get actions for a specific customer
- `POST /api/actions/batch` - Create multiple actions in a batch

### SMS
- `POST /api/sms/send-bulk` - Send a bulk SMS to multiple recipients
- `POST /api/sms/send` - Send custom SMS to a customer
- `POST /api/sms/send/warning/{customer_id}` - Send warning SMS
- `POST /api/sms/send/disconnection/{customer_id}` - Send disconnection SMS
- `POST /api/sms/send/connection/{customer_id}` - Send connection confirmation SMS
- `GET /api/sms/status/{message_id}` - Get SMS delivery status

### Upload
- `POST /api/upload/excel` - Upload and validate Excel file
- `POST /api/upload/process-batch` - Process validated batch data
- `POST /api/upload/validate-customers` - Validate customer data

## Frontend Integration

The backend is designed to work with the React frontend in the `insight-ops-flow` directory. The frontend can:

1. **Upload Excel files** using SheetJS to convert data to JSON
2. **Send data to backend** for processing and database storage
3. **Send SMS notifications** with arrears information
4. **Track all actions** through the backend API

## SMS Service Integration

The backend integrates with the Arkesel V2 SMS API for sending bulk messages. Configure your Arkesel credentials in the `.env` file.

## Error Handling

The API includes comprehensive error handling:
- Validation errors for input data
- Database connection errors
- SMS service errors
- File upload errors

All errors are returned in a consistent JSON format with appropriate HTTP status codes.

## Security

- CORS is configured for the frontend origins
- Input validation using Pydantic models
- SQL injection protection through Supabase
- Environment variable protection for sensitive data

## Development

For development, you can use the `--reload` flag with uvicorn to automatically restart the server when code changes are detected.

```bash
uvicorn main:app --reload
```
