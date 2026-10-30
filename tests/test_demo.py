from continuity_conformance.demo import run_demo


def test_demo_reports_single_verified_effect(tmp_path):
    result = run_demo(tmp_path / "demo.sqlite3")
    assert result["state"] == "VERIFIED"
    assert result["generation"] == 2
    assert result["provider_admissions"] == 1
    assert result["provider_effects"] == 1
    assert result["event_chain_valid"] is True

def test_installed_console_command_runs():
    import json
    import subprocess

    completed = subprocess.run(
        ["continuity-demo"], capture_output=True, text=True, check=True
    )
    result = json.loads(completed.stdout)
    assert result["state"] == "VERIFIED"
    assert result["provider_admissions"] == 1
    assert result["provider_effects"] == 1
