"""
Instance Transformer
Transforms vendor instances/runs to Tallyfy runs
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class InstanceTransformer:
    """Transform vendor instances to Tallyfy format"""
    
    def __init__(self, ai_client=None):
        """Initialize instance transformer"""
        self.ai_client = ai_client
    
    def transform_instance(self, instance: Dict[str, Any]) -> Dict[str, Any]:
        """Transform a vendor instance to Tallyfy format"""
        try:
            tallyfy_instance = {
                'name': instance.get('name', 'Untitled Instance'),
                'template_id': instance.get('template_id', ''),
                'status': self._transform_status(instance),
                'created_at': instance.get('created_at', ''),
                'updated_at': instance.get('updated_at', ''),
                'completed_at': instance.get('completed_at'),
                'data': self._transform_instance_data(instance),
                'steps': self._transform_instance_steps(instance),
                'vendor_metadata': {
                    'original_id': instance.get('id', ''),
                    'original_status': instance.get('status', ''),
                    'original_data': instance
                }
            }
            
            return tallyfy_instance
            
        except Exception as e:
            logger.error(f"Error transforming instance: {e}")
            return self._create_fallback_instance(instance)
    
    def _transform_status(self, instance: Dict[str, Any]) -> str:
        """Transform instance status"""
        status = instance.get('status', '').lower()
        
        status_map = {
            'active': 'in_progress',
            'running': 'in_progress',
            'in_progress': 'in_progress',
            'completed': 'completed',
            'done': 'completed',
            'finished': 'completed',
            'cancelled': 'cancelled',
            'canceled': 'cancelled',
            'paused': 'paused',
            'pending': 'pending',
            'draft': 'draft'
        }
        
        return status_map.get(status, 'in_progress')
    
    def _transform_instance_data(self, instance: Dict[str, Any]) -> Dict[str, Any]:
        """Transform instance data/responses"""
        # Override in vendor-specific implementation
        return instance.get('data', instance.get('responses', {}))
    
    def _transform_instance_steps(self, instance: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Transform instance steps"""
        steps = []
        vendor_steps = instance.get('steps', instance.get('tasks', []))
        
        for step in vendor_steps:
            steps.append({
                'name': step.get('name', ''),
                'status': self._transform_status(step),
                'completed_at': step.get('completed_at'),
                'completed_by': step.get('completed_by'),
                'data': step.get('data', {})
            })
        
        return steps
    
    def _create_fallback_instance(self, instance: Dict[str, Any]) -> Dict[str, Any]:
        """Create fallback instance when transformation fails"""
        return {
            'name': str(instance.get('name', 'Untitled Instance')),
            'status': 'pending',
            'vendor_metadata': {'original_data': instance}
        }
