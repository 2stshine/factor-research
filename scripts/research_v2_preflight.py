"""Read-only live attestation and immutable regime adoption for the v2 pilot."""
import argparse
import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from engine import panel as P, silver
from engine.research_regime_adoption import adopt_shadow_bundle
from scripts import run
from scripts.research import _campaign_snapshot_boundary


def save(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-panel", type=Path, required=True)
    parser.add_argument("--shadow", type=Path, required=True)
    parser.add_argument("--policy", type=Path, default=Path("research/regime_assumption_policy.json"))
    parser.add_argument("--use-aws-cli", action="store_true", help="Use the CLI's valid cached session for the same read-only secret lookup")
    parser.add_argument("--resume", action="store_true", help="Reuse an already persisted matching live audit; never rerun or overwrite it")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=args.resume)
    audit_path = args.output / "live-audit.json"
    reuse = args.resume and audit_path.is_file()
    if args.use_aws_cli and not reuse:
        silver._load_environment()
        secret_id = os.environ.get("SILVER_DB_SECRET_ID")
        if not secret_id:
            raise SystemExit("Secret identifier is not configured")
        command = ["aws", "secretsmanager", "get-secret-value", "--secret-id", secret_id, "--output", "json"]
        if os.environ.get("AWS_PROFILE"):
            command += ["--profile", os.environ["AWS_PROFILE"]]
        response = subprocess.run(command, capture_output=True, text=True, timeout=40)
        if response.returncode:
            raise SystemExit("AWS CLI read-only secret lookup failed; login is required")
        secret = json.loads(json.loads(response.stdout)["SecretString"])
        os.environ["SILVER_DB_URL"] = secret["SILVER_DB_URL"]
        os.environ["SILVER_DB_SECRET_ID"] = ""
    panel = run._load()
    expected = P.verify_asset_identity(panel)
    snapshot = P.snapshot_digest(panel)
    file_sha = hashlib.sha256(args.source_panel.read_bytes()).hexdigest()
    if reuse:
        receipt = json.loads(audit_path.read_text())
        if (receipt.get("status") != "MATCH" or receipt.get("cache") != expected
                or receipt.get("snapshot_sha256") != snapshot or receipt.get("source_panel_file_sha256") != file_sha):
            raise SystemExit("Persisted audit does not match this source")
    else:
        with silver.connect(read_only=True) as connection:
            returns = silver.verify_live_total_return_contract(connection, panel.meta.get("return_contract_validation_evidence"))
            actual = P.verify_live_asset_identity(connection, panel)
        receipt = {"status": "MATCH", "cache": expected, "rds": actual,
                   "snapshot_sha256": snapshot, "source_panel_file_sha256": file_sha,
                   "total_return_contract": returns, "gold_write": False,
                   "observed_at": datetime.now(timezone.utc).isoformat()}
        save(audit_path, receipt)
    boundary = _campaign_snapshot_boundary(panel)
    adopted = adopt_shadow_bundle(args.shadow, args.policy,
        contract_id="research-v2-20261002-diagnostic-regime",
        authorization_ref="research/v2/execution-plan-20261002.json + existing user PIT assumption policy",
        adopted_at=datetime.now(timezone.utc).isoformat(),
        start_month="2016-02", end_month=str(boundary.discovery_signal_end))
    save(args.output / "regime-contract.json", adopted)
    print(json.dumps({"status": "MATCH", "output": str(args.output),
                      "snapshot_sha256": receipt["snapshot_sha256"],
                      "discovery_cutoff": boundary.discovery_data_cutoff,
                      "discovery_signal_end": str(boundary.discovery_signal_end),
                      "gold_write": False}))


if __name__ == "__main__":
    main()
