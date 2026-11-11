#!/usr/bin/env python3
"""
Comprehensive Migrator Verification Script
Verifies that all 17 migrators are complete and production-ready

AI checks follow issue #23: a migrator may ship no AI client on purpose, and
then its README says it makes no AI calls. A migrator with a client must have
every prompt template it loads in its src/prompts/ folder, which is where
ai_client.py reads them from.
"""

import os
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Any
from datetime import datetime
import ast
import re


class MigratorVerifier:
    """Verify completeness and quality of all migrators"""
    
    # All expected migrators
    EXPECTED_MIGRATORS = [
        'asana', 'basecamp', 'bpmn', 'clickup', 'cognito-forms', 'google-forms',
        'jotform', 'kissflow', 'monday', 'nextmatter', 'pipefy',
        'process-street', 'rocketlane', 'surveymonkey', 'trello', 'typeform', 'wrike'
    ]
    
    # Required files for each migrator
    REQUIRED_FILES = {
        'readme': 'README.md',
        'env_example': '.env.example',
        'requirements': 'requirements.txt',
        'migrate_script': 'migrate.sh',
        'object_mapping': 'OBJECT_MAPPING.md',
        'main': 'src/main.py',
        'vendor_client': 'src/api/{vendor}_client.py',
        'tallyfy_client': 'src/api/tallyfy_client.py',
        'ai_client': 'src/api/ai_client.py',
        'field_transformer': 'src/transformers/field_transformer.py',
        'template_transformer': 'src/transformers/template_transformer.py',
        'user_transformer': 'src/transformers/user_transformer.py',
        'checkpoint_manager': 'src/utils/checkpoint_manager.py',
        'validator': 'src/utils/validator.py'
    }
    
    # Required README sections
    README_SECTIONS = [
        'Requirements', 'Installation', 'Configuration', 'Quick Start',
        'Architecture', 'AI-Powered Features', 'Data Mapping', 'API Integration',
        'Features', 'Usage Examples', 'Paradigm Shifts', 'Limitations',
        'Migration Process', 'Error Handling', 'Performance', 'Troubleshooting',
        'Best Practices', 'Support'
    ]
    
    # The words that name each required section, taken from the section's name
    # and its definition in CLAUDE.md ("Required README Sections", quoted after
    # each entry). One list per section, used the same way for every vendor: a
    # section counts when the README names it anywhere (the original test), or
    # when a heading or a bold label ("**Label**:") outside a code block
    # contains one of these words.
    README_SECTION_ALIASES = {
        'Requirements': ['requirements', 'prerequisites'],  # Include Anthropic API key
        'Installation': ['install', 'setup', 'set up'],  # Step-by-step setup
        'Configuration': ['configuration', 'environment variables'],  # AI configuration details
        'Quick Start': ['quick start', 'getting started'],  # With/without AI
        # 5-phase pattern. These READMEs describe it in their "Migration Phases"
        # section, as kissflow does inside its Architecture section.
        'Architecture': ['architecture', '5-phase', 'five-phase', 'migration phases'],
        'AI-Powered Features': ['ai-powered features', 'ai features', 'ai-assisted', 'when ai'],  # What AI enhances
        'Data Mapping': ['data mapping', 'object mapping', 'field mapping', 'field type mapping',
                         'question type mapping', 'mapping rules'],  # Link to OBJECT_MAPPING.md
        'API Integration': ['api integration', 'api implementation', 'api compatibility',
                            'api access', 'authentication'],  # Authentication details
        'Features': ['features', 'capabilities'],  # Core capabilities
        # Common scenarios: a section of runnable usage scenarios counts.
        'Usage Examples': ['usage', 'example', 'scenario', 'selective migration', 'specific phases',
                           'run migration', 'running the migration', 'command line options'],
        'Paradigm Shifts': ['paradigm', 'critical transformation'],  # Critical transformations
        'Limitations': ['limitation', 'cannot migrate', 'not migrated'],  # What cannot migrate
        'Migration Process': ['migration process', 'migration phases', 'migration steps'],  # Phase details
        'Error Handling': ['error handling', 'recover', 'resume', 'checkpoint', 'rollback',
                           'retry'],  # Recovery strategies
        'Performance': ['performance', 'processing speed', 'migration times'],  # Time estimates
        'Troubleshooting': ['troubleshooting', 'common issues'],  # Common issues
        'Best Practices': ['best practice', 'recommendation', 'recommended approach',
                           'before migration', 'before running migration', 'during migration',
                           'pre-migration checklist'],  # Recommendations
        'Support': ['support', 'getting help'],  # Getting help
    }
    
    # Required OBJECT_MAPPING.md sections, and the words that name each one.
    # CLAUDE.md does not define these, so the words come from the section names
    # and the sections the template vendors (basecamp, clickup, cognito-forms)
    # carry under those names. Used the same way as README_SECTION_ALIASES.
    OBJECT_MAPPING_SECTIONS = [
        'core object mappings',
        'field type mappings',
        'paradigm shifts',
        'data preservation',
        'migration complexity',
        'special handling',
        'known limitations',
        'validation checklist'
    ]
    OBJECT_MAPPING_SECTION_ALIASES = {
        # The vendor's main objects (organizations, users, templates, instances)
        'core object mappings': ['core object', 'terminology', 'object mapping', 'element mappings',
                                 'core platform concepts', 'organization & user mappings',
                                 'template & workflow mappings', 'instance & process mappings'],
        'field type mappings': ['field type', 'field mapping', 'question type', 'column type'],
        'paradigm shifts': ['paradigm shift', 'critical transformation'],
        # What the migration keeps
        'data preservation': ['preserv', 'fully supported', 'successfully migrated',
                              'what gets migrated'],
        # Also passes on a section split into size or complexity tiers (see has_tiers)
        'migration complexity': ['complexity'],
        # How the features that need more than a direct mapping are handled
        'special handling': ['special', 'edge case', 'complex transformation',
                             'complex field transformation', 'module-specific', 'partial support',
                             'manual adjustment', 'requires manual', 'manual work'],
        'known limitations': ['limitation', 'not supported', 'cannot be migrated',
                              'cannot migrate', 'lost in migration', 'non-migrated'],
        'validation checklist': ['checklist', 'validat', 'required checks', 'verification'],
    }
    
    # Words that name a size or complexity tier ("Small Projects (< 20 tasks)")
    COMPLEXITY_TIERS = ('simple', 'small', 'medium', 'large', 'complex', 'enterprise')
    
    # The README section that only applies to a migrator that makes AI calls
    AI_README_SECTION = 'AI-Powered Features'
    
    # What a README says when its migrator ships no AI client on purpose (issue #23).
    # Matched case-insensitively, with line breaks folded to spaces.
    NO_AI_STATEMENT = 'makes no ai calls'
    
    def __init__(self, base_path: str = None):
        """Initialize verifier with base path (default: the folder this script is in)"""
        if base_path is None:
            self.base_path = Path(__file__).resolve().parent
        else:
            self.base_path = Path(os.path.expanduser(base_path))
        self._live_files = {}
        self.results = {}
        self.summary = {
            'total_migrators': len(self.EXPECTED_MIGRATORS),
            'complete': 0,
            'partial': 0,
            'missing': 0,
            'scores': {}
        }
    
    def verify_all(self) -> Dict[str, Any]:
        """Run all verification checks"""
        print("="*80)
        print("COMPREHENSIVE MIGRATOR VERIFICATION")
        print("="*80)
        print(f"Checking {len(self.EXPECTED_MIGRATORS)} migrators...\n")
        
        for vendor in self.EXPECTED_MIGRATORS:
            print(f"\n{'='*40}")
            print(f"Verifying: {vendor.upper()}")
            print('='*40)
            
            vendor_path = self.base_path / vendor
            
            if not vendor_path.exists():
                self.results[vendor] = {
                    'status': 'missing',
                    'score': 0,
                    'issues': ['Migrator directory does not exist']
                }
                self.summary['missing'] += 1
                print(f"❌ {vendor}: Directory not found")
                continue
            
            # Run all checks
            score, issues = self.verify_migrator(vendor, vendor_path)
            
            # Determine status
            if score >= 95:
                status = 'complete'
                self.summary['complete'] += 1
                symbol = "✅"
            elif score >= 70:
                status = 'partial'
                self.summary['partial'] += 1
                symbol = "⚠️"
            else:
                status = 'incomplete'
                symbol = "❌"
            
            self.results[vendor] = {
                'status': status,
                'score': score,
                'issues': issues
            }
            self.summary['scores'][vendor] = score
            
            print(f"\n{symbol} {vendor}: {score}% complete ({status})")
            if issues:
                print("Issues found:")
                for issue in issues[:5]:  # Show first 5 issues
                    print(f"  - {issue}")
                if len(issues) > 5:
                    print(f"  ... and {len(issues)-5} more issues")
    
        self.generate_report()
        return self.results
    
    def verify_migrator(self, vendor: str, path: Path) -> Tuple[float, List[str]]:
        """Verify a single migrator"""
        checks_passed = 0
        total_checks = 0
        issues = []
        
        # 1. Check required files
        print("\n1. Checking required files...")
        file_score, file_issues = self.check_required_files(vendor, path)
        checks_passed += file_score
        total_checks += len(self.REQUIRED_FILES)
        issues.extend(file_issues)
        
        # 2. Check README completeness
        print("2. Checking README sections...")
        readme_score, readme_issues = self.check_readme_sections(path)
        checks_passed += readme_score
        total_checks += len(self.README_SECTIONS)
        issues.extend(readme_issues)
        
        # 3. Check code quality
        print("3. Checking code quality...")
        code_score, code_issues = self.check_code_quality(path)
        checks_passed += code_score
        total_checks += 10  # 10 code quality checks
        issues.extend(code_issues)
        
        # 4. Check AI integration
        print("4. Checking AI integration...")
        ai_score, ai_issues = self.check_ai_integration(path)
        checks_passed += ai_score
        total_checks += 5  # 5 AI checks
        issues.extend(ai_issues)
        
        # 5. Check OBJECT_MAPPING completeness
        print("5. Checking OBJECT_MAPPING documentation...")
        mapping_score, mapping_issues = self.check_object_mapping(path)
        checks_passed += mapping_score
        total_checks += 8  # 8 mapping sections
        issues.extend(mapping_issues)
        
        # 6. Check tests
        print("6. Checking test coverage...")
        test_score, test_issues = self.check_tests(path)
        checks_passed += test_score
        total_checks += 3  # 3 test checks
        issues.extend(test_issues)
        
        # Calculate final score
        score = (checks_passed / total_checks * 100) if total_checks > 0 else 0
        
        return round(score, 1), issues
    
    def check_required_files(self, vendor: str, path: Path) -> Tuple[int, List[str]]:
        """Check if all required files exist"""
        passed = 0
        issues = []
        no_ai = self.declares_no_ai(path)
        
        for file_type, file_pattern in self.REQUIRED_FILES.items():
            # Module names use underscores: process-street ships process_street_client.py
            file_path = file_pattern.replace('{vendor}', vendor.replace('-', '_'))
            full_path = path / file_path
            
            if file_type == 'ai_client' and no_ai:
                passed += 1  # no AI client on purpose, and the README says so
                continue
            
            if full_path.exists():
                passed += 1
                
                # Additional checks for specific files
                if file_type == 'migrate_script' and not os.access(full_path, os.X_OK):
                    issues.append(f"{file_path} is not executable")
                
                if file_type == 'requirements' and full_path.stat().st_size < 10:
                    issues.append(f"{file_path} appears to be empty")
            else:
                issues.append(f"Missing required file: {file_path}")
        
        return passed, issues
    
    def check_readme_sections(self, path: Path) -> Tuple[int, List[str]]:
        """Check if README has all required sections"""
        readme_path = path / 'README.md'
        
        if not readme_path.exists():
            return 0, ["README.md not found"]
        
        with open(readme_path, 'r') as f:
            content = f.read().lower()
        
        passed = 0
        issues = []
        no_ai = self.declares_no_ai(path)
        headings = self.headings(content)
        
        for section in self.README_SECTIONS:
            if section == self.AI_README_SECTION and no_ai:
                passed += 1  # a migrator that makes no AI calls has no AI features to list
            elif self.has_section(section, content, headings, self.README_SECTION_ALIASES):
                passed += 1
            else:
                issues.append(f"README missing section: {section}")
        
        return passed, issues
    
    def headings(self, text: str) -> List[str]:
        """The document's section titles, lower-cased, skipping fenced code
        blocks: every heading line, and every bold label that opens a line
        item ("- **Best practice**: Run during off-hours")."""
        return [title for _, title in self.titled_lines(text)]
    
    def titled_lines(self, text: str) -> List[Tuple[int, str]]:
        """(heading level, lower-cased title) for each section title outside
        code blocks. A bold label counts as a title one level below any heading."""
        found, in_code = [], False
        for line in text.split('\n'):
            if line.lstrip().startswith('```'):
                in_code = not in_code
                continue
            if in_code:
                continue
            heading = re.match(r'(#{1,6}) ', line)
            if heading:
                found.append((len(heading.group(1)), line.lower()))
                continue
            for label in re.findall(r'\*\*([^*\n]+?)\*\*\s*:|\*\*([^*\n]+?):\*\*', line):
                found.append((7, (label[0] or label[1]).lower()))
        return found
    
    def has_tiers(self, text: str) -> bool:
        """True when some heading's direct subsections include two or more size
        or complexity tiers, such as "Small Projects (< 20 tasks)" and "Large
        Projects (100+ tasks)" under "Migration Strategies"."""
        titles = [(level, title) for level, title in self.titled_lines(text) if level <= 6]
        for i, (level, _) in enumerate(titles):
            tiers = 0
            for child_level, child in titles[i + 1:]:
                if child_level <= level:
                    break
                if child_level == level + 1 and any(word in child for word in self.COMPLEXITY_TIERS):
                    tiers += 1
            if tiers >= 2:
                return True
        return False
    
    def has_section(self, section: str, content: str, headings: List[str],
                    aliases: Dict[str, List[str]]) -> bool:
        """True when the lower-cased document names the section, or a section title uses a word for it"""
        if section.lower() in content:
            return True
        return any(alias in heading for alias in aliases.get(section, []) for heading in headings)
    
    def live_files(self, path: Path) -> List[Path]:
        """src/main.py and every file it reaches through imports, inside this
        migrator or the repo's shared/ folder. A file nothing imports is not live,
        so code in it is not evidence of what the migrator does."""
        key = str(path)
        if key not in self._live_files:
            allowed = [path.resolve(), (self.base_path / 'shared').resolve()]
            found, todo = [], [path / 'src' / 'main.py']
            while todo:
                py_file = todo.pop().resolve()
                if py_file in found or not py_file.is_file():
                    continue
                if not any(self._is_inside(py_file, folder) for folder in allowed):
                    continue
                found.append(py_file)
                try:
                    with open(py_file, 'r') as f:
                        tree = ast.parse(f.read())
                except SyntaxError:
                    continue
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            todo.extend(self._resolve_import(alias.name, 0, py_file, path, []))
                    elif isinstance(node, ast.ImportFrom):
                        todo.extend(self._resolve_import(node.module or '', node.level, py_file, path,
                                                         [alias.name for alias in node.names]))
            self._live_files[key] = sorted(found)
        return self._live_files[key]
    
    def _is_inside(self, py_file: Path, folder: Path) -> bool:
        try:
            py_file.relative_to(folder)
            return True
        except ValueError:
            return False
    
    def _resolve_import(self, module: str, level: int, from_file: Path, path: Path,
                        names: List[str]) -> List[Path]:
        """The files one import statement loads. Absolute imports are tried from
        src/, the migrator folder, the repo root and shared/, the folders the
        migrators put on sys.path."""
        if level:
            root = from_file.parent
            for _ in range(level - 1):
                root = root.parent
            roots = [root]
        else:
            roots = [path / 'src', path, self.base_path, self.base_path / 'shared']
        parts = module.split('.') if module else []
        for root in roots:
            target = root.joinpath(*parts)
            found = []
            if parts and target.with_suffix('.py').is_file():
                found.append(target.with_suffix('.py'))
            if (target / '__init__.py').is_file():
                found.append(target / '__init__.py')
            found.extend(target / f'{name}.py' for name in names if (target / f'{name}.py').is_file())
            if found:
                # Importing a.b.c also runs a/__init__.py and a/b/__init__.py
                found.extend(root.joinpath(*parts[:i]) / '__init__.py' for i in range(1, len(parts))
                             if (root.joinpath(*parts[:i]) / '__init__.py').is_file())
                return found
        return []
    
    def _walk_in_functions(self, node, function=None):
        """Every node under this one, with the function that encloses it (None at module level)"""
        for child in ast.iter_child_nodes(node):
            yield function, child
            inner = child if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) else function
            yield from self._walk_in_functions(child, inner)
    
    def _mentions(self, node, word: str) -> bool:
        """True when a name or attribute under this node contains the word"""
        return any(word in (n.id if isinstance(n, ast.Name) else n.attr).lower()
                   for n in ast.walk(node) if isinstance(n, (ast.Name, ast.Attribute)))
    
    def live_evidence(self, path: Path) -> Dict[str, str]:
        """Where the migrator's live code rate-limits, batches and frees memory.
        
        Returns 'file:line' of the first piece of evidence for each, or None.
        Only live files count (see live_files), and only code at module level
        or in a function some live code calls by name. Comments and strings
        never count.
        
        - rate_limiting: the HTTP 429 status as a number, or a sleep inside a
          function whose name says rate_limit or throttle.
        - batch_processing: a call to a live function whose name says batch,
          or a range() step or slice bound that names a batch size.
        - memory_management: gc.collect(), or del of a whole variable (del of
          a dict key removes a key, it frees nothing).
        """
        trees = []
        for py_file in self.live_files(path):
            try:
                with open(py_file, 'r') as f:
                    trees.append((py_file, ast.parse(f.read())))
            except SyntaxError:
                continue
        
        def call_name(call):
            return call.func.attr if isinstance(call.func, ast.Attribute) else getattr(call.func, 'id', '')
        
        called, defined = set(), set()
        for _, tree in trees:
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    called.add(call_name(node))
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    defined.add(node.name)
        
        evidence = {'rate_limiting': None, 'batch_processing': None, 'memory_management': None}
        for py_file, tree in trees:
            try:
                where_file = py_file.relative_to(self.base_path.resolve())
            except ValueError:
                where_file = py_file
            for function, node in self._walk_in_functions(tree):
                if function is not None and function.name != '__init__' and function.name not in called:
                    continue
                found = []
                if isinstance(node, ast.Constant) and type(node.value) is int and node.value == 429:
                    found.append('rate_limiting')
                if (isinstance(node, ast.Call) and call_name(node) == 'sleep' and function is not None
                        and ('rate_limit' in function.name.lower() or 'throttl' in function.name.lower())):
                    found.append('rate_limiting')
                if isinstance(node, ast.Call):
                    name = call_name(node)
                    if name in defined and 'batch' in name.lower():
                        found.append('batch_processing')
                    if name == 'range' and len(node.args) == 3 and self._mentions(node.args[2], 'batch'):
                        found.append('batch_processing')
                    if (name == 'collect' and isinstance(node.func, ast.Attribute)
                            and isinstance(node.func.value, ast.Name) and node.func.value.id == 'gc'):
                        found.append('memory_management')
                if isinstance(node, ast.Slice) and node.upper is not None and self._mentions(node.upper, 'batch'):
                    found.append('batch_processing')
                if isinstance(node, ast.Delete) and any(isinstance(t, ast.Name) for t in node.targets):
                    found.append('memory_management')
                for kind in found:
                    if evidence[kind] is None:
                        evidence[kind] = f'{where_file}:{getattr(node, "lineno", 0)}'
        return evidence
    
    def phase_names(self, source: str) -> Tuple[set, set, List[str]]:
        """The phases main.py runs, read from its code rather than its words.
        
        Returns the names it dispatches on (a value compared to a `phase`
        variable, a list assigned to a `...phases` name, or a `_phase_<name>`
        method), the numbers of its 'Phase N: ...' strings, and every name seen.
        """
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return set(), set(), []
        named, numbered, seen = set(), set(), []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare):
                left = node.left
                left_name = left.id if isinstance(left, ast.Name) else getattr(left, 'attr', '')
                if 'phase' in left_name.lower():
                    for value in node.comparators:
                        if isinstance(value, ast.Constant) and isinstance(value.value, str):
                            named.add(value.value.lower())
            elif isinstance(node, ast.Assign) and isinstance(node.value, (ast.List, ast.Tuple)):
                targets = [t.id if isinstance(t, ast.Name) else getattr(t, 'attr', '') for t in node.targets]
                if any('phase' in t.lower() for t in targets):
                    named.update(e.value.lower() for e in node.value.elts
                                 if isinstance(e, ast.Constant) and isinstance(e.value, str))
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                match = re.match(r'_?phase_(?:\d+_)?(\w+)$', node.name)
                if match:
                    named.add(match.group(1).lower())
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                match = re.search(r'phase\s*(\d+)\s*:\s*(.+)', node.value, re.IGNORECASE)
                if match:
                    numbered.add(match.group(1))
                    seen.append(match.group(2).lower())
        seen.extend(named)
        return named, numbered, seen
    
    def has_five_phases(self, source: str) -> bool:
        """True when main.py runs at least five phases, among them a discovery,
        a users and a validation phase. Vendors name the template and instance
        phases in their own terms (projects, boards, pipes, cards), so those
        two are counted, not spelled."""
        named, numbered, seen = self.phase_names(source)
        return (max(len(named), len(numbered)) >= 5
                and any('discover' in name for name in seen)
                and any(word in name for name in seen for word in ('user', 'member', 'people'))
                and any('validat' in name for name in seen))
    
    def check_code_quality(self, path: Path) -> Tuple[int, List[str]]:
        """Check code quality indicators
        
        Most checks read src/main.py. Rate limiting, batch processing and
        memory management usually live in the API clients and transformers, so
        those three also pass on evidence anywhere in the live code."""
        passed = 0
        issues = []
        checks = {
            'has_logging': False,
            'has_error_handling': False,
            'has_docstrings': False,
            'has_type_hints': False,
            'has_5_phases': False,
            'has_checkpoint': False,
            'has_validation': False,
            'has_rate_limiting': False,
            'has_batch_processing': False,
            'has_memory_management': False
        }
        
        # Check main.py
        main_path = path / 'src' / 'main.py'
        if main_path.exists():
            with open(main_path, 'r') as f:
                content = f.read()
            
            # Check for various patterns
            if 'import logging' in content or 'from logging' in content:
                checks['has_logging'] = True
                passed += 1
            
            if 'try:' in content and 'except' in content:
                checks['has_error_handling'] = True
                passed += 1
            
            if '"""' in content or "'''" in content:
                checks['has_docstrings'] = True
                passed += 1
            
            if '-> ' in content and ': ' in content:
                checks['has_type_hints'] = True
                passed += 1
            
            evidence = self.live_evidence(path)
            
            # Check for 5-phase pattern
            phases = ['discovery', 'users', 'templates', 'instances', 'validation']
            if all(phase in content.lower() for phase in phases) or self.has_five_phases(content):
                checks['has_5_phases'] = True
                passed += 1
            else:
                issues.append("Missing 5-phase migration pattern")
            
            if 'checkpoint' in content.lower():
                checks['has_checkpoint'] = True
                passed += 1
            
            if 'validat' in content.lower():
                checks['has_validation'] = True
                passed += 1
            
            if ('rate' in content.lower() and 'limit' in content.lower()) or evidence['rate_limiting']:
                checks['has_rate_limiting'] = True
                passed += 1
            
            if 'batch' in content.lower() or evidence['batch_processing']:
                checks['has_batch_processing'] = True
                passed += 1
            
            if 'gc.collect' in content or 'del ' in content or evidence['memory_management']:
                checks['has_memory_management'] = True
                passed += 1
        else:
            issues.append("main.py not found")
        
        # Add issues for failed checks
        for check, status in checks.items():
            if not status:
                issues.append(f"Code quality issue: {check.replace('_', ' ')}")
        
        return passed, issues
    
    def ai_client_path(self, path: Path) -> Path:
        return path / 'src' / 'api' / 'ai_client.py'
    
    def declares_no_ai(self, path: Path) -> bool:
        """True when the migrator ships no AI client and its README says it makes no AI calls"""
        readme_path = path / 'README.md'
        if self.ai_client_path(path).exists() or not readme_path.exists():
            return False
        with open(readme_path, 'r') as f:
            content = ' '.join(f.read().lower().split())
        return self.NO_AI_STATEMENT in content
    
    def find_template_loads(self, path: Path) -> Tuple[List[Tuple[str, str]], set]:
        """Every prompt template the migrator's code loads through its AI client.
        
        Same rule as shared/tests/test_prompt_templates.py: a call whose first
        argument is a literal *.txt name, made on a method the AI client defines.
        That test reads all of src/; this reads only the live files under src/
        (see live_files), because a load in a file nothing imports never runs.
        Returns (template, 'file:line') pairs, and the names the client has
        in-code text for (bpmn writes its prompts from code).
        """
        with open(self.ai_client_path(path), 'r') as f:
            client_tree = ast.parse(f.read())
        methods, defaults = set(), set()
        for node in ast.walk(client_tree):
            if isinstance(node, ast.ClassDef):
                methods.update(item.name for item in node.body
                               if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)))
            if isinstance(node, ast.Dict):
                for key, value in zip(node.keys, node.values):
                    if (isinstance(key, ast.Constant) and isinstance(key.value, str)
                            and key.value.endswith('.txt')
                            and (isinstance(value, ast.JoinedStr)
                                 or (isinstance(value, ast.Constant) and isinstance(value.value, str)))):
                        defaults.add(key.value)
        
        loads = []
        src = (path / 'src').resolve()
        for py_file in self.live_files(path):
            if not self._is_inside(py_file, src):
                continue
            with open(py_file, 'r') as f:
                tree = ast.parse(f.read())
            for node in ast.walk(tree):
                if not (isinstance(node, ast.Call) and node.args
                        and isinstance(node.args[0], ast.Constant)
                        and isinstance(node.args[0].value, str)
                        and node.args[0].value.endswith('.txt')):
                    continue
                name = (node.func.attr if isinstance(node.func, ast.Attribute)
                        else getattr(node.func, 'id', None))
                if name in methods:
                    loads.append((node.args[0].value, f'{py_file.relative_to(path.resolve())}:{node.lineno}'))
        return loads, defaults
    
    def check_ai_integration(self, path: Path) -> Tuple[int, List[str]]:
        """Check AI integration completeness (5 checks)
        
        A migrator with no AI client passes all five when its README says it makes
        no AI calls, and fails all five otherwise. One with a client must load at
        least one prompt template, and every template it loads must be in its
        src/prompts/ folder or have in-code text.
        """
        passed = 0
        issues = []
        
        # Check for AI client
        ai_client_path = self.ai_client_path(path)
        if not ai_client_path.exists():
            if self.declares_no_ai(path):
                return 5, []
            return 0, ["AI client not found, and README.md does not say this migrator makes no AI calls"]
        
        passed += 1
        
        with open(ai_client_path, 'r') as f:
            content = f.read()
        
        if 'fallback' in content.lower():
            passed += 1
        else:
            issues.append("AI client missing fallback logic")
        
        # Check the prompt templates, in the folder ai_client.py reads them from
        prompts_dir = path / 'src' / 'prompts'
        loads, defaults = self.find_template_loads(path)
        missing = [(name, where) for name, where in loads
                   if name not in defaults and not (prompts_dir / name).is_file()]
        
        if prompts_dir.is_dir() or (loads and all(name in defaults for name, _ in loads)):
            passed += 1
        else:
            issues.append("Prompts directory not found: src/prompts/")
        
        if not loads:
            issues.append("AI client is never asked to load a prompt template")
        elif missing:
            for name, where in missing:
                issues.append(f"Prompt template not found: {where} loads src/prompts/{name}")
        else:
            passed += 1
        
        # Check .env.example for AI configuration
        env_path = path / '.env.example'
        if env_path.exists():
            with open(env_path, 'r') as f:
                content = f.read()
            
            if 'ANTHROPIC_API_KEY' in content or 'OPENAI_API_KEY' in content:
                passed += 1
            else:
                issues.append(".env.example missing AI API key configuration")
        
        return passed, issues
    
    def check_object_mapping(self, path: Path) -> Tuple[int, List[str]]:
        """Check OBJECT_MAPPING.md completeness"""
        mapping_path = path / 'OBJECT_MAPPING.md'
        
        if not mapping_path.exists():
            return 0, ["OBJECT_MAPPING.md not found"]
        
        with open(mapping_path, 'r') as f:
            content = f.read().lower()
        
        passed = 0
        issues = []
        headings = self.headings(content)
        
        for section in self.OBJECT_MAPPING_SECTIONS:
            if self.has_section(section, content, headings, self.OBJECT_MAPPING_SECTION_ALIASES):
                passed += 1
            elif section == 'migration complexity' and self.has_tiers(content):
                passed += 1
            else:
                issues.append(f"OBJECT_MAPPING missing section: {section}")
        
        # Check for minimum content
        lines = content.split('\n')
        if len(lines) < 200:
            issues.append(f"OBJECT_MAPPING seems incomplete ({len(lines)} lines, expected 200+)")
        
        return passed, issues
    
    def check_tests(self, path: Path) -> Tuple[int, List[str]]:
        """Check test coverage"""
        passed = 0
        issues = []
        
        # Check for tests directory
        tests_dir = path / 'tests'
        if tests_dir.exists():
            passed += 1
            
            # Check for test files
            test_files = list(tests_dir.glob('test_*.py'))
            if test_files:
                passed += 1
                
                # Check test content
                for test_file in test_files:
                    with open(test_file, 'r') as f:
                        content = f.read()
                    
                    if 'unittest' in content or 'pytest' in content:
                        passed += 1
                        break
            else:
                issues.append("No test files found in tests directory")
        else:
            issues.append("Tests directory not found")
        
        return passed, issues
    
    def generate_report(self):
        """Generate final verification report"""
        print("\n" + "="*80)
        print("VERIFICATION SUMMARY")
        print("="*80)
        
        # Overall statistics
        print(f"\nTotal Migrators: {self.summary['total_migrators']}")
        print(f"✅ Complete (95%+): {self.summary['complete']}")
        print(f"⚠️  Partial (70-94%): {self.summary['partial']}")
        print(f"❌ Missing/Incomplete: {self.summary['missing']}")
        
        # Average score
        if self.summary['scores']:
            avg_score = sum(self.summary['scores'].values()) / len(self.summary['scores'])
            print(f"\nAverage Completion Score: {avg_score:.1f}%")
        
        # Leaderboard
        print("\n" + "-"*40)
        print("MIGRATOR LEADERBOARD")
        print("-"*40)
        
        sorted_scores = sorted(self.summary['scores'].items(), key=lambda x: x[1], reverse=True)
        
        for i, (vendor, score) in enumerate(sorted_scores[:10], 1):
            status = self.results[vendor]['status']
            symbol = "✅" if status == 'complete' else "⚠️" if status == 'partial' else "❌"
            print(f"{i:2}. {symbol} {vendor:20} {score:5.1f}%")
        
        # Critical issues
        print("\n" + "-"*40)
        print("CRITICAL ISSUES TO ADDRESS")
        print("-"*40)
        
        critical_issues = {}
        for vendor, result in self.results.items():
            if result['status'] != 'complete':
                for issue in result['issues']:
                    if 'Missing required file' in issue or 'not found' in issue:
                        if issue not in critical_issues:
                            critical_issues[issue] = []
                        critical_issues[issue].append(vendor)
        
        for issue, vendors in list(critical_issues.items())[:10]:
            print(f"\n{issue}:")
            print(f"  Affects: {', '.join(vendors[:5])}" + 
                  (f" and {len(vendors)-5} others" if len(vendors) > 5 else ""))
        
        # Save detailed report
        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': self.summary,
            'results': self.results,
            'critical_issues': critical_issues
        }
        
        report_path = Path('verification_report.json')
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n\nDetailed report saved to: {report_path}")
        
        # Final verdict
        print("\n" + "="*80)
        if self.summary['complete'] == self.summary['total_migrators']:
            print("🎉 ALL MIGRATORS ARE COMPLETE AND PRODUCTION-READY! 🎉")
        elif self.summary['complete'] >= self.summary['total_migrators'] * 0.8:
            print("✅ MAJORITY OF MIGRATORS ARE COMPLETE")
            print(f"   {self.summary['total_migrators'] - self.summary['complete']} migrators need finishing touches")
        else:
            print("⚠️  MIGRATORS NEED MORE WORK")
            print(f"   Only {self.summary['complete']}/{self.summary['total_migrators']} are complete")
        print("="*80)
        
        return report
    
    def fix_common_issues(self):
        """Attempt to fix common issues automatically"""
        print("\n" + "="*80)
        print("ATTEMPTING AUTOMATIC FIXES")
        print("="*80)
        
        fixes_applied = 0
        
        for vendor, result in self.results.items():
            if result['status'] == 'complete':
                continue
            
            vendor_path = self.base_path / vendor
            
            for issue in result['issues']:
                # Fix missing requirements.txt
                if 'requirements.txt' in issue and 'Missing' in issue:
                    req_path = vendor_path / 'requirements.txt'
                    if not req_path.exists():
                        print(f"Creating requirements.txt for {vendor}")
                        with open(req_path, 'w') as f:
                            f.write("""python-dotenv>=1.0.0
requests>=2.31.0
anthropic>=0.18.0
pydantic>=2.0.0
tenacity>=8.2.0
""")
                        fixes_applied += 1
                
                # Fix non-executable migrate.sh
                if 'migrate.sh is not executable' in issue:
                    script_path = vendor_path / 'migrate.sh'
                    if script_path.exists():
                        print(f"Making migrate.sh executable for {vendor}")
                        os.chmod(script_path, 0o755)
                        fixes_applied += 1
                
                # A missing prompt template is not fixed here: an empty folder
                # would not give the AI client the template it loads.
        
        print(f"\nApplied {fixes_applied} automatic fixes")
        print("Please run verification again to see updated results")


def main():
    """Main verification entry point"""
    verifier = MigratorVerifier()
    
    # Run verification
    results = verifier.verify_all()
    
    # Offer to fix common issues
    if verifier.summary['complete'] < verifier.summary['total_migrators']:
        response = input("\nWould you like to attempt automatic fixes for common issues? (y/n): ")
        if response.lower() == 'y':
            verifier.fix_common_issues()
            
            # Re-run verification
            print("\nRe-running verification after fixes...")
            verifier = MigratorVerifier()
            results = verifier.verify_all()
    
    # Return success code based on completeness
    if verifier.summary['complete'] == verifier.summary['total_migrators']:
        return 0  # All complete
    elif verifier.summary['complete'] >= verifier.summary['total_migrators'] * 0.8:
        return 1  # Mostly complete
    else:
        return 2  # Needs work


if __name__ == '__main__':
    exit(main())