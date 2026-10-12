import logging
from typing import Dict, List, Any, Optional


class ProcedureService:
    def __init__(self, services):
        self.services = services
        self.data_svc = services.get('data_svc')
        self.log = logging.getLogger('procedures_svc')
        
        # Cache for loaded procedures
        self._procedures_cache = None
        
    async def get_procedures(self) -> List[Dict[str, Any]]:
        """Get all available procedures/abilities from Caldera's data service"""
        try:
            # Get all abilities from Caldera's data service
            abilities = await self.data_svc.locate('abilities')
            
        procedures = []
            for ability in abilities:
                try:
                    # Convert ability to procedure format
                    procedure_data = {
                        'procedure_id': ability.ability_id,
                        'id': ability.ability_id,
                        'name': ability.name,
                        'description': ability.description or 'No description available',
                        'tactic': ability.tactic or 'unknown',
                        'technique_id': ability.technique_id or '',
                        'technique_name': ability.technique_name or '',
                        'executors': [],
                        'plugin': getattr(ability, 'plugin', 'unknown'),
                        'platforms': [],
                        'repeatable': getattr(ability, 'repeatable', True),
                        'singleton': getattr(ability, 'singleton', False),
                        'buckets': getattr(ability, 'buckets', []),
                        'access': getattr(ability, 'access', {}),
                        'requirements': []
                    }
                    
                    # Process executors
                    if hasattr(ability, 'executors') and ability.executors:
                        for executor in ability.executors:
                            executor_data = {
                                'name': executor.name,
                                'platform': executor.platform,
                                'command': executor.command,
                                'cleanup': getattr(executor, 'cleanup', []),
                                'timeout': getattr(executor, 'timeout', 60),
                                'parsers': getattr(executor, 'parsers', []),
                                'payloads': getattr(executor, 'payloads', [])
                            }
                            procedure_data['executors'].append(executor_data)
                            
                            # Add platform to platforms list if not already there
                            if executor.platform not in procedure_data['platforms']:
                                procedure_data['platforms'].append(executor.platform)
                    
                    # Process requirements
                    if hasattr(ability, 'requirements') and ability.requirements:
                        for req in ability.requirements:
                            req_data = {
                                'module': getattr(req, 'module', ''),
                                'relationship_match': getattr(req, 'relationship_match', [])
                            }
                            procedure_data['requirements'].append(req_data)
                    
                    procedures.append(procedure_data)
                    
                    except Exception as e:
                    self.log.warning(f"Failed to process ability {getattr(ability, 'ability_id', 'unknown')}: {e}")
                    continue
                    
            self.log.info(f"Loaded {len(procedures)} procedures from Caldera data service")
            self._procedures_cache = procedures
            return procedures
                        
        except Exception as e:
            self.log.error(f"Failed to load procedures from data service: {e}")
            return []
        
    async def get_procedure_by_id(self, procedure_id: str) -> Optional[Dict[str, Any]]:
        """Get specific procedure by ID"""
        procedures = await self.get_procedures()
        return next((p for p in procedures if p['procedure_id'] == procedure_id), None)
        
    async def get_procedures_by_tactic(self, tactic: str) -> List[Dict[str, Any]]:
        """Get procedures filtered by tactic"""
        procedures = await self.get_procedures()
        return [p for p in procedures if p['tactic'].lower() == tactic.lower()]
        
    async def create_procedure(self, procedure_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new procedure"""
        try:
            # For now, just return the data with an ID
            # In a full implementation, this would create an actual ability in Caldera
            import uuid
            procedure_data['procedure_id'] = procedure_data.get('procedure_id', str(uuid.uuid4()))
            procedure_data['id'] = procedure_data['procedure_id']
            
            self.log.info(f"Created procedure: {procedure_data['name']}")
            
            # Clear cache to force reload
            self._procedures_cache = None
            
            return procedure_data
            
        except Exception as e:
            self.log.error(f"Failed to create procedure: {e}")
            raise ValueError(f"Failed to create procedure: {e}")
            
    async def update_procedure(self, procedure_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update an existing procedure"""
        try:
            procedure = await self.get_procedure_by_id(procedure_id)
            if not procedure:
                return None
                
            # Update the procedure data
            procedure.update(update_data)
            
            self.log.info(f"Updated procedure: {procedure_id}")
            
            # Clear cache to force reload
            self._procedures_cache = None
            
            return procedure
            
        except Exception as e:
            self.log.error(f"Failed to update procedure {procedure_id}: {e}")
            raise ValueError(f"Failed to update procedure: {e}")
            
    async def delete_procedure(self, procedure_id: str) -> bool:
        """Delete a procedure"""
        try:
            procedure = await self.get_procedure_by_id(procedure_id)
            if not procedure:
                return False
                
            self.log.info(f"Deleted procedure: {procedure_id}")
            
            # Clear cache to force reload
            self._procedures_cache = None
            
            return True
            
        except Exception as e:
            self.log.error(f"Failed to delete procedure {procedure_id}: {e}")
            return False
            
    async def bulk_update_procedures(self, procedure_ids: List[str], update_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Bulk update multiple procedures"""
        updated_procedures = []
        
        try:
            for procedure_id in procedure_ids:
                procedure = await self.update_procedure(procedure_id, update_data)
                if procedure:
                    updated_procedures.append(procedure)
                    
            self.log.info(f"Bulk updated {len(updated_procedures)} procedures")
            return updated_procedures
            
        except Exception as e:
            self.log.error(f"Failed to bulk update procedures: {e}")
            raise ValueError(f"Failed to bulk update procedures: {e}")
        
    async def get_procedure_options(self, procedure_id: str) -> List[Dict[str, Any]]:
        """Get available command options for a procedure"""
        # This would ideally parse the actual procedure configuration
        # For now, return common options structure
        return [
            {'name': 'format', 'description': 'Output format', 'options': ['json', 'csv'], 'default': 'json'},
            {'name': 'verbose', 'description': 'Verbose output', 'type': 'boolean', 'default': False},
            {'name': 'log', 'description': 'Enable logging', 'type': 'boolean', 'default': False}
        ]
        
    async def build_command(self, procedure_id: str, options: Dict[str, Any]) -> str:
        """Build command string with selected options"""
        procedure = await self.get_procedure_by_id(procedure_id)
        if not procedure or not procedure.get('executors'):
            return ""
            
        # Get first available command
        first_executor = procedure['executors'][0]
        base_command = first_executor.get('command', '')
        
        # Parse options and build command
        option_parts = []
        for key, value in options.items():
            if value is True:
                option_parts.append(f"--{key}")
            elif value and value != "":
                option_parts.append(f"--{key} {value}")
                
        if option_parts:
            return f"{base_command} {' '.join(option_parts)}"
            
        return base_command
        
    async def get_execution_history(self) -> List[Dict[str, Any]]:
        """Get history of executed procedures"""
        # This would typically come from operation logs
        # For now, return empty list
        return []
        
    async def save_execution(self, procedure_id: str, command: str, result: str) -> bool:
        """Save execution result"""
        try:
            # This would save to operation logs
            self.log.info(f"Executed procedure {procedure_id}: {command}")
            return True
        except Exception as e:
            self.log.error(f"Failed to save execution: {e}")
            return False
            
    async def get_tactic_stats(self) -> Dict[str, int]:
        """Get count of procedures by tactic"""
        procedures = await self.get_procedures()
        stats = {}
        for procedure in procedures:
            tactic = procedure['tactic']
            stats[tactic] = stats.get(tactic, 0) + 1
        return stats
