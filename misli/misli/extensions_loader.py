import os
from typing import List, Union
from pathlib import Path
from importlib.util import spec_from_file_location, module_from_spec
import sys


class ExtensionsLoader:
    def __init__(self, root_folder: Union[Path, str]):
        self.root_path = Path(root_folder)

    def get_py_files(self, folder: Path) -> List[Path]:
        py_files = []
        for root, dirs, files in os.walk(folder):
            for file in files:
                if file.endswith('.py'):
                    py_files.append(folder / root / file)

        return py_files

    def load_all_recursively(self, folder: Path):
        py_files = self.get_py_files(folder)
        for file_path in py_files:
            if file_path.name == '__init__.py':
                continue

            rel_path = file_path.relative_to(self.root_path.parent)
            module_name = '.'.join(rel_path.parts[:-1] + (rel_path.stem,))
            if module_name in sys.modules:
                continue

            spec = spec_from_file_location(module_name, file_path)
            module = module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
