import logging
import json
import traceback
from datetime import datetime
from typing import Any, Dict, Optional
from contextvars import ContextVar

# Context variable for request tracking
request_id_var: ContextVar[Optional[str]] = ContextVar('request_id', default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar('user_id', default=None)

class StructuredLogger:
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Create console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
    
    def _get_context(self) -> Dict[str, Any]:
        """Get current request context"""
        context = {
            'timestamp': datetime.utcnow().isoformat(),
        }
        
        if request_id := request_id_var.get():
            context['request_id'] = request_id
        
        if user_id := user_id_var.get():
            context['user_id'] = user_id
            
        return context
    
    def info(self, message: str, **kwargs):
        """Log info message with context"""
        log_data = {
            'message': message,
            'level': 'INFO',
            **self._get_context(),
            **kwargs
        }
        self.logger.info(json.dumps(log_data))
    
    def error(self, message: str, error: Optional[Exception] = None, **kwargs):
        """Log error message with context and stack trace"""
        log_data = {
            'message': message,
            'level': 'ERROR',
            **self._get_context(),
            **kwargs
        }
        
        if error:
            log_data.update({
                'error_type': type(error).__name__,
                'error_message': str(error),
                'stack_trace': traceback.format_exc()
            })
        
        self.logger.error(json.dumps(log_data))
    
    def warning(self, message: str, **kwargs):
        """Log warning message with context"""
        log_data = {
            'message': message,
            'level': 'WARNING',
            **self._get_context(),
            **kwargs
        }
        self.logger.warning(json.dumps(log_data))

# Create logger instances
logger = StructuredLogger('insight_ops_flow')
api_logger = StructuredLogger('api')
db_logger = StructuredLogger('database')
