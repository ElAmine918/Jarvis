import os
import yaml
from abc import ABC, abstractmethod
from typing import List, Optional


class Skill(ABC):
    """Base class for a Skill, which is a prompt-based workflow or manual."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the skill."""

    @property
    @abstractmethod
    def description(self) -> str:
        """Short description of the skill."""

    @property
    @abstractmethod
    def instructions(self) -> str:
        """The core instructions/prompt for the skill."""

    def is_applicable(self, context: str) -> bool:
        """Check if this skill is applicable given the context string (e.g., user prompt)."""
        return False


class MarkdownSkill(Skill):
    """A skill loaded from a markdown file with YAML frontmatter."""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self._name = ""
        self._description = ""
        self._instructions = ""
        self._triggers: List[str] = []
        self._load()

    def _load(self):
        if not os.path.exists(self.filepath):
            raise FileNotFoundError(f"Skill file not found: {self.filepath}")

        with open(self.filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                frontmatter = yaml.safe_load(parts[1]) or {}
                self._name = frontmatter.get("name", os.path.basename(os.path.dirname(self.filepath)))
                if self._name == "." or not self._name:
                    self._name = os.path.basename(self.filepath).replace('.md', '')
                self._description = frontmatter.get("description", "")
                self._triggers = frontmatter.get("triggers", [])
                self._instructions = parts[2].strip()
                return

        # Fallback if no frontmatter
        self._name = os.path.basename(self.filepath).replace('.md', '')
        self._instructions = content.strip()

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def instructions(self) -> str:
        return self._instructions
    
    @property
    def triggers(self) -> List[str]:
        return self._triggers

    def is_applicable(self, context: str) -> bool:
        if not self._triggers:
            return False
        context_lower = context.lower()
        return any(trigger.lower() in context_lower for trigger in self._triggers)


class SkillRegistry:
    """Registry for managing and retrieving skills."""

    def __init__(self):
        self._skills: dict[str, Skill] = {}

    def register(self, skill: Skill):
        self._skills[skill.name] = skill

    def get_skill(self, name: str) -> Optional[Skill]:
        return self._skills.get(name)
        
    def get_all_skills(self) -> List[Skill]:
        return list(self._skills.values())

    def find_applicable_skills(self, context: str) -> List[Skill]:
        return [skill for skill in self._skills.values() if skill.is_applicable(context)]

    def load_from_directory(self, directory: str):
        """Load all markdown skills from a directory structure.
        Expected format: directory/skill_name/SKILL.md or directory/skill_name.md
        """
        if not os.path.exists(directory):
            return

        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith(".md"):
                    filepath = os.path.join(root, file)
                    try:
                        skill = MarkdownSkill(filepath)
                        self.register(skill)
                    except Exception as e:
                        print(f"Error loading skill from {filepath}: {e}")
