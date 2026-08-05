"""Default deterministic planner for EAG Chief Runtime."""

from eag.benchmark.templates import get_benchmark_plan
from eag.chief.runtime.models import Plan, PlanStep, RunContext


class DefaultPlanner:
    """Translates a goal into a deterministic execution plan."""

    def create_plan(self, context: RunContext) -> Plan:
        """
        Create a plan based on the run context.

        Priority order:
        1. If benchmark_id is provided and starts with 'EBS-', use template.
        2. If goal contains 'knowledge base' or 'fastapi', use the full app plan.
        3. If goal contains 'calculator' or benchmark_id == 'EBS-001', use calculator template.
        4. Otherwise, use a generic fallback plan.
        """
        # Extract benchmark ID from metadata
        benchmark_id = context.metadata.get("benchmark_id")
        print(f"DEBUG: goal_text='{context.goal_text}', benchmark_id={benchmark_id}")
        # 1. Use the template planner for known benchmark IDs
        if benchmark_id and benchmark_id.startswith("EBS-"):
            try:
                return get_benchmark_plan(benchmark_id)
            except KeyError:
                pass  # Fall through to other logic

        goal = context.goal_text.lower() if context.goal_text else ""

        # 2. New: Knowledge Base / FastAPI full application
        if "knowledge base" in goal or "fastapi" in goal:
            return self._create_knowledge_base_plan(context)

        # 3. Calculator / EBS‑001 fallback
        if "calculator" in goal or benchmark_id == "EBS-001":
            return get_benchmark_plan("EBS-001")

        # 4. Generic fallback for unknown goals
        return self._create_generic_plan(context)

    def _create_knowledge_base_plan(self, context: RunContext) -> Plan:
        """Create a full FastAPI knowledge base application plan."""
        steps: list[PlanStep] = []

        # Step 1: Initialize Git repository
        steps.append(PlanStep(
            step_id="step_1_git_init",
            name="Initialize Git Repository",
            capability_id="repository",
            metadata={"operation": "init"}
        ))

        # Step 2: Database models
        steps.append(PlanStep(
            step_id="step_2_models",
            name="Create Database Models",
            capability_id="workspace",
            dependencies=("step_1_git_init",),
            metadata={
                "operation": "write",
                "path": "models.py",
                "content": (
                    "from sqlalchemy import Column, Integer, String, Text, DateTime\n"
                    "from sqlalchemy.orm import declarative_base\n"
                    "from datetime import datetime\n\n"
                    "Base = declarative_base()\n\n"
                    "class Article(Base):\n"
                    "    __tablename__ = \"articles\"\n"
                    "    id = Column(Integer, primary_key=True, index=True)\n"
                    "    title = Column(String, index=True)\n"
                    "    content = Column(Text)\n"
                    "    tags = Column(String, index=True)\n"
                    "    created_at = Column(DateTime, default=datetime.utcnow)\n"
                    "    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)\n"
                )
            }
        ))

        # Step 3: Database connection
        steps.append(PlanStep(
            step_id="step_3_database",
            name="Create Database Connection",
            capability_id="workspace",
            dependencies=("step_2_models",),
            metadata={
                "operation": "write",
                "path": "database.py",
                "content": (
                    "from sqlalchemy import create_engine\n"
                    "from sqlalchemy.orm import sessionmaker\n"
                    "import models\n\n"
                    'SQLALCHEMY_DATABASE_URL = "sqlite:///./knowledge_base.db"\n\n'
                    "engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={\"check_same_thread\": False})\n"
                    "SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)\n\n"
                    "def init_db():\n"
                    "    models.Base.metadata.create_all(bind=engine)\n\n"
                    "def get_db():\n"
                    "    db = SessionLocal()\n"
                    "    try:\n"
                    "        yield db\n"
                    "    finally:\n"
                    "        db.close()\n"
                )
            }
        ))

        # Step 4: Main FastAPI application
        steps.append(PlanStep(
            step_id="step_4_main",
            name="Create FastAPI Application",
            capability_id="workspace",
            dependencies=("step_3_database",),
            metadata={
                "operation": "write",
                "path": "main.py",
                "content": (
                    "from fastapi import FastAPI, HTTPException, Depends\n"
                    "from sqlalchemy.orm import Session\n"
                    "from pydantic import BaseModel\n"
                    "from typing import List, Optional\n"
                    "import models, database\n\n"
                    'app = FastAPI(title="Personal Knowledge Base API")\n\n'
                    "@app.on_event(\"startup\")\n"
                    "def startup():\n"
                    "    database.init_db()\n\n"
                    "class ArticleBase(BaseModel):\n"
                    "    title: str\n"
                    "    content: str\n"
                    "    tags: Optional[str] = None\n\n"
                    "class ArticleCreate(ArticleBase):\n"
                    "    pass\n\n"
                    "class ArticleResponse(ArticleBase):\n"
                    "    id: int\n"
                    "    class Config:\n"
                    "        from_attributes = True\n\n"
                    "@app.post(\"/articles/\", response_model=ArticleResponse)\n"
                    "def create_article(article: ArticleCreate, db: Session = Depends(database.get_db)):\n"
                    "    db_article = models.Article(**article.dict())\n"
                    "    db.add(db_article)\n"
                    "    db.commit()\n"
                    "    db.refresh(db_article)\n"
                    "    return db_article\n\n"
                    "@app.get(\"/articles/\", response_model=List[ArticleResponse])\n"
                    "def list_articles(skip: int = 0, limit: int = 10, db: Session = Depends(database.get_db)):\n"
                    "    return db.query(models.Article).offset(skip).limit(limit).all()\n\n"
                    "@app.get(\"/articles/{article_id}\", response_model=ArticleResponse)\n"
                    "def get_article(article_id: int, db: Session = Depends(database.get_db)):\n"
                    "    article = db.query(models.Article).filter(models.Article.id == article_id).first()\n"
                    "    if not article:\n"
                    "        raise HTTPException(status_code=404, detail=\"Article not found\")\n"
                    "    return article\n\n"
                    "@app.put(\"/articles/{article_id}\", response_model=ArticleResponse)\n"
                    "def update_article(article_id: int, article: ArticleCreate, db: Session = Depends(database.get_db)):\n"
                    "    db_article = db.query(models.Article).filter(models.Article.id == article_id).first()\n"
                    "    if not db_article:\n"
                    "        raise HTTPException(status_code=404, detail=\"Article not found\")\n"
                    "    for key, value in article.dict().items():\n"
                    "        setattr(db_article, key, value)\n"
                    "    db.commit()\n"
                    "    db.refresh(db_article)\n"
                    "    return db_article\n\n"
                    "@app.delete(\"/articles/{article_id}\")\n"
                    "def delete_article(article_id: int, db: Session = Depends(database.get_db)):\n"
                    "    db_article = db.query(models.Article).filter(models.Article.id == article_id).first()\n"
                    "    if not db_article:\n"
                    "        raise HTTPException(status_code=404, detail=\"Article not found\")\n"
                    "    db.delete(db_article)\n"
                    "    db.commit()\n"
                    "    return {\"detail\": \"Article deleted\"}\n"
                )
            }
        ))

        # Step 5: Requirements file
        steps.append(PlanStep(
            step_id="step_5_requirements",
            name="Create Requirements File",
            capability_id="workspace",
            dependencies=("step_4_main",),
            metadata={
                "operation": "write",
                "path": "requirements.txt",
                "content": "fastapi\nuvicorn\nsqlalchemy\npydantic\n"
            }
        ))

        # Step 6: Dockerfile
        steps.append(PlanStep(
            step_id="step_6_dockerfile",
            name="Create Dockerfile",
            capability_id="workspace",
            dependencies=("step_5_requirements",),
            metadata={
                "operation": "write",
                "path": "Dockerfile",
                "content": (
                    "FROM python:3.12-slim\n"
                    "WORKDIR /app\n"
                    "COPY requirements.txt .\n"
                    "RUN pip install --no-cache-dir -r requirements.txt\n"
                    "COPY . .\n"
                    "EXPOSE 8000\n"
                    'CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]\n'
                )
            }
        ))

        # Step 7: Docker Compose
        steps.append(PlanStep(
            step_id="step_7_docker_compose",
            name="Create Docker Compose File",
            capability_id="workspace",
            dependencies=("step_6_dockerfile",),
            metadata={
                "operation": "write",
                "path": "docker-compose.yml",
                "content": (
                    "version: '3.8'\n"
                    "services:\n"
                    "  api:\n"
                    "    build: .\n"
                    "    ports:\n"
                    "      - \"8000:8000\"\n"
                    "    volumes:\n"
                    "      - ./data:/app/data\n"
                )
            }
        ))

        # Step 8: README
        steps.append(PlanStep(
            step_id="step_8_readme",
            name="Create README",
            capability_id="workspace",
            dependencies=("step_7_docker_compose",),
            metadata={
                "operation": "write",
                "path": "README.md",
                "content": (
                    "# Personal Knowledge Base API\n\n"
                    "A FastAPI application to store and manage personal knowledge base articles.\n\n"
                    "## Usage\n\n"
                    "```bash\n"
                    "docker compose up\n"
                    "```\n\n"
                    "Access the API at http://localhost:8000/docs"
                )
            }
        ))

        # Step 9: Commit everything
        steps.append(PlanStep(
            step_id="step_9_commit",
            name="Commit Implementation",
            capability_id="repository",
            dependencies=("step_8_readme",),
            metadata={"operation": "commit", "message": "feat: implement knowledge base API"}
        ))

        return Plan(steps=tuple(steps))

    def _create_generic_plan(self, context: RunContext) -> Plan:
        """Create a minimal generic plan for unknown goals."""
        return Plan(
            steps=(
                PlanStep(
                    step_id="step_1_git_init",
                    name="Initialize Git Repository",
                    capability_id="repository",
                    metadata={"operation": "init"},
                ),
                PlanStep(
                    step_id="step_2_readme",
                    name="Create README.md",
                    capability_id="workspace",
                    dependencies=("step_1_git_init",),
                    metadata={
                        "operation": "write",
                        "path": "README.md",
                        "content": f"# Project\n\n{context.goal_text}",
                    },
                ),
                PlanStep(
                    step_id="step_3_commit",
                    name="Commit Implementation",
                    capability_id="repository",
                    dependencies=("step_2_readme",),
                    metadata={"operation": "commit", "message": "Initial commit"},
                ),
            )
        )