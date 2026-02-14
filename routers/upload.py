from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from typing import List
import pandas as pd
import io
import uuid
from database import get_db
from services.supabase_service import SupabaseService
from models import (
    BatchUploadRequest, BatchUploadResponse, BatchUploadItem, CustomerActionCreate, User,
    CustomerForValidation, CustomerValidationResponse, BatchProcessResponse, CustomerCreate,
    CustomerUpdate, SystemAuditLogCreate
)
from supabase import Client
from utils.logger import api_logger
from utils.errors import DatabaseError, create_http_exception
from utils.security import get_current_user, resolve_display_name

router = APIRouter()

@router.post("/excel", response_model=BatchUploadResponse)
async def upload_excel_file(
    file: UploadFile = File(...),
    db: Client = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Upload and process Excel file for batch operations"""
    try:
        api_logger.info("Starting Excel file upload", filename=file.filename)
        
        # Validate file type
        if not file.filename.endswith(('.xlsx', '.xls')):
            api_logger.warning("Invalid file type uploaded", filename=file.filename)
            raise HTTPException(status_code=400, detail="File must be an Excel file (.xlsx or .xls)")
        
        # Read Excel file
        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents))
        
        # Validate required columns
        required_columns = ['name', 'account_number', 'phone', 'arrears']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            api_logger.warning("Missing required columns", missing_columns=missing_columns)
            raise HTTPException(
                status_code=400, 
                detail=f"Missing required columns: {', '.join(missing_columns)}"
            )
        
        # Process data
        batch_id = str(uuid.uuid4())
        validated_data = []
        errors = []
        
        for index, row in df.iterrows():
            try:
                # Validate row data
                item = BatchUploadItem(
                    row=index + 2,  # +2 because Excel rows start at 1 and we skip header
                    name=str(row['name']).strip(),
                    account_number=str(row['account_number']).strip(),
                    phone=str(row['phone']).strip(),
                    arrears=str(row['arrears']).strip(),
                    status="validated"
                )
                validated_data.append(item)
            except Exception as e:
                api_logger.warning("Row validation failed", row=index + 2, error=str(e))
                errors.append({
                    "row": index + 2,
                    "error": str(e),
                    "data": row.to_dict()
                })
        
        # Create batch upload response
        response = BatchUploadResponse(
            batch_id=batch_id,
            total_rows=len(df),
            validated_rows=len(validated_data),
            error_rows=len(errors),
            errors=errors
        )
        
        api_logger.info("Excel file processed successfully", 
                       batch_id=batch_id, 
                       total_rows=len(df),
                       validated_rows=len(validated_data),
                       error_rows=len(errors))
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        api_logger.error("Excel file processing failed", error=e, filename=file.filename)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/process-batch", response_model=BatchProcessResponse)
async def process_batch_upload(
    batch_request: BatchUploadRequest,
    db: Client = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Process validated batch upload data, creating or updating customers and logging actions."""
    try:
        api_logger.info("Starting batch processing", 
                       batch_id=batch_request.batch_id,
                       total_items=len(batch_request.data))
        
        service = SupabaseService(db)
        
        # 1. Get unique items from the request, preferring the last entry in case of duplicates
        unique_items_by_account_no = {
            item.account_number: item 
            for item in reversed(batch_request.data) 
            if item.status == "validated"
        }.values()

        if not unique_items_by_account_no:
            return BatchProcessResponse(
                message="No valid data to process.",
                actions_created=0, customers_created=0, customers_updated=0,
                batch_id=batch_request.batch_id, success=True, errors=[]
            )

        incoming_account_numbers = [item.account_number for item in unique_items_by_account_no]
        
        # 2. Find which customers already exist in the DB in a single query
        existing_customers_map = await service.get_customers_by_account_numbers(incoming_account_numbers)
        
        customers_to_create_data = []
        customers_to_update_data = []
        
        # 3. Separate items into create and update lists based on initial DB state
        for item in unique_items_by_account_no:
            if item.account_number in existing_customers_map:
                customer_id = existing_customers_map[item.account_number].id
                customers_to_update_data.append({"id": customer_id, "data": item})
            else:
                customers_to_create_data.append(item)

        actions_to_create = []
        processing_errors = []
        
        # 4. Batch create new customers
        created_customers = []
        if customers_to_create_data:
            new_customer_models = [
                CustomerCreate(name=item.name, account_number=item.account_number, phone=item.phone, arrears=item.arrears)
                for item in customers_to_create_data
            ]
            try:
                created_customers = await service.create_batch_customers(new_customer_models)
                for customer in created_customers:
                    performed_by = resolve_display_name(current_user, db)
                    actions_to_create.append({
                        "customer_id": customer.id,
                        "action": "connect",
                        "performed_by": performed_by,
                        "source": "batch",
                        "batch_id": batch_request.batch_id
                    })
            except Exception as e:
                api_logger.error("Batch customer creation failed", error=e, batch_id=batch_request.batch_id)
                processing_errors.append({"row": "N/A", "error": f"Batch creation failed: {e}", "data": {}})

        # 5. Update existing customers one by one
        updated_customer_ids = []
        if customers_to_update_data:
            for update_item in customers_to_update_data:
                customer_id, item_data = update_item['id'], update_item['data']
                try:
                    update_payload = CustomerUpdate(status="connected", arrears=item_data.arrears)
                    await service.update_customer(customer_id, update_payload)
                    updated_customer_ids.append(customer_id)
                    performed_by = resolve_display_name(current_user, db)
                    actions_to_create.append({
                        "customer_id": customer_id,
                        "action": "connect",
                        "performed_by": performed_by,
                        "source": "batch",
                        "batch_id": batch_request.batch_id
                    })
                except Exception as e:
                    api_logger.error(f"Failed to update customer {customer_id} in batch", error=e, batch_id=batch_request.batch_id)
                    processing_errors.append({"row": item_data.row, "error": f"Update failed: {e}", "data": item_data.dict()})

        # 6. Create all actions in a single batch
        created_actions = []
        if actions_to_create:
            created_actions = await service.create_batch_actions(actions_to_create)

        # 7. Final response
        success = len(processing_errors) == 0
        customers_created = len(created_customers)
        customers_updated = len(updated_customer_ids)
        
        api_logger.info("Batch processing completed", 
                       batch_id=batch_request.batch_id,
                       success=success,
                       customers_created=customers_created,
                       customers_updated=customers_updated,
                       actions_created=len(created_actions))
        
        # Log to system audit trail
        try:
            await service.log_system_event(SystemAuditLogCreate(
                action_category="SYSTEM",
                action_type="BATCH_PROCESS",
                performed_by=resolve_display_name(current_user, db),
                details={
                    "batch_id": batch_request.batch_id,
                    "customers_created": customers_created,
                    "customers_updated": customers_updated,
                    "actions_created": len(created_actions)
                }
            ))
        except Exception as e:
            api_logger.warning("Failed to log batch process to audit trail", error=e)

        return BatchProcessResponse(
            message=f"Batch processed. Created {customers_created} new customers, updated {customers_updated} existing customers.",
            actions_created=len(created_actions),
            customers_created=customers_created,
            customers_updated=customers_updated,
            batch_id=batch_request.batch_id,
            success=success,
            errors=processing_errors
        )
        
    except Exception as e:
        api_logger.error("Batch processing failed", 
                        error=e, 
                        batch_id=batch_request.batch_id)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/batch/{batch_id}/verify", response_model=dict)
async def verify_batch_completion(
    batch_id: str,
    db: Client = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Verify batch upload completion by checking created actions and customers"""
    try:
        api_logger.info("Starting batch verification", batch_id=batch_id)
        
        service = SupabaseService(db)
        
        # Get all actions for this batch
        actions_result = db.table("customer_actions").select("*").eq("batch_id", batch_id).execute()
        actions = actions_result.data if actions_result.data else []
        
        # Get unique customer IDs from actions
        customer_ids = list(set([action["customer_id"] for action in actions]))
        
        # Get customer details
        customers = []
        for customer_id in customer_ids:
            customer = await service.get_customer(customer_id)
            if customer:
                customers.append(customer)
        
        # Verify all customers are connected
        connected_customers = [c for c in customers if c.status == "connected"]
        verification_passed = len(actions) > 0 and len(connected_customers) == len(customers)
        
        api_logger.info("Batch verification completed", 
                       batch_id=batch_id,
                       verification_passed=verification_passed,
                       total_actions=len(actions),
                       total_customers=len(customers),
                       connected_customers=len(connected_customers))
        
        return {
            "batch_id": batch_id,
            "total_actions": len(actions),
            "total_customers": len(customers),
            "connected_customers": len(connected_customers),
            "verification_passed": verification_passed,
            "actions": [
                {
                    "id": action["id"],
                    "customer_id": action["customer_id"],
                    "action": action["action"],
                    "timestamp": action["timestamp"]
                } for action in actions
            ],
            "customers": [
                {
                    "id": customer.id,
                    "name": customer.name,
                    "account_number": customer.account_number,
                    "status": customer.status
                } for customer in customers
            ]
        }
        
    except Exception as e:
        api_logger.error("Batch verification failed", error=e, batch_id=batch_id)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/validate-customers", response_model=CustomerValidationResponse)
async def validate_customers(
    customers: List[CustomerForValidation],
    db: Client = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Validate customer data before processing"""
    try:
        validated_rows = []
        errors = []
        
        for i, customer in enumerate(customers):
            try:
                # Pydantic's CustomerForValidation model already ensures fields exist.
                
                # Phone number validation (basic)
                phone = str(customer.phone).strip()
                if len(phone) < 10:
                    raise ValueError("Phone number must be at least 10 digits")
                
                # Arrears validation
                try:
                    float(customer.arrears)
                except (ValueError, TypeError):
                    raise ValueError("Arrears must be a valid number")
                
                validated_rows.append({
                    "row": i + 1,
                    "name": customer.name.strip(),
                    "account_number": customer.account_number.strip(),
                    "phone": phone,
                    "arrears": customer.arrears.strip(),
                    "status": "validated"
                })
                
            except Exception as e:
                errors.append({
                    "row": i + 1,
                    "error": str(e),
                    "data": customer.dict()
                })
        
        return CustomerValidationResponse(
            validated=validated_rows,
            errors=errors,
            total=len(customers),
            valid_count=len(validated_rows),
            error_count=len(errors),
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
