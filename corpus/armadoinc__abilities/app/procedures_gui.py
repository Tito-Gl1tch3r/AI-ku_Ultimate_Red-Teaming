import logging

from aiohttp_jinja2 import template

from app.service.auth_svc import for_all_public_methods, check_authorization
from app.utility.base_world import BaseWorld
from plugins.procedures.app.procedures_svc import ProcedureService


@for_all_public_methods(check_authorization)
class ProceduresGUI(BaseWorld):

    def __init__(self, services, name, description):
        self.auth_svc = services.get('auth_svc')
        self.data_svc = services.get('data_svc')
        self.procedures_svc = ProcedureService(services)
        self.log = logging.getLogger('procedures_gui') 

    @template('procedures.html')
    async def splash(self, request):
        """Main procedures page with table of all procedures"""
        try:
            procedures = await self.procedures_svc.get_procedures()
            tactic_stats = await self.procedures_svc.get_tactic_stats()
            
            return dict(
                procedures=procedures, 
                tactic_stats=tactic_stats,
                total_procedures=len(procedures)
            )
        except Exception as e:
            self.log.error(f"Error loading procedures: {e}")
            return dict(
                procedures=[], 
                tactic_stats={},
                total_procedures=0,
                error=str(e)
            )

    @template('matrix.html')  
    async def matrix(self, request):
        """MITRE ATT&CK Matrix View"""
        try:
            procedures = await self.procedures_svc.get_procedures()
            
            # Organize procedures by tactic
            tactics_data = {}
            for procedure in procedures:
                tactic = procedure['tactic']
                if tactic not in tactics_data:
                    tactics_data[tactic] = []
                tactics_data[tactic].append({
                    'id': procedure['id'],
                    'name': procedure['name'],
                    'technique_id': procedure['technique_id'],
                    'technique_name': procedure['technique_name'],
                    'description': procedure['description']
                })
            
            return dict(tactics_data=tactics_data)
        except Exception as e:
            self.log.error(f"Error loading matrix: {e}")
            return dict(tactics_data={}, error=str(e))

    async def procedures(self, request):
        """API endpoint to get all procedures from the procedures plugin"""
        try:
            procedures = await self.procedures_svc.get_procedures()
            return self.auth_svc.web_response(content=procedures)
        except Exception as e:
            self.log.error(f"Error in procedures API: {e}")
            return self.auth_svc.web_response(content=[], status=500) 