"""Tests for rule engine."""

from unittest.mock import Mock

import pytest  # type: ignore[import-not-found]

from time_audit.core.models import ProcessRule
from time_audit.automation.rule_engine import RuleEngine


class TestRuleEngine:
    """Test RuleEngine."""

    def test_initialization(self) -> None:
        """Test rule engine initialization."""
        storage = Mock()
        storage.load_rules.return_value = []

        engine = RuleEngine(storage)

        assert engine.storage == storage
        assert engine._rules_cache is None  # Cache starts as None

    def test_match_process_loads_rules_on_first_match(self) -> None:
        """Test matching loads rules from storage on first call."""
        storage = Mock()
        rule1 = ProcessRule(pattern="vscode", task_name="Development")
        rule2 = ProcessRule(pattern="chrome", task_name="Browsing")
        storage.load_rules.return_value = [rule1, rule2]

        engine = RuleEngine(storage)

        # Cache is None until first match
        assert engine._rules_cache is None

        # First match loads rules
        engine.match_process("vscode")

        # Now cache should be populated
        assert engine._rules_cache is not None
        assert len(engine._rules_cache) == 2

    def test_match_process_exact_match(self) -> None:
        """Test matching process with exact pattern."""
        storage = Mock()
        rule = ProcessRule(pattern="vscode", task_name="Development")
        storage.load_rules.return_value = [rule]

        engine = RuleEngine(storage)

        matched_rule = engine.match_process("vscode")

        assert matched_rule == rule

    def test_match_process_regex_match(self) -> None:
        """Test matching process with regex pattern."""
        storage = Mock()
        rule = ProcessRule(pattern="chrome|firefox", task_name="Browsing")
        storage.load_rules.return_value = [rule]

        engine = RuleEngine(storage)

        assert engine.match_process("chrome") == rule
        assert engine.match_process("firefox") == rule

    def test_match_process_partial_match(self) -> None:
        """Test matching process with partial pattern."""
        storage = Mock()
        rule = ProcessRule(pattern="code", task_name="Development")
        storage.load_rules.return_value = [rule]

        engine = RuleEngine(storage)

        matched_rule = engine.match_process("vscode")

        assert matched_rule == rule

    def test_match_process_no_match(self) -> None:
        """Test matching process with no matching rule."""
        storage = Mock()
        rule = ProcessRule(pattern="vscode", task_name="Development")
        storage.load_rules.return_value = [rule]

        engine = RuleEngine(storage)

        matched_rule = engine.match_process("firefox")

        assert matched_rule is None

    def test_match_process_prioritizes_explicit_rules(self) -> None:
        """Test matching prioritizes explicit rules over learned ones."""
        storage = Mock()
        learned_rule = ProcessRule(pattern="code", task_name="Coding", learned=True, confidence=0.9)
        explicit_rule = ProcessRule(pattern="code", task_name="Development", learned=False)
        storage.load_rules.return_value = [learned_rule, explicit_rule]

        engine = RuleEngine(storage)

        matched_rule = engine.match_process("vscode")

        # Should prefer explicit rule
        assert matched_rule == explicit_rule

    def test_match_process_prioritizes_higher_confidence(self) -> None:
        """Test matching prioritizes higher confidence among learned rules."""
        storage = Mock()
        low_confidence = ProcessRule(
            pattern="code", task_name="Coding", learned=True, confidence=0.6
        )
        high_confidence = ProcessRule(
            pattern="code", task_name="Development", learned=True, confidence=0.9
        )
        storage.load_rules.return_value = [low_confidence, high_confidence]

        engine = RuleEngine(storage)

        matched_rule = engine.match_process("vscode")

        # Should prefer higher confidence
        assert matched_rule == high_confidence

    def test_match_process_prioritizes_match_count(self) -> None:
        """Test matching uses match count as tiebreaker."""
        storage = Mock()
        less_used = ProcessRule(
            pattern="code",
            task_name="Coding",
            learned=True,
            confidence=0.8,
            match_count=5,
        )
        more_used = ProcessRule(
            pattern="code",
            task_name="Development",
            learned=True,
            confidence=0.8,
            match_count=10,
        )
        storage.load_rules.return_value = [less_used, more_used]

        engine = RuleEngine(storage)

        matched_rule = engine.match_process("vscode")

        # Should prefer more frequently used
        assert matched_rule == more_used

    def test_match_process_skips_disabled_rules(self) -> None:
        """Test matching skips disabled rules."""
        storage = Mock()
        disabled_rule = ProcessRule(pattern="vscode", task_name="Development", enabled=False)
        enabled_rule = ProcessRule(pattern="code", task_name="Coding", enabled=True)
        storage.load_rules.return_value = [disabled_rule, enabled_rule]

        engine = RuleEngine(storage)

        matched_rule = engine.match_process("vscode")

        # Should match enabled rule, not disabled one
        assert matched_rule == enabled_rule

    def test_add_rule(self) -> None:
        """Test adding a new rule."""
        storage = Mock()
        # Initial load returns empty, after save returns the new rule
        new_rule_ref = []

        def save_rule(rule):
            new_rule_ref.append(rule)

        def load_rules(enabled_only=True):
            return new_rule_ref.copy()

        storage.save_rule = save_rule
        storage.load_rules = load_rules

        engine = RuleEngine(storage)

        rule = engine.add_rule(
            pattern="slack",
            task_name="Communication",
            project="work",
            category="communication",
        )

        assert rule.pattern == "slack"
        assert rule.task_name == "Communication"
        assert rule.project == "work"
        assert rule.category == "communication"
        assert rule.learned is False
        assert rule.enabled is True
        # After refresh, cache should contain the rule
        assert rule in engine._rules_cache

    def test_learn_rule_creates_new(self) -> None:
        """Test learning creates new rule."""
        storage = Mock()
        rules = []

        def save_rule(rule):
            # Update existing or add new
            for i, r in enumerate(rules):
                if r.id == rule.id:
                    rules[i] = rule
                    return
            rules.append(rule)

        def load_rules(enabled_only=True):
            return rules.copy()

        storage.save_rule = save_rule
        storage.load_rules = load_rules

        engine = RuleEngine(storage)

        rule = engine.learn_rule(process_name="slack", task_name="Communication", confidence=0.8)

        assert rule.pattern == "slack"
        assert rule.task_name == "Communication"
        assert rule.learned is True
        assert rule.confidence == 0.8
        assert rule.match_count == 0
        assert rule in engine._rules_cache

    def test_learn_rule_updates_existing(self) -> None:
        """Test learning updates existing learned rule."""
        storage = Mock()
        existing_rule = ProcessRule(
            pattern="slack",
            task_name="Communication",
            learned=True,
            confidence=0.7,
            match_count=5,
        )
        rules = [existing_rule]

        def save_rule(rule):
            for i, r in enumerate(rules):
                if r.id == rule.id:
                    rules[i] = rule
                    return

        def load_rules(enabled_only=True):
            return rules.copy()

        storage.save_rule = save_rule
        storage.load_rules = load_rules

        engine = RuleEngine(storage)

        rule = engine.learn_rule(process_name="slack", task_name="Communication", confidence=0.9)

        # Should update confidence (+0.1) and increment match count
        assert rule == existing_rule
        assert rule.confidence == pytest.approx(0.8)  # 0.7 + 0.1
        assert rule.match_count == 6

    def test_learn_rule_creates_separate_from_explicit(self) -> None:
        """Test learning creates separate rule alongside explicit rules."""
        storage = Mock()
        explicit_rule = ProcessRule(pattern="slack", task_name="Work Chat", learned=False)
        rules = [explicit_rule]

        def save_rule(rule):
            for i, r in enumerate(rules):
                if r.id == rule.id:
                    rules[i] = rule
                    return
            rules.append(rule)

        def load_rules(enabled_only=True):
            return rules.copy()

        storage.save_rule = save_rule
        storage.load_rules = load_rules

        engine = RuleEngine(storage)

        rule = engine.learn_rule(process_name="slack", task_name="Communication", confidence=0.9)

        # Should create new learned rule with same pattern
        assert rule != explicit_rule
        assert rule.learned is True
        assert len(engine._rules_cache) == 2
        assert explicit_rule in engine._rules_cache
        assert rule in engine._rules_cache

    def test_update_rule(self) -> None:
        """Test updating an existing rule."""
        storage = Mock()
        existing_rule = ProcessRule(pattern="vscode", task_name="Development")

        def get_rule(rule_id):
            if rule_id == existing_rule.id:
                return existing_rule
            return None

        def save_rule(rule):
            pass

        def load_rules(enabled_only=True):
            return [existing_rule]

        storage.get_rule = get_rule
        storage.save_rule = save_rule
        storage.load_rules = load_rules

        engine = RuleEngine(storage)

        updated = engine.update_rule(
            existing_rule.id,
            pattern="code",
            task_name="Coding",
            category="dev",
        )

        assert updated is not None
        assert updated == existing_rule
        assert existing_rule.pattern == "code"
        assert existing_rule.task_name == "Coding"
        assert existing_rule.category == "dev"

    def test_update_rule_not_found(self) -> None:
        """Test updating non-existent rule."""
        storage = Mock()
        storage.get_rule = Mock(return_value=None)
        storage.load_rules = Mock(return_value=[])

        engine = RuleEngine(storage)

        updated = engine.update_rule("nonexistent-id", task_name="New Name")

        assert updated is None

    def test_delete_rule(self) -> None:
        """Test deleting a rule."""
        storage = Mock()
        rule = ProcessRule(pattern="vscode", task_name="Development")
        rules = [rule]

        def delete_rule_fn(rule_id):
            for r in rules:
                if r.id == rule_id:
                    rules.remove(r)
                    return True
            return False

        def load_rules(enabled_only=True):
            return rules.copy()

        storage.delete_rule = delete_rule_fn
        storage.load_rules = load_rules

        engine = RuleEngine(storage)

        # Load cache first
        engine.match_process("vscode")
        assert rule in engine._rules_cache

        # Delete the rule
        deleted = engine.delete_rule(rule.id)

        assert deleted is True
        assert rule not in engine._rules_cache

    def test_delete_rule_not_found(self) -> None:
        """Test deleting non-existent rule."""
        storage = Mock()
        storage.load_rules.return_value = []
        storage.delete_rule = Mock(return_value=False)

        engine = RuleEngine(storage)

        deleted = engine.delete_rule("nonexistent-id")

        assert deleted is False

    def test_increment_match_count(self) -> None:
        """Test incrementing rule match count."""
        storage = Mock()
        rule = ProcessRule(pattern="vscode", task_name="Development", match_count=5)
        storage.load_rules.return_value = [rule]
        storage.save_rule = Mock()

        engine = RuleEngine(storage)

        engine.increment_match_count(rule)

        assert rule.match_count == 6
        storage.save_rule.assert_called_once_with(rule)

    def test_get_all_rules(self) -> None:
        """Test getting all rules."""
        storage = Mock()
        rule1 = ProcessRule(pattern="vscode", task_name="Development")
        rule2 = ProcessRule(pattern="chrome", task_name="Browsing")
        storage.load_rules.return_value = [rule1, rule2]

        engine = RuleEngine(storage)

        rules = engine.get_all_rules()

        assert len(rules) == 2
        assert rule1 in rules
        assert rule2 in rules
