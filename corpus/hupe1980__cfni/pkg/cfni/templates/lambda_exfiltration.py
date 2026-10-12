def cfni(synth):
    node_js_injection = """{{.NodeJSCodeInjection}}"""
    python_injection = """{{.PythonCodeInjection}}"""

    for assembly in synth.assemblies:
        for stack in assembly.stacks:
            for func in stack.lambda_functions:
                if not func.clean_runtime in ["nodejs", "python"] or func.is_inline():
                    continue

                handler = func.get_handler()

                injection = node_js_injection
                if func.clean_runtime == "python":
                    injection = python_injection    
                
                if injection in handler:
                    continue
                
                handler = f"{injection}{handler}"

                synth.add_update(func.absolute_handler_filename, handler)

