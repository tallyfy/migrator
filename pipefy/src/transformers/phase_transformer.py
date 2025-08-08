"""
Phase to Step Transformer
Transforms Pipefy phases (containers) to Tallyfy step groups (sequential)
This is the most complex transformation due to paradigm differences
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import hashlib

logger = logging.getLogger(__name__)


class PhaseToStepTransformer:
    """
    Transform Pipefy phases to Tallyfy step groups
    
    Critical: Pipefy phases are containers where cards exist, while
    Tallyfy steps are sequential tasks that complete. This requires
    creative transformation to maintain workflow logic.
    """
    
    def __init__(self, id_mapper=None):
        """
        Initialize phase transformer
        
        Args:
            id_mapper: Optional ID mapping utility
        """
        self.id_mapper = id_mapper
        self.transformation_stats = {
            'total': 0,
            'successful': 0,
            'failed': 0,
            'warnings': []
        }
    
    def transform_pipe_to_checklist(self, pipefy_pipe: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform a Pipefy pipe to a Tallyfy checklist template
        
        Args:
            pipefy_pipe: Pipefy pipe object
            
        Returns:
            Tallyfy checklist object with transformed phases as steps
        """
        self.transformation_stats['total'] += 1
        
        try:
            pipe_id = pipefy_pipe.get('id', '')
            
            # Generate Tallyfy checklist ID
            tallyfy_id = self._generate_tallyfy_id('chk', pipe_id)
            
            # Transform basic pipe properties
            tallyfy_checklist = {
                'id': tallyfy_id,
                'title': pipefy_pipe.get('name', 'Untitled Pipe'),
                'description': pipefy_pipe.get('description', ''),
                'status': 'active',
                'is_template': True,
                'is_public': pipefy_pipe.get('public', False),
                'icon': self._map_icon(pipefy_pipe.get('icon')),
                'color': pipefy_pipe.get('color', '#4A90E2'),
                'created_at': pipefy_pipe.get('created_at'),
                'updated_at': pipefy_pipe.get('updated_at'),
                'external_ref': pipe_id,
                'external_source': 'pipefy',
                
                # Configuration
                'config': {
                    'allow_public_submission': pipefy_pipe.get('anyone_can_create_card', False),
                    'sla_minutes': self._calculate_sla_minutes(
                        pipefy_pipe.get('expiration_time_by_unit'),
                        pipefy_pipe.get('expiration_unit')
                    ),
                    'sequential': False,  # Pipefy phases are not strictly sequential
                    'allow_comments': True,
                    'allow_attachments': True,
                    'pipefy_metadata': {
                        'original_pipe_id': pipe_id,
                        'phase_count': len(pipefy_pipe.get('phases', [])),
                        'has_start_form': bool(pipefy_pipe.get('start_form_fields', []))
                    }
                },
                
                # Transform phases to steps
                'steps': self._transform_phases_to_steps(pipefy_pipe.get('phases', [])),
                
                # Transform start form fields to initial field
                'field': self._transform_start_form_fields(pipefy_pipe.get('start_form_fields', [])),
                
                # Labels to tags
                'tags': self._transform_labels(pipefy_pipe.get('labels', [])),
                
                # Permissions
                'permissions': self._transform_permissions(pipefy_pipe.get('members', []))
            }
            
            # Store ID mapping
            if self.id_mapper:
                self.id_mapper.add_mapping(pipe_id, tallyfy_id, 'multiselect')
            
            self.transformation_stats['successful'] += 1
            logger.info(f"Transformed pipe '{pipefy_pipe.get('name')}' to checklist")
            
            return tallyfy_checklist
            
        except Exception as e:
            self.transformation_stats['failed'] += 1
            logger.error(f"Failed to transform pipe: {e}")
            raise
    
    def _transform_phases_to_steps(self, pipefy_phases: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Transform Pipefy phases to Tallyfy step groups
        
        Each phase becomes a group of 3 steps:
        1. Entry notification (card enters phase)
        2. Phase work (complete fields, tasks)
        3. Exit decision (move to next phase)
        
        Args:
            pipefy_phases: List of Pipefy phase objects
            
        Returns:
            List of Tallyfy steps
        """
        tallyfy_steps = []
        
        # Sort phases by index to maintain order
        sorted_phases = sorted(pipefy_phases, key=lambda p: p.get('index', 0))
        
        for phase_index, phase in enumerate(sorted_phases):
            phase_id = phase.get('id', '')
            phase_name = phase.get('name', f'Phase {phase_index + 1}')
            is_done_phase = phase.get('done', False)
            
            # Generate base position (multiply by 100 to leave room for sub-steps)
            base_position = phase_index * 100
            
            # Step 1: Entry notification
            entry_step = {
                'id': self._generate_tallyfy_id('stp', f"{phase_id}_entry"),
                'title': f"📥 Enter {phase_name}",
                'description': f"Card has entered the {phase_name} phase",
                'task_type': 'notification',
                'position': base_position + 10,
                'is_required': False,
                'is_blocking': False,
                'external_ref': f"{phase_id}_entry",
                'config': {
                    'auto_complete': True,
                    'notification_message': f"Process has moved to {phase_name}",
                    'phase_metadata': {
                        'phase_id': phase_id,
                        'phase_name': phase_name,
                        'is_entry': True
                    }
                }
            }
            tallyfy_steps.append(entry_step)
            
            # Step 2: Phase work (fields and tasks)
            if phase.get('fields'):
                work_step = {
                    'id': self._generate_tallyfy_id('stp', f"{phase_id}_work"),
                    'title': f"📝 Complete {phase_name}",
                    'description': phase.get('description', f"Complete all tasks in {phase_name}"),
                    'task_type': 'form',
                    'position': base_position + 20,
                    'is_required': True,
                    'is_blocking': True,  # Must complete before moving on
                    'external_ref': f"{phase_id}_work",
                    'field': self._transform_phase_fields(phase.get('fields', [])),
                    'config': {
                        'phase_metadata': {
                            'phase_id': phase_id,
                            'phase_name': phase_name,
                            'cards_count': phase.get('cards_count', 0),
                            'is_work': True
                        }
                    }
                }
                tallyfy_steps.append(work_step)
            
            # Step 3: Exit decision (unless it's the done phase)
            if not is_done_phase:
                # Determine possible next phases
                next_phases = phase.get('cards_can_be_moved_to_phases', [])
                
                exit_step = {
                    'id': self._generate_tallyfy_id('stp', f"{phase_id}_exit"),
                    'title': f"🔀 Route from {phase_name}",
                    'description': "Decide where to route this process next",
                    'task_type': 'decision',
                    'position': base_position + 30,
                    'is_required': True,
                    'is_blocking': True,
                    'external_ref': f"{phase_id}_exit",
                    'config': {
                        'decision_type': 'single_choice',
                        'options': self._create_routing_options(next_phases, sorted_phases),
                        'phase_metadata': {
                            'phase_id': phase_id,
                            'phase_name': phase_name,
                            'is_exit': True
                        }
                    }
                }
                tallyfy_steps.append(exit_step)
            else:
                # Done phase - add completion step
                completion_step = {
                    'id': self._generate_tallyfy_id('stp', f"{phase_id}_complete"),
                    'title': f"✅ Complete Process",
                    'description': f"Process completed in {phase_name}",
                    'task_type': 'approval',
                    'position': base_position + 30,
                    'is_required': True,
                    'is_blocking': False,
                    'external_ref': f"{phase_id}_complete",
                    'config': {
                        'auto_complete': False,
                        'completion_message': "Process has been completed",
                        'phase_metadata': {
                            'phase_id': phase_id,
                            'phase_name': phase_name,
                            'is_done': True
                        }
                    }
                }
                tallyfy_steps.append(completion_step)
            
            # Store phase mapping
            if self.id_mapper:
                # Map the entire phase group
                phase_group_id = self._generate_tallyfy_id('grp', phase_id)
                self.id_mapper.add_mapping(phase_id, phase_group_id, 'phase_group')
        
        return tallyfy_steps
    
    def _transform_phase_fields(self, pipefy_fields: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Transform Pipefy phase fields to Tallyfy field
        
        Args:
            pipefy_fields: List of Pipefy field objects
            
        Returns:
            List of Tallyfy field objects
        """
        from .field_transformer import FieldTransformer
        
        field_transformer = FieldTransformer(self.id_mapper)
        tallyfy_captures = []
        
        for field in pipefy_fields:
            try:
                transformed = field_transformer.transform_field(field)
                tallyfy_captures.append(transformed)
            except Exception as e:
                logger.warning(f"Failed to transform field {field.get('id')}: {e}")
                self.transformation_stats['warnings'].append({
                    'field_id': field.get('id'),
                    'error': str(e)
                })
        
        return tallyfy_captures
    
    def _transform_start_form_fields(self, start_fields: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Transform Pipefy start form fields to Tallyfy initial field
        
        Args:
            start_fields: List of start form field objects
            
        Returns:
            List of Tallyfy field objects
        """
        if not start_fields:
            return []
        
        # Use field transformer for consistency
        from .field_transformer import FieldTransformer
        
        field_transformer = FieldTransformer(self.id_mapper)
        field = []
        
        for field in start_fields:
            try:
                field = field_transformer.transform_field(field)
                # Mark as start form field
                field['metadata'] = field.get('metadata', {})
                field['metadata']['is_start_form'] = True
                field.append(field)
            except Exception as e:
                logger.warning(f"Failed to transform start form field: {e}")
        
        return field
    
    def _create_routing_options(self, next_phases: List[Dict], all_phases: List[Dict]) -> List[Dict[str, Any]]:
        """
        Create routing options for phase exit decisions
        
        Args:
            next_phases: Phases that cards can move to
            all_phases: All phases in the pipe
            
        Returns:
            List of decision options
        """
        options = []
        
        # If no specific next phases defined, allow movement to any phase
        if not next_phases:
            next_phases = all_phases
        
        for phase in next_phases:
            phase_name = phase.get('name', 'Unknown Phase')
            phase_id = phase.get('id', '')
            
            # Find the corresponding step group in Tallyfy
            step_group_id = None
            if self.id_mapper:
                step_group_id = self.id_mapper.get_tallyfy_id(phase_id, 'phase_group')
            
            options.append({
                'label': f"Move to {phase_name}",
                'value': step_group_id or phase_id,
                'action': 'jump_to_step',
                'target_step': step_group_id,
                'metadata': {
                    'original_phase_id': phase_id,
                    'phase_name': phase_name
                }
            })
        
        # Always add option to complete/cancel
        options.extend([
            {
                'label': "Complete Process",
                'value': 'complete',
                'action': 'complete_process',
                'metadata': {'final_action': True}
            },
            {
                'label': "Cancel Process",
                'value': 'cancel',
                'action': 'cancel_process',
                'metadata': {'final_action': True}
            }
        ])
        
        return options
    
    def _transform_labels(self, labels: List[Dict[str, Any]]) -> List[str]:
        """
        Transform Pipefy labels to Tallyfy tags
        
        Args:
            labels: List of label objects
            
        Returns:
            List of tag strings
        """
        tags = []
        
        for label in labels:
            tag = label.get('name', '')
            if tag:
                tags.append(tag)
                
                # Store label mapping
                if self.id_mapper:
                    label_id = label.get('id')
                    if label_id:
                        self.id_mapper.add_mapping(label_id, tag, 'label')
        
        return tags
    
    def _transform_permissions(self, members: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Transform Pipefy pipe members to Tallyfy permissions
        
        Args:
            members: List of pipe members
            
        Returns:
            Permissions dictionary
        """
        permissions = {
            'visibility': 'organization',  # Default to organization visibility
            'can_edit': [],
            'can_run': [],
            'can_view': [],
            'can_delete': []
        }
        
        for member in members:
            user = member.get('user', {})
            role = member.get('role_name', 'member')
            user_id = user.get('id')
            
            if not user_id:
                continue
            
            # Map user ID if we have a mapper
            if self.id_mapper:
                tallyfy_user_id = self.id_mapper.get_tallyfy_id(user_id, 'user')
                if tallyfy_user_id:
                    user_id = tallyfy_user_id
            
            # Map roles to permissions
            if role in ['admin', 'Admin']:
                permissions['can_edit'].append(user_id)
                permissions['can_run'].append(user_id)
                permissions['can_view'].append(user_id)
                permissions['can_delete'].append(user_id)
            elif role in ['member', 'Member', 'Normal']:
                permissions['can_run'].append(user_id)
                permissions['can_view'].append(user_id)
            else:  # Guest or limited access
                permissions['can_view'].append(user_id)
        
        return permissions
    
    def _calculate_sla_minutes(self, time_value: Optional[int], time_unit: Optional[str]) -> Optional[int]:
        """
        Calculate SLA in minutes from Pipefy expiration settings
        
        Args:
            time_value: Numeric time value
            time_unit: Time unit (hours, days, months)
            
        Returns:
            SLA in minutes
        """
        if not time_value or not time_unit:
            return None
        
        unit_multipliers = {
            'minutes': 1,
            'minute': 1,
            'hours': 60,
            'hour': 60,
            'days': 60 * 24,
            'day': 60 * 24,
            'weeks': 60 * 24 * 7,
            'week': 60 * 24 * 7,
            'months': 60 * 24 * 30,
            'month': 60 * 24 * 30
        }
        
        multiplier = unit_multipliers.get(time_unit.lower(), 60)
        return int(time_value * multiplier)
    
    def _map_icon(self, pipefy_icon: Optional[str]) -> str:
        """
        Map Pipefy icon to Tallyfy icon
        
        Args:
            pipefy_icon: Pipefy icon name
            
        Returns:
            Tallyfy icon name
        """
        if not pipefy_icon:
            return 'clipboard'
        
        # Basic icon mapping (extend as needed)
        icon_mapping = {
            'pipe': 'clipboard',
            'cart': 'shopping-cart',
            'hr': 'users',
            'it': 'computer',
            'marketing': 'megaphone',
            'sales': 'dollar-sign',
            'finance': 'calculator',
            'support': 'life-ring',
            'legal': 'balance-scale',
            'operations': 'cogs'
        }
        
        return icon_mapping.get(pipefy_icon.lower(), 'clipboard')
    
    def _generate_tallyfy_id(self, prefix: str, source_id: str) -> str:
        """
        Generate a Tallyfy-compatible ID
        
        Args:
            prefix: ID prefix
            source_id: Source ID for consistent hashing
            
        Returns:
            32-character ID
        """
        hash_input = f"{prefix}_{source_id}"
        hash_value = hashlib.md5(hash_input.encode()).hexdigest()
        
        if prefix:
            prefix_len = min(len(prefix), 8)
            return prefix[:prefix_len] + hash_value[:32-prefix_len]
        
        return hash_value[:32]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get transformation statistics"""
        return self.transformation_stats.copy()