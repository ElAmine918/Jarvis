import os
import tempfile
from jarvis.rules.base import Rule, MarkdownRule, RuleRegistry

def test_markdown_rule_universal():
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write("""---
name: always_polite
---
Always be polite.
""")
        temp_path = f.name

    try:
        rule = MarkdownRule(temp_path)
        assert rule.name == "always_polite"
        assert rule.content == "Always be polite."
        assert rule.is_active("any random context") is True
    finally:
        os.unlink(temp_path)

def test_markdown_rule_conditional():
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write("""---
name: code_style
conditions:
  - python
  - rust
---
Use type hints.
""")
        temp_path = f.name

    try:
        rule = MarkdownRule(temp_path)
        assert rule.name == "code_style"
        assert rule.content == "Use type hints."
        assert rule.is_active("I am writing some python code") is True
        assert rule.is_active("tell me a joke") is False
    finally:
        os.unlink(temp_path)

def test_rule_registry():
    registry = RuleRegistry()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "rule1.md"), "w") as f:
            f.write("---\nname: rule1\n---\ncontent1")
            
        with open(os.path.join(tmpdir, "rule2.md"), "w") as f:
            f.write("---\nname: rule2\nconditions:\n  - trigger2\n---\ncontent2")

        registry.load_from_directory(tmpdir)
        
        assert len(registry.get_all_rules()) == 2
        
        active = registry.get_active_rules("some random text")
        assert len(active) == 1
        assert active[0].name == "rule1"
        
        active_triggered = registry.get_active_rules("here is trigger2")
        assert len(active_triggered) == 2
