import pytest
from utils.validators import (
    PhoneValidator, AccountNumberValidator, AmountValidator,
    NameValidator, StatusValidator, ActionValidator,
    validate_pagination, validate_uuid
)
from utils.errors import ValidationError

class TestPhoneValidator:
    def test_valid_phone_numbers(self):
        valid_phones = [
            "0241234567",
            "0 24 123 4567",
            "+233241234567",
            "233241234567",
            "241234567",
            241234567
        ]
        
        for phone in valid_phones:
            result = PhoneValidator.validate(phone)
            assert result == "0241234567"
    
    def test_invalid_phone_numbers(self):
        invalid_phones = [
            "123456789",  # Too short
            "01234567890",  # Too long
            "abc1234567",  # Contains letters
            "",  # Empty
            None  # None
        ]
        
        for phone in invalid_phones:
            with pytest.raises(ValidationError):
                PhoneValidator.validate(phone)

class TestAccountNumberValidator:
    def test_valid_account_numbers(self):
        valid_accounts = [
            "GWL-123456",
            "ACC-12345678",
            "ABC-1234"
        ]
        
        for account in valid_accounts:
            result = AccountNumberValidator.validate(account)
            assert result == account.upper()
    
    def test_invalid_account_numbers(self):
        invalid_accounts = [
            "123456",  # No prefix
            "GWL123456",  # No dash
            "GWL-abc123",  # Contains letters in number
            "",  # Empty
            None  # None
        ]
        
        for account in invalid_accounts:
            with pytest.raises(ValidationError):
                AccountNumberValidator.validate(account)

class TestAmountValidator:
    def test_valid_amounts(self):
        valid_amounts = [
            "123.45",
            "123",
            "0.00",
            "1,234.56",
            "GHS 123.45"
        ]
        
        expected_results = [
            "123.45",
            "123.00",
            "0.00",
            "1234.56",
            "123.45"
        ]
        
        for amount, expected in zip(valid_amounts, expected_results):
            result = AmountValidator.validate(amount)
            assert result == expected
    
    def test_invalid_amounts(self):
        invalid_amounts = [
            "abc",
            "12.345",  # Too many decimal places
            "",  # Empty
            None  # None
        ]
        
        for amount in invalid_amounts:
            with pytest.raises(ValidationError):
                AmountValidator.validate(amount)

class TestNameValidator:
    def test_valid_names(self):
        valid_names = [
            "John Doe",
            "Mary-Jane Smith",
            "O'Connor",
            "Jean-Pierre"
        ]
        
        for name in valid_names:
            result = NameValidator.validate(name)
            assert result == name.title()
    
    def test_invalid_names(self):
        invalid_names = [
            "A",  # Too short
            "John123",  # Contains numbers
            "John@Doe",  # Contains special characters
            "",  # Empty
            None  # None
        ]
        
        for name in invalid_names:
            with pytest.raises(ValidationError):
                NameValidator.validate(name)

class TestStatusValidator:
    def test_valid_statuses(self):
        valid_statuses = ["connected", "disconnected", "warned"]
        
        for status in valid_statuses:
            result = StatusValidator.validate(status)
            assert result == status
    
    def test_invalid_statuses(self):
        invalid_statuses = [
            "active",
            "inactive",
            "",
            None
        ]
        
        for status in invalid_statuses:
            with pytest.raises(ValidationError):
                StatusValidator.validate(status)

class TestActionValidator:
    def test_valid_actions(self):
        valid_actions = ["connect", "disconnect", "warn", "sms_sent"]
        
        for action in valid_actions:
            result = ActionValidator.validate(action)
            assert result == action
    
    def test_invalid_actions(self):
        invalid_actions = [
            "create",
            "delete",
            "",
            None
        ]
        
        for action in invalid_actions:
            with pytest.raises(ValidationError):
                ActionValidator.validate(action)

class TestPaginationValidator:
    def test_valid_pagination(self):
        valid_cases = [
            (1, 10),
            (5, 50),
            (10, 100)
        ]
        
        for page, limit in valid_cases:
            result_page, result_limit = validate_pagination(page, limit)
            assert result_page == page
            assert result_limit == limit
    
    def test_invalid_pagination(self):
        invalid_cases = [
            (0, 10),  # Page too small
            (1, 0),   # Limit too small
            (1, 101), # Limit too large
        ]
        
        for page, limit in invalid_cases:
            with pytest.raises(ValidationError):
                validate_pagination(page, limit)

class TestUUIDValidator:
    def test_valid_uuids(self):
        valid_uuids = [
            "550e8400-e29b-41d4-a716-446655440000",
            "6ba7b810-9dad-11d1-80b4-00c04fd430c8"
        ]
        
        for uuid_str in valid_uuids:
            result = validate_uuid(uuid_str)
            assert result == uuid_str
    
    def test_invalid_uuids(self):
        invalid_uuids = [
            "not-a-uuid",
            "550e8400-e29b-41d4-a716",
            "",
            None
        ]
        
        for uuid_str in invalid_uuids:
            with pytest.raises(ValidationError):
                validate_uuid(uuid_str)
