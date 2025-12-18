#!/usr/bin/env python3
"""
Architecture JSON Generator - Universal Python Project Analyzer

Génère un fichier architecture.json complet pour n'importe quel projet Python:
- Tous les modules Python
- Classes avec leurs attributs et méthodes
- Fonctions avec signatures complètes
- Constantes et variables globales
- Décorateurs et annotations de type
- Docstrings complètes
- Graphe de dépendances

Usage:
    # Analyser le dossier courant
    python3 generate_architecture.py

    # Analyser un dossier spécifique
    python3 generate_architecture.py --dir src/plugins/duplicate_finder

    # Spécifier le nom de sortie
    python3 generate_architecture.py --dir src/plugins/duplicate_finder --output df_architecture.json

    # Analyser duplicateflow
    python3 generate_architecture.py --dir duplicateflow --output duplicateflow/architecture.json
"""

import ast
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
from collections import defaultdict


@dataclass
class ParameterInfo:
    """Information sur un paramètre de fonction/méthode."""
    name: str
    type_annotation: Optional[str] = None
    default_value: Optional[str] = None
    kind: str = "positional"


@dataclass
class FunctionInfo:
    """Information complète sur une fonction."""
    name: str
    description: str
    parameters: List[Dict[str, Any]]
    returns: Optional[str] = None
    decorators: List[str] = None
    is_async: bool = False
    is_static: bool = False
    is_classmethod: bool = False
    is_property: bool = False


@dataclass
class AttributeInfo:
    """Information sur un attribut de classe."""
    name: str
    type_annotation: Optional[str] = None
    default_value: Optional[str] = None
    is_class_var: bool = False


@dataclass
class ClassInfo:
    """Information complète sur une classe."""
    name: str
    description: str
    bases: List[str] = None
    attributes: Dict[str, Dict] = None
    methods: Dict[str, Dict] = None
    properties: Dict[str, Dict] = None
    decorators: List[str] = None
    is_dataclass: bool = False


@dataclass
class ModuleInfo:
    """Information complète sur un module."""
    name: str
    file_path: str
    description: str
    imports: List[str] = None
    classes: Dict[str, Dict] = None
    functions: Dict[str, Dict] = None
    constants: Dict[str, Dict] = None


class ArchitectureGenerator:
    """
    Générateur d'architecture.json universel.

    Analyse n'importe quel dossier Python et extrait toute la structure.
    """

    def __init__(self, scan_dir: Path, project_root: Optional[Path] = None):
        """
        Args:
            scan_dir: Dossier à analyser (ex: src/plugins/duplicate_finder)
            project_root: Racine du projet (optionnel, déduit automatiquement)
        """
        self.scan_dir = Path(scan_dir).resolve()
        self.project_root = Path(project_root).resolve() if project_root else self.scan_dir

        # Déterminer le nom du package
        if self.scan_dir == self.project_root:
            self.package_name = self.scan_dir.name
        else:
            self.package_name = str(self.scan_dir.relative_to(self.project_root)).replace('/', '.')

        self.architecture = {
            "version": "1.0.0",
            "generated_at": datetime.now().isoformat(),
            "generator": "generate_architecture.py",
            "scan_directory": str(self.scan_dir),
            "project_root": str(self.project_root),
            "package_name": self.package_name,
            "modules": {},
            "dependency_graph": {},
            "statistics": {}
        }

        self.stats = {
            "total_modules": 0,
            "total_classes": 0,
            "total_functions": 0,
            "total_methods": 0,
            "total_constants": 0,
            "total_lines_of_code": 0
        }

    def generate(self) -> Dict[str, Any]:
        """Génère l'architecture complète."""
        print(f"🔍 Scanning {self.scan_dir}...")

        if not self.scan_dir.exists():
            raise FileNotFoundError(f"Directory not found: {self.scan_dir}")

        # Parser tous les fichiers Python
        python_files = sorted(self.scan_dir.rglob("*.py"))

        if not python_files:
            print(f"⚠️  No Python files found in {self.scan_dir}")
            return self.architecture

        for py_file in python_files:
            if self._should_skip_file(py_file):
                continue

            try:
                rel_path = py_file.relative_to(self.project_root)
            except ValueError:
                rel_path = py_file.relative_to(self.scan_dir)

            print(f"  📄 {rel_path}")
            try:
                self._parse_file(py_file)
            except Exception as e:
                print(f"    ⚠️  Warning: {e}")

        # Générer le graphe de dépendances
        print("🔗 Building dependency graph...")
        self._build_dependency_graph()

        # Ajouter les stats
        self.architecture["statistics"] = self.stats

        print(f"\n✅ Analysis complete!")
        print(f"   📦 {self.stats['total_modules']} modules")
        print(f"   🏛️  {self.stats['total_classes']} classes")
        print(f"   📝 {self.stats['total_functions']} functions")
        print(f"   🔧 {self.stats['total_methods']} methods")
        print(f"   🔢 {self.stats['total_constants']} constants")
        print(f"   📊 {self.stats['total_lines_of_code']} lines of code")

        return self.architecture

    def _should_skip_file(self, file_path: Path) -> bool:
        """Vérifie si un fichier doit être ignoré."""
        parts_str = str(file_path)

        # Ignorer les tests
        if "/test" in parts_str or "\\test" in parts_str:
            return True
        # Ignorer __pycache__
        if "__pycache__" in parts_str:
            return True
        # Ignorer fichiers temporaires
        if file_path.name.startswith(".") or file_path.name.endswith("~"):
            return True
        # Ignorer fichiers de backup
        if file_path.name.endswith(".bak") or file_path.name.endswith(".tmp"):
            return True
        return False

    def _parse_file(self, file_path: Path):
        """Parse un fichier Python complet."""
        with open(file_path, 'r', encoding='utf-8') as f:
            source_code = f.read()

        tree = ast.parse(source_code, filename=str(file_path))

        # Compter les lignes de code
        lines = [l for l in source_code.split('\n') if l.strip() and not l.strip().startswith('#')]
        self.stats["total_lines_of_code"] += len(lines)

        # Construire le nom du module
        module_name = self._get_module_name(file_path)

        # Extraire la docstring du module
        module_docstring = ast.get_docstring(tree) or ""

        # Créer l'info du module
        module_info = ModuleInfo(
            name=module_name,
            file_path=str(file_path.relative_to(self.project_root)),
            description=module_docstring,
            imports=[],
            classes={},
            functions={},
            constants={}
        )

        # Parser le contenu
        for node in tree.body:
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module_info.imports.append(alias.name)

            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    module_info.imports.append(f"{module}.{alias.name}")

            elif isinstance(node, ast.ClassDef):
                class_info = self._parse_class(node)
                module_info.classes[node.name] = asdict(class_info)
                self.stats["total_classes"] += 1

            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_info = self._parse_function(node)
                module_info.functions[node.name] = asdict(func_info)
                self.stats["total_functions"] += 1

            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        const_info = self._parse_constant(target.id, node.value)
                        if const_info:
                            module_info.constants[target.id] = const_info
                            self.stats["total_constants"] += 1

        # Stocker le module
        self.architecture["modules"][module_name] = asdict(module_info)
        self.stats["total_modules"] += 1

    def _get_module_name(self, file_path: Path) -> str:
        """Convertit un chemin de fichier en nom de module."""
        try:
            relative = file_path.relative_to(self.scan_dir)
        except ValueError:
            relative = file_path.relative_to(self.project_root)

        parts = list(relative.parts)

        # Retirer l'extension .py
        if parts[-1].endswith('.py'):
            parts[-1] = parts[-1][:-3]

        # Retirer __init__
        if parts[-1] == '__init__':
            parts = parts[:-1]

        return '.'.join(parts) if parts else "root"

    def _parse_class(self, node: ast.ClassDef) -> ClassInfo:
        """Parse une classe complète."""
        docstring = ast.get_docstring(node) or ""

        # Bases (héritage)
        bases = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                bases.append(base.id)
            elif isinstance(base, ast.Attribute):
                bases.append(self._get_full_name(base))

        # Décorateurs
        decorators = [self._get_decorator_name(dec) for dec in node.decorator_list]
        is_dataclass = any('dataclass' in dec for dec in decorators)

        # Parser attributs et méthodes
        attributes = {}
        methods = {}
        properties = {}

        for item in node.body:
            if isinstance(item, ast.AnnAssign):
                if isinstance(item.target, ast.Name):
                    attr_name = item.target.id
                    attr_info = AttributeInfo(
                        name=attr_name,
                        type_annotation=self._get_annotation(item.annotation),
                        default_value=self._get_value_repr(item.value) if item.value else None
                    )
                    attributes[attr_name] = asdict(attr_info)

            elif isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name) and not target.id.startswith('_'):
                        attr_info = AttributeInfo(
                            name=target.id,
                            default_value=self._get_value_repr(item.value)
                        )
                        attributes[target.id] = asdict(attr_info)

            elif isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_info = self._parse_function(item)
                is_prop = any('property' in dec for dec in func_info.decorators or [])

                if is_prop:
                    properties[item.name] = asdict(func_info)
                else:
                    methods[item.name] = asdict(func_info)
                    self.stats["total_methods"] += 1

        return ClassInfo(
            name=node.name,
            description=docstring,
            bases=bases,
            attributes=attributes,
            methods=methods,
            properties=properties,
            decorators=decorators,
            is_dataclass=is_dataclass
        )

    def _parse_function(self, node) -> FunctionInfo:
        """Parse une fonction ou méthode."""
        docstring = ast.get_docstring(node) or ""
        parameters = self._parse_parameters(node.args)

        returns = None
        if node.returns:
            returns = self._get_annotation(node.returns)

        decorators = [self._get_decorator_name(dec) for dec in node.decorator_list]

        return FunctionInfo(
            name=node.name,
            description=docstring,
            parameters=[asdict(p) for p in parameters],
            returns=returns,
            decorators=decorators,
            is_async=isinstance(node, ast.AsyncFunctionDef),
            is_static='staticmethod' in decorators,
            is_classmethod='classmethod' in decorators,
            is_property='property' in decorators
        )

    def _parse_parameters(self, args: ast.arguments) -> List[ParameterInfo]:
        """Parse les paramètres d'une fonction."""
        params = []

        # Arguments positionnels
        for i, arg in enumerate(args.args):
            default_value = None
            defaults_offset = len(args.args) - len(args.defaults)
            if i >= defaults_offset:
                default_idx = i - defaults_offset
                default_value = self._get_value_repr(args.defaults[default_idx])

            param = ParameterInfo(
                name=arg.arg,
                type_annotation=self._get_annotation(arg.annotation) if arg.annotation else None,
                default_value=default_value,
                kind="positional"
            )
            params.append(param)

        # *args
        if args.vararg:
            param = ParameterInfo(
                name=args.vararg.arg,
                type_annotation=self._get_annotation(args.vararg.annotation) if args.vararg.annotation else None,
                kind="var_positional"
            )
            params.append(param)

        # Keyword-only arguments
        for i, arg in enumerate(args.kwonlyargs):
            default_value = None
            if i < len(args.kw_defaults) and args.kw_defaults[i]:
                default_value = self._get_value_repr(args.kw_defaults[i])

            param = ParameterInfo(
                name=arg.arg,
                type_annotation=self._get_annotation(arg.annotation) if arg.annotation else None,
                default_value=default_value,
                kind="keyword_only"
            )
            params.append(param)

        # **kwargs
        if args.kwarg:
            param = ParameterInfo(
                name=args.kwarg.arg,
                type_annotation=self._get_annotation(args.kwarg.annotation) if args.kwarg.annotation else None,
                kind="var_keyword"
            )
            params.append(param)

        return params

    def _parse_constant(self, name: str, value_node: ast.expr) -> Optional[Dict]:
        """Parse une constante."""
        if name.startswith('_') and not name.startswith('__'):
            return None

        return {
            "name": name,
            "type": self._infer_type(value_node),
            "value": self._get_value_repr(value_node)
        }

    def _get_annotation(self, node: ast.expr) -> str:
        """Convertit une annotation AST en string."""
        if node is None:
            return None

        try:
            return ast.unparse(node)
        except:
            if isinstance(node, ast.Name):
                return node.id
            return str(node)

    def _get_value_repr(self, node: ast.expr) -> str:
        """Obtient la représentation d'une valeur."""
        if node is None:
            return None
        try:
            return ast.unparse(node)
        except:
            return repr(node)

    def _infer_type(self, node: ast.expr) -> str:
        """Infère le type d'une expression."""
        if isinstance(node, ast.Constant):
            return type(node.value).__name__
        elif isinstance(node, ast.List):
            return "list"
        elif isinstance(node, ast.Dict):
            return "dict"
        elif isinstance(node, ast.Set):
            return "set"
        elif isinstance(node, ast.Tuple):
            return "tuple"
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            return node.func.id
        return "unknown"

    def _get_decorator_name(self, dec: ast.expr) -> str:
        """Obtient le nom d'un décorateur."""
        if isinstance(dec, ast.Name):
            return dec.id
        elif isinstance(dec, ast.Call):
            return self._get_decorator_name(dec.func)
        elif isinstance(dec, ast.Attribute):
            return self._get_full_name(dec)
        return str(dec)

    def _get_full_name(self, node: ast.Attribute) -> str:
        """Obtient le nom complet d'un attribut."""
        parts = []
        current = node
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        return '.'.join(reversed(parts))

    def _build_dependency_graph(self):
        """Construit le graphe de dépendances entre modules."""
        graph = defaultdict(set)

        for module_name, module_info in self.architecture["modules"].items():
            imports = module_info.get("imports", [])
            for imp in imports:
                # Garder imports internes et relatifs
                if '.' in imp or imp in self.architecture["modules"]:
                    graph[module_name].add(imp)

        self.architecture["dependency_graph"] = {
            k: sorted(list(v)) for k, v in graph.items()
        }

    def save(self, output_path: Path):
        """Sauvegarde l'architecture en JSON."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.architecture, f, indent=2, ensure_ascii=False)

        print(f"\n💾 Architecture saved to: {output_path}")
        print(f"   Size: {output_path.stat().st_size / 1024:.1f} KB")


def main():
    """Point d'entrée principal."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate architecture.json for any Python project",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze current directory
  python3 generate_architecture.py

  # Analyze specific folder
  python3 generate_architecture.py --dir src/plugins/duplicate_finder

  # Custom output
  python3 generate_architecture.py --dir duplicateflow --output arch.json

  # Analyze with custom project root
  python3 generate_architecture.py --dir src/core --root /path/to/project
        """
    )
    parser.add_argument(
        '--dir', '-d',
        type=Path,
        default=Path.cwd(),
        help="Directory to analyze (default: current directory)"
    )
    parser.add_argument(
        '--output', '-o',
        type=Path,
        default=None,
        help="Output file (default: <dir>/architecture.json)"
    )
    parser.add_argument(
        '--root', '-r',
        type=Path,
        default=None,
        help="Project root directory (default: same as --dir)"
    )

    args = parser.parse_args()

    # Déterminer les chemins
    scan_dir = args.dir.resolve()
    project_root = args.root.resolve() if args.root else scan_dir

    # Output par défaut
    if args.output is None:
        output_path = scan_dir / "architecture.json"
    else:
        output_path = args.output

    print("=" * 70)
    print(" 🏗️  Python Architecture Generator")
    print("=" * 70)
    print(f"Scan directory:  {scan_dir}")
    print(f"Project root:    {project_root}")
    print(f"Output file:     {output_path}")
    print("=" * 70)
    print()

    # Générer
    generator = ArchitectureGenerator(
        scan_dir=scan_dir,
        project_root=project_root
    )

    try:
        architecture = generator.generate()
        generator.save(output_path)
        print(f"\n✅ Success!")
        return 0
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
