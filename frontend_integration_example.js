// Frontend Integration Example for Insight Ops Flow
// This shows how to use SheetJS to process Excel files and send data to the backend

// Example: Process Excel file and upload to backend
async function processExcelFile(file) {
    try {
        // Read Excel file using SheetJS
        const workbook = XLSX.read(await file.arrayBuffer(), { type: 'array' });
        const sheetName = workbook.SheetNames[0];
        const worksheet = workbook.Sheets[sheetName];
        
        // Convert to JSON
        const jsonData = XLSX.utils.sheet_to_json(worksheet);
        
        // Validate and transform data
        const validatedData = jsonData.map((row, index) => ({
            row: index + 2, // +2 because Excel rows start at 1 and we skip header
            name: row.name || '',
            account_number: row.account_number || '',
            phone: row.phone || '',
            arrears: row.arrears || '0',
            reason: row.reason || '',
            status: 'pending'
        }));
        
        // Send to backend for validation
        const response = await fetch('http://localhost:8000/api/upload/validate-customers', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(validatedData)
        });
        
        const result = await response.json();
        
        if (response.ok) {
            console.log('Validation successful:', result);
            return result;
        } else {
            throw new Error(result.detail || 'Validation failed');
        }
        
    } catch (error) {
        console.error('Error processing Excel file:', error);
        throw error;
    }
}

// Example: Upload Excel file directly to backend
async function uploadExcelFile(file) {
    try {
        const formData = new FormData();
        formData.append('file', file);
        
        const response = await fetch('http://localhost:8000/api/upload/excel', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (response.ok) {
            console.log('Upload successful:', result);
            return result;
        } else {
            throw new Error(result.detail || 'Upload failed');
        }
        
    } catch (error) {
        console.error('Error uploading file:', error);
        throw error;
    }
}

// Example: Process batch data
async function processBatchData(batchId, validatedData) {
    try {
        const response = await fetch('http://localhost:8000/api/upload/process-batch', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                batch_id: batchId,
                data: validatedData
            })
        });
        
        const result = await response.json();
        
        if (response.ok) {
            console.log('Batch processing successful:', result);
            return result;
        } else {
            throw new Error(result.detail || 'Batch processing failed');
        }
        
    } catch (error) {
        console.error('Error processing batch:', error);
        throw error;
    }
}

// Example: Send SMS to customer
async function sendSMS(customerId, message, includeArrears = true) {
    try {
        const response = await fetch('http://localhost:8000/api/sms/send', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                customer_id: customerId,
                message: message,
                include_arrears: includeArrears
            })
        });
        
        const result = await response.json();
        
        if (response.ok) {
            console.log('SMS sent successfully:', result);
            return result;
        } else {
            throw new Error(result.detail || 'SMS sending failed');
        }
        
    } catch (error) {
        console.error('Error sending SMS:', error);
        throw error;
    }
}

// Example: Get customers with filters
async function getCustomers(filters = {}) {
    try {
        const queryParams = new URLSearchParams();
        
        if (filters.search) queryParams.append('search', filters.search);
        if (filters.status) queryParams.append('status', filters.status);
        if (filters.arrears_min) queryParams.append('arrears_min', filters.arrears_min);
        if (filters.arrears_max) queryParams.append('arrears_max', filters.arrears_max);
        if (filters.page) queryParams.append('page', filters.page);
        if (filters.limit) queryParams.append('limit', filters.limit);
        
        const response = await fetch(`http://localhost:8000/api/customers/?${queryParams}`);
        const result = await response.json();
        
        if (response.ok) {
            return result;
        } else {
            throw new Error(result.detail || 'Failed to fetch customers');
        }
        
    } catch (error) {
        console.error('Error fetching customers:', error);
        throw error;
    }
}

// Example: Get dashboard data
async function getDashboardData() {
    try {
        const response = await fetch('http://localhost:8000/api/customers/dashboard/data');
        const result = await response.json();
        
        if (response.ok) {
            return result;
        } else {
            throw new Error(result.detail || 'Failed to fetch dashboard data');
        }
        
    } catch (error) {
        console.error('Error fetching dashboard data:', error);
        throw error;
    }
}

// Example: Create customer action
async function createAction(customerId, action, reason, performedBy) {
    try {
        const response = await fetch('http://localhost:8000/api/actions/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                customer_id: customerId,
                action: action,
                reason: reason,
                performed_by: performedBy,
                source: 'manual'
            })
        });
        
        const result = await response.json();
        
        if (response.ok) {
            console.log('Action created successfully:', result);
            return result;
        } else {
            throw new Error(result.detail || 'Action creation failed');
        }
        
    } catch (error) {
        console.error('Error creating action:', error);
        throw error;
    }
}

// Export functions for use in React components
export {
    processExcelFile,
    uploadExcelFile,
    processBatchData,
    sendSMS,
    getCustomers,
    getDashboardData,
    createAction
};
