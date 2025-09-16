import pytest
from unittest.mock import Mock, AsyncMock
from services.supabase_service import SupabaseService
from models import CustomerCreate, CustomerUpdate
from utils.errors import CustomerNotFoundError, CustomerAlreadyExistsError

class TestSupabaseService:
    @pytest.fixture
    def mock_client(self):
        return Mock()
    
    @pytest.fixture
    def service(self, mock_client):
        return SupabaseService(mock_client)
    
    @pytest.fixture
    def sample_customer_data(self):
        return CustomerCreate(
            name="John Doe",
            account_number="GWL-123456",
            phone="0241234567",
            status="connected",
            arrears="0.00"
        )
    
    @pytest.mark.asyncio
    async def test_create_customer_success(self, service, mock_client, sample_customer_data):
        # Mock successful response
        mock_client.table.return_value.insert.return_value.execute.return_value.data = [{
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "name": "John Doe",
            "account_number": "GWL-123456",
            "phone": "0241234567",
            "status": "connected",
            "arrears": "0.00",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z"
        }]
        
        # Mock get_customer_by_account_number to return None (no existing customer)
        service.get_customer_by_account_number = AsyncMock(return_value=None)
        
        result = await service.create_customer(sample_customer_data)
        
        assert result.name == "John Doe"
        assert result.account_number == "GWL-123456"
        mock_client.table.assert_called_with("customers")
    
    @pytest.mark.asyncio
    async def test_create_customer_already_exists(self, service, sample_customer_data):
        # Mock existing customer
        existing_customer = Mock()
        service.get_customer_by_account_number = AsyncMock(return_value=existing_customer)
        
        with pytest.raises(CustomerAlreadyExistsError):
            await service.create_customer(sample_customer_data)
    
    @pytest.mark.asyncio
    async def test_get_customer_success(self, service, mock_client):
        customer_id = "550e8400-e29b-41d4-a716-446655440000"
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [{
            "id": customer_id,
            "name": "John Doe",
            "account_number": "GWL-123456",
            "phone": "0241234567",
            "status": "connected",
            "arrears": "0.00",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z"
        }]
        
        result = await service.get_customer(customer_id)
        
        assert result is not None
        assert result.id == customer_id
        assert result.name == "John Doe"
    
    @pytest.mark.asyncio
    async def test_get_customer_not_found(self, service, mock_client):
        customer_id = "550e8400-e29b-41d4-a716-446655440000"
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
        
        result = await service.get_customer(customer_id)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_customers_with_filters(self, service, mock_client):
        mock_client.table.return_value.select.return_value.or_.return_value.eq.return_value.range.return_value.execute.return_value.data = [
            {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "John Doe",
                "account_number": "GWL-123456",
                "phone": "0241234567",
                "status": "connected",
                "arrears": "0.00",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z"
            }
        ]
        
        filters = {"search": "John", "status": "connected"}
        result = await service.get_customers(filters=filters, page=1, limit=10)
        
        assert len(result) == 1
        assert result[0].name == "John Doe"
    
    @pytest.mark.asyncio
    async def test_update_customer_success(self, service, mock_client):
        customer_id = "550e8400-e29b-41d4-a716-446655440000"
        update_data = CustomerUpdate(name="Jane Doe")
        
        mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [{
            "id": customer_id,
            "name": "Jane Doe",
            "account_number": "GWL-123456",
            "phone": "0241234567",
            "status": "connected",
            "arrears": "0.00",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z"
        }]
        
        result = await service.update_customer(customer_id, update_data)
        
        assert result is not None
        assert result.name == "Jane Doe"
    
    @pytest.mark.asyncio
    async def test_delete_customer_success(self, service, mock_client):
        customer_id = "550e8400-e29b-41d4-a716-446655440000"
        
        # Mock existing customer
        existing_customer = Mock()
        service.get_customer = AsyncMock(return_value=existing_customer)
        
        # Mock successful deletion
        mock_client.table.return_value.delete.return_value.eq.return_value.execute.return_value.data = [{
            "id": customer_id
        }]
        
        result = await service.delete_customer(customer_id)
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_delete_customer_not_found(self, service):
        customer_id = "550e8400-e29b-41d4-a716-446655440000"
        
        # Mock customer not found
        service.get_customer = AsyncMock(return_value=None)
        
        result = await service.delete_customer(customer_id)
        
        assert result is False
