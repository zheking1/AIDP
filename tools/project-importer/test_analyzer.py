import sys
sys.path.insert(0, '/app')
from app.tech_analyzer import TechAnalyzer

analyzer = TechAnalyzer()
techs = analyzer._analyze_pom('/tmp/test-project/pom.xml')
print('Detected:', len(techs))
for t in techs:
    print(f'  - {t["name"]}: {t["version"]}')