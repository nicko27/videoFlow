#!/usr/bin/env python3
"""
DuplicateFlow - Architecture JSON Generator

Génère un fichier architecture.json complet contenant:
- Tous les modules Python
- Classes avec leurs attributs et méthodes
- Fonctions avec signatures complètes
- Constantes et variables globales
- Décorateurs et annotations de type
- Docstrings complètes
- Graphe de dépendances

Usage:
    python3 generate_architecture_json.py [--output architecture.json]

**IMPORTANT**: Ce fichier est la référence centrale pour Claude.
Il doit contenir TOUTES les informations nécessaires pour éviter
les erreurs d'API dans les sessions futures.
"""

import ast
import inspect
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
from collections import defaultdict
import importlib.util


@dataclass
class ParameterInfo:
    """Information sur un paramètre de fonction/méthode."""
    name: str
    type_annotation: Optional[str] = None
    default_value: Optional[str] = None
    kind: str = "positional"  # positional, keyword, var_positional, var_keyword
    description: str = ""


@dataclass
class FunctionInfo:
    """Information complète sur une fonction."""
    name: str
    description: str
    parameters: List[Dict[str, Any]]
    returns: Optional[str] = None
    raises: List[str] = None
    decorators: List[str] = None
    is_async: bool = False
    is_static: bool = False
    is_classmethod: bool = False
    is_property: bool = False
    examples: List[str] = None
    notes: List[str] = None


@dataclass
class AttributeInfo:
    """Information sur un attribut de classe."""
    name: str
    type_annotation: Optional[str] = None
    default_value: Optional[str] = None
    description: str = ""
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
    is_abstract: bool = False
    is_dataclass: bool = False
    examples: List[str] = None


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
    decorators: Dict[str, Dict] = None


class ArchitectureGenerator:
    """
    Générateur d'architecture.json.

    Utilise l'analyse statique (AST) pour extraire toutes les informations
    du code source sans l'exécuter.
    """

    def __init__(self, project_root: Path, package_name: str = "duplicateflow"):
        self.project_root = Path(project_root)
        self.package_name = package_name
        self.package_dir = self.project_root / package_name

        self.architecture = {
            "version": "1.0.0",
            "generated_at": datetime.now().isoformat(),
            "generator": "generate_architecture_json.py",
            "project_root": str(self.project_root),
            "package_name": package_name,
            "modules": {},
            "dependency_graph": {},
            "algorithm_registry": {},
            "cli_commands": {},
            "statistics": {}
        }

        # Compteurs pour stats
        self.stats = {
            "total_modules": 0,
            "total_classes": 0,
            "total_functions": 0,
            "total_methods": 0,
            "total_constants": 0,
            "total_lines_of_code": 0
        }

    def generate(self) -> Dict[str, Any]:
        """
        Génère l'architecture complète.

        Returns:
            Dictionnaire complet de l'architecture
        """
        print(f"🔍 Scanning {self.package_dir}...")

        if not self.package_dir.exists():
            raise FileNotFoundError(f"Package directory not found: {self.package_dir}")

        # Parser tous les fichiers Python
        for py_file in sorted(self.package_dir.rglob("*.py")):
            if self._should_skip_file(py_file):
                continue

            print(f"  📄 Parsing {py_file.relative_to(self.project_root)}...")
            try:
                self._parse_file(py_file)
            except Exception as e:
                print(f"    ⚠️  Warning: Failed to parse {py_file}: {e}")

        # Générer le graphe de dépendances
        print("🔗 Building dependency graph...")
        self._build_dependency_graph()

        # Extraire les algorithmes enregistrés
        print("🔌 Extracting registered algorithms...")
        self._extract_algorithm_registry()

        # Extraire les commandes CLI
        print("💻 Extracting CLI commands...")
        self._extract_cli_commands()

        # Ajouter les stats
        self.architecture["statistics"] = self.stats

        print(f"✅ Architecture generated successfully!")
        print(f"   - {self.stats['total_modules']} modules")
        print(f"   - {self.stats['total_classes']} classes")
        print(f"   - {self.stats['total_functions']} functions")
        print(f"   - {self.stats['total_methods']} methods")
        print(f"   - {self.stats['total_constants']} constants")
        print(f"   - {self.stats['total_lines_of_code']} lines of code")

        return self.architecture

    def _should_skip_file(self, file_path: Path) -> bool:
        """Vérifie si un fichier doit être ignoré."""
        # Ignorer les tests
        if "test" in file_path.parts:
            return True
        # Ignorer les __pycache__
        if "__pycache__" in file_path.parts:
            return True
        # Ignorer les fichiers temporaires
        if file_path.name.startswith(".") or file_path.name.endswith("~"):
            return True
        return False

    def _parse_file(self, file_path: Path):
        """Parse un fichier Python complet."""
        with open(file_path, 'r', encoding='utf-8') as f:
            source_code = f.read()

        try:
            tree = ast.parse(source_code, filename=str(file_path))
        except SyntaxError as e:
            print(f"    ⚠️  Syntax error in {file_path}: {e}")
            return

        # Compter les lignes de code
        lines = source_code.split('\n')
        loc = len([line for line in lines if line.strip() and not line.strip().startswith('#')])
        self.stats["total_lines_of_code"] += loc

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
            constants={},
            decorators={}
        )

        # Parser le contenu
        for node in tree.body:
            if isinstance(node, ast.Import):
                # import foo
                for alias in node.names:
                    module_info.imports.append(alias.name)

            elif isinstance(node, ast.ImportFrom):
                # from foo import bar
                module = node.module or ""
                for alias in node.names:
                    module_info.imports.append(f"{module}.{alias.name}")

            elif isinstance(node, ast.ClassDef):
                # Classe
                class_info = self._parse_class(node)
                module_info.classes[node.name] = asdict(class_info)
                self.stats["total_classes"] += 1

            elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                # Fonction (hors classe)
                func_info = self._parse_function(node)
                module_info.functions[node.name] = asdict(func_info)
                self.stats["total_functions"] += 1

            elif isinstance(node, ast.Assign):
                # Constante ou variable globale
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        const_info = self._parse_constant(target.id, node.value, node)
                        if const_info:
                            module_info.constants[target.id] = const_info
                            self.stats["total_constants"] += 1

        # Stocker le module
        self.architecture["modules"][module_name] = asdict(module_info)
        self.stats["total_modules"] += 1

    def _get_module_name(self, file_path: Path) -> str:
        """Convertit un chemin de fichier en nom de module."""
        relative = file_path.relative_to(self.project_root)
        parts = list(relative.parts)

        # Retirer l'extension .py
        if parts[-1].endswith('.py'):
            parts[-1] = parts[-1][:-3]

        # Retirer __init__
        if parts[-1] == '__init__':
            parts = parts[:-1]

        return '.'.join(parts)

    def _parse_class(self, node: ast.ClassDef) -> ClassInfo:
        """Parse une classe complète."""
        # Docstring
        docstring = ast.get_docstring(node) or ""

        # Bases (héritage)
        bases = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                bases.append(base.id)
            elif isinstance(base, ast.Attribute):
                bases.append(self._get_full_attribute_name(base))

        # Décorateurs
        decorators = [self._get_decorator_name(dec) for dec in node.decorator_list]

        # Vérifier si dataclass
        is_dataclass = any('dataclass' in dec for dec in decorators)

        # Vérifier si abstract
        is_abstract = any(
            isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef))
            and any('abstractmethod' in self._get_decorator_name(dec)
                   for dec in method.decorator_list)
            for method in node.body
        )

        # Parser les attributs et méthodes
        attributes = {}
        methods = {}
        properties = {}

        for item in node.body:
            if isinstance(item, ast.AnnAssign):
                # Attribut annoté (ex: name: str = "default")
                if isinstance(item.target, ast.Name):
                    attr_name = item.target.id
                    attr_info = AttributeInfo(
                        name=attr_name,
                        type_annotation=self._get_annotation(item.annotation),
                        default_value=self._get_value_repr(item.value) if item.value else None,
                        description=self._extract_inline_comment(item) or ""
                    )
                    attributes[attr_name] = asdict(attr_info)

            elif isinstance(item, ast.Assign):
                # Attribut classique (ex: name = "default")
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        attr_name = target.id
                        if not attr_name.startswith('_'):  # Ignorer privés
                            attr_info = AttributeInfo(
                                name=attr_name,
                                default_value=self._get_value_repr(item.value),
                                description=""
                            )
                            attributes[attr_name] = asdict(attr_info)

            elif isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Méthode
                func_info = self._parse_function(item, is_method=True)

                # Vérifier si property
                is_prop = any('property' in dec for dec in func_info.decorators or [])

                if is_prop:
                    properties[item.name] = asdict(func_info)
                else:
                    methods[item.name] = asdict(func_info)
                    self.stats["total_methods"] += 1

        # Extraire exemples de la docstring
        examples = self._extract_examples_from_docstring(docstring)

        return ClassInfo(
            name=node.name,
            description=docstring,
            bases=bases,
            attributes=attributes,
            methods=methods,
            properties=properties,
            decorators=decorators,
            is_abstract=is_abstract,
            is_dataclass=is_dataclass,
            examples=examples
        )

    def _parse_function(self, node,
                       is_method: bool = False) -> FunctionInfo:
        """Parse une fonction ou méthode."""
        # Docstring
        docstring = ast.get_docstring(node) or ""

        # Paramètres
        parameters = self._parse_parameters(node.args)

        # Type de retour
        returns = None
        if node.returns:
            returns = self._get_annotation(node.returns)

        # Décorateurs
        decorators = [self._get_decorator_name(dec) for dec in node.decorator_list]

        # Vérifier les types de décorateurs
        is_static = 'staticmethod' in decorators
        is_classmethod = 'classmethod' in decorators
        is_property = 'property' in decorators

        # Extraire raises de la docstring
        raises = self._extract_raises_from_docstring(docstring)

        # Extraire exemples
        examples = self._extract_examples_from_docstring(docstring)

        # Extraire notes
        notes = self._extract_notes_from_docstring(docstring)

        return FunctionInfo(
            name=node.name,
            description=docstring,
            parameters=[asdict(p) for p in parameters],
            returns=returns,
            raises=raises,
            decorators=decorators,
            is_async=isinstance(node, ast.AsyncFunctionDef),
            is_static=is_static,
            is_classmethod=is_classmethod,
            is_property=is_property,
            examples=examples,
            notes=notes
        )

    def _parse_parameters(self, args: ast.arguments) -> List[ParameterInfo]:
        """Parse les paramètres d'une fonction."""
        params = []

        # Arguments positionnels
        for i, arg in enumerate(args.args):
            # Chercher la valeur par défaut
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

    def _parse_constant(self, name: str, value_node: ast.expr, assign_node: ast.Assign) -> Optional[Dict]:
        """Parse une constante."""
        # Ignorer les privées (commencent par _)
        if name.startswith('_') and not name.startswith('__'):
            return None

        # Type et valeur
        type_annotation = None
        value_repr = self._get_value_repr(value_node)

        # Essayer d'inférer le type
        inferred_type = self._infer_type(value_node)

        return {
            "name": name,
            "type": inferred_type,
            "value": value_repr,
            "description": ""
        }

    def _get_annotation(self, node: ast.expr) -> str:
        """Convertit une annotation AST en string."""
        if node is None:
            return None

        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Constant):
            return repr(node.value)
        elif isinstance(node, ast.Subscript):
            # Ex: List[str], Dict[str, int]
            base = self._get_annotation(node.value)
            slice_val = self._get_annotation(node.slice)
            return f"{base}[{slice_val}]"
        elif isinstance(node, ast.Tuple):
            # Ex: Tuple[int, str]
            elements = [self._get_annotation(elt) for elt in node.elts]
            return ', '.join(elements)
        elif isinstance(node, ast.Attribute):
            return self._get_full_attribute_name(node)
        elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            # Ex: str | None (Python 3.10+)
            left = self._get_annotation(node.left)
            right = self._get_annotation(node.right)
            return f"{left} | {right}"
        else:
            return ast.unparse(node)

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
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                return node.func.id
        return "unknown"

    def _get_decorator_name(self, dec: ast.expr) -> str:
        """Obtient le nom d'un décorateur."""
        if isinstance(dec, ast.Name):
            return dec.id
        elif isinstance(dec, ast.Call):
            return self._get_decorator_name(dec.func)
        elif isinstance(dec, ast.Attribute):
            return self._get_full_attribute_name(dec)
        return str(dec)

    def _get_full_attribute_name(self, node: ast.Attribute) -> str:
        """Obtient le nom complet d'un attribut (ex: foo.bar.baz)."""
        parts = []
        current = node
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        return '.'.join(reversed(parts))

    def _extract_inline_comment(self, node: ast.stmt) -> Optional[str]:
        """Extrait un commentaire inline (limité avec AST)."""
        # AST ne capture pas les commentaires, donc on retourne None
        # Une amélioration serait d'utiliser le tokenizer
        return None

    def _extract_raises_from_docstring(self, docstring: str) -> List[str]:
        """Extrait les exceptions depuis la docstring."""
        raises = []
        lines = docstring.split('\n')

        in_raises_section = False
        for line in lines:
            stripped = line.strip()
            if stripped.lower().startswith('raises:'):
                in_raises_section = True
                continue
            elif in_raises_section:
                if stripped and not stripped.startswith(' '):
                    # Fin de la section
                    break
                if ':' in stripped:
                    # Ex: "ValueError: Si le paramètre est invalide"
                    exception = stripped.split(':')[0].strip()
                    raises.append(exception)

        return raises if raises else None

    def _extract_examples_from_docstring(self, docstring: str) -> List[str]:
        """Extrait les exemples depuis la docstring."""
        examples = []
        lines = docstring.split('\n')

        in_example_section = False
        current_example = []

        for line in lines:
            stripped = line.strip()
            if stripped.lower().startswith('example') or stripped.lower().startswith('examples:'):
                in_example_section = True
                continue
            elif in_example_section:
                if stripped and not stripped.startswith(' ') and not stripped.startswith('>>>'):
                    # Fin de la section
                    if current_example:
                        examples.append('\n'.join(current_example))
                    break
                if stripped:
                    current_example.append(stripped)

        if current_example and not examples:
            examples.append('\n'.join(current_example))

        return examples if examples else None

    def _extract_notes_from_docstring(self, docstring: str) -> List[str]:
        """Extrait les notes depuis la docstring."""
        notes = []
        lines = docstring.split('\n')

        for line in lines:
            stripped = line.strip()
            if stripped.lower().startswith('note:') or stripped.lower().startswith('warning:'):
                notes.append(stripped)

        return notes if notes else None

    def _build_dependency_graph(self):
        """Construit le graphe de dépendances entre modules."""
        graph = defaultdict(set)

        for module_name, module_info in self.architecture["modules"].items():
            imports = module_info.get("imports", [])
            for imp in imports:
                # Filtrer pour ne garder que les imports internes
                if imp.startswith(self.package_name):
                    graph[module_name].add(imp)

        # Convertir sets en listes pour JSON
        self.architecture["dependency_graph"] = {
            k: list(v) for k, v in graph.items()
        }

    def _extract_algorithm_registry(self):
        """Extrait la liste des algorithmes enregistrés."""
        # Chercher dans algorithms/__init__.py ou core/registry.py
        # Cette partie est spécifique à l'implémentation

        # Pour l'instant, on laisse vide (sera rempli lors de l'implémentation réelle)
        self.architecture["algorithm_registry"] = {
            "note": "Will be populated when algorithms are implemented",
            "expected_location": f"{self.package_name}.algorithms",
            "registration_decorator": "@register_algorithm"
        }

    def _extract_cli_commands(self):
        """Extrait les commandes CLI."""
        # Chercher dans cli/commands/
        # Cette partie est spécifique à l'implémentation

        self.architecture["cli_commands"] = {
            "note": "Will be populated when CLI is implemented",
            "expected_location": f"{self.package_name}.cli.commands",
            "framework": "click"
        }

    def save(self, output_path: Path):
        """Sauvegarde l'architecture en JSON."""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.architecture, f, indent=2, ensure_ascii=False)
        print(f"💾 Architecture saved to {output_path}")


def main():
    """Point d'entrée principal."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate architecture.json for DuplicateFlow"
    )
    parser.add_argument(
        '--output',
        type=Path,
        default=Path('architecture.json'),
        help="Output file path (default: architecture.json)"
    )
    parser.add_argument(
        '--project-root',
        type=Path,
        default=Path(__file__).parent.parent,
        help="Project root directory"
    )
    parser.add_argument(
        '--package',
        type=str,
        default='duplicateflow',
        help="Package name to scan (default: duplicateflow)"
    )

    args = parser.parse_args()

    # Générer
    generator = ArchitectureGenerator(
        project_root=args.project_root,
        package_name=args.package
    )

    try:
        architecture = generator.generate()
        generator.save(args.output)
        print(f"\n✅ Success! Architecture JSON generated.")
        return 0
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
