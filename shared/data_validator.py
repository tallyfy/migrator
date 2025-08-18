#!/usr/bin/env python3
"""
Universal Data Validation System using Pydantic
Ensures data integrity throughout migration pipeline
"""

from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from pydantic import BaseModel, Field, validator, root_validator, EmailStr, HttpUrl
from enum import Enum
import hashlib
import json


# ============= BASE MODELS =============

class FieldType(str, Enum):
    """Standard field types across all vendors"""
    TEXT = "text"
    SHORT_TEXT = "short_text"
    LONG_TEXT = "long_text"
    NUMBER = "number"
    DATE = "date"
    DATETIME = "datetime"
    EMAIL = "email"
    PHONE = "phone"
    URL = "url"
    DROPDOWN = "dropdown"
    MULTI_SELECT = "multi_select"
    CHECKBOX = "checkbox"
    YES_NO = "yes_no"
    FILE = "file"
    USER = "user"
    CURRENCY = "currency"
    PERCENTAGE = "percentage"
    RATING = "rating"
    SIGNATURE = "signature"
    LOCATION = "location"
    JSON = "json"


class BaseField(BaseModel):
    """Base field model for all vendors"""
    id: str
    name: str = Field(..., min_length=1, max_length=255)
    type: FieldType
    required: bool = False
    description: Optional[str] = None
    default_value: Optional[Any] = None
    validation_rules: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = {}
    
    @validator('name')
    def clean_name(cls, v):
        """Clean and validate field name"""
        # Remove leading/trailing whitespace
        v = v.strip()
        # Ensure no special characters that break systems
        if any(char in v for char in ['<', '>', '"', '\\', '|']):
            raise ValueError(f"Field name contains invalid characters: {v}")
        return v
    
    def get_hash(self) -> str:
        """Get deterministic hash of field"""
        canonical = json.dumps({
            'name': self.name,
            'type': self.type.value,
            'required': self.required
        }, sort_keys=True)
        return hashlib.md5(canonical.encode()).hexdigest()


class BaseUser(BaseModel):
    """Base user model for all vendors"""
    id: str
    email: EmailStr
    name: str = Field(..., min_length=1, max_length=255)
    role: str = Field(default="member")
    active: bool = True
    created_at: Optional[datetime] = None
    metadata: Dict[str, Any] = {}
    
    @validator('email')
    def lowercase_email(cls, v):
        """Normalize email to lowercase"""
        return v.lower()
    
    @validator('role')
    def validate_role(cls, v):
        """Validate role is acceptable"""
        valid_roles = ['admin', 'manager', 'member', 'guest', 'viewer', 'editor']
        if v.lower() not in valid_roles:
            # Try to map to closest valid role
            if 'admin' in v.lower():
                return 'admin'
            elif 'edit' in v.lower():
                return 'editor'
            elif 'view' in v.lower():
                return 'viewer'
            else:
                return 'member'
        return v.lower()


# ============= VENDOR-SPECIFIC MODELS =============

class TrelloCard(BaseModel):
    """Trello card data model"""
    id: str
    name: str = Field(..., min_length=1)
    desc: str = ""
    due: Optional[datetime] = None
    dueComplete: bool = False
    idList: str
    idBoard: str
    idMembers: List[str] = []
    labels: List[Dict[str, Any]] = []
    pos: float = 0
    url: HttpUrl
    badges: Dict[str, Any] = {}
    customFieldItems: List[Dict] = []
    
    @validator('due', pre=True)
    def parse_due_date(cls, v):
        """Parse Trello's date format"""
        if v and isinstance(v, str):
            try:
                return datetime.fromisoformat(v.replace('Z', '+00:00'))
            except:
                return None
        return v
    
    @root_validator
    def validate_card(cls, values):
        """Validate card has required relationships"""
        if not values.get('idList'):
            raise ValueError("Card must belong to a list")
        if not values.get('idBoard'):
            raise ValueError("Card must belong to a board")
        return values


class AsanaTask(BaseModel):
    """Asana task data model"""
    gid: str
    name: str
    notes: str = ""
    completed: bool = False
    due_on: Optional[datetime] = None
    due_at: Optional[datetime] = None
    assignee: Optional[Dict[str, str]] = None
    projects: List[Dict[str, str]] = []
    tags: List[Dict[str, str]] = []
    custom_fields: List[Dict[str, Any]] = []
    followers: List[Dict[str, str]] = []
    
    @validator('due_on', 'due_at', pre=True)
    def parse_dates(cls, v):
        """Parse Asana date formats"""
        if v and isinstance(v, str):
            try:
                if 'T' in v:
                    return datetime.fromisoformat(v.replace('Z', '+00:00'))
                else:
                    return datetime.strptime(v, '%Y-%m-%d')
            except:
                return None
        return v


class MondayItem(BaseModel):
    """Monday.com item data model"""
    id: str
    name: str
    state: str = "active"
    board: Dict[str, Any]
    group: Dict[str, Any]
    column_values: List[Dict[str, Any]] = []
    creator_id: Optional[str] = None
    updated_at: datetime
    
    @validator('column_values')
    def validate_columns(cls, v):
        """Validate column values have required fields"""
        for col in v:
            if 'id' not in col or 'value' not in col:
                raise ValueError(f"Invalid column value: {col}")
        return v


class TypeformResponse(BaseModel):
    """Typeform response data model"""
    response_id: str
    submitted_at: datetime
    answers: List[Dict[str, Any]]
    variables: Dict[str, Any] = {}
    hidden: Dict[str, Any] = {}
    calculated: Dict[str, float] = {}
    
    @validator('answers')
    def validate_answers(cls, v):
        """Validate answer structure"""
        for answer in v:
            if 'field' not in answer or 'type' not in answer:
                raise ValueError(f"Invalid answer structure: {answer}")
        return v


# ============= TALLYFY MODELS =============

class TallyfyField(BaseModel):
    """Tallyfy field data model"""
    name: str = Field(..., min_length=1, max_length=255)
    type: str
    required: bool = False
    description: Optional[str] = Field(None, max_length=1000)
    default_value: Optional[Any] = None
    options: Optional[List[str]] = None  # For dropdowns
    validation: Optional[Dict[str, Any]] = None
    position: int = 0
    
    @validator('type')
    def validate_type(cls, v):
        """Ensure type is valid Tallyfy type"""
        valid_types = [
            'short_text', 'long_text', 'number', 'date', 'datetime',
            'email', 'phone', 'url', 'dropdown', 'multi_select',
            'yes_no', 'file_attachment', 'member_select', 'rating',
            'currency', 'signature', 'location'
        ]
        if v not in valid_types:
            raise ValueError(f"Invalid Tallyfy field type: {v}")
        return v
    
    @root_validator
    def validate_options(cls, values):
        """Validate options for select fields"""
        field_type = values.get('type')
        options = values.get('options')
        
        if field_type in ['dropdown', 'multi_select'] and not options:
            raise ValueError(f"Field type {field_type} requires options")
        
        return values


class TallyfyStep(BaseModel):
    """Tallyfy process step model"""
    name: str = Field(..., min_length=1, max_length=255)
    type: str = Field(..., regex="^(task|approval|notification|form)$")
    description: Optional[str] = None
    fields: List[TallyfyField] = []
    assignees: List[str] = []
    due_date_offset: Optional[int] = None  # Days from process start
    conditions: Optional[Dict[str, Any]] = None
    position: int = 0
    
    @validator('assignees')
    def validate_assignees(cls, v):
        """Ensure assignees are valid"""
        if v and len(v) > 10:
            raise ValueError("Too many assignees (max 10)")
        return v


class TallyfyBlueprint(BaseModel):
    """Tallyfy blueprint (process template) model"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=5000)
    category: Optional[str] = None
    tags: List[str] = []
    steps: List[TallyfyStep] = []
    kick_off_form: List[TallyfyField] = []
    visibility: str = Field(default="private", regex="^(public|private|team)$")
    
    @validator('tags')
    def clean_tags(cls, v):
        """Clean and validate tags"""
        # Remove duplicates and clean
        return list(set(tag.strip().lower() for tag in v if tag.strip()))
    
    @root_validator
    def validate_blueprint(cls, values):
        """Validate blueprint has required elements"""
        steps = values.get('steps', [])
        kick_off = values.get('kick_off_form', [])
        
        if not steps and not kick_off:
            raise ValueError("Blueprint must have either steps or kick-off form")
        
        # Validate step positions are unique
        positions = [s.position for s in steps]
        if len(positions) != len(set(positions)):
            raise ValueError("Step positions must be unique")
        
        return values


# ============= VALIDATION FUNCTIONS =============

class DataValidator:
    """Universal data validator for migrations"""
    
    @staticmethod
    def validate_vendor_data(vendor: str, data_type: str, data: Any) -> bool:
        """
        Validate vendor-specific data
        
        Args:
            vendor: Vendor name (trello, asana, monday, etc.)
            data_type: Type of data (card, task, user, etc.)
            data: Data to validate
        
        Returns:
            bool: True if valid
        
        Raises:
            ValueError: If validation fails with details
        """
        validators = {
            'trello': {
                'card': TrelloCard,
                'user': BaseUser
            },
            'asana': {
                'task': AsanaTask,
                'user': BaseUser
            },
            'monday': {
                'item': MondayItem,
                'user': BaseUser
            },
            'typeform': {
                'response': TypeformResponse,
                'user': BaseUser
            }
        }
        
        vendor_validators = validators.get(vendor, {})
        validator_class = vendor_validators.get(data_type, BaseModel)
        
        try:
            if isinstance(data, list):
                for item in data:
                    validator_class(**item)
            else:
                validator_class(**data)
            return True
        except Exception as e:
            raise ValueError(f"Validation failed for {vendor} {data_type}: {str(e)}")
    
    @staticmethod
    def validate_transformation(source_data: Dict, target_data: Dict, 
                              transformation_rules: Dict) -> Dict[str, Any]:
        """
        Validate data transformation
        
        Returns:
            Dict with validation results and issues
        """
        issues = []
        warnings = []
        
        # Check required fields
        for field in transformation_rules.get('required_fields', []):
            if field not in target_data or target_data[field] is None:
                issues.append(f"Required field missing: {field}")
        
        # Check data types
        for field, expected_type in transformation_rules.get('field_types', {}).items():
            if field in target_data:
                actual_type = type(target_data[field]).__name__
                if actual_type != expected_type and target_data[field] is not None:
                    warnings.append(f"Field {field} type mismatch: expected {expected_type}, got {actual_type}")
        
        # Check data loss
        source_fields = set(source_data.keys())
        target_fields = set(target_data.keys())
        unmapped_fields = source_fields - target_fields
        
        if unmapped_fields:
            warnings.append(f"Unmapped fields: {unmapped_fields}")
        
        # Check value constraints
        for field, constraints in transformation_rules.get('constraints', {}).items():
            if field in target_data:
                value = target_data[field]
                
                if 'min' in constraints and value < constraints['min']:
                    issues.append(f"Field {field} below minimum: {value} < {constraints['min']}")
                
                if 'max' in constraints and value > constraints['max']:
                    issues.append(f"Field {field} above maximum: {value} > {constraints['max']}")
                
                if 'pattern' in constraints:
                    import re
                    if not re.match(constraints['pattern'], str(value)):
                        issues.append(f"Field {field} doesn't match pattern: {constraints['pattern']}")
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings,
            'data_loss_percentage': len(unmapped_fields) / len(source_fields) * 100 if source_fields else 0
        }
    
    @staticmethod
    def validate_tallyfy_data(data_type: str, data: Any) -> bool:
        """Validate Tallyfy data before import"""
        validators = {
            'field': TallyfyField,
            'step': TallyfyStep,
            'blueprint': TallyfyBlueprint,
            'user': BaseUser
        }
        
        validator_class = validators.get(data_type)
        if not validator_class:
            raise ValueError(f"Unknown Tallyfy data type: {data_type}")
        
        try:
            if isinstance(data, list):
                for item in data:
                    validator_class(**item)
            else:
                validator_class(**data)
            return True
        except Exception as e:
            raise ValueError(f"Tallyfy validation failed for {data_type}: {str(e)}")
    
    @staticmethod
    def detect_duplicates(items: List[Dict], key_fields: List[str]) -> List[Tuple[int, int]]:
        """
        Detect duplicate items based on key fields
        
        Returns:
            List of tuples with duplicate item indices
        """
        duplicates = []
        seen = {}
        
        for i, item in enumerate(items):
            # Create key from specified fields
            key_values = tuple(item.get(field) for field in key_fields)
            
            if key_values in seen:
                duplicates.append((seen[key_values], i))
            else:
                seen[key_values] = i
        
        return duplicates
    
    @staticmethod
    def sanitize_data(data: Dict, rules: Dict = None) -> Dict:
        """
        Sanitize data before migration
        
        Args:
            data: Data to sanitize
            rules: Sanitization rules
        
        Returns:
            Sanitized data
        """
        if rules is None:
            rules = {
                'strip_html': True,
                'max_length': 5000,
                'remove_null': True,
                'normalize_whitespace': True
            }
        
        import re
        from html import unescape
        
        def clean_value(value, field_rules=None):
            if value is None:
                return None if not rules.get('remove_null') else ""
            
            if isinstance(value, str):
                # Strip HTML
                if rules.get('strip_html'):
                    value = re.sub('<[^<]+?>', '', value)
                    value = unescape(value)
                
                # Normalize whitespace
                if rules.get('normalize_whitespace'):
                    value = ' '.join(value.split())
                
                # Apply max length
                max_len = field_rules.get('max_length') if field_rules else rules.get('max_length')
                if max_len and len(value) > max_len:
                    value = value[:max_len-3] + '...'
                
                return value.strip()
            
            elif isinstance(value, dict):
                return {k: clean_value(v) for k, v in value.items()}
            
            elif isinstance(value, list):
                return [clean_value(item) for item in value]
            
            return value
        
        sanitized = {}
        for key, value in data.items():
            field_rules = rules.get('fields', {}).get(key)
            sanitized[key] = clean_value(value, field_rules)
        
        return sanitized


# ============= USAGE EXAMPLES =============

if __name__ == "__main__":
    # Example: Validate Trello card
    trello_card = {
        "id": "abc123",
        "name": "Test Card",
        "desc": "Description",
        "idList": "list123",
        "idBoard": "board123",
        "url": "https://trello.com/c/abc123",
        "due": "2024-12-31T23:59:59Z"
    }
    
    try:
        card = TrelloCard(**trello_card)
        print(f"✅ Valid Trello card: {card.name}")
    except Exception as e:
        print(f"❌ Invalid card: {e}")
    
    # Example: Validate Tallyfy blueprint
    blueprint_data = {
        "name": "Employee Onboarding",
        "description": "Standard onboarding process",
        "tags": ["hr", "onboarding"],
        "steps": [
            {
                "name": "Collect Information",
                "type": "form",
                "position": 0,
                "fields": [
                    {
                        "name": "Full Name",
                        "type": "short_text",
                        "required": True,
                        "position": 0
                    }
                ]
            }
        ]
    }
    
    try:
        blueprint = TallyfyBlueprint(**blueprint_data)
        print(f"✅ Valid blueprint: {blueprint.name}")
    except Exception as e:
        print(f"❌ Invalid blueprint: {e}")
    
    # Example: Detect duplicates
    items = [
        {"id": "1", "email": "user@example.com", "name": "User 1"},
        {"id": "2", "email": "user@example.com", "name": "User 2"},  # Duplicate email
        {"id": "3", "email": "other@example.com", "name": "User 3"}
    ]
    
    validator = DataValidator()
    duplicates = validator.detect_duplicates(items, ['email'])
    if duplicates:
        print(f"⚠️  Found duplicates at indices: {duplicates}")
    
    print("\nData validation system ready for production use!")