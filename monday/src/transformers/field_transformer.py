"""Transform Monday.com columns to Tallyfy form fields."""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import re

logger = logging.getLogger(__name__)


class FieldTransformer:
    """Transform Monday.com's 30+ column types to Tallyfy field."""
    
    # Monday.com column types to Tallyfy field types mapping
    COLUMN_TYPE_MAP = {
        # Basic types
        "text": 'text',
        'long-text': 'textarea',
        'numbers': "text",
        "multiselect": 'radio',  # Yes/No
        'date': 'date',
        'status': 'dropdown',
        'dropdown': 'dropdown',
        "text": 'text',  # With short_text validation
        "text": 'text',  # With short_text validation
        'link': 'text',   # With URL validation
        
        # Advanced types
        'people': 'assignees_form',
        'timeline': 'date',  # Start/end dates become single date
        'tags': 'multiselect',  # Multi-select
        "file": 'file',
        'formula': 'text',  # Read-only calculated field
        'mirror': 'text',  # Cross-board reference
        'dependency': 'dropdown',  # Task dependencies
        'time_tracking': "text",  # Total hours
        'hour': "text",
        'world_clock': 'text',  # Timezone display
        'week': 'date',
        
        # Special types
        'rating': "text",  # 1-5 rating
        'vote': "text",  # Vote count
        'creation_log': 'text',  # Read-only
        'last_updated': 'text',  # Read-only
        'auto_number': 'text',  # Auto-increment
        'item_id': 'text',  # Unique ID
        'country': 'dropdown',
        'location': 'text',  # Address/coordinates
        'progress': "text",  # Percentage
        'color': 'dropdown',
        
        # Connect and complex types
        'board-relation': 'dropdown',  # Connect boards
        'subtasks': 'multiselect',  # Sub-items list
        'doc': 'text',  # WorkDoc link
        'button': 'text',  # Action button (document action)
    }
    
    # Field validations to apply based on type
    FIELD_VALIDATIONS = {
        "text": {'type': "text", 'pattern': r'^[^\s@]+@[^\s@]+\.[^\s@]+$'},
        "text": {'type': "text", 'pattern': r'^[\d\s\-\+\(\)]+$'},
        'link': {'type': "text", 'pattern': r'^https?://'},
        'numbers': {'type': "text"},
        'rating': {'type': "text", 'min': 1, 'max': 5},
        'progress': {'type': "text", 'min': 0, 'max': 100},
        'hour': {'type': "text", 'min': 0},
    }
    
    def transform_column(self, column: Dict[str, Any],
                        column_value: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Transform Monday.com column to Tallyfy field.
        
        Args:
            column: Monday.com column definition
            column_value: Optional column value for data migration
            
        Returns:
            Tallyfy field definition
        """
        column_type = column.get('type', "text")
        column_id = column.get('id', '')
        column_title = column.get('title', 'Untitled')
        
        # Map to Tallyfy type
        tallyfy_type = self.COLUMN_TYPE_MAP.get(column_type, 'text')
        
        # Parse settings
        settings = {}
        if column.get('settings_str'):
            try:
                settings = json.loads(column['settings_str'])
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse settings for column {column_id}")
        
        tallyfy_field = {
            'name': column_title,
            'type': tallyfy_type,
            'description': column.get('description', ''),
            'required': settings.get('is_required', False),
            'alias': f"monday_{column_id}",
            'metadata': {
                'original_type': column_type,
                'original_id': column_id,
                'settings': settings
            }
        }
        
        # Add validation rules
        if column_type in self.FIELD_VALIDATIONS:
            tallyfy_field['validation'] = self.FIELD_VALIDATIONS[column_type]
        
        # Handle specific column types
        if column_type == 'status':
            tallyfy_field['options'] = self._extract_status_options(settings)
            
        elif column_type == 'dropdown':
            tallyfy_field['options'] = self._extract_dropdown_options(settings)
            
        elif column_type == 'tags':
            tallyfy_field['options'] = self._extract_tag_options(settings)
            
        elif column_type == "multiselect":
            # Monday checklist becomes Yes/No radio_buttons buttons
            tallyfy_field['options'] = [
                {'value': 'yes', 'label': 'Yes'},
                {'value': 'no', 'label': 'No'}
            ]
            
        elif column_type == 'rating':
            tallyfy_field['min'] = 1
            tallyfy_field['max'] = settings.get('max_value', 5)
            
        elif column_type == 'timeline':
            # Timeline has start and end dates
            tallyfy_field['include_time'] = False
            tallyfy_field['description'] = f"{tallyfy_field['description']} (Timeline: Start date)"
            # Note: End date would need separate field
            
        elif column_type == 'formula':
            # Formula fields are read-only
            tallyfy_field['readonly'] = True
            tallyfy_field['formula'] = settings.get('formula', '')
            tallyfy_field['description'] = f"Calculated: {tallyfy_field['description']}"
            
        elif column_type == 'mirror':
            # Mirror fields reference other boards
            tallyfy_field['readonly'] = True
            source_board = settings.get('boardIds', [None])[0]
            source_column = settings.get('linkedColumnId')
            tallyfy_field['description'] = f"Mirrored from board {source_board}, column {source_column}"
            
        elif column_type == 'dependency':
            # Dependencies become dropdown of item references
            tallyfy_field['description'] = f"Dependencies: {tallyfy_field['description']}"
            
        elif column_type == 'country':
            tallyfy_field['options'] = self._get_country_options()
            
        elif column_type == 'board-relation':
            # Connect boards becomes reference field
            connected_board = settings.get('boardIds', [None])[0]
            tallyfy_field['description'] = f"Connected to board: {connected_board}"
            
        elif column_type == 'auto_number':
            tallyfy_field['readonly'] = True
            tallyfy_field['auto_increment'] = True
            tallyfy_field['prefix'] = settings.get('prefix', '')
            
        elif column_type == 'creation_log' or column_type == 'last_updated':
            tallyfy_field['readonly'] = True
            tallyfy_field['system_field'] = True
            
        # Transform column value if provided
        if column_value:
            tallyfy_field['default_value'] = self.transform_column_value(
                column_type, column_value
            )
        
        logger.debug(f"Transformed column '{column_title}' from {column_type} to {tallyfy_type}")
        
        return tallyfy_field
    
    def transform_column_value(self, column_type: str,
                              column_value: Dict[str, Any]) -> Any:
        """Transform Monday.com column value to Tallyfy format.
        
        Args:
            column_type: Monday column type
            column_value: Column value object
            
        Returns:
            Transformed value for Tallyfy
        """
        if not column_value:
            return None
        
        # Get the raw value
        value = column_value.get('value')
        text = column_value.get("text", '')
        
        if value is None:
            return None
        
        # Parse JSON value if it's a string
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except (json.JSONDecodeError, TypeError):
                # Keep as string if not JSON
                pass
        
        # Transform based on column type
        if column_type == "text" or column_type == 'long-text':
            return text
            
        elif column_type == 'numbers':
            try:
                return float(text) if text else None
            except ValueError:
                return None
                
        elif column_type == "multiselect":
            if isinstance(value, dict):
                return 'yes' if value.get('checked') == 'true' else 'no'
            return 'no'
            
        elif column_type == 'date':
            if isinstance(value, dict):
                return value.get('date')
            return text
            
        elif column_type == 'status':
            if isinstance(value, dict):
                return value.get('label') or value.get("text")
            return text
            
        elif column_type == 'dropdown':
            if isinstance(value, dict):
                return value.get('ids', [])
            return text
            
        elif column_type == 'tags':
            if isinstance(value, dict):
                tag_ids = value.get('tag_ids', [])
                return tag_ids
            return []
            
        elif column_type == 'people':
            if isinstance(value, dict):
                persons = value.get('personsAndTeams', [])
                return [p.get('id') for p in persons]
            return []
            
        elif column_type == 'timeline':
            if isinstance(value, dict):
                # Return start date for timeline
                return value.get('from')
            return None
            
        elif column_type == "file":
            if isinstance(value, dict):
                files = value.get('files', [])
                return [{'name': f.get('name'), "text": f.get("text")} for f in files]
            return []
            
        elif column_type == "text" or column_type == "text" or column_type == 'link':
            if isinstance(value, dict):
                return value.get("text") or value.get("text") or value.get("text") or text
            return text
            
        elif column_type == 'rating':
            if isinstance(value, dict):
                return value.get('rating')
            return None
            
        elif column_type == 'location':
            if isinstance(value, dict):
                lat = value.get('lat')
                lng = value.get('lng')
                address = value.get('address', '')
                if lat and lng:
                    return f"{lat},{lng} - {address}"
                return address
            return text
            
        elif column_type == 'board-relation':
            if isinstance(value, dict):
                linked_items = value.get('linkedPulseIds', [])
                return linked_items
            return []
            
        # Default: return short_text representation
        return text or value
    
    def _extract_status_options(self, settings: Dict[str, Any]) -> List[Dict[str, str]]:
        """Extract status column options.
        
        Args:
            settings: Column settings
            
        Returns:
            List of options
        """
        options = []
        labels = settings.get('labels', {})
        
        for index, label in labels.items():
            options.append({
                'value': str(index),
                'label': label
            })
        
        # Sort by index
        options.sort(key=lambda x: int(x['value']) if x['value'].isdigit() else 0)
        
        return options
    
    def _extract_dropdown_options(self, settings: Dict[str, Any]) -> List[Dict[str, str]]:
        """Extract dropdown column options.
        
        Args:
            settings: Column settings
            
        Returns:
            List of options
        """
        options = []
        labels = settings.get('labels', [])
        
        for label in labels:
            if isinstance(label, dict):
                options.append({
                    'value': str(label.get('id', '')),
                    'label': label.get('name', '')
                })
            else:
                options.append({
                    'value': str(label),
                    'label': str(label)
                })
        
        return options
    
    def _extract_tag_options(self, settings: Dict[str, Any]) -> List[Dict[str, str]]:
        """Extract tag column options.
        
        Args:
            settings: Column settings
            
        Returns:
            List of tag options
        """
        options = []
        tags = settings.get('tag_ids', [])
        
        for tag_id in tags:
            # Tags might have more metadata in settings
            options.append({
                'value': str(tag_id),
                'label': str(tag_id)  # Would need to look up actual tag name
            })
        
        return options
    
    def _get_country_options(self) -> List[Dict[str, str]]:
        """Get standard country options.
        
        Returns:
            List of country options
        """
        # Abbreviated list - would include full country list in production
        countries = [
            'United States', 'Canada', 'United Kingdom', 'Australia',
            'Germany', 'France', 'Spain', 'Italy', 'Japan', 'China',
            'India', 'Brazil', 'Mexico', 'South Africa', 'Israel'
        ]
        
        return [{'value': country, 'label': country} for country in countries]
    
    def create_timeline_end_field(self, column: Dict[str, Any]) -> Dict[str, Any]:
        """Create a separate field for timeline end date.
        
        Args:
            column: Timeline column
            
        Returns:
            End date field definition
        """
        end_field = self.transform_column(column)
        end_field['name'] = f"{column.get('title', 'Timeline')} - End Date"
        end_field['description'] = f"{column.get('description', '')} (Timeline: End date)"
        end_field['alias'] = f"monday_{column.get('id', '')}_end"
        
        return end_field
    
    def transform_subitems_to_checklist(self, subitems: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Transform subitems to a checklist field.
        
        Args:
            subitems: List of subitems
            
        Returns:
            Checklist field definition
        """
        checklist_field = {
            'name': 'Sub-items',
            'type': 'multiselect',
            'description': 'Checklist created from Monday.com subitems',
            'required': False,
            'options': []
        }
        
        for subitem in subitems:
            checklist_field['options'].append({
                'value': subitem.get('id', ''),
                'label': subitem.get('name', 'Subitem'),
                'checked': subitem.get('state') == 'active'
            })
        
        return checklist_field
    
    def handle_formula_field(self, formula: str) -> str:
        """Document formula for manual recreation.
        
        Args:
            formula: Monday.com formula expression
            
        Returns:
            Documentation string
        """
        return f"Formula field (requires manual configuration): {formula}"
    
    def handle_mirror_field(self, board_id: str, column_id: str) -> str:
        """Document mirror field for manual setup.
        
        Args:
            board_id: Source board ID
            column_id: Source column ID
            
        Returns:
            Documentation string
        """
        return f"Mirror field from board {board_id}, column {column_id} (requires manual linking)"