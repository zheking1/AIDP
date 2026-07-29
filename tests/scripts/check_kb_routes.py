import sys
sys.path.insert(0, "/app")
from app.modules.knowledge.routes import router
print(f"{len(router.routes)} routes")
for r in router.routes[:5]:
    print(f"  {r.methods} {r.path}")