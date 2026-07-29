"""
AIDP Tech Stack Scanner
Scans local project files to detect tech stack and updates controller

Usage:
  python scripts/tech_scan.py --project-id 1 --path D:\\Project\\openCode
"""

import os
import json
import argparse
import urllib.request

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def scan_tech_stack(project_path: str) -> dict:
    techs = set()
    frameworks = set()

    # Check package.json (Node/JS/TS)
    pkg_path = os.path.join(project_path, "package.json")
    if os.path.exists(pkg_path):
        techs.add("Node.js")
        with open(pkg_path, "r", encoding="utf-8", errors="ignore") as f:
            try:
                pkg = json.load(f)
                deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
                dep_names = set(deps.keys())
                if any("vue" in d.lower() for d in dep_names): frameworks.add("Vue")
                if any("react" in d.lower() for d in dep_names): frameworks.add("React")
                if any("next" in d.lower() for d in dep_names): frameworks.add("Next.js")
                if any("nuxt" in d.lower() for d in dep_names): frameworks.add("Nuxt")
                if any("angular" in d.lower() for d in dep_names): frameworks.add("Angular")
            except:
                pass

    # Check pom.xml (Java/Maven)
    pom_path = os.path.join(project_path, "pom.xml")
    if os.path.exists(pom_path):
        techs.add("Java")
        with open(pom_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read().lower()
            if "spring-boot" in content: frameworks.add("Spring Boot")
            if "spring-cloud" in content: frameworks.add("Spring Cloud")
            if "mybatis" in content: frameworks.add("MyBatis")

    # Check requirements.txt (Python)
    req_path = os.path.join(project_path, "requirements.txt")
    if os.path.exists(req_path):
        techs.add("Python")
        with open(req_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read().lower()
            if "fastapi" in content: frameworks.add("FastAPI")
            if "django" in content: frameworks.add("Django")
            if "flask" in content: frameworks.add("Flask")
            if "pytorch" in content or "tensorflow" in content: frameworks.add("ML/AI")

    # Check build.gradle (Kotlin/Gradle)
    gradle_path = os.path.join(project_path, "build.gradle")
    if os.path.exists(gradle_path):
        techs.add("Gradle")
        with open(gradle_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read().lower()
            if "kotlin" in content: techs.add("Kotlin")
            if "spring" in content: frameworks.add("Spring Boot")

    # Check Cargo.toml (Rust)
    cargo_path = os.path.join(project_path, "Cargo.toml")
    if os.path.exists(cargo_path):
        techs.add("Rust")
        with open(cargo_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read().lower()
            if "actix" in content: frameworks.add("Actix")
            if "axum" in content: frameworks.add("Axum")
            if "rocket" in content: frameworks.add("Rocket")

    # Check go.mod (Go)
    go_path = os.path.join(project_path, "go.mod")
    if os.path.exists(go_path):
        techs.add("Go")

    # Check .csproj or .sln (C#)
    csproj = [f for f in os.listdir(project_path) if f.endswith(".csproj") or f.endswith(".sln")]
    if csproj:
        techs.add("C#")
        techs.add(".NET")

    # Check Docker
    if os.path.exists(os.path.join(project_path, "Dockerfile")):
        techs.add("Docker")

    # Detect language from file extensions
    ext_counts = {}
    for root, dirs, files in os.walk(project_path):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in {"node_modules", "__pycache__", "venv", "dist", "build", "target"}]
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in (".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rs", ".rb", ".php", ".cs", ".swift", ".kt", ".vue", ".sql", ".yaml", ".yml", ".json", ".xml", ".html", ".css", ".scss", ".md"):
                ext_counts[ext] = ext_counts.get(ext, 0) + 1

    top_langs = {"python": ".py", "javascript": ".js", "typescript": ".ts", "java": ".java",
                 "go": ".go", "rust": ".rs"}
    for lang, ext in top_langs.items():
        if ext_counts.get(ext, 0) > 5:
            techs.add(lang.capitalize())

    return {
        "tech_stack": sorted(techs),
        "frameworks": sorted(frameworks),
        "language_extensions": {k: v for k, v in sorted(ext_counts.items(), key=lambda x: -x[1])[:10]},
    }


def update_controller(controller_url: str, project_id: int, tech_data: dict):
    payload = json.dumps({
        "tech_stack": json.dumps(tech_data["tech_stack"] + tech_data["frameworks"]),
    }).encode()
    req = urllib.request.Request(
        f"{controller_url}/api/projects/{project_id}",
        data=payload, headers={"Content-Type": "application/json"}, method="PUT"
    )
    try:
        with urllib.request.urlopen(req, timeout=10):
            print(f"  Updated project {project_id} tech_stack")
    except Exception as e:
        print(f"  Update failed: {e}")


def main():
    parser = argparse.ArgumentParser(description="AIDP Tech Stack Scanner")
    parser.add_argument("--project-id", type=int, required=True)
    parser.add_argument("--path", default=PROJECT_ROOT)
    parser.add_argument("--controller-url", default="http://192.168.0.100:8883")
    args = parser.parse_args()

    print(f"[tech-scan] Scanning {args.path}...")
    result = scan_tech_stack(args.path)
    print(f"  Tech stack: {', '.join(result['tech_stack']) or '(none)'}")
    print(f"  Frameworks: {', '.join(result['frameworks']) or '(none)'}")

    update_controller(args.controller_url, args.project_id, result)
    print("[tech-scan] Done!")


if __name__ == "__main__":
    main()