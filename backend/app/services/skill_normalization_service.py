import re
from typing import Optional, Dict, Set


# Canonical dictionary mapping aliases and variations to their standardized representation
SKILL_ALIASES: Dict[str, str] = {
    # Languages & Frameworks
    "js": "JavaScript",
    "javascript": "JavaScript",
    "ts": "TypeScript",
    "typescript": "TypeScript",
    "py": "Python",
    "python": "Python",
    "python3": "Python",
    "golang": "Go",
    "go": "Go",
    "c#": "C#",
    "csharp": "C#",
    "c++": "C++",
    "cpp": "C++",
    "react": "React",
    "reactjs": "React",
    "react.js": "React",
    "react native": "React Native",
    "reactnative": "React Native",
    "vue": "Vue.js",
    "vuejs": "Vue.js",
    "vue.js": "Vue.js",
    "angular": "Angular",
    "angularjs": "Angular",
    "angular.js": "Angular",
    "node": "Node.js",
    "nodejs": "Node.js",
    "node.js": "Node.js",
    "next": "Next.js",
    "nextjs": "Next.js",
    "next.js": "Next.js",
    "express": "Express.js",
    "expressjs": "Express.js",
    "fastapi": "FastAPI",
    "flask": "Flask",
    "django": "Django",
    "spring": "Spring Boot",
    "springboot": "Spring Boot",
    "spring boot": "Spring Boot",
    "dotnet": ".NET",
    ".net": ".NET",
    "dotnet core": ".NET Core",
    ".net core": ".NET Core",
    "ruby on rails": "Ruby on Rails",
    "rails": "Ruby on Rails",
    "ror": "Ruby on Rails",

    # Databases
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "postgre sql": "PostgreSQL",
    "psql": "PostgreSQL",
    "mysql": "MySQL",
    "mssql": "SQL Server",
    "sql server": "SQL Server",
    "sqlite": "SQLite",
    "mongodb": "MongoDB",
    "mongo": "MongoDB",
    "redis": "Redis",
    "elasticsearch": "Elasticsearch",
    "cassandra": "Cassandra",
    "dynamodb": "DynamoDB",
    "oracle": "Oracle DB",

    # Cloud, DevOps & Containers
    "aws": "Amazon Web Services (AWS)",
    "amazon web services": "Amazon Web Services (AWS)",
    "gcp": "Google Cloud Platform (GCP)",
    "google cloud": "Google Cloud Platform (GCP)",
    "azure": "Microsoft Azure",
    "microsoft azure": "Microsoft Azure",
    "k8s": "Kubernetes",
    "kubernetes": "Kubernetes",
    "docker": "Docker",
    "terraform": "Terraform",
    "ansible": "Ansible",
    "ci/cd": "CI/CD",
    "cicd": "CI/CD",
    "continuous integration": "CI/CD",
    "jenkins": "Jenkins",
    "github actions": "GitHub Actions",
    "gitlab ci": "GitLab CI",

    # AI / ML & Data
    "ml": "Machine Learning",
    "machine learning": "Machine Learning",
    "ai": "Artificial Intelligence",
    "artificial intelligence": "Artificial Intelligence",
    "dl": "Deep Learning",
    "deep learning": "Deep Learning",
    "nlp": "Natural Language Processing",
    "natural language processing": "Natural Language Processing",
    "llm": "Large Language Models",
    "llms": "Large Language Models",
    "large language models": "Large Language Models",
    "cv": "Computer Vision",
    "computer vision": "Computer Vision",
    "pytorch": "PyTorch",
    "torch": "PyTorch",
    "tensorflow": "TensorFlow",
    "tf": "TensorFlow",
    "scikit-learn": "Scikit-Learn",
    "sklearn": "Scikit-Learn",
    "pandas": "Pandas",
    "numpy": "NumPy",

    # Architecture, APIs & Standards
    "rest": "REST APIs",
    "restful": "REST APIs",
    "rest api": "REST APIs",
    "rest apis": "REST APIs",
    "graphql": "GraphQL",
    "grpc": "gRPC",
    "kafka": "Apache Kafka",
    "apache kafka": "Apache Kafka",
    "rabbitmq": "RabbitMQ",
    "microservices": "Microservices",
    "microservice": "Microservices",
    "oauth": "OAuth 2.0",
    "oauth2": "OAuth 2.0",
    "jwt": "JWT",
    "sql": "SQL",
    "nosql": "NoSQL",
    "git": "Git",
    "linux": "Linux",
    "bash": "Bash",
    "html": "HTML5",
    "html5": "HTML5",
    "css": "CSS3",
    "css3": "CSS3",
    "tailwind": "Tailwind CSS",
    "tailwindcss": "Tailwind CSS",
}


class SkillNormalizationService:
    """
    Standardizes skill names and aliases into canonical taxonomy representations.
    Ensures identical skills in different naming conventions match accurately.
    """

    def __init__(self, custom_aliases: Optional[Dict[str, str]] = None):
        self._aliases = dict(SKILL_ALIASES)
        if custom_aliases:
            for k, v in custom_aliases.items():
                self._aliases[k.lower().strip()] = v

    @staticmethod
    def clean_key(raw_skill: str) -> str:
        """Lowercases, normalizes whitespace and punctuation for dictionary key lookup."""
        if not raw_skill:
            return ""
        # Replace punctuation like dashes/underscores with spaces, except specific symbols like # or ++ or .
        cleaned = raw_skill.lower().strip()
        cleaned = re.sub(r"[\s_]+", " ", cleaned)
        return cleaned

    def normalize(self, raw_skill: Optional[str]) -> str:
        """
        Returns the standardized canonical name for a given skill string.
        If no canonical alias exists, returns a title-cased cleaned version.
        """
        if not raw_skill or not raw_skill.strip():
            return ""

        key = self.clean_key(raw_skill)
        if key in self._aliases:
            return self._aliases[key]

        # Check without punctuation
        simplified = re.sub(r"[^\w\s#+.]", "", key).strip()
        if simplified in self._aliases:
            return self._aliases[simplified]

        # Fallback to title-casing the cleaned string
        return raw_skill.strip()

    def are_skills_equivalent(self, skill_a: Optional[str], skill_b: Optional[str]) -> bool:
        """
        Checks whether two skill strings represent the exact same canonical skill.
        """
        if not skill_a or not skill_b:
            return False

        norm_a = self.normalize(skill_a).lower()
        norm_b = self.normalize(skill_b).lower()

        if norm_a == norm_b:
            return True

        # Check raw clean keys
        return self.clean_key(skill_a) == self.clean_key(skill_b)

    def matches(self, skill_a: Optional[str], skill_b: Optional[str]) -> bool:
        """
        Alias for are_skills_equivalent.
        """
        return self.are_skills_equivalent(skill_a, skill_b)

    def extract_matching_canonical_skills(self, text: str) -> Set[str]:

        """
        Scans free-text for canonical skills present in the dictionary.
        """
        if not text:
            return set()

        found = set()
        lower_text = f" {self.clean_key(text)} "
        for alias, canonical in self._aliases.items():
            pattern = rf"(?:\b|\s){re.escape(alias)}(?:\b|\s)"
            if re.search(pattern, lower_text):
                found.add(canonical)
        return found


# Global singleton instance
skill_normalizer = SkillNormalizationService()
