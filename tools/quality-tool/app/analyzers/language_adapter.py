from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from dataclasses import dataclass


class LanguageAdapter(ABC):
    @abstractmethod
    def parse(self, code: str) -> Dict:
        ...

    @abstractmethod
    def calculate_complexity(self, ast: Dict) -> float:
        ...

    @abstractmethod
    def detect_issues(self, ast: Dict) -> List[Dict]:
        ...

    @abstractmethod
    def get_metrics(self, ast: Dict) -> Dict:
        ...


class PythonAdapter(LanguageAdapter):
    extensions = [".py"]
    max_func_len = 50
    max_params = 5

    def parse(self, code: str) -> Dict:
        import ast as ast_mod
        try:
            tree = ast_mod.parse(code)
            return {"type": "module", "functions": self._count_functions(tree), "classes": self._count_classes(tree), "lines": len(code.split("\n"))}
        except SyntaxError as e:
            return {"type": "error", "message": str(e)}

    def calculate_complexity(self, ast: Dict) -> float:
        if ast.get("type") == "error":
            return 0.0
        return 1.0 + ast.get("functions", 0) * 0.1 + ast.get("classes", 0) * 0.2

    def detect_issues(self, ast: Dict) -> List[Dict]:
        issues = []
        if ast.get("functions", 0) > self.max_func_len:
            issues.append({"type": "too_many_functions", "severity": "warning", "message": f"文件包含 {ast['functions']} 个函数"})
        return issues

    def get_metrics(self, ast: Dict) -> Dict:
        return {"functions": ast.get("functions", 0), "classes": ast.get("classes", 0), "lines": ast.get("lines", 0)}

    def _count_functions(self, tree) -> int:
        import ast as ast_mod
        return sum(1 for n in ast_mod.walk(tree) if isinstance(n, ast_mod.FunctionDef))

    def _count_classes(self, tree) -> int:
        import ast as ast_mod
        return sum(1 for n in ast_mod.walk(tree) if isinstance(n, ast_mod.ClassDef))


class JavaScriptAdapter(LanguageAdapter):
    extensions = [".js", ".ts", ".jsx", ".tsx"]
    max_callback_depth = 3

    def parse(self, code: str) -> Dict:
        import re
        funcs = len(re.findall(r'(?:function\s+\w+|const\s+\w+\s*=\s*(?:async\s*)?\()', code))
        classes = len(re.findall(r'class\s+\w+', code))
        return {"type": "program", "functions": funcs, "classes": classes, "lines": len(code.split("\n"))}

    def calculate_complexity(self, ast: Dict) -> float:
        return 1.0 + ast.get("functions", 0) * 0.1

    def detect_issues(self, ast: Dict) -> List[Dict]:
        return []

    def get_metrics(self, ast: Dict) -> Dict:
        return {"functions": ast.get("functions", 0), "classes": ast.get("classes", 0), "lines": ast.get("lines", 0)}


class LanguageManager:
    def __init__(self):
        self.adapters = {
            "python": PythonAdapter(),
            "javascript": JavaScriptAdapter(),
            "typescript": JavaScriptAdapter(),
        }

    def get_adapter(self, file_path: str) -> Optional[LanguageAdapter]:
        for lang, adapter in self.adapters.items():
            if any(file_path.endswith(ext) for ext in adapter.extensions):
                return adapter
        return None

    def get_supported_languages(self) -> List[str]:
        return list(self.adapters.keys())