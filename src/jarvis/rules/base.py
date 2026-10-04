import os
import yaml
from abc import ABC, abstractmethod
from typing import List, Optional

class Rule(ABC):
    """Base class for a Rule, which is a universal guideline or constraint."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the rule."""

    @property
    @abstractmethod
    def content(self) -> str:
        """The actual rule content/guideline."""

    def is_active(self, context: str) -> bool:
        """Check if this rule should be applied in the current context."""
        return True # Rules are typically universal, but can be conditional


class MarkdownRule(Rule):
    """A rule loaded from a markdown file."""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self._name = ""
        self._content = ""
        self._conditions: List[str] = []
        self._load()

    def _load(self):
        if not os.path.exists(self.filepath):
            raise FileNotFoundError(f"Rule file not found: {self.filepath}")

        with open(self.filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                frontmatter = yaml.safe_load(parts[1]) or {}
                self._name = frontmatter.get("name", os.path.basename(self.filepath).replace('.md', ''))
                self._conditions = frontmatter.get("conditions", [])
                self._content = parts[2].strip()
                return

        # Fallback
        self._name = os.path.basename(self.filepath).replace('.md', '')
        self._content = content.strip()

    @property
    def name(self) -> str:
        return self._name

    @property
    def content(self) -> str:
        return self._content

    def is_active(self, context: str) -> bool:
        if not self._conditions:
            return True # Universal rule
        context_lower = context.lower()
        return any(cond.lower() in context_lower for cond in self._conditions)


class RuleRegistry:
    """Registry for managing and retrieving rules."""

    def __init__(self):
        self._rules: dict[str, Rule] = {}

    def register(self, rule: Rule):
        self._rules[rule.name] = rule

    def get_all_rules(self) -> List[Rule]:
        return list(self._rules.values())

    def get_active_rules(self, context: str) -> List[Rule]:
        return [rule for rule in self._rules.values() if rule.is_active(context)]

    def load_from_directory(self, directory: str):
        if not os.path.exists(directory):
            return

        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith(".md"):
                    filepath = os.path.join(root, file)
                    try:
                        rule = MarkdownRule(filepath)
                        self.register(rule)
                    except Exception as e:
                        print(f"Error loading rule from {filepath}: {e}")
