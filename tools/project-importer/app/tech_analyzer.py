"""Technology stack analyzer and official doc importer."""
import re
import xml.etree.ElementTree as ET
import json
import logging
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin
import httpx

logger = logging.getLogger(__name__)

# Official documentation URLs for common technologies
OFFICIAL_DOCS = {
    # Spring ecosystem
    "spring-boot": {
        "name": "Spring Boot",
        "base_url": "https://spring.io/projects/spring-boot",
        "doc_url": "https://docs.spring.io/spring-boot/docs/{version}/reference/html/",
        "default_version": "3.2.0",
    },
    "spring-cloud": {
        "name": "Spring Cloud",
        "base_url": "https://spring.io/projects/spring-cloud",
        "doc_url": "https://docs.spring.io/spring-cloud/docs/{version}/reference/html/",
        "default_version": "2023.0.0",
    },
    "spring-cloud-alibaba": {
        "name": "Spring Cloud Alibaba",
        "base_url": "https://github.com/alibaba/spring-cloud-alibaba",
        "doc_url": "https://sca.aliyun.com/docs/{version}/overview/terminology/",
        "default_version": "2022.0.0",
    },
    "spring-security": {
        "name": "Spring Security",
        "base_url": "https://spring.io/projects/spring-security",
        "doc_url": "https://docs.spring.io/spring-security/reference/{version}/",
        "default_version": "6.2",
    },
    # Alibaba ecosystem
    "nacos": {
        "name": "Nacos",
        "base_url": "https://nacos.io",
        "doc_url": "https://nacos.io/zh-cn/docs/{version}/what-is-nacos.html",
        "default_version": "v2.3",
    },
    "seata": {
        "name": "Seata",
        "base_url": "https://seata.io",
        "doc_url": "https://seata.io/zh-cn/docs/{version}/overview/what-is-seata.html",
        "default_version": "v2.0",
    },
    "sentinel": {
        "name": "Sentinel",
        "base_url": "https://sentinelguard.io",
        "doc_url": "https://sentinelguard.io/zh-cn/docs/{version}/introduction.html",
        "default_version": "v1.8",
    },
    "rocketmq": {
        "name": "Apache RocketMQ",
        "base_url": "https://rocketmq.apache.org",
        "doc_url": "https://rocketmq.apache.org/docs/{version}/",
        "default_version": "v5.0",
    },
    "dubbo": {
        "name": "Apache Dubbo",
        "base_url": "https://dubbo.apache.org",
        "doc_url": "https://dubbo.apache.org/zh-cn/docs/{version}/",
        "default_version": "v3.2",
    },
    # Databases
    "mysql": {
        "name": "MySQL",
        "base_url": "https://www.mysql.com",
        "doc_url": "https://dev.mysql.com/doc/refman/{version}/en/",
        "default_version": "8.0",
    },
    "postgresql": {
        "name": "PostgreSQL",
        "base_url": "https://www.postgresql.org",
        "doc_url": "https://www.postgresql.org/docs/{version}/",
        "default_version": "16",
    },
    "redis": {
        "name": "Redis",
        "base_url": "https://redis.io",
        "doc_url": "https://redis.io/docs/latest/",
        "default_version": "7.2",
    },
    "elasticsearch": {
        "name": "Elasticsearch",
        "base_url": "https://www.elastic.co/elasticsearch",
        "doc_url": "https://www.elastic.co/guide/en/elasticsearch/reference/{version}/",
        "default_version": "8.11",
    },
    # Message Queue
    "kafka": {
        "name": "Apache Kafka",
        "base_url": "https://kafka.apache.org",
        "doc_url": "https://kafka.apache.org/{version}/documentation.html",
        "default_version": "3.6",
    },
    "rabbitmq": {
        "name": "RabbitMQ",
        "base_url": "https://www.rabbitmq.com",
        "doc_url": "https://www.rabbitmq.com/docs",
        "default_version": "3.12",
    },
    # Cache
    "redisson": {
        "name": "Redisson",
        "base_url": "https://redisson.org",
        "doc_url": "https://github.com/redisson/redisson/wiki",
        "default_version": "3.24",
    },
    # Tools
    "mybatis-plus": {
        "name": "MyBatis-Plus",
        "base_url": "https://baomidou.com",
        "doc_url": "https://baomidou.com/pages/{version}/",
        "default_version": "v3.5",
    },
    "mybatis": {
        "name": "MyBatis",
        "base_url": "https://mybatis.org",
        "doc_url": "https://mybatis.org/mybatis-{version}/",
        "default_version": "3.5",
    },
    "hutool": {
        "name": "Hutool",
        "base_url": "https://hutool.cn",
        "doc_url": "https://hutool.cn/docs/{version}/",
        "default_version": "v5.8",
    },
    "xxl-job": {
        "name": "XXL-JOB",
        "base_url": "https://www.xuxueli.com/xxl-job",
        "doc_url": "https://www.xuxueli.com/xxl-job/{version}/",
        "default_version": "v2.4",
    },
    "snailjob": {
        "name": "SnailJob",
        "base_url": "https://snailjob.opensnail.com",
        "doc_url": "https://snailjob.opensnail.com/docs/",
        "default_version": "v1.0",
    },
    "sa-token": {
        "name": "Sa-Token",
        "base_url": "https://sa-token.cc",
        "doc_url": "https://sa-token.cc/doc.html",
        "default_version": "v1.37",
    },
    # Frontend
    "vue": {
        "name": "Vue.js",
        "base_url": "https://vuejs.org",
        "doc_url": "https://vuejs.org/guide/introduction.html",
        "default_version": "3.4",
    },
    "element-plus": {
        "name": "Element Plus",
        "base_url": "https://element-plus.org",
        "doc_url": "https://element-plus.org/zh-CN/guide/design.html",
        "default_version": "2.5",
    },
    "axios": {
        "name": "Axios",
        "base_url": "https://axios-http.com",
        "doc_url": "https://axios-http.com/docs/intro",
        "default_version": "1.6",
    },
    "vite": {
        "name": "Vite",
        "base_url": "https://vitejs.dev",
        "doc_url": "https://vitejs.dev/guide/",
        "default_version": "5.0",
    },
    # Container & Cloud
    "docker": {
        "name": "Docker",
        "base_url": "https://www.docker.com",
        "doc_url": "https://docs.docker.com/",
        "default_version": "24.0",
    },
    "kubernetes": {
        "name": "Kubernetes",
        "base_url": "https://kubernetes.io",
        "doc_url": "https://kubernetes.io/docs/home/",
        "default_version": "1.29",
    },
    # Logging
    "logback": {
        "name": "Logback",
        "base_url": "https://logback.qos.ch",
        "doc_url": "https://logback.qos.ch/documentation.html",
        "default_version": "1.4",
    },
    "log4j2": {
        "name": "Log4j2",
        "base_url": "https://logging.apache.org/log4j/2.x/",
        "doc_url": "https://logging.apache.org/log4j/2.x/manual/",
        "default_version": "2.22",
    },
}

# Technology detection patterns
TECH_PATTERNS = {
    # From artifactId or groupId
    "spring-boot-starter": "spring-boot",
    "spring-cloud-starter": "spring-cloud",
    "spring-cloud-alibaba": "spring-cloud-alibaba",
    "spring-security": "spring-security",
    "nacos-client": "nacos",
    "nacos-config": "nacos",
    "seata-spring-boot-starter": "seata",
    "sentinel-core": "sentinel",
    "rocketmq-spring-boot-starter": "rocketmq",
    "dubbo-spring-boot-starter": "dubbo",
    "mysql-connector": "mysql",
    "postgresql": "postgresql",
    "lettuce-core": "redis",
    "redisson": "redisson",
    "elasticsearch-rest": "elasticsearch",
    "kafka-clients": "kafka",
    "spring-kafka": "kafka",
    "spring-rabbit": "rabbitmq",
    "amqp-client": "rabbitmq",
    "mybatis-plus": "mybatis-plus",
    "mybatis-spring": "mybatis",
    "hutool": "hutool",
    "xxl-job-core": "xxl-job",
    "snail-job": "snailjob",
    "sa-token": "sa-token",
    "vue": "vue",
    "element-plus": "element-plus",
    "axios": "axios",
    "vite": "vite",
    "logback-classic": "logback",
    "log4j-core": "log4j2",
}


class TechAnalyzer:
    """Analyze project technology stack from dependency files."""
    
    def __init__(self):
        self.detected_techs: Dict[str, dict] = {}
    
    def analyze_project(self, project_path: str) -> List[dict]:
        """Analyze project and return list of detected technologies."""
        techs = []
        
        # Try Maven
        pom_path = f"{project_path}/pom.xml"
        import os
        if os.path.exists(pom_path):
            techs.extend(self._analyze_pom(pom_path))
        
        # Try Gradle
        gradle_path = f"{project_path}/build.gradle"
        if os.path.exists(gradle_path):
            techs.extend(self._analyze_gradle(gradle_path))
        
        # Try package.json
        package_path = f"{project_path}/package.json"
        if os.path.exists(package_path):
            techs.extend(self._analyze_package_json(package_path))
        
        # Try requirements.txt
        requirements_path = f"{project_path}/requirements.txt"
        if os.path.exists(requirements_path):
            techs.extend(self._analyze_requirements(requirements_path))
        
        # Deduplicate by tech key
        seen = set()
        unique_techs = []
        for tech in techs:
            if tech["key"] not in seen:
                seen.add(tech["key"])
                unique_techs.append(tech)
        
        return unique_techs
    
    def _analyze_pom(self, pom_path: str) -> List[dict]:
        """Parse pom.xml and extract dependencies."""
        techs = []
        
        try:
            tree = ET.parse(pom_path)
            root = tree.getroot()
            
            # Handle namespace
            ns = {"m": "http://maven.apache.org/POM/4.0.0"}
            
            # Extract parent info
            parent = root.find("m:parent", ns)
            if parent is not None:
                parent_group = parent.findtext("m:groupId", "", ns)
                parent_artifact = parent.findtext("m:artifactId", "", ns)
                parent_version = parent.findtext("m:version", "", ns)
                
                if "spring-boot" in parent_artifact:
                    version = self._extract_version(parent_version)
                    techs.append(self._create_tech_info("spring-boot", version))
                elif "spring-cloud" in parent_artifact:
                    version = self._extract_version(parent_version)
                    techs.append(self._create_tech_info("spring-cloud", version))
            
            # Extract dependencies
            deps = root.find("m:dependencies", ns)
            if deps is not None:
                for dep in deps.findall("m:dependency", ns):
                    group_id = dep.findtext("m:groupId", "", ns)
                    artifact_id = dep.findtext("m:artifactId", "", ns)
                    version = dep.findtext("m:version", "", ns)
                    
                    tech_key = self._match_tech(artifact_id, group_id)
                    if tech_key:
                        extracted_version = self._extract_version(version) if version else None
                        techs.append(self._create_tech_info(tech_key, extracted_version))
            
            # Also check dependencyManagement
            dep_mgmt = root.find("m:dependencyManagement", ns)
            if dep_mgmt is not None:
                deps = dep_mgmt.find("m:dependencies", ns)
                if deps is not None:
                    for dep in deps.findall("m:dependency", ns):
                        group_id = dep.findtext("m:groupId", "", ns)
                        artifact_id = dep.findtext("m:artifactId", "", ns)
                        version = dep.findtext("m:version", "", ns)
                        
                        tech_key = self._match_tech(artifact_id, group_id)
                        if tech_key:
                            extracted_version = self._extract_version(version) if version else None
                            techs.append(self._create_tech_info(tech_key, extracted_version))
        
        except Exception as e:
            logger.error(f"Failed to parse pom.xml: {e}")
        
        return techs
    
    def _analyze_gradle(self, gradle_path: str) -> List[dict]:
        """Parse build.gradle and extract dependencies."""
        techs = []
        
        try:
            with open(gradle_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Match implementation/compile dependencies
            pattern = r'(implementation|compile|api)\s+[\'"]([^\'"]+)[\'"]'
            matches = re.findall(pattern, content)
            
            for _, dep_str in matches:
                # Format: group:name:version
                parts = dep_str.split(':')
                if len(parts) >= 2:
                    group_id = parts[0]
                    artifact_id = parts[1]
                    version = parts[2] if len(parts) > 2 else None
                    
                    tech_key = self._match_tech(artifact_id, group_id)
                    if tech_key:
                        extracted_version = self._extract_version(version) if version else None
                        techs.append(self._create_tech_info(tech_key, extracted_version))
        
        except Exception as e:
            logger.error(f"Failed to parse build.gradle: {e}")
        
        return techs
    
    def _analyze_package_json(self, package_path: str) -> List[dict]:
        """Parse package.json and extract dependencies."""
        techs = []
        
        try:
            with open(package_path, 'r', encoding='utf-8', errors='ignore') as f:
                data = json.load(f)
            
            # Check all dependency types
            dep_types = ["dependencies", "devDependencies", "peerDependencies"]
            for dep_type in dep_types:
                deps = data.get(dep_type, {})
                for pkg_name, version in deps.items():
                    tech_key = self._match_tech(pkg_name, "")
                    if tech_key:
                        extracted_version = self._extract_version(version)
                        techs.append(self._create_tech_info(tech_key, extracted_version))
        
        except Exception as e:
            logger.error(f"Failed to parse package.json: {e}")
        
        return techs
    
    def _analyze_requirements(self, req_path: str) -> List[dict]:
        """Parse requirements.txt and extract packages."""
        techs = []
        
        try:
            with open(req_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        # Format: package==version or package>=version
                        match = re.match(r'^([a-zA-Z0-9_-]+)[=<>!~]+(.+)', line)
                        if match:
                            pkg_name = match.group(1)
                            version = match.group(2)
                            tech_key = self._match_tech(pkg_name, "")
                            if tech_key:
                                extracted_version = self._extract_version(version)
                                techs.append(self._create_tech_info(tech_key, extracted_version))
        
        except Exception as e:
            logger.error(f"Failed to parse requirements.txt: {e}")
        
        return techs
    
    def _match_tech(self, artifact_id: str, group_id: str) -> Optional[str]:
        """Match artifact to technology key."""
        artifact_lower = artifact_id.lower()
        group_lower = group_id.lower()
        
        for pattern, tech_key in TECH_PATTERNS.items():
            if pattern in artifact_lower or pattern in group_lower:
                return tech_key
        
        return None
    
    def _extract_version(self, version_str: str) -> Optional[str]:
        """Extract version number from string."""
        if not version_str:
            return None
        
        # Remove prefixes like 'v', '~', '^', '>='
        cleaned = re.sub(r'^[v~^>=<]+', '', version_str.strip())
        
        # Extract major.minor version
        match = re.match(r'(\d+)(?:\.(\d+))?', cleaned)
        if match:
            major = match.group(1)
            minor = match.group(2)
            if minor:
                return f"{major}.{minor}"
            return major
        
        return None
    
    def _create_tech_info(self, tech_key: str, version: Optional[str] = None) -> dict:
        """Create technology info dict."""
        doc_info = OFFICIAL_DOCS.get(tech_key, {})
        
        actual_version = version or doc_info.get("default_version", "latest")
        doc_url = doc_info.get("doc_url", "").format(version=actual_version)
        
        return {
            "key": tech_key,
            "name": doc_info.get("name", tech_key),
            "version": actual_version,
            "doc_url": doc_url,
            "base_url": doc_info.get("base_url", ""),
            "has_doc": bool(doc_url),
        }


class AutoDocImporter:
    """Automatically import official docs to knowledge base."""
    
    def __init__(self, knowledge_base_url: str = "http://127.0.0.1:18081"):
        self.knowledge_url = knowledge_base_url
    
    async def import_tech_docs(
        self, 
        techs: List[dict], 
        project_id: str,
        workspace_id: str = "default"
    ) -> List[dict]:
        """Import official docs for detected technologies."""
        imported = []
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            for tech in techs:
                if not tech.get("has_doc"):
                    continue
                
                try:
                    # First, create knowledge base for this tech
                    kb_result = await self._create_knowledge_base(client, tech)
                    if not kb_result:
                        continue
                    
                    kb_id = kb_result["kb_id"]
                    
                    # Then import the doc URL
                    import_result = await self._import_doc_url(
                        client, tech["doc_url"], kb_id, tech["name"]
                    )
                    
                    imported.append({
                        "tech": tech["name"],
                        "kb_id": kb_id,
                        "kb_name": kb_result["kb_name"],
                        "doc_url": tech["doc_url"],
                        "status": "success",
                        "documents_imported": import_result.get("count", 0),
                    })
                
                except Exception as e:
                    logger.error(f"Failed to import docs for {tech['name']}: {e}")
                    imported.append({
                        "tech": tech["name"],
                        "status": "error",
                        "error": str(e),
                    })
        
        return imported
    
    async def _create_knowledge_base(self, client: httpx.AsyncClient, tech: dict) -> Optional[dict]:
        """Create a knowledge base for the technology."""
        kb_name = f"{tech['name']} 官方文档"
        slug = f"{tech['key']}-docs"
        
        try:
            resp = await client.post(
                f"{self.knowledge_url}/api/knowledge-bases",
                json={
                    "name": kb_name,
                    "slug": slug,
                    "description": f"{tech['name']} 官方文档 (版本: {tech['version']})",
                    "kb_level": "framework",
                    "domains": ["documentation", tech["key"]],
                    "tech_stack": [tech["key"]],
                    "keywords": [tech["name"], tech["key"], "official", "documentation"],
                    "visibility": "public",
                    "chunk_size": 512,
                }
            )
            
            if resp.status_code == 200 or resp.status_code == 201:
                data = resp.json()
                return {
                    "kb_id": data.get("data", {}).get("id"),
                    "kb_name": kb_name,
                }
            elif resp.status_code == 400:  # KB might already exist
                # Try to get existing KB
                list_resp = await client.get(
                    f"{self.knowledge_url}/api/knowledge-bases?slug={slug}"
                )
                if list_resp.status_code == 200:
                    data = list_resp.json()
                    items = data.get("data", {}).get("items", [])
                    if items:
                        return {
                            "kb_id": items[0]["id"],
                            "kb_name": kb_name,
                        }
        
        except Exception as e:
            logger.error(f"Failed to create KB for {tech['name']}: {e}")
        
        return None
    
    async def _import_doc_url(
        self, 
        client: httpx.AsyncClient, 
        url: str, 
        kb_id: str,
        tech_name: str
    ) -> dict:
        """Import document from URL to knowledge base."""
        try:
            # Use the import-web API
            resp = await client.post(
                f"{self.knowledge_url}/api/import-web/direct-import",
                json={
                    "url": url,
                    "kb_name": f"{tech_name} 文档",
                    "kb_level": "framework",
                    "auto_detect": True,
                }
            )
            
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "success": True,
                    "count": data.get("data", {}).get("document_count", 0),
                }
            else:
                return {
                    "success": False,
                    "error": resp.text,
                }
        
        except Exception as e:
            logger.error(f"Failed to import doc from {url}: {e}")
            return {"success": False, "error": str(e)}


# Convenience function for main.py
def analyze_project_techs(project_path: str) -> List[dict]:
    """Analyze project and return detected technologies."""
    analyzer = TechAnalyzer()
    return analyzer.analyze_project(project_path)


async def auto_import_official_docs(
    techs: List[dict],
    project_id: str,
    knowledge_base_url: str = "http://127.0.0.1:18081"
) -> List[dict]:
    """Automatically import official docs for technologies."""
    importer = AutoDocImporter(knowledge_base_url)
    return await importer.import_tech_docs(techs, project_id)
