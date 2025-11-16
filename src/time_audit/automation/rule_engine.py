"""Rule engine for process-based task matching."""

from typing import Optional

from time_audit.core.models import ProcessRule
from time_audit.core.storage import StorageManager


class RuleEngine:
    """Match processes against rules and manage rule learning."""

    def __init__(self, storage: StorageManager):
        """Initialize rule engine.

        Args:
            storage: StorageManager instance for rule persistence
        """
        self.storage = storage
        self._rules_cache: Optional[list[ProcessRule]] = None

    def match_process(self, process_name: str) -> Optional[ProcessRule]:
        """Find the best matching rule for a process.

        Args:
            process_name: Process name to match

        Returns:
            Matching ProcessRule or None if no match

        Note:
            Returns the first matching enabled rule, prioritizing:
            1. Non-learned rules (explicitly created by user)
            2. Learned rules with higher confidence
            3. Rules with higher match count
        """
        if not process_name:
            return None

        # Load rules if not cached
        if self._rules_cache is None:
            self._refresh_rules()

        # Separate learned and non-learned rules
        non_learned = []
        learned = []

        for rule in self._rules_cache or []:
            if not rule.enabled:
                continue

            if rule.matches(process_name):
                if rule.learned:
                    learned.append(rule)
                else:
                    non_learned.append(rule)

        # Prioritize non-learned (explicit) rules
        if non_learned:
            return non_learned[0]

        # Sort learned rules by confidence and match count
        if learned:
            learned.sort(key=lambda r: (r.confidence, r.match_count), reverse=True)
            return learned[0]

        return None

    def learn_rule(
        self,
        process_name: str,
        task_name: str,
        project: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[list[str]] = None,
        confidence: float = 0.8,
    ) -> ProcessRule:
        """Create a learned rule from user behavior.

        Args:
            process_name: Process name pattern
            task_name: Task name to suggest
            project: Project identifier
            category: Category identifier
            tags: Tags to apply
            confidence: Initial confidence score (0-1)

        Returns:
            Created ProcessRule
        """
        # Check if a learned rule for this process already exists
        existing = None
        for rule in self.storage.load_rules():
            if rule.learned and rule.pattern == process_name:
                existing = rule
                break

        if existing:
            # Update existing learned rule
            existing.task_name = task_name
            existing.project = project
            existing.category = category
            existing.tags = tags or []
            existing.confidence = min(1.0, existing.confidence + 0.1)  # Increase confidence
            existing.match_count += 1
            self.storage.save_rule(existing)
            self._refresh_rules()
            return existing
        else:
            # Create new learned rule
            new_rule = ProcessRule(
                pattern=process_name,
                task_name=task_name,
                project=project,
                category=category,
                tags=tags or [],
                learned=True,
                confidence=confidence,
            )
            self.storage.save_rule(new_rule)
            self._refresh_rules()
            return new_rule

    def increment_match_count(self, rule: ProcessRule) -> None:
        """Increment match count for a rule.

        Args:
            rule: Rule that matched
        """
        rule.match_count += 1
        self.storage.save_rule(rule)
        self._refresh_rules()

    def add_rule(
        self,
        pattern: str,
        task_name: str,
        project: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[list[str]] = None,
    ) -> ProcessRule:
        """Add an explicit (non-learned) rule.

        Args:
            pattern: Regex pattern for process matching
            task_name: Task name to suggest
            project: Project identifier
            category: Category identifier
            tags: Tags to apply

        Returns:
            Created ProcessRule
        """
        rule = ProcessRule(
            pattern=pattern,
            task_name=task_name,
            project=project,
            category=category,
            tags=tags or [],
            learned=False,
            confidence=1.0,
        )
        self.storage.save_rule(rule)
        self._refresh_rules()
        return rule

    def update_rule(
        self,
        rule_id: str,
        pattern: Optional[str] = None,
        task_name: Optional[str] = None,
        project: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[list[str]] = None,
        enabled: Optional[bool] = None,
    ) -> Optional[ProcessRule]:
        """Update an existing rule.

        Args:
            rule_id: ID of rule to update
            pattern: New pattern (if provided)
            task_name: New task name (if provided)
            project: New project (if provided)
            category: New category (if provided)
            tags: New tags (if provided)
            enabled: New enabled state (if provided)

        Returns:
            Updated ProcessRule or None if not found
        """
        rule = self.storage.get_rule(rule_id)
        if not rule:
            return None

        if pattern is not None:
            rule.pattern = pattern
        if task_name is not None:
            rule.task_name = task_name
        if project is not None:
            rule.project = project
        if category is not None:
            rule.category = category
        if tags is not None:
            rule.tags = tags
        if enabled is not None:
            rule.enabled = enabled

        self.storage.save_rule(rule)
        self._refresh_rules()
        return rule

    def delete_rule(self, rule_id: str) -> bool:
        """Delete a rule.

        Args:
            rule_id: ID of rule to delete

        Returns:
            True if deleted, False if not found
        """
        result = self.storage.delete_rule(rule_id)
        if result:
            self._refresh_rules()
        return result

    def get_all_rules(self, enabled_only: bool = False) -> list[ProcessRule]:
        """Get all rules.

        Args:
            enabled_only: If True, only return enabled rules

        Returns:
            List of ProcessRule objects
        """
        return self.storage.load_rules(enabled_only=enabled_only)

    def _refresh_rules(self) -> None:
        """Refresh the rules cache."""
        self._rules_cache = self.storage.load_rules(enabled_only=True)
