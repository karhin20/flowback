from supabase import Client
from typing import List, Optional, Dict, Any
from typing import Any
from models import (
    Customer, CustomerCreate, CustomerUpdate, CustomerAction, 
    CustomerActionCreate, User, SystemAuditLog, SystemAuditLogCreate
)
from config.settings import settings
from utils.logger import db_logger
from utils.errors import (
    CustomerNotFoundError, CustomerAlreadyExistsError, DatabaseError,
    create_http_exception, ValidationError
)
from utils.validators import validate_uuid, validate_pagination
from utils.cache import cached, CacheManager
from datetime import datetime

class SupabaseService:
    def __init__(self, client: Client):
        self.client = client

    # Customer operations
    async def create_customer(self, customer_data: CustomerCreate) -> Customer:
        """Create a new customer"""
        try:
            db_logger.info("Creating new customer", customer_data=customer_data.dict())
            
            # Check if customer already exists
            existing = await self.get_customer_by_account_number(customer_data.account_number)
            if existing:
                raise CustomerAlreadyExistsError(customer_data.account_number)
            
            result = self.client.table("customers").insert(customer_data.dict()).execute()
            if result.data:
                customer = Customer(**result.data[0])
                db_logger.info("Customer created successfully", customer_id=customer.id)
                return customer
            
            raise DatabaseError("Failed to create customer", "insert")
        except (CustomerAlreadyExistsError, DatabaseError):
            raise
        except Exception as e:
            db_logger.error("Unexpected error creating customer", error=e)
            raise DatabaseError(f"Unexpected error creating customer: {str(e)}", "insert")

    async def get_customer(self, customer_id: str) -> Optional[Customer]:
        """Get a customer by ID"""
        try:
            validate_uuid(customer_id, "customer_id")
            db_logger.info("Fetching customer", customer_id=customer_id)
            
            result = self.client.table("customers").select("*").eq("id", customer_id).execute()
            if result.data:
                customer = Customer(**result.data[0])
                db_logger.info("Customer fetched successfully", customer_id=customer_id)
                return customer
            
            db_logger.warning("Customer not found", customer_id=customer_id)
            return None
        except Exception as e:
            db_logger.error("Error getting customer", error=e, customer_id=customer_id)
            raise DatabaseError(f"Error getting customer: {str(e)}", "select")

    async def get_customer_by_account_number(self, account_number: str) -> Optional[Customer]:
        """Get a customer by account number"""
        try:
            result = self.client.table("customers").select("*").eq("account_number", account_number).execute()
            if result.data and len(result.data) > 0:
                customer_data = result.data[0]
                if customer_data:
                    return Customer(**customer_data)
            return None
        except Exception as e:
            db_logger.error(f"Error getting customer by account number: {e}", account_number=account_number)
            raise DatabaseError(f"Error getting customer by account number: {str(e)}", "select")

    async def get_customers_by_account_numbers(self, account_numbers: List[str]) -> Dict[str, Customer]:
        """Get multiple customers by their account numbers."""
        if not account_numbers:
            return {}
        try:
            result = self.client.table("customers").select("*").in_("account_number", account_numbers).execute()
            if result.data:
                return {customer_data['account_number']: Customer(**customer_data) for customer_data in result.data}
            return {}
        except Exception as e:
            db_logger.error(f"Error getting customers by account numbers: {e}")
            raise DatabaseError(f"Error getting customers by account numbers: {str(e)}", "select")

    @cached(ttl=300, key_prefix="customers")
    async def get_customers(self, filters: Dict[str, Any] = None, page: int = 1, limit: int = 50) -> List[Customer]:
        """Get customers with optional filters"""
        try:
            # Validate pagination
            try:
                page, limit = validate_pagination(page, limit)
            except ValidationError as ve:
                db_logger.error("Pagination validation failed", error=ve)
                raise DatabaseError(f"Invalid pagination parameters: {str(ve)}", "validation")
            
            db_logger.info("Fetching customers", filters=filters, page=page, limit=limit)
            
            query = self.client.table("customers").select("*")
            
            if filters:
                if filters.get("search"):
                    search_term = filters["search"]
                    query = query.or_(f"name.ilike.%{search_term}%,account_number.ilike.%{search_term}%,phone.ilike.%{search_term}%")
                
                if filters.get("status"):
                    query = query.eq("status", filters["status"])
                
                if filters.get("arrears_min"):
                    query = query.gte("arrears", filters["arrears_min"])
                
                if filters.get("arrears_max"):
                    query = query.lte("arrears", filters["arrears_max"])
            
            # Add pagination and ordering
            offset = (page - 1) * limit
            query = query.order("created_at", desc=True).range(offset, offset + limit - 1)
            
            # Debug the query
            db_logger.info("Query parameters", offset=offset, limit=limit, page=page)
            
            result = query.execute()
            
            # Debug logging
            db_logger.info("Supabase query result", 
                          result_type=type(result).__name__,
                          has_data=hasattr(result, 'data'),
                          data_type=type(result.data).__name__ if hasattr(result, 'data') else 'No data attr',
                          data_length=len(result.data) if hasattr(result, 'data') and result.data else 0)
            
            # Handle case where result.data might be None or empty
            if not result.data:
                db_logger.warning("No data returned from customers query", filters=filters)
                return []
            
            # Debug first row if available
            if result.data and len(result.data) > 0:
                db_logger.info("First row sample", first_row=result.data[0])
            
            # Convert rows to Customer objects with error handling
            customers = []
            for i, row in enumerate(result.data):
                try:
                    customer = Customer(**row)
                    customers.append(customer)
                except Exception as e:
                    db_logger.error(f"Error creating Customer object from row {i}", 
                                   error=str(e), 
                                   error_type=type(e).__name__,
                                   row_data=row)
                    # Skip this row for now - we'll fix the validation issues
                    continue
            
            db_logger.info("Customers fetched successfully", count=len(customers))
            return customers
            
        except ValidationError as ve:
            db_logger.error("Validation error in get_customers", error=ve)
            raise DatabaseError(f"Validation error: {str(ve)}", "validation")
        except Exception as e:
            db_logger.error("Error getting customers", error=e, filters=filters)
            raise DatabaseError(f"Error getting customers: {str(e)}", "select")

    async def update_customer(self, customer_id: str, customer_data: CustomerUpdate) -> Optional[Customer]:
        """Update a customer"""
        try:
            update_data = {k: v for k, v in customer_data.dict().items() if v is not None}
            db_logger.info(f"Updating customer {customer_id} with data: {update_data}")
            
            if not update_data:
                db_logger.info(f"No data to update for customer {customer_id}")
                return await self.get_customer(customer_id)
            
            result = self.client.table("customers").update(update_data).eq("id", customer_id).execute()
            if result.data:
                db_logger.info(f"Successfully updated customer {customer_id}")
                return Customer(**result.data[0])
            else:
                db_logger.warning(f"No data returned when updating customer {customer_id}")
                return None
        except Exception as e:
            db_logger.error(f"Error updating customer: {e}", customer_id=customer_id, update_data=update_data)
            raise DatabaseError(f"Error updating customer: {str(e)}", "update")

    async def delete_customer(self, customer_id: str) -> bool:
        """Delete a customer"""
        try:
            # First check if customer exists
            existing_customer = await self.get_customer(customer_id)
            if not existing_customer:
                db_logger.warning(f"Customer {customer_id} not found for deletion")
                return False
            
            # Delete the customer (actions will be cascade deleted due to foreign key constraint)
            result = self.client.table("customers").delete().eq("id", customer_id).execute()
            
            # Check if deletion was successful
            if result.data and len(result.data) > 0:
                db_logger.info(f"Successfully deleted customer {customer_id}")
                return True
            else:
                db_logger.warning(f"No data returned when deleting customer {customer_id}")
                return False
        except Exception as e:
            db_logger.error(f"Error deleting customer {customer_id}: {e}")
            raise DatabaseError(f"Error deleting customer: {str(e)}", "delete")

    # Action operations
    async def create_action(self, action_data: dict) -> CustomerAction:
        """Create a new customer action"""
        try:
            result = self.client.table("customer_actions").insert(action_data).execute()
            if result.data:
                return CustomerAction(**result.data[0])
            raise Exception("Failed to create action")
        except Exception as e:
            db_logger.error(f"Error creating action: {e}")
            raise DatabaseError(f"Error creating action: {str(e)}", "insert")

    async def get_customer_actions(self, customer_id: str = None, page: int = 1, limit: int = 50) -> List[dict]:
        """Get customer actions with optional customer filter"""
        try:
            # Use proper foreign key join syntax for Supabase
            query = self.client.table("customer_actions").select(
                """
                id,
                customer_id,
                action,
                performed_by,
                source,
                batch_id,
                timestamp,
                customers!customer_actions_customer_id_fkey(
                    name,
                    account_number
                )
                """
            )
            
            if customer_id:
                query = query.eq("customer_id", customer_id)
            
            # Add pagination
            offset = (page - 1) * limit
            query = query.range(offset, offset + limit - 1).order("timestamp", desc=True)
            
            result = query.execute()

            # Manually construct the response to include customer details
            actions = []
            if result.data:
                for row in result.data:
                    # Extract customer data from the joined customers table
                    customer_data = row.get('customers', {}) or {}
                    action_data = {
                        "id": row.get("id"),
                        "customer_id": row.get("customer_id"),
                        "action": row.get("action"),
                        "performed_by": row.get("performed_by"),
                        "source": row.get("source"),
                        "batch_id": row.get("batch_id"),
                        "timestamp": row.get("timestamp"),
                        "customer": customer_data.get("name") if customer_data else None,
                        "account_number": customer_data.get("account_number") if customer_data else None,
                    }
                    actions.append(action_data)
            return actions
        except Exception as e:
            db_logger.error(f"Error getting actions: {e}")
            raise DatabaseError(f"Error getting actions: {str(e)}", "select")

    async def get_dashboard_data(self) -> Dict[str, Any]:
        """Get dashboard statistics"""
        try:
            # Get customer counts by status
            customers_result = self.client.table("customers").select("status, arrears").execute()
            
            # Handle case where result.data might be None
            customers_data = customers_result.data or []
            
            total_customers = len(customers_data)
            connected = len([c for c in customers_data if c["status"] == "connected"])
            disconnected = len([c for c in customers_data if c["status"] == "disconnected"])
            warned = len([c for c in customers_data if c["status"] == "warned"])
            
            # Calculate total arrears
            total_arrears = sum(
                float(c["arrears"]) for c in customers_data 
                if c["arrears"] and c["arrears"] != "" and c["arrears"] is not None
            )
            
            # Get recent actions with the SAME join style used by history/audit trails
            # Use alias relation: customer:customers(name, account_number)
            recent_actions_result = self.client.table("customer_actions").select(
                "id, customer_id, action, performed_by, source, batch_id, timestamp, customer:customers(name, account_number)"
            ).order("timestamp", desc=True).limit(10).execute()
            recent_actions_data = recent_actions_result.data or []

            recent_actions = []
            if recent_actions_data:
                for row in recent_actions_data:
                    # Match history approach: relation is under key 'customer'
                    customer_rel = row.get('customer', {}) or {}
                    action_data = {
                        "id": row.get("id"),
                        "customer_id": row.get("customer_id"),
                        "action": row.get("action"),
                        "performed_by": row.get("performed_by"),
                        "source": row.get("source"),
                        "batch_id": row.get("batch_id"),
                        "timestamp": row.get("timestamp"),
                        "customer": customer_rel.get("name") if customer_rel else None,
                        "account_number": customer_rel.get("account_number") if customer_rel else None,
                    }
                    recent_actions.append(action_data)
            
            return {
                "total_customers": total_customers,
                "connected_customers": connected,
                "disconnected_customers": disconnected,
                "warned_customers": warned,
                "total_arrears": str(total_arrears),
                "recent_actions": recent_actions
            }
        except Exception as e:
            db_logger.error(f"Error getting dashboard data: {e}")
            raise DatabaseError(f"Error getting dashboard data: {str(e)}", "select")

    # Batch operations
    async def create_batch_customers(self, customers_data: List[CustomerCreate]) -> List[Customer]:
        """Create multiple customers in a batch."""
        if not customers_data:
            return []
        try:
            # Convert Pydantic models to dictionaries
            customers_dict_list = [c.dict() for c in customers_data]
            result = self.client.table("customers").insert(customers_dict_list).execute()
            if result.data:
                return [Customer(**data) for data in result.data]
            raise DatabaseError("Failed to create batch customers", "insert")
        except Exception as e:
            db_logger.error(f"Error creating batch customers: {e}")
            raise DatabaseError(f"Error creating batch customers: {str(e)}", "insert")

    async def create_batch_actions(self, actions_data: List[Any]) -> List[CustomerAction]:
        """Create multiple actions in a batch. Accepts dicts or Pydantic models."""
        try:
            # Normalize to list[dict]
            normalized: List[dict] = []
            for item in actions_data:
                if isinstance(item, dict):
                    normalized.append(item)
                elif hasattr(item, "dict") and callable(getattr(item, "dict")):
                    normalized.append(item.dict())
                else:
                    raise ValidationError(f"Unsupported action item type: {type(item).__name__}")

            result = self.client.table("customer_actions").insert(normalized).execute()
            return [CustomerAction(**row) for row in (result.data or [])]
        except (ValidationError, DatabaseError):
            raise
        except Exception as e:
            db_logger.error(f"Error creating batch actions: {e}")
            raise DatabaseError(f"Error creating batch actions: {str(e)}", "insert")

    async def get_all_message_templates(self) -> List[dict]:
        """Fetch all message templates (action, message)."""
        try:
            response = self.client.table("message_templates").select("action, message").execute()
            return response.data or []
        except Exception as e:
            db_logger.error(f"Failed to fetch message templates: {e}")
            raise DatabaseError(f"Failed to fetch message templates: {e}", "fetch_templates")

    async def update_message_template(self, action: str, message: str) -> Optional[dict]:
        """Update a message template by action."""
        try:
            response = self.client.table("message_templates") \
                .update({
                    "message": message,
                    "updated_at": datetime.utcnow().isoformat()
                }) \
                .eq("action", action) \
                .execute()
            if response.data:
                return response.data[0]
            return None
        except Exception as e:
            db_logger.error(f"Failed to update message template: {e}")
            raise DatabaseError(f"Failed to update message template: {e}", "update_template")

    # Auth operations
    async def sign_in(self, email: str, password: str) -> Optional[Any]:
        """Sign in a user using Supabase Auth."""
        try:
            session = self.client.auth.sign_in_with_password({"email": email, "password": password})
            db_logger.info(f"User sign-in successful for email: {email}")
            return session
        except Exception as e:
            db_logger.error(f"Error signing in user {email}: {e}")
            # The exception from gotrue-py is specific, but we'll catch the generic one.
            return None

    async def sign_up(self, email: str, password: str, data: dict) -> Optional[User]:
        """Sign up a new user using Supabase Auth."""
        try:
            user_response = self.client.auth.sign_up({
                "email": email,
                "password": password,
                "options": {
                    "data": data,
                    "email_redirect_to": f"{settings.frontend_url}{settings.email_redirect_path}"
                }
            })
            db_logger.info(f"User sign-up successful for email: {email}")
            
            if user_response and getattr(user_response, 'user', None):
                user = user_response.user
                # Create profile in public.users table
                try:
                    profile_data = {
                        "id": user.id,
                        "email": email,
                        "display_name": data.get("name"),
                        "role": data.get("role", "user")
                    }
                    self.client.table("users").upsert(profile_data).execute()
                    db_logger.info(f"Public profile created for user: {email}")
                except Exception as ex:
                    db_logger.error(f"Failed to create public profile for user {email}: {ex}")
                
                try:
                    return User(**user.dict())
                except Exception:
                    # Fallback to returning raw user if structure differs
                    return user
            return None
        except Exception as e:
            db_logger.error(f"Error signing up user {email}: {e}")
            return None

    # System Audit operations
    async def log_system_event(self, log_data: SystemAuditLogCreate) -> Optional[SystemAuditLog]:
        """Log a system-wide or administrative event"""
        try:
            db_logger.info("Logging system event", category=log_data.action_category, type=log_data.action_type)
            result = self.client.table("system_audit_log").insert(log_data.dict()).execute()
            if result.data:
                return SystemAuditLog(**result.data[0])
            return None
        except Exception as e:
            db_logger.error("Error logging system event", error=e)
            return None

    async def get_system_audit_logs(self, category: str = None, page: int = 1, limit: int = 50) -> List[SystemAuditLog]:
        """Fetch system audit logs with optional filtering"""
        try:
            query = self.client.table("system_audit_log").select("*")
            
            if category and category != "all":
                query = query.eq("action_category", category.upper())
            
            # Add pagination and ordering
            offset = (page - 1) * limit
            query = query.order("timestamp", desc=True).range(offset, offset + limit - 1)
            
            result = query.execute()
            return [SystemAuditLog(**row) for row in (result.data or [])]
        except Exception as e:
            db_logger.error("Error fetching system audit logs", error=e)
            raise DatabaseError(f"Error fetching system audit logs: {str(e)}", "select")
