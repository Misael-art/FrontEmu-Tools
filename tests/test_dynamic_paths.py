#!/usr/bin/env python3
"""
Testes para validar o sistema de paths dinâmicos.

Este módulo testa se o sistema de paths foi corretamente implementado
sem paths hardcoded e com resolução dinâmica.

Author: SD Emulation Team
Date: 2025-01-19
"""

import json
import sys
import unittest
from pathlib import Path

# Add project root to path - conftest.py already handles this
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))


class TestDynamicPaths(unittest.TestCase):
    """Testes para validar o sistema de paths dinâmicos."""

    def test_path_config_json_no_hardcoded_paths(self):
        """Testa se path_config.json não contém paths hardcoded."""
        config_file = project_root / "meta" / "config" / "path_config.json"

        if config_file.exists():
            with open(config_file, encoding="utf-8") as f:
                config_data = json.load(f)

            # Verifica se os valores são null ou não contêm paths hardcoded
            hardcoded_patterns = ["F:/", "F:\\", "C:/", "C:\\"]

            def check_dict_values(data, path=""):
                if isinstance(data, dict):
                    for key, value in data.items():
                        current_path = f"{path}.{key}" if path else key
                        if isinstance(value, str):
                            for pattern in hardcoded_patterns:
                                self.assertNotIn(
                                    pattern,
                                    value,
                                    f"Hardcoded path '{pattern}' found in {current_path}: {value}",
                                )
                        elif isinstance(value, (dict, list)):
                            check_dict_values(value, current_path)
                elif isinstance(data, list):
                    for i, item in enumerate(data):
                        check_dict_values(item, f"{path}[{i}]")

            check_dict_values(config_data)

    def test_no_hardcoded_strings_in_source(self):
        """Testa se não há strings hardcoded nos arquivos fonte principais."""
        # Check key source files for hardcoded paths
        source_files = [
            project_root / "meta" / "config" / "path_resolver.py",
            project_root / "meta" / "config" / "path_config.py",
            project_root / "src" / "sd_emulation_gui" / "adapters" / "fs_adapter.py",
            project_root / "src" / "sd_emulation_gui" / "services" / "migration_service.py",
            project_root / "src" / "sd_emulation_gui" / "gui" / "main_window.py",
            project_root / "src" / "sd_emulation_gui" / "domain" / "sd_rules.py",
        ]

        hardcoded_patterns = ["F:/", "F:\\\\", "C:/", "C:\\\\"]

        for file_path in source_files:
            if file_path.exists():
                with open(file_path, encoding="utf-8") as f:
                    content = f.read()
                    for pattern in hardcoded_patterns:
                        # Allow patterns in comments or test data
                        lines = content.split("\n")
                        for line_num, line in enumerate(lines, 1):
                            if pattern in line:
                                # Skip if it's in a comment, docstring, or example
                                line_stripped = line.strip()
                                if (
                                    line_stripped.startswith("#")
                                    or '"""' in line
                                    or "'''" in line
                                    or "example" in line.lower()
                                    or "test" in line.lower()
                                    or "# Example:" in line
                                    or "# e.g." in line.lower()
                                ):
                                    continue

                                self.fail(
                                    f"Hardcoded path '{pattern}' found in {file_path.name}:{line_num}: {line.strip()}"
                                )

    def test_path_config_structure(self):
        """Testa se o arquivo de configuração de paths não contém paths hardcoded."""
        config_path = project_root / "meta" / "config" / "path_config.json"
        self.assertTrue(config_path.exists(), "Arquivo path_config.json não encontrado")

        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)

        # Verifica se a estrutura básica existe (agora usa base_path ao invés de base_paths)
        self.assertIn("base_path", config, f"'base_path' not found in {config}")

        # Verifica se não há paths hardcoded
        config_str = json.dumps(config)
        hardcoded_patterns = ["F:/", "F:\\", "C:/", "C:\\"]

        for pattern in hardcoded_patterns:
            self.assertNotIn(
                pattern, config_str, f"Path hardcoded encontrado: {pattern}"
            )

        print("✓ Arquivo path_config.json validado - sem paths hardcoded")

    def test_migration_service_no_hardcoded_paths(self):
        """Testa se migration_service.py não contém paths hardcoded."""
        migration_file = project_root / "src" / "sd_emulation_gui" / "services" / "migration_service.py"

        if migration_file.exists():
            with open(migration_file, encoding="utf-8") as f:
                content = f.read()

            # Verifica se não há paths hardcoded no código
            hardcoded_patterns = ["F:/", "F:\\\\", "C:/", "C:\\\\"]

            for pattern in hardcoded_patterns:
                # Conta ocorrências que não são comentários
                lines = content.split("\n")
                for line_num, line in enumerate(lines, 1):
                    if pattern in line:
                        line_stripped = line.strip()
                        # Skip comments, docstrings, and examples
                        if (
                            line_stripped.startswith("#")
                            or '"""' in line
                            or "'''" in line
                            or "description=" in line
                            or "help=" in line
                        ):
                            continue

                        self.fail(
                            f"Hardcoded path '{pattern}' found in migration_service.py:{line_num}: {line.strip()}"
                        )


if __name__ == "__main__":
    # Executa os testes
    unittest.main(verbosity=2)