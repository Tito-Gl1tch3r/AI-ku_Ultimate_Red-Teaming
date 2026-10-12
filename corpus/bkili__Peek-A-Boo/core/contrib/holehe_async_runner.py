# core/contrib/holehe_runner.py
import importlib
import pkgutil
import traceback
import trio
import httpx


def get_all_holehe_modules(package_path, base_import_path):
    for _, modname, ispkg in pkgutil.iter_modules(package_path):
        full_import = f"{base_import_path}.{modname}"
        if ispkg:
            subpkg = importlib.import_module(full_import)
            yield from get_all_holehe_modules(subpkg.__path__, full_import)
        else:
            yield full_import, modname


async def run_holehe_modules(
    email, module_base, out, debug_level=0, progress_bar_callback=None
):
    """
    Runs all async functions under a package path,
    (like holehe.modules) in parallel using trio.

    :param email: Email address to check
    :param module_base: Base import path string (e.g., "holehe.modules")
    :param out: List to collect results
    :param debug_level: 0 = silent, 1 = errors only, 2 = full traceback
    :param progress_bar_callback: function(completed, total) to update UI
    """
    try:
        root = importlib.import_module(module_base)
    except ImportError:
        raise ImportError(f"Could not import module base {module_base}")

    all_modules = list(get_all_holehe_modules(root.__path__, module_base))
    total = len(all_modules)
    progress = {"completed": 0}

    async with httpx.AsyncClient() as client:

        async def run_single_module(full_import, modname):
            try:
                module = importlib.import_module(full_import)
                func = getattr(module, modname)
                await func(email, client, out)
            except Exception as e:
                if debug_level == 1:
                    print(f"[!] Error in {full_import}: {e}")
                elif debug_level > 1:
                    tb = traceback.format_exc(limit=1).strip()
                    print(
                        f"[!] Error in {full_import}: {type(e).__name__}: {e}\n↳ {tb}"
                    )
            finally:
                progress["completed"] += 1
                if progress_bar_callback:
                    progress_bar_callback(progress["completed"], total)

        async with trio.open_nursery() as nursery:
            for full_import, modname in all_modules:
                nursery.start_soon(run_single_module, full_import, modname)

    return out
