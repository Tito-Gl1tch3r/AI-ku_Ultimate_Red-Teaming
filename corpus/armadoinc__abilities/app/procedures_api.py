import json
from aiohttp import web

from app.service.auth_svc import for_all_public_methods, check_authorization
from plugins.procedures.app.procedures_svc import ProcedureService


@for_all_public_methods(check_authorization)
class ProceduresAPI:

    def __init__(self, services):
        self.services = services
        self.auth_svc = self.services.get('auth_svc')
        self.data_svc = self.services.get('data_svc')
        self.procedures_svc = ProcedureService(services)

    async def get_procedures(self, request):
        """Get all available procedures"""
        try:
            tactic_filter = request.query.get('tactic')
            
            if tactic_filter:
                procedures = await self.procedures_svc.get_procedures_by_tactic(tactic_filter)
            else:
                procedures = await self.procedures_svc.get_procedures()
                
            return web.json_response({
                'status': 'success',
                'data': procedures,
                'total': len(procedures)
            })
        except Exception as e:
            return web.json_response({
                'status': 'error',
                'message': str(e)
            }, status=500)

    async def get_procedure(self, request):
        """Get specific procedure by ID"""
        try:
            procedure_id = request.match_info['procedure_id']
            procedure = await self.procedures_svc.get_procedure_by_id(procedure_id)
            
            if not procedure:
                return web.json_response({
                    'status': 'error',
                    'message': 'Procedure not found'
                }, status=404)
                
            return web.json_response({
                'status': 'success',
                'data': procedure
            })
        except Exception as e:
            return web.json_response({
                'status': 'error',
                'message': str(e)
            }, status=500)

    async def create_procedure(self, request):
        """Create a new procedure"""
        try:
            data = await request.json()
            
            # Validate required fields
            required_fields = ['name', 'description', 'tactic', 'technique_id', 'technique_name']
            for field in required_fields:
                if not data.get(field):
                    return web.json_response({
                        'status': 'error',
                        'message': f'{field} is required'
                    }, status=400)
            
            procedure = await self.procedures_svc.create_procedure(data)
            
            return web.json_response({
                'status': 'success',
                'data': procedure,
                'message': 'Procedure created successfully'
            }, status=201)
        except ValueError as e:
            return web.json_response({
                'status': 'error',
                'message': str(e)
            }, status=400)
        except Exception as e:
            return web.json_response({
                'status': 'error',
                'message': str(e)
            }, status=500)

    async def update_procedure(self, request):
        """Update an existing procedure"""
        try:
            procedure_id = request.match_info['procedure_id']
            data = await request.json()
            
            procedure = await self.procedures_svc.update_procedure(procedure_id, data)
            
            if not procedure:
                return web.json_response({
                    'status': 'error',
                    'message': 'Procedure not found'
                }, status=404)
                
            return web.json_response({
                'status': 'success',
                'data': procedure,
                'message': 'Procedure updated successfully'
            })
        except ValueError as e:
            return web.json_response({
                'status': 'error',
                'message': str(e)
            }, status=400)
        except Exception as e:
            return web.json_response({
                'status': 'error',
                'message': str(e)
            }, status=500)

    async def delete_procedure(self, request):
        """Delete a procedure"""
        try:
            procedure_id = request.match_info['procedure_id']
            
            success = await self.procedures_svc.delete_procedure(procedure_id)
            
            if not success:
                return web.json_response({
                    'status': 'error',
                    'message': 'Procedure not found or could not be deleted'
                }, status=404)
                
            return web.json_response({
                'status': 'success',
                'message': 'Procedure deleted successfully'
            })
        except Exception as e:
            return web.json_response({
                'status': 'error',
                'message': str(e)
            }, status=500)

    async def bulk_update_procedures(self, request):
        """Bulk update multiple procedures"""
        try:
            data = await request.json()
            procedure_ids = data.get('procedure_ids', [])
            update_data = data.get('update_data', {})
            
            if not procedure_ids:
                return web.json_response({
                    'status': 'error',
                    'message': 'procedure_ids is required'
                }, status=400)
                
            updated_procedures = await self.procedures_svc.bulk_update_procedures(procedure_ids, update_data)
            
            return web.json_response({
                'status': 'success',
                'data': updated_procedures,
                'message': f'Updated {len(updated_procedures)} procedures'
            })
        except Exception as e:
            return web.json_response({
                'status': 'error',
                'message': str(e)
            }, status=500)

    async def create_procedure(self, request):
        """Create a new procedure"""
        try:
            data = await request.json()
            
            # Validate required fields
            required_fields = ['name', 'description', 'tactic', 'technique_id', 'technique_name']
            for field in required_fields:
                if not data.get(field):
                    return web.json_response({
                        'status': 'error',
                        'message': f'{field} is required'
                    }, status=400)
            
            procedure = await self.procedures_svc.create_procedure(data)
            
            return web.json_response({
                'status': 'success',
                'data': procedure,
                'message': 'Procedure created successfully'
            }, status=201)
        except ValueError as e:
            return web.json_response({
                'status': 'error',
                'message': str(e)
            }, status=400)
        except Exception as e:
            return web.json_response({
                'status': 'error',
                'message': str(e)
            }, status=500)

    async def update_procedure(self, request):
        """Update an existing procedure"""
        try:
            procedure_id = request.match_info['procedure_id']
            data = await request.json()
            
            procedure = await self.procedures_svc.update_procedure(procedure_id, data)
            
            if not procedure:
                return web.json_response({
                    'status': 'error',
                    'message': 'Procedure not found'
                }, status=404)
                
            return web.json_response({
                'status': 'success',
                'data': procedure,
                'message': 'Procedure updated successfully'
            })
        except ValueError as e:
            return web.json_response({
                'status': 'error',
                'message': str(e)
            }, status=400)
        except Exception as e:
            return web.json_response({
                'status': 'error',
                'message': str(e)
            }, status=500)

    async def delete_procedure(self, request):
        """Delete a procedure"""
        try:
            procedure_id = request.match_info['procedure_id']
            
            success = await self.procedures_svc.delete_procedure(procedure_id)
            
            if not success:
                return web.json_response({
                    'status': 'error',
                    'message': 'Procedure not found or could not be deleted'
                }, status=404)
                
            return web.json_response({
                'status': 'success',
                'message': 'Procedure deleted successfully'
            })
        except Exception as e:
            return web.json_response({
                'status': 'error',
                'message': str(e)
            }, status=500)

    async def bulk_update_procedures(self, request):
        """Bulk update multiple procedures"""
        try:
            data = await request.json()
            procedure_ids = data.get('procedure_ids', [])
            update_data = data.get('update_data', {})
            
            if not procedure_ids:
                return web.json_response({
                    'status': 'error',
                    'message': 'procedure_ids is required'
                }, status=400)
                
            updated_procedures = await self.procedures_svc.bulk_update_procedures(procedure_ids, update_data)
            
            return web.json_response({
                'status': 'success',
                'data': updated_procedures,
                'message': f'Updated {len(updated_procedures)} procedures'
            })
        except Exception as e:
            return web.json_response({
                'status': 'error',
                'message': str(e)
            }, status=500)

    async def get_procedure_options(self, request):
        """Get available options for a procedure"""
        try:
            procedure_id = request.match_info['procedure_id']
            options = await self.procedures_svc.get_procedure_options(procedure_id)
            
            return web.json_response({
                'status': 'success',
                'data': options
            })
        except Exception as e:
            return web.json_response({
                'status': 'error',
                'message': str(e)
            }, status=500)

    async def build_command(self, request):
        """Build command with selected options"""
        try:
            data = await request.json()
            procedure_id = data.get('procedure_id')
            options = data.get('options', {})
            
            if not procedure_id:
                return web.json_response({
                    'status': 'error',
                    'message': 'procedure_id is required'
                }, status=400)
                
            command = await self.procedures_svc.build_command(procedure_id, options)
            
            return web.json_response({
                'status': 'success',
                'data': {
                    'command': command,
                    'procedure_id': procedure_id,
                    'options': options
                }
            })
        except Exception as e:
            return web.json_response({
                'status': 'error',
                'message': str(e)
            }, status=500)

    async def get_tactic_stats(self, request):
        """Get statistics by tactic"""
        try:
            stats = await self.procedures_svc.get_tactic_stats()
            
            return web.json_response({
                'status': 'success',
                'data': stats
            })
        except Exception as e:
            return web.json_response({
                'status': 'error',
                'message': str(e)
            }, status=500)

    async def get_execution_history(self, request):
        """Get execution history"""
        try:
            history = await self.procedures_svc.get_execution_history()
            
            return web.json_response({
                'status': 'success',
                'data': history
            })
        except Exception as e:
            return web.json_response({
                'status': 'error',
                'message': str(e)
            }, status=500)

    async def save_execution(self, request):
        """Save execution result"""
        try:
            data = await request.json()
            procedure_id = data.get('procedure_id')
            command = data.get('command')
            result = data.get('result', '')
            
            if not procedure_id or not command:
                return web.json_response({
                    'status': 'error',
                    'message': 'procedure_id and command are required'
                }, status=400)
                
            success = await self.procedures_svc.save_execution(procedure_id, command, result)
            
            return web.json_response({
                'status': 'success' if success else 'error',
                'message': 'Execution saved' if success else 'Failed to save execution'
            })
        except Exception as e:
            return web.json_response({
                'status': 'error',
                'message': str(e)
            }, status=500)
