from continuity_conformance.demo import run_demo

def test_demo_reports_single_verified_effect(tmp_path):
    result = run_demo(tmp_path / "demo.sqlite3")
    assert result["state"] == "VERIFIED"
    assert result["generation"] == 2
    assert result["provider_admissions"] == 1
    assert result["provider_effects"] == 1
    assert result["event_chain_valid"] is True
