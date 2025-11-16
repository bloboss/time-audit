"""Tests for ProcessRule model."""

from datetime import datetime

import pytest  # type: ignore[import-not-found]

from time_audit.core.models import ProcessRule


class TestProcessRule:
    """Test ProcessRule model."""

    def test_rule_creation(self) -> None:
        """Test creating a process rule."""
        rule = ProcessRule(
            pattern="vscode|code",
            task_name="Development",
            project="my-project",
            category="development",
        )

        assert rule.pattern == "vscode|code"
        assert rule.task_name == "Development"
        assert rule.project == "my-project"
        assert rule.category == "development"
        assert rule.enabled is True
        assert rule.learned is False
        assert rule.confidence == 1.0
        assert rule.match_count == 0

    def test_rule_matches_exact(self) -> None:
        """Test rule matches exact process name."""
        rule = ProcessRule(pattern="vscode", task_name="Development")

        assert rule.matches("vscode")
        assert rule.matches("VSCode")  # Case insensitive
        assert rule.matches("VSCODE")

    def test_rule_matches_regex(self) -> None:
        """Test rule matches with regex pattern."""
        rule = ProcessRule(pattern="vscode|code", task_name="Development")

        assert rule.matches("vscode")
        assert rule.matches("code")
        assert not rule.matches("vim")

    def test_rule_matches_partial(self) -> None:
        """Test rule matches partial process name."""
        rule = ProcessRule(pattern="chrome", task_name="Browsing")

        assert rule.matches("chrome")
        assert rule.matches("google-chrome")
        assert rule.matches("chrome-browser")

    def test_rule_no_match(self) -> None:
        """Test rule doesn't match unrelated process."""
        rule = ProcessRule(pattern="vscode", task_name="Development")

        assert not rule.matches("firefox")
        assert not rule.matches("chrome")
        assert not rule.matches("")

    def test_rule_invalid_regex(self) -> None:
        """Test rule handles invalid regex gracefully."""
        rule = ProcessRule(pattern="[invalid(regex", task_name="Test")

        # Should not raise, should return False
        assert not rule.matches("anything")

    def test_rule_with_tags(self) -> None:
        """Test rule with tags."""
        rule = ProcessRule(
            pattern="vscode",
            task_name="Development",
            tags=["backend", "python"],
        )

        assert rule.tags == ["backend", "python"]

    def test_learned_rule(self) -> None:
        """Test learned rule properties."""
        rule = ProcessRule(
            pattern="slack",
            task_name="Communication",
            learned=True,
            confidence=0.8,
        )

        assert rule.learned is True
        assert rule.confidence == 0.8

    def test_rule_serialization(self) -> None:
        """Test rule to_dict."""
        rule = ProcessRule(
            pattern="vscode",
            task_name="Development",
            project="test-project",
            category="dev",
            tags=["python"],
            learned=True,
            confidence=0.9,
            match_count=5,
        )

        data = rule.to_dict()

        assert data["pattern"] == "vscode"
        assert data["task_name"] == "Development"
        assert data["project"] == "test-project"
        assert data["category"] == "dev"
        assert data["tags"] == "python"
        assert data["learned"] is True
        assert data["confidence"] == 0.9
        assert data["match_count"] == 5

    def test_rule_deserialization(self) -> None:
        """Test rule from_dict."""
        data = {
            "id": "test-id",
            "pattern": "vscode",
            "task_name": "Development",
            "project": "test-project",
            "category": "dev",
            "tags": "python,backend",
            "enabled": True,
            "learned": True,
            "confidence": 0.9,
            "match_count": 5,
            "created_at": "2025-11-16T10:00:00",
        }

        rule = ProcessRule.from_dict(data)

        assert rule.id == "test-id"
        assert rule.pattern == "vscode"
        assert rule.task_name == "Development"
        assert rule.project == "test-project"
        assert rule.category == "dev"
        assert rule.tags == ["python", "backend"]
        assert rule.enabled is True
        assert rule.learned is True
        assert rule.confidence == 0.9
        assert rule.match_count == 5

    def test_rule_roundtrip_serialization(self) -> None:
        """Test rule serialization roundtrip."""
        original = ProcessRule(
            pattern="chrome.*gmail",
            task_name="Email",
            category="communication",
            tags=["work", "email"],
            learned=True,
            confidence=0.85,
        )

        data = original.to_dict()
        restored = ProcessRule.from_dict(data)

        assert restored.pattern == original.pattern
        assert restored.task_name == original.task_name
        assert restored.category == original.category
        assert restored.tags == original.tags
        assert restored.learned == original.learned
        assert restored.confidence == original.confidence

    def test_rule_empty_fields(self) -> None:
        """Test rule with empty optional fields."""
        rule = ProcessRule(pattern="test", task_name="Test")

        assert rule.project is None
        assert rule.category is None
        assert rule.tags == []

        data = rule.to_dict()
        assert data["project"] == ""
        assert data["category"] == ""
        assert data["tags"] == ""

    def test_rule_case_insensitive_matching(self) -> None:
        """Test rule matching is case insensitive."""
        rule = ProcessRule(pattern="Firefox", task_name="Browsing")

        assert rule.matches("firefox")
        assert rule.matches("FIREFOX")
        assert rule.matches("Firefox")
        assert rule.matches("firefox-browser")
