import hashlib
from typing import Dict, List
from datetime import datetime


class IncrementalAnalyzer:
    """增量分析器"""

    def __init__(self):
        self.cache: Dict[str, dict] = {}

    def analyze(self, files: List[Dict], force_full: bool = False) -> Dict:
        if force_full:
            return self._full_analysis(files)

        changed, unchanged = self._detect_changes(files)
        changed_results = []
        for f in changed:
            r = self._analyze_file(f)
            changed_results.append(r)
            self.cache[f["path"]] = {"hash": self._hash(f.get("content", "")), "result": r,
                                       "timestamp": datetime.now()}

        all_results = changed_results
        for f in unchanged:
            if f["path"] in self.cache:
                all_results.append(self.cache[f["path"]]["result"])

        return {"files_analyzed": len(changed), "files_cached": len(unchanged),
                "results": all_results, "analysis_type": "incremental"}

    def _full_analysis(self, files: List[Dict]) -> Dict:
        results = []
        for f in files:
            r = self._analyze_file(f)
            results.append(r)
            self.cache[f["path"]] = {"hash": self._hash(f.get("content", "")), "result": r,
                                       "timestamp": datetime.now()}
        return {"files_analyzed": len(files), "files_cached": 0,
                "results": results, "analysis_type": "full"}

    def _detect_changes(self, files: List[Dict]) -> tuple:
        changed, unchanged = [], []
        for f in files:
            h = self._hash(f.get("content", ""))
            if f["path"] in self.cache and self.cache[f["path"]]["hash"] == h:
                unchanged.append(f)
            else:
                changed.append(f)
        return changed, unchanged

    def _hash(self, content: str) -> str:
        return hashlib.md5(content.encode()).hexdigest()

    def _analyze_file(self, f: Dict) -> Dict:
        return {"file": f["path"], "issues": [], "metrics": {}}