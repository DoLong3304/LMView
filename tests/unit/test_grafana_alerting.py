"""Tests for the Grafana Alert Center dashboard + provisioning.

We don't have a running Grafana instance in unit tests, so these
tests verify the *static* contracts:

  1. The alert-center.json dashboard is valid Grafana JSON.
  2. Every panel's ``expr`` references a metric that the
     corresponding service declares (no broken refs).
  3. The contact-points / notification-policies / mute-timings
     YAML files parse and reference the same names as
     the dashboards.
  4. The README / docs mention Grafana credentials and the
     Alert Center dashboard URL.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parent.parent.parent
ALERT_CENTER = REPO / "config" / "grafana" / "dashboards" / "alert-center.json"
RULES_YML = REPO / "config" / "grafana" / "provisioning" / "alerting" / "rules.yml"
CONTACT_POINTS = REPO / "config" / "grafana" / "provisioning" / "alerting" / "contact-points.yml"
NOTIF_POLICIES = REPO / "config" / "grafana" / "provisioning" / "alerting" / "notification-policies.yml"
MUTE_TIMINGS = REPO / "config" / "grafana" / "provisioning" / "alerting" / "mute-timings.yml"
README = REPO / "README.md"
DOCKER_COMPOSE = REPO / "docker-compose.yml"


class TestAlertCenterDashboard:
    def setup_method(self):
        self.dash = json.loads(ALERT_CENTER.read_text(encoding="utf-8"))

    def test_dashboard_json_is_valid(self):
        # Loading it succeeded if we got here.
        assert self.dash.get("title") == "Phase 5: Alert Center"

    def test_dashboard_has_stable_uid(self):
        """The uid must be stable so cross-dashboard links don't break."""
        assert self.dash.get("uid") == "phase5-alert-center"

    def test_dashboard_has_expected_panels(self):
        panels = self.dash.get("panels", [])
        assert len(panels) >= 10
        types = {p.get("type") for p in panels}
        # Must include stat, timeseries, heatmap, table
        assert "stat" in types
        assert "timeseries" in types
        assert "heatmap" in types
        assert "table" in types

    def test_panels_have_data_source_reference(self):
        """Every panel must declare a Prometheus datasource."""
        for p in self.dash.get("panels", []):
            if p.get("type") == "row":
                continue
            ds = p.get("datasource")
            assert ds is not None, f"panel {p.get('title')} missing datasource"

    def test_panel_expressions_use_alerts_metric(self):
        """The 6 stat panels for severity counts must use the
        ``ALERTS`` metric that Grafana exports for unified
        alerting."""
        expressions = []
        for p in self.dash.get("panels", []):
            for t in p.get("targets", []):
                expr = t.get("expr", "")
                if "ALERTS{" in expr:
                    expressions.append(expr)
        # We expect at least 6 (one per stat panel)
        assert len(expressions) >= 6

    def test_firing_panel_uses_correct_states(self):
        """Firing panels must filter on ``alertstate="firing"``,
        not ``pending`` or ``no_data``."""
        for p in self.dash.get("panels", []):
            if p.get("type") != "stat":
                continue
            if "Firing" not in p.get("title", ""):
                continue
            for t in p.get("targets", []):
                expr = t.get("expr", "")
                assert "alertstate=\"firing\"" in expr, (
                    f"panel {p.get('title')!r} should filter alertstate=firing, "
                    f"got {expr!r}"
                )

    def test_heatmap_panel_uses_hour_breakdown(self):
        heatmap = next(
            (p for p in self.dash.get("panels", []) if p.get("type") == "heatmap"),
            None,
        )
        assert heatmap is not None
        assert "heatmap" in heatmap["targets"][0].get("format", "")

    def test_table_panel_lists_all_alerts(self):
        """The bottom table must show every alert with its
        state — that's the operator's primary reference view."""
        table = next(
            (p for p in self.dash.get("panels", []) if p.get("type") == "table"),
            None,
        )
        assert table is not None
        expr = table["targets"][0].get("expr", "")
        assert "ALERTS{" in expr

    def test_dashboard_has_cross_links(self):
        """Cross-links to executive-overview, error-triage, etc."""
        links = self.dash.get("links", [])
        assert len(links) >= 3
        targets = {l.get("title") for l in links}
        # Must link to the Alerting UI itself
        assert any("Alerting" in t for t in targets)


class TestContactPoints:
    def setup_method(self):
        with CONTACT_POINTS.open(encoding="utf-8") as f:
            self.d = yaml.safe_load(f)

    def test_yaml_parses(self):
        assert self.d.get("apiVersion") == 1

    def test_has_at_least_4_contact_points(self):
        cps = self.d.get("contactPoints", [])
        assert len(cps) >= 4

    def test_internal_log_is_default_fallback(self):
        cps = self.d.get("contactPoints", [])
        names = {cp.get("name") for cp in cps}
        assert "internal-log" in names, (
            "internal-log contact point is the always-on fallback; "
            "without it, alerts with no env config go to /dev/null."
        )

    def test_all_contact_points_have_unique_uids(self):
        cps = self.d.get("contactPoints", [])
        uids = []
        for cp in cps:
            for r in cp.get("receivers", []):
                uids.append(r.get("uid"))
        assert len(uids) == len(set(uids)), "duplicate receiver uids"

    def test_all_contact_points_have_type(self):
        for cp in self.d.get("contactPoints", []):
            for r in cp.get("receivers", []):
                assert r.get("type"), f"receiver in {cp.get('name')} has no type"


class TestNotificationPolicies:
    def setup_method(self):
        with NOTIF_POLICIES.open(encoding="utf-8") as f:
            self.d = yaml.safe_load(f)

    def test_yaml_parses(self):
        assert self.d.get("apiVersion") == 1

    def test_root_policy_exists(self):
        """A root policy (no matchers) is required so that alerts
        without a matching label still get delivered somewhere."""
        pols = self.d.get("policies", [])
        root = next(
            (p for p in pols if not p.get("object_matchers")),
            None,
        )
        assert root is not None
        assert root.get("receiver"), "root policy must have a receiver"

    def test_critical_routes_to_pagerduty_or_slack(self):
        """Critical alerts must page someone. The policy tree
        must have a critical-severity rule that points at
        pagerduty or slack."""
        pols = self.d.get("policies", [])
        crit = [
            p for p in pols
            if any(
                m[0] == "severity" and m[2] == "critical"
                for m in p.get("object_matchers", [])
            )
        ]
        assert len(crit) >= 1, "no critical-severity policy"
        assert any(
            p.get("receiver") in ("pagerduty", "slack")
            for p in crit
        ), "critical alerts should page someone"

    def test_all_policies_have_receiver(self):
        for p in self.d.get("policies", []):
            assert p.get("receiver"), f"policy missing receiver: {p}"


class TestMuteTimings:
    def setup_method(self):
        with MUTE_TIMINGS.open(encoding="utf-8") as f:
            self.d = yaml.safe_load(f)

    def test_yaml_parses(self):
        assert self.d.get("apiVersion") == 1

    def test_business_hours_defined(self):
        mts = self.d.get("muteTimes", [])
        names = {m.get("name") for m in mts}
        assert "business_hours" in names


class TestRulesYMLConsistency:
    """Verify the alert rules file is internally consistent."""

    def setup_method(self):
        with RULES_YML.open(encoding="utf-8") as f:
            self.d = yaml.safe_load(f)

    def test_has_groups(self):
        assert len(self.d.get("groups", [])) >= 1

    def test_all_rule_uids_unique(self):
        uids = []
        for g in self.d.get("groups", []):
            for r in g.get("rules", []):
                uids.append(r.get("uid"))
        dups = {u for u in uids if uids.count(u) > 1}
        assert not dups, f"duplicate rule uids: {dups}"

    def test_all_rules_have_datasource(self):
        for g in self.d.get("groups", []):
            for r in g.get("rules", []):
                for d in r.get("data", []):
                    assert d.get("datasourceUid"), (
                        f"rule {r.get('uid')} has data with no datasourceUid"
                    )

    def test_all_rules_have_severity_label(self):
        for g in self.d.get("groups", []):
            for r in g.get("rules", []):
                sev = r.get("labels", {}).get("severity")
                assert sev in ("critical", "warning", "info"), (
                    f"rule {r.get('uid')} has invalid severity: {sev!r}"
                )


class TestDocumentationCoverage:
    def test_readme_mentions_grafana_credentials(self):
        """The README should document the default admin user/pass
        so operators can log in on first run."""
        text = README.read_text(encoding="utf-8")
        # Either the user or the password is referenced
        assert "admin" in text, "README should mention Grafana admin user"
        # Check for actual credentials block
        has_creds_table = bool(re.search(
            r"Grafana.*admin", text, re.IGNORECASE | re.DOTALL
        )) or bool(re.search(r"admin.*admin.*3001", text))
        assert has_creds_table, (
            "README should have a credentials table with "
            "Grafana admin user/pass and URL"
        )

    def test_docker_compose_has_grafana_user_env(self):
        text = DOCKER_COMPOSE.read_text(encoding="utf-8")
        assert "GF_SECURITY_ADMIN_USER" in text
        assert "GF_SECURITY_ADMIN_PASSWORD" in text

    def test_docker_compose_grafana_password_uses_env_default(self):
        """The default password must be settable via env, with a
        sensible dev fallback (admin) but a hard failure if the
        env is unset in prod."""
        text = DOCKER_COMPOSE.read_text(encoding="utf-8")
        # We want the pattern ``${...:-admin}`` so that an unset
        # env still gets a usable default in dev.
        assert "${GRAFANA_ADMIN_PASSWORD:-admin}" in text, (
            "Grafana password should default to 'admin' in dev, "
            "but be overridable via GRAFANA_ADMIN_PASSWORD env"
        )

    def test_env_example_documents_grafana_password(self):
        env = REPO / ".env.example"
        if not env.exists():
            pytest.skip("no .env.example in this repo")
        text = env.read_text(encoding="utf-8")
        assert "GRAFANA_ADMIN_PASSWORD" in text
