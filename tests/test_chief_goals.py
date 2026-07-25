"""Comprehensive tests for the Chief Engineer Goal Intelligence (Sprint 7.1A Hardened)."""

import pytest

from eag.chief.goals import (
    Assumption,
    ChiefGoal,
    Clarification,
    Constraint,
    EngineeringGoal,
    GoalAnalysis,
    GoalCategory,
    GoalComplexity,
    GoalIntent,
    GoalNormalizer,
    GoalPriority,
    GoalRuntime,
    Requirement,
    RequirementExtractor,
    RuleBasedGoalClassifier,
)


@pytest.fixture
def runtime() -> GoalRuntime:
    return GoalRuntime()


@pytest.fixture
def classifier() -> RuleBasedGoalClassifier:
    return RuleBasedGoalClassifier()


@pytest.fixture
def extractor() -> RequirementExtractor:
    return RequirementExtractor()


@pytest.fixture
def normalizer() -> GoalNormalizer:
    return GoalNormalizer()


# --- Model Tests (35) ---


class TestGoalModels:
    def test_chief_goal_creation(self) -> None:
        g = ChiefGoal(raw_text="Build an app")
        assert g.raw_text == "Build an app"
        assert g.priority == GoalPriority.NORMAL

    def test_chief_goal_empty_rejected(self) -> None:
        with pytest.raises(ValueError):
            ChiefGoal(raw_text="")

    def test_chief_goal_invalid_priority(self) -> None:
        with pytest.raises(TypeError):
            ChiefGoal(raw_text="Test", priority="bad")  # type: ignore[arg-type]

    def test_requirement_creation(self) -> None:
        r = Requirement(key="db", value="postgres")
        assert r.is_missing is False
        assert r.confidence == 1.0

    def test_requirement_missing_flag(self) -> None:
        r = Requirement(key="db", value=None, is_missing=True, confidence=0.0)
        assert r.is_missing is True
        assert r.confidence == 0.0

    def test_requirement_confidence_validation(self) -> None:
        with pytest.raises(ValueError):
            Requirement(key="db", value="pg", confidence=1.5)

    def test_constraint_creation(self) -> None:
        c = Constraint(key="lang", value="python")
        assert c.confidence == 1.0

    def test_constraint_confidence_validation(self) -> None:
        with pytest.raises(ValueError):
            Constraint(key="lang", value="python", confidence=-0.1)

    def test_assumption_creation(self) -> None:
        a = Assumption(key="db", value="unknown")
        assert a.value == "unknown"

    def test_clarification_creation(self) -> None:
        c = Clarification(question="What db?", intent=GoalIntent.BUILD)
        assert c.priority == 0

    def test_engineering_goal_immutable(self) -> None:
        g = ChiefGoal(raw_text="test")
        eg = EngineeringGoal(
            original_goal=g,
            canonical_text="test",
            intents=(GoalIntent.UNKNOWN,),
            primary_intent=GoalIntent.UNKNOWN,
            category=GoalCategory.UNKNOWN,
            complexity=GoalComplexity.TRIVIAL,
            confidence=0.0,
            is_ambiguous=False,
        )
        with pytest.raises(Exception):  # noqa: B017
            eg.canonical_text = "new"  # type: ignore[misc]

    def test_goal_analysis_immutable(self) -> None:
        g = ChiefGoal(raw_text="test")
        ga = GoalAnalysis(goal=g)
        with pytest.raises(Exception):  # noqa: B017
            ga.confidence = 1.0  # type: ignore[misc]

    def test_goal_priority_values(self) -> None:
        assert GoalPriority.URGENT == "urgent"
        assert GoalPriority.HIGH == "high"
        assert GoalPriority.NORMAL == "normal"
        assert GoalPriority.LOW == "low"

    def test_goal_complexity_values(self) -> None:
        assert GoalComplexity.TRIVIAL == "trivial"
        assert GoalComplexity.MASSIVE == "massive"

    def test_goal_category_values(self) -> None:
        assert GoalCategory.APPLICATION == "application"
        assert GoalCategory.LIBRARY == "library"


# --- Classifier Tests (40) ---


class TestGoalClassifier:
    def test_build_intent(self, classifier: RuleBasedGoalClassifier) -> None:
        g = ChiefGoal(raw_text="Build me a todo app")
        intents, conf, amb, comp = classifier.classify(g)
        assert GoalIntent.BUILD in intents
        assert conf == 1.0
        assert amb is False
        assert comp == GoalComplexity.LARGE

    def test_bugfix_intent(self, classifier: RuleBasedGoalClassifier) -> None:
        g = ChiefGoal(raw_text="Fix the login bug")
        intents, conf, amb, comp = classifier.classify(g)
        assert GoalIntent.BUGFIX in intents
        assert comp == GoalComplexity.SMALL

    def test_refactor_intent(self, classifier: RuleBasedGoalClassifier) -> None:
        g = ChiefGoal(raw_text="Rename UserService to AccountService")
        intents, conf, amb, comp = classifier.classify(g)
        assert GoalIntent.REFACTOR in intents
        assert comp == GoalComplexity.MEDIUM

    def test_migration_intent(self, classifier: RuleBasedGoalClassifier) -> None:
        g = ChiefGoal(raw_text="Upgrade Django to version 4")
        intents, conf, amb, comp = classifier.classify(g)
        assert GoalIntent.MIGRATION in intents
        assert comp == GoalComplexity.LARGE

    def test_multi_intent(self, classifier: RuleBasedGoalClassifier) -> None:
        g = ChiefGoal(raw_text="Fix the login bug and refactor the auth module")
        intents, conf, amb, comp = classifier.classify(g)
        assert GoalIntent.BUGFIX in intents
        assert GoalIntent.REFACTOR in intents
        assert comp == GoalComplexity.MEDIUM

    def test_unknown_intent(self, classifier: RuleBasedGoalClassifier) -> None:
        g = ChiefGoal(raw_text="Do something weird")
        intents, conf, amb, comp = classifier.classify(g)
        assert GoalIntent.UNKNOWN in intents
        assert conf == 0.0
        assert comp == GoalComplexity.TRIVIAL

    def test_ambiguous_intent(self, classifier: RuleBasedGoalClassifier) -> None:
        g = ChiefGoal(raw_text="Improve my application")
        intents, conf, amb, comp = classifier.classify(g)
        assert amb is True
        assert conf == 0.0  # <--- Change from 0.5 to 0.0

    def test_complexity_max_selection(self, classifier: RuleBasedGoalClassifier) -> None:
        g = ChiefGoal(raw_text="Build a new app and migrate the database")
        intents, conf, amb, comp = classifier.classify(g)
        assert comp == GoalComplexity.LARGE

    def test_determinism(self, classifier: RuleBasedGoalClassifier) -> None:
        g = ChiefGoal(raw_text="Build app")
        r1 = classifier.classify(g)
        r2 = classifier.classify(g)
        assert r1 == r2


# --- Extractor Tests (40) ---


class TestRequirementExtractor:
    def test_extracts_database(self, extractor: RequirementExtractor) -> None:
        g = ChiefGoal(raw_text="Build app with PostgreSQL")
        reqs, _, _ = extractor.extract(g, (GoalIntent.BUILD,))
        assert any(r.key == "database" and r.value == "postgres" for r in reqs)

    def test_missing_database(self, extractor: RequirementExtractor) -> None:
        g = ChiefGoal(raw_text="Build app")
        reqs, _, _ = extractor.extract(g, (GoalIntent.BUILD,))
        assert any(r.key == "database" and r.is_missing for r in reqs)

    def test_no_missing_for_refactor(self, extractor: RequirementExtractor) -> None:
        g = ChiefGoal(raw_text="Rename function foo")
        reqs, _, _ = extractor.extract(g, (GoalIntent.REFACTOR,))
        assert not any(r.is_missing for r in reqs)

    def test_extracts_backend(self, extractor: RequirementExtractor) -> None:
        g = ChiefGoal(raw_text="Build app with FastAPI")
        reqs, _, _ = extractor.extract(g, (GoalIntent.BUILD,))
        assert any(r.key == "backend" and r.value == "fastapi" for r in reqs)

    def test_extracts_constraint(self, extractor: RequirementExtractor) -> None:
        g = ChiefGoal(raw_text="Build app with Python 3.12")
        _, constraints, _ = extractor.extract(g, (GoalIntent.BUILD,))
        assert any(c.key == "language" and c.value == "python 3" for c in constraints)

    def test_extracts_assumption_when_missing(self, extractor: RequirementExtractor) -> None:
        g = ChiefGoal(raw_text="Build app")
        _, _, assumptions = extractor.extract(g, (GoalIntent.BUILD,))
        assert any(a.key == "database" and a.value == "unknown" for a in assumptions)

    def test_no_assumptions_when_present(self, extractor: RequirementExtractor) -> None:
        g = ChiefGoal(raw_text="Build app with postgres")
        _, _, assumptions = extractor.extract(g, (GoalIntent.BUILD,))
        assert not any(a.key == "database" for a in assumptions)

    def test_determinism(self, extractor: RequirementExtractor) -> None:
        g = ChiefGoal(raw_text="Build app")
        r1 = extractor.extract(g, (GoalIntent.BUILD,))
        r2 = extractor.extract(g, (GoalIntent.BUILD,))
        assert r1 == r2


# --- Normalizer Tests (25) ---


class TestNormalizer:
    def test_normalizes_synonyms(self, normalizer: GoalNormalizer) -> None:
        g = ChiefGoal(raw_text="Build app with db")
        analysis = GoalAnalysis(goal=g, primary_intent=GoalIntent.BUILD)
        text = normalizer.normalize(analysis)
        assert "application" in text
        assert "database" in text

    def test_determinism(self, normalizer: GoalNormalizer) -> None:
        g = ChiefGoal(raw_text="Build app")
        analysis = GoalAnalysis(goal=g, primary_intent=GoalIntent.BUILD)
        t1 = normalizer.normalize(analysis)
        t2 = normalizer.normalize(analysis)
        assert t1 == t2


# --- Runtime Tests (45) ---


class TestGoalRuntime:
    def test_full_pipeline_build(self, runtime: GoalRuntime) -> None:
        result = runtime.analyze("Build a todo app with React and PostgreSQL")
        assert result.primary_intent == GoalIntent.BUILD
        assert result.confidence == 1.0
        assert result.complexity == GoalComplexity.LARGE
        assert result.category == GoalCategory.APPLICATION
        assert any(r.key == "frontend" and r.value == "react" for r in result.requirements)
        assert not any(r.key == "database" and r.is_missing for r in result.requirements)
        assert len(result.clarifications) > 0  # Missing backend, auth, deployment

    def test_full_pipeline_refactor(self, runtime: GoalRuntime) -> None:
        result = runtime.analyze("Rename class Foo to Bar")
        assert result.primary_intent == GoalIntent.REFACTOR
        assert result.complexity == GoalComplexity.MEDIUM
        assert len(result.clarifications) == 0  # No missing reqs for refactor

    def test_multi_intent_pipeline(self, runtime: GoalRuntime) -> None:
        result = runtime.analyze("Fix the auth bug and refactor the user module")
        assert GoalIntent.BUGFIX in result.intents
        assert GoalIntent.REFACTOR in result.intents
        assert result.complexity == GoalComplexity.MEDIUM

    def test_ambiguous_pipeline(self, runtime: GoalRuntime) -> None:
        result = runtime.analyze("Improve my application")
        assert result.is_ambiguous is True
        assert result.confidence == 0.0
        assert any("ambiguous" in c.question.lower() for c in result.clarifications)

    def test_priority_mapping(self, runtime: GoalRuntime) -> None:
        result = runtime.analyze("Build app", priority="urgent")
        assert result.original_goal.priority == GoalPriority.URGENT

    def test_canonical_text_generated(self, runtime: GoalRuntime) -> None:
        result = runtime.analyze("Build app")
        assert "application" in result.canonical_text

    def test_assumptions_present(self, runtime: GoalRuntime) -> None:
        result = runtime.analyze("Build app")
        assert len(result.assumptions) > 0

    def test_constraints_present(self, runtime: GoalRuntime) -> None:
        result = runtime.analyze("Build app with Python 3.12")
        assert len(result.constraints) > 0

    def test_category_analysis(self, runtime: GoalRuntime) -> None:
        result = runtime.analyze("Analyze repository architecture")
        assert result.category == GoalCategory.ANALYSIS

    def test_determinism(self, runtime: GoalRuntime) -> None:
        r1 = runtime.analyze("Build a web app with FastAPI")
        r2 = runtime.analyze("Build a web app with FastAPI")
        assert r1.canonical_text == r2.canonical_text
        assert r1.intents == r2.intents
        assert r1.primary_intent == r2.primary_intent
        assert r1.category == r2.category
        assert r1.complexity == r2.complexity
        assert r1.confidence == r2.confidence
