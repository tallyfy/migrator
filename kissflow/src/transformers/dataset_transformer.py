"""Transform Kissflow datasets to Tallyfy data structures."""

import logging
from typing import Dict, Any, List, Optional
from .field_transformer import FieldTransformer

logger = logging.getLogger(__name__)


class DatasetTransformer:
    """Transform Kissflow datasets (master data) to Tallyfy data structures.
    
    Kissflow Datasets are structured data tables used for lookups, dropdowns,
    and reference data across processes and apps.
    """
    
    def __init__(self):
        self.field_transformer = FieldTransformer()
        
    def transform_dataset_to_blueprint(self, dataset: Dict[str, Any],
                                      records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Transform Kissflow dataset to Tallyfy blueprint with data management workflow.
        
        Since Tallyfy doesn't have a direct dataset equivalent, we create a
        data management blueprint that can maintain the dataset records.
        
        Args:
            dataset: Kissflow dataset definition
            records: Dataset records
            
        Returns:
            Tallyfy blueprint for data management
        """
        logger.info(f"Transforming dataset '{dataset.get('Name')}' with {len(records)} records")
        
        blueprint = {
            'name': f"Data: {dataset.get('Name', 'Dataset')}",
            'description': self._format_description(dataset, records),
            'steps': self._create_data_management_steps(dataset),
            'kick_off_form': self._create_dataset_form(dataset),
            'tags': self._extract_tags(dataset),
            'metadata': {
                'source': 'kissflow',
                'original_id': dataset.get('Id'),
                'original_type': 'dataset',
                'record_count': len(records),
                'created_at': dataset.get('CreatedAt'),
                'modified_at': dataset.get('ModifiedAt'),
                'is_lookup_data': True,
                'primary_key': dataset.get('PrimaryKey', 'Id')
            }
        }
        
        # Store dataset records as reference data
        blueprint['reference_data'] = self._transform_records(dataset, records)
        
        # Add data validation rules
        if dataset.get('Validations'):
            blueprint['rules'] = self._transform_validations(dataset['Validations'])
        
        # Add import/export configurations
        blueprint['data_operations'] = self._create_data_operations(dataset)
        
        return blueprint
    
    def _format_description(self, dataset: Dict[str, Any], 
                           records: List[Dict[str, Any]]) -> str:
        """Format dataset description with migration notes.
        
        Args:
            dataset: Kissflow dataset
            records: Dataset records
            
        Returns:
            Formatted description
        """
        description = dataset.get('Description', '')
        
        # Add dataset migration warning
        dataset_warning = f"""

⚠️ **DATASET MIGRATION** ⚠️
This is a Kissflow Dataset (master data) with {len(records)} records.

**Original Dataset Structure:**
• Record Count: {len(records)}
• Fields: {len(dataset.get('Fields', []))}
• Primary Key: {dataset.get('PrimaryKey', 'Id')}
• Used For: {dataset.get('UsedFor', 'Reference data and lookups')}

**Migration Approach:**
Since Tallyfy doesn't have native datasets, this has been converted to:
1. A data management workflow for CRUD operations
2. Reference data stored in the blueprint metadata
3. Lookup fields in other processes will reference this data

**Critical Notes:**
• Dataset records are stored as reference data
• Use the data management workflow to maintain records
• Lookups from other processes need manual configuration
• Consider using external database for large datasets (>1000 records)

**Data Usage:**
"""
        
        # Add usage information
        if dataset.get('UsedIn'):
            dataset_warning += "\nThis dataset is referenced by:"
            for usage in dataset['UsedIn']:
                dataset_warning += f"\n• {usage.get('Name', 'Process')} ({usage.get('Type', 'unknown')})"
        
        # Add field information
        dataset_warning += "\n\n**Dataset Fields:**"
        for field in dataset.get('Fields', []):
            field_type = field.get('Type', "text")
            required = "Required" if field.get('Required') else "Optional"
            dataset_warning += f"\n• {field.get('Name', 'Field')} ({field_type}, {required})"
        
        # Add sample records
        if records:
            dataset_warning += "\n\n**Sample Records (first 5):**"
            for idx, record in enumerate(records[:5]):
                dataset_warning += f"\n{idx + 1}. "
                # Show first few fields
                field_values = []
                for key, value in list(record.items())[:3]:
                    if key != '_id' and value:
                        field_values.append(f"{key}: {value}")
                dataset_warning += ", ".join(field_values)
        
        migration_note = f"\n\n---\n*Migrated from Kissflow Dataset*"
        
        if dataset.get('Category'):
            migration_note += f"\n*Category: {dataset['Category']}*"
        
        if dataset.get('LastSyncTime'):
            migration_note += f"\n*Last Sync: {dataset['LastSyncTime']}*"
        
        return description + dataset_warning + migration_note
    
    def _create_data_management_steps(self, dataset: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create CRUD workflow steps for dataset management.
        
        Args:
            dataset: Dataset definition
            
        Returns:
            List of workflow steps
        """
        steps = []
        
        # Step 1: Choose operation
        steps.append({
            'order': 1,
            'name': 'Select Data Operation',
            'type': 'task',
            'description': 'Choose the operation to perform on the dataset',
            "assignees_form": 'process_initiator',
            'duration': 0,
            'form_fields': [
                {
                    'name': 'Operation',
                    'type': 'dropdown',
                    'description': 'Select the data operation',
                    'required': True,
                    'options': [
                        {'value': 'create', 'label': 'Create New Record'},
                        {'value': 'read', 'label': 'View/Search Records'},
                        {'value': 'update', 'label': 'Update Existing Record'},
                        {'value': 'delete', 'label': 'Delete Record'},
                        {'value': 'import', 'label': 'Bulk Import'},
                        {'value': 'export', 'label': 'Export Data'}
                    ]
                },
                {
                    'name': 'Record ID',
                    'type': 'text',
                    'description': 'For update/delete operations, specify the record ID',
                    'required': False,
                    'conditional': {
                        'field': 'Operation',
                        'values': ['update', 'delete']
                    }
                }
            ]
        })
        
        # Step 2: Data entry/modification
        steps.append({
            'order': 2,
            'name': 'Enter/Modify Data',
            'type': 'task',
            'description': 'Enter new data or modify existing record',
            "assignees_form": 'process_initiator',
            'duration': 0,
            'form_fields': self._create_dataset_fields(dataset),
            'metadata': {
                'conditional_on': 'Operation',
                'show_when': ['create', 'update']
            }
        })
        
        # Step 3: Search/filter (for read operations)
        steps.append({
            'order': 3,
            'name': 'Search Records',
            'type': 'task',
            'description': 'Search and filter dataset records',
            "assignees_form": 'process_initiator',
            'duration': 0,
            'form_fields': [
                {
                    'name': 'Search Query',
                    'type': 'text',
                    'description': 'Enter search terms',
                    'required': False
                },
                {
                    'name': 'Filter Field',
                    'type': 'dropdown',
                    'description': 'Select field to filter by',
                    'required': False,
                    'options': [
                        {'value': field.get('Id', ''), 'label': field.get('Name', '')}
                        for field in dataset.get('Fields', [])
                    ]
                },
                {
                    'name': 'Filter Value',
                    'type': 'text',
                    'description': 'Enter filter value',
                    'required': False
                }
            ],
            'metadata': {
                'conditional_on': 'Operation',
                'show_when': ['read']
            }
        })
        
        # Step 4: Validation
        steps.append({
            'order': 4,
            'name': 'Validate Data',
            'type': 'task',
            'description': 'Validate data integrity and business rules',
            "assignees_form": 'process_owner',
            'duration': 0,
            'form_fields': [
                {
                    'name': 'Validation Status',
                    'type': 'radio',
                    'description': 'Is the data valid?',
                    'required': True,
                    'options': [
                        {'value': 'valid', 'label': 'Data is Valid'},
                        {'value': 'invalid', 'label': 'Data has Errors'}
                    ]
                },
                {
                    'name': 'Validation Errors',
                    'type': 'textarea',
                    'description': 'Describe any validation errors',
                    'required': False,
                    'conditional': {
                        'field': 'Validation Status',
                        'value': 'invalid'
                    }
                }
            ]
        })
        
        # Step 5: Approval (for create/update/delete)
        steps.append({
            'order': 5,
            'name': 'Approve Data Change',
            'type': 'approval',
            'description': 'Approve the data modification',
            "assignees_form": 'process_owner',
            'duration': 1,
            'form_fields': [
                {
                    'name': 'Approval Decision',
                    'type': 'radio',
                    'required': True,
                    'options': [
                        {'value': 'approved', 'label': 'Approved'},
                        {'value': 'rejected', 'label': 'Rejected'}
                    ]
                },
                {
                    'name': 'Approval Comments',
                    'type': 'textarea',
                    'required': False
                }
            ],
            'metadata': {
                'conditional_on': 'Operation',
                'show_when': ['create', 'update', 'delete']
            }
        })
        
        # Step 6: Execute operation
        steps.append({
            'order': 6,
            'name': 'Execute Operation',
            'type': 'task',
            'description': 'Perform the requested data operation',
            "assignees_form": 'process_owner',
            'duration': 0,
            'form_fields': [
                {
                    'name': 'Operation Result',
                    'type': 'textarea',
                    'description': 'Result of the operation',
                    'required': True,
                    'readonly': True
                },
                {
                    'name': 'Records Affected',
                    'type': "text",
                    'description': 'Number of records affected',
                    'required': False
                }
            ]
        })
        
        # Step 7: Audit log
        steps.append({
            'order': 7,
            'name': 'Log Operation',
            'type': 'task',
            'description': 'Create audit log entry',
            "assignees_form": 'process_owner',
            'duration': 0,
            'form_fields': [
                {
                    'name': 'Audit Entry',
                    'type': 'textarea',
                    'description': 'Audit log details',
                    'required': True,
                    'default_value': 'Operation: {Operation}\nUser: {current_user}\nTimestamp: {now}\nResult: {Operation Result}'
                }
            ]
        })
        
        return steps
    
    def _create_dataset_form(self, dataset: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create kick-off form for dataset operations.
        
        Args:
            dataset: Dataset definition
            
        Returns:
            List of form fields
        """
        form_fields = []
        
        # Add operation selector
        form_fields.append({
            'name': 'Dataset Operation',
            'type': 'dropdown',
            'description': f"Operation on {dataset.get('Name', 'dataset')}",
            'required': True,
            'options': [
                {'value': 'manage', 'label': 'Manage Records'},
                {'value': 'query', 'label': 'Query Data'},
                {'value': 'sync', 'label': 'Sync with External Source'},
                {'value': 'validate', 'label': 'Validate All Records'},
                {'value': 'report', 'label': 'Generate Report'}
            ]
        })
        
        # Add metadata fields
        form_fields.append({
            'name': 'Operation Reason',
            'type': 'textarea',
            'description': 'Why is this operation needed?',
            'required': True
        })
        
        form_fields.append({
            'name': 'Priority',
            'type': 'dropdown',
            'description': 'Operation priority',
            'required': False,
            'options': [
                {'value': 'urgent', 'label': 'Urgent'},
                {'value': 'high', 'label': 'High'},
                {'value': 'normal', 'label': 'Normal'},
                {'value': 'low', 'label': 'Low'}
            ],
            'default_value': 'normal'
        })
        
        return form_fields
    
    def _create_dataset_fields(self, dataset: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create form fields from dataset schema.
        
        Args:
            dataset: Dataset definition
            
        Returns:
            List of form fields
        """
        form_fields = []
        
        for field in dataset.get('Fields', []):
            # Skip system fields
            if field.get('Name') in ['_id', 'CreatedAt', 'ModifiedAt', 'CreatedBy', 'ModifiedBy']:
                continue
            
            transformed_field = self.field_transformer.transform_field_definition(field)
            
            # Add unique constraint note if applicable
            if field.get('Unique'):
                transformed_field['description'] = f"{transformed_field.get('description', '')} (Must be unique)"
            
            # Add foreign key note if applicable
            if field.get('ForeignKey'):
                transformed_field['description'] = f"{transformed_field.get('description', '')} (References: {field['ForeignKey']})"
            
            form_fields.append(transformed_field)
        
        return form_fields
    
    def _transform_records(self, dataset: Dict[str, Any],
                         records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Transform dataset records to reference data format.
        
        Args:
            dataset: Dataset definition
            records: Dataset records
            
        Returns:
            Reference data structure
        """
        reference_data = {
            'schema': self._create_schema(dataset),
            'records': [],
            'indexes': {},
            'statistics': {
                'total_records': len(records),
                'unique_values': {},
                'null_counts': {}
            }
        }
        
        # Transform each record
        for record in records:
            transformed_record = {}
            
            for field in dataset.get('Fields', []):
                field_name = field.get('Name', '')
                field_id = field.get('Id', field_name)
                
                if field_id in record:
                    value = record[field_id]
                    # Transform value based on field type
                    transformed_value = self.field_transformer.transform_field_value(field, value)
                    transformed_record[field_name] = transformed_value
                    
                    # Update statistics
                    if transformed_value is None:
                        reference_data['statistics']['null_counts'][field_name] = \
                            reference_data['statistics']['null_counts'].get(field_name, 0) + 1
            
            # Add system fields
            transformed_record['_original_id'] = record.get('_id') or record.get('Id')
            transformed_record['_created_at'] = record.get('CreatedAt')
            transformed_record['_modified_at'] = record.get('ModifiedAt')
            
            reference_data['records'].append(transformed_record)
        
        # Create indexes for common lookup fields
        primary_key = dataset.get('PrimaryKey', 'Id')
        for record in reference_data['records']:
            if primary_key in record:
                key_value = record[primary_key]
                if key_value:
                    if primary_key not in reference_data['indexes']:
                        reference_data['indexes'][primary_key] = {}
                    reference_data['indexes'][primary_key][key_value] = record
        
        # Calculate unique values for categorical fields
        for field in dataset.get('Fields', []):
            if field.get('Type') in ['dropdown', "radio", 'multi_dropdown']:
                field_name = field.get('Name', '')
                unique_values = set()
                for record in reference_data['records']:
                    if field_name in record and record[field_name]:
                        if isinstance(record[field_name], list):
                            unique_values.update(record[field_name])
                        else:
                            unique_values.add(record[field_name])
                reference_data['statistics']['unique_values'][field_name] = list(unique_values)
        
        logger.info(f"Transformed {len(records)} records with {len(reference_data['indexes'])} indexed fields")
        
        return reference_data
    
    def _create_schema(self, dataset: Dict[str, Any]) -> Dict[str, Any]:
        """Create schema definition from dataset.
        
        Args:
            dataset: Dataset definition
            
        Returns:
            Schema definition
        """
        schema = {
            'name': dataset.get('Name', 'Dataset'),
            'fields': [],
            'primary_key': dataset.get('PrimaryKey', 'Id'),
            'unique_fields': [],
            'required_fields': [],
            'foreign_keys': []
        }
        
        for field in dataset.get('Fields', []):
            field_def = {
                'name': field.get('Name', ''),
                'type': field.get('Type', "text"),
                'description': field.get('Description', ''),
                'required': field.get('Required', False),
                'unique': field.get('Unique', False),
                'default': field.get('DefaultValue')
            }
            
            schema['fields'].append(field_def)
            
            if field.get('Required'):
                schema['required_fields'].append(field['Name'])
            
            if field.get('Unique'):
                schema['unique_fields'].append(field['Name'])
            
            if field.get('ForeignKey'):
                schema['foreign_keys'].append({
                    'field': field['Name'],
                    'references': field['ForeignKey']
                })
        
        return schema
    
    def _transform_validations(self, validations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform dataset validations to Tallyfy rules.
        
        Args:
            validations: Dataset validation rules
            
        Returns:
            List of Tallyfy rules
        """
        rules = []
        
        for validation in validations:
            rule = {
                'name': validation.get('Name', 'Validation'),
                'description': validation.get('Description', ''),
                'trigger': {
                    'type': 'field_change',
                    'field': validation.get('Field', ''),
                    'event': 'on_change'
                },
                'actions': []
            }
            
            # Add validation action
            validation_type = validation.get('Type', 'custom')
            if validation_type == 'unique':
                rule['actions'].append({
                    'type': 'validate_unique',
                    'field': validation['Field'],
                    'error_message': f"{validation['Field']} must be unique"
                })
            elif validation_type == 'required':
                rule['actions'].append({
                    'type': 'validate_required',
                    'field': validation['Field'],
                    'error_message': f"{validation['Field']} is required"
                })
            elif validation_type == 'format':
                rule['actions'].append({
                    'type': 'validate_format',
                    'field': validation['Field'],
                    'pattern': validation.get('Pattern', ''),
                    'error_message': validation.get('ErrorMessage', 'Invalid format')
                })
            elif validation_type == 'range':
                rule['actions'].append({
                    'type': 'validate_range',
                    'field': validation['Field'],
                    'min': validation.get('Min'),
                    'max': validation.get('Max'),
                    'error_message': f"Value must be between {validation.get('Min')} and {validation.get('Max')}"
                })
            else:
                # Custom validation
                rule['actions'].append({
                    'type': 'custom_validation',
                    'script': validation.get('Script', ''),
                    'error_message': validation.get('ErrorMessage', 'Validation failed')
                })
            
            rules.append(rule)
        
        return rules
    
    def _create_data_operations(self, dataset: Dict[str, Any]) -> Dict[str, Any]:
        """Create data operation configurations.
        
        Args:
            dataset: Dataset definition
            
        Returns:
            Data operation configurations
        """
        return {
            'import': {
                'enabled': True,
                'formats': ['csv', 'excel', 'json'],
                'max_records': 10000,
                'field_mapping': {
                    field.get('Name', ''): field.get('Id', '')
                    for field in dataset.get('Fields', [])
                }
            },
            'export': {
                'enabled': True,
                'formats': ['csv', 'excel', 'json', 'pdf'],
                'max_records': 50000,
                'include_metadata': True
            },
            'sync': {
                'enabled': dataset.get('HasExternalSource', False),
                'source': dataset.get('ExternalSource', {}),
                'schedule': dataset.get('SyncSchedule', 'manual'),
                'last_sync': dataset.get('LastSyncTime')
            },
            'backup': {
                'enabled': True,
                'frequency': 'daily',
                'retention_days': 30
            }
        }
    
    def _extract_tags(self, dataset: Dict[str, Any]) -> List[str]:
        """Extract tags from dataset.
        
        Args:
            dataset: Kissflow dataset
            
        Returns:
            List of tags
        """
        tags = []
        
        # Add existing tags
        if dataset.get('Tags'):
            tags.extend(dataset['Tags'])
        
        # Add metadata tags
        tags.append('type:dataset')
        tags.append('source:kissflow')
        tags.append('data:reference')
        
        if dataset.get('Category'):
            tags.append(f"category:{dataset['Category']}")
        
        # Add usage tags
        if dataset.get('UsedFor'):
            for usage in dataset['UsedFor'].split(','):
                tags.append(f"used-for:{usage.strip().lower()}")
        
        return tags
    
    def create_lookup_field_mapping(self, dataset: Dict[str, Any]) -> Dict[str, Any]:
        """Create mapping for fields that reference this dataset.
        
        Args:
            dataset: Dataset definition
            
        Returns:
            Lookup field mapping configuration
        """
        return {
            'dataset_id': dataset.get('Id'),
            'dataset_name': dataset.get('Name'),
            'lookup_fields': {
                'display_field': dataset.get('DisplayField', 'Name'),
                'value_field': dataset.get('ValueField', 'Id'),
                'search_fields': dataset.get('SearchFields', ['Name']),
                'filter_fields': dataset.get('FilterFields', [])
            },
            'usage_instructions': """
To use this dataset as a lookup in other processes:
1. Create a dropdown field in the target process
2. Set the options to reference this dataset's records
3. Use the display_field for labels and value_field for values
4. Apply any necessary filters based on filter_fields
            """
        }