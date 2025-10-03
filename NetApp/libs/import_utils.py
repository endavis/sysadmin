import importlib
import inspect
import sys

def import_all_files(package_name, package_path):
    for file in package_path.iterdir():
        if not file.name.startswith("__"):
            module_name = file.stem
            full_module_name = f"{package_name}.{module_name}"

            module = importlib.import_module(full_module_name)

            for name, obj in inspect.getmembers(module):
                if inspect.isfunction(obj) or inspect.isclass(obj):
                    setattr(sys.modules[package_name], name, obj)