import os
import tempfile
import pytest
from jarvis.skills.base import Skill, MarkdownSkill, SkillRegistry

def test_markdown_skill_loading():
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write("""---
name: test_skill
description: A skill for testing
triggers:
  - test
  - mock
---
This is a test skill.
It has some instructions.
""")
        temp_path = f.name

    try:
        skill = MarkdownSkill(temp_path)
        assert skill.name == "test_skill"
        assert skill.description == "A skill for testing"
        assert skill.triggers == ["test", "mock"]
        assert "This is a test skill." in skill.instructions
    finally:
        os.unlink(temp_path)

def test_markdown_skill_without_frontmatter():
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write("Just some instructions without frontmatter.")
        temp_path = f.name
        basename = os.path.basename(temp_path).replace('.md', '')

    try:
        skill = MarkdownSkill(temp_path)
        assert skill.name == basename
        assert skill.description == ""
        assert skill.triggers == []
        assert skill.instructions == "Just some instructions without frontmatter."
    finally:
        os.unlink(temp_path)

def test_skill_applicability():
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write("""---
name: test_skill
triggers:
  - hello
  - world
---
content
""")
        temp_path = f.name

    try:
        skill = MarkdownSkill(temp_path)
        assert skill.is_applicable("hello there") is True
        assert skill.is_applicable("the world is big") is True
        assert skill.is_applicable("goodbye") is False
    finally:
        os.unlink(temp_path)

def test_skill_registry():
    registry = SkillRegistry()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a few skill files
        with open(os.path.join(tmpdir, "skill1.md"), "w") as f:
            f.write("---\nname: skill1\ntriggers:\n  - ping\n---\ncontent1")
        
        os.makedirs(os.path.join(tmpdir, "skill2_dir"))
        with open(os.path.join(tmpdir, "skill2_dir", "SKILL.md"), "w") as f:
            f.write("---\nname: skill2\ntriggers:\n  - pong\n---\ncontent2")

        registry.load_from_directory(tmpdir)
        
        assert len(registry.get_all_skills()) == 2
        
        skill1 = registry.get_skill("skill1")
        assert skill1 is not None
        assert skill1.name == "skill1"

        skill2 = registry.get_skill("skill2")
        assert skill2 is not None
        assert skill2.name == "skill2"
        
        applicable = registry.find_applicable_skills("let's ping the server")
        assert len(applicable) == 1
        assert applicable[0].name == "skill1"
