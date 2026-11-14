from pipeline.__main__ import main


def test_cli_runs_without_command():
    assert main([]) == 0
