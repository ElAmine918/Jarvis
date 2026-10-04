import pytest
from jarvis.tools.python_repl import PythonREPLTool


@pytest.fixture
def repl():
    return PythonREPLTool()


@pytest.mark.asyncio
async def test_python_repl_simple_execution(repl):
    code = "a = 10\nb = 32\nprint(f'Total: {a + b}')"
    res = await repl.execute(code=code)
    assert "✅ Exécution réussie" in res
    assert "Total: 42" in res


@pytest.mark.asyncio
async def test_python_repl_syntax_error(repl):
    code = "def broken(:"
    res = await repl.execute(code=code)
    assert "❌ Erreur d'exécution" in res
    assert "SyntaxError" in res


@pytest.mark.asyncio
async def test_python_repl_runtime_error(repl):
    code = "print(1 / 0)"
    res = await repl.execute(code=code)
    assert "❌ Erreur d'exécution" in res
    assert "ZeroDivisionError" in res


@pytest.mark.asyncio
async def test_python_repl_code_size_limit(repl):
    oversized_code = "# " + ("A" * (60 * 1024))
    res = await repl.execute(code=oversized_code)
    assert "❌ Le code dépasse la limite" in res


@pytest.mark.asyncio
async def test_python_repl_timeout(repl):
    code = "import time\ntime.sleep(35)"
    res = await repl.execute(code=code)
    assert "Temps limite" in res or "30 secondes" in res
