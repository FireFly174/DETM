from __future__ import annotations

from detm_app.runner.headless.options import HeadlessMainOptions, resolve_headless_main_options
from detm_app.runner.headless.parser import build_headless_parser


def test_resolve_headless_main_options_keeps_fabric_list_fields_from_cli():
    parser = build_headless_parser()
    args = parser.parse_args(
        [
            "--fabric-validator-set",
            "validator.a,validator.b",
            "--fabric-validator-auth-key-id",
            "validator.a=kid-a,validator.b=kid-b",
            "--fabric-validator-transport-identity",
            "validator.a=tls://a,validator.b=tls://b",
            "--fabric-validator-coordination-replica-state",
            "coord_a.json,coord_b.json",
            "--fabric-epoch-replica-state",
            "epoch_a.json,epoch_b.json",
            "--fabric-delivery-validator-set",
            "validator.a,validator.b",
        ]
    )

    options = resolve_headless_main_options(args=args, runner_defaults={})

    assert isinstance(options, HeadlessMainOptions)
    assert options.fabric_required_validator_ids == ["validator.a", "validator.b"]
    assert options.fabric_validator_auth_key_ids == ["validator.a=kid-a", "validator.b=kid-b"]
    assert options.fabric_validator_transport_identities == ["validator.a=tls://a", "validator.b=tls://b"]
    assert options.fabric_validator_coordination_replica_state_paths == ["coord_a.json", "coord_b.json"]
    assert options.fabric_epoch_replica_state_paths == ["epoch_a.json", "epoch_b.json"]
    assert options.fabric_delivery_required_validator_ids == ["validator.a", "validator.b"]


def test_resolve_headless_main_options_uses_runner_defaults_for_fabric_list_fields():
    parser = build_headless_parser()
    args = parser.parse_args([])
    options = resolve_headless_main_options(
        args=args,
        runner_defaults={
            "fabric_required_validator_ids": ["validator.default"],
            "fabric_validator_auth_key_ids": ["validator.default=kid-default"],
            "fabric_validator_transport_identities": ["validator.default=tls://default"],
            "fabric_validator_coordination_replica_state_paths": ["coord_default.json"],
            "fabric_epoch_replica_state_paths": ["epoch_default.json"],
            "fabric_delivery_required_validator_ids": ["validator.default"],
        },
    )

    assert options.fabric_required_validator_ids == ["validator.default"]
    assert options.fabric_validator_auth_key_ids == ["validator.default=kid-default"]
    assert options.fabric_validator_transport_identities == ["validator.default=tls://default"]
    assert options.fabric_validator_coordination_replica_state_paths == ["coord_default.json"]
    assert options.fabric_epoch_replica_state_paths == ["epoch_default.json"]
    assert options.fabric_delivery_required_validator_ids == ["validator.default"]
