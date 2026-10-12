from app.utility.base_world import BaseWorld
from plugins.procedures.app.procedures_gui import ProceduresGUI
from plugins.procedures.app.procedures_api import ProceduresAPI

name = 'Procedures'
description = 'Enhanced Procedures Management Plugin - Unified view of all techniques and procedures'
address = '/plugin/procedures/gui'
access = BaseWorld.Access.RED


async def enable(services):
    """Enable the procedures plugin with proper GUI and API routes"""
    
    app = services.get('app_svc').application
    
    # Initialize the GUI and API handlers
    procedures_gui = ProceduresGUI(services, name, description)
    procedures_api = ProceduresAPI(services)
    
    # Static assets
    app.router.add_static('/procedures', 'plugins/procedures/static', append_version=True)
    
    # Main GUI routes
    app.router.add_route('GET', '/plugin/procedures/gui', procedures_gui.splash)
    app.router.add_route('GET', '/plugin/procedures/matrix', procedures_gui.matrix)
    
    # API routes for the plugin
    app.router.add_route('GET', '/plugin/procedures/api/procedures', procedures_api.get_procedures)
    app.router.add_route('GET', '/plugin/procedures/api/procedures/{procedure_id}', procedures_api.get_procedure)
    app.router.add_route('POST', '/plugin/procedures/api/procedures', procedures_api.create_procedure)
    app.router.add_route('PUT', '/plugin/procedures/api/procedures/{procedure_id}', procedures_api.update_procedure)
    app.router.add_route('DELETE', '/plugin/procedures/api/procedures/{procedure_id}', procedures_api.delete_procedure)
    app.router.add_route('POST', '/plugin/procedures/api/procedures/bulk-update', procedures_api.bulk_update_procedures)
    app.router.add_route('GET', '/plugin/procedures/api/tactic-stats', procedures_api.get_tactic_stats)
    app.router.add_route('GET', '/plugin/procedures/api/execution-history', procedures_api.get_execution_history)
    app.router.add_route('POST', '/plugin/procedures/api/save-execution', procedures_api.save_execution)
    
    # Override the native procedures route to redirect to our enhanced plugin
    async def redirect_to_enhanced_procedures(request):
        """Redirect native procedures to enhanced plugin"""
        return procedures_gui.splash(request)
    
    # Override the main /procedures route to use our enhanced interface
    app.router.add_route('GET', '/procedures', redirect_to_enhanced_procedures) 