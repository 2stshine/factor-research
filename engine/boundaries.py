"""Shared campaign boundary calculations for discovery and sealed OOS."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


QUALIFICATION_POLICY = "all_discovery_non_reject_by_pass_v1"
HISTORICAL_HOLDOUT_MODE = "trailing_historical_holdout"
PROSPECTIVE_HOLDOUT_MODE = "prospective_holdout"


def _date(value: str, *, label: str) -> pd.Timestamp:
    """Normalize a required manifest date without accepting ``None`` as today."""
    if value is None:
        raise ValueError(f"{label}가 필요합니다")
    try:
        timestamp = pd.Timestamp(value).normalize()
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label}가 올바른 날짜가 아닙니다: {value!r}") from exc
    if pd.isna(timestamp):
        raise ValueError(f"{label}가 올바른 날짜가 아닙니다: {value!r}")
    return timestamp


@dataclass(frozen=True)
class CampaignWindow:
    """One immutable, non-overlapping discovery/confirmation window.

    ``discovery_data_cutoff`` is the last row exposed to discovery.  It exists
    only to supply the final discovery signal's one-month forward return.
    ``snapshot_cutoff`` is the last completed Silver month sealed at campaign
    creation; that month supplies the final OOS signal's forward return.
    """

    discovery_data_cutoff: str
    snapshot_cutoff: str
    discovery_signal_end: pd.Period
    discovery_return_end: pd.Period
    oos_signal_start: pd.Period
    oos_signal_end: pd.Period
    oos_return_start: pd.Period
    oos_return_end: pd.Period
    closure_month: pd.Period
    oos_months: int
    mode: str
    snapshot_completed_month: pd.Period

    @classmethod
    def from_completed_snapshot(
        cls,
        *,
        discovery_data_cutoff: str,
        snapshot_cutoff: str,
        oos_months: int,
    ) -> "CampaignWindow":
        """Derive an exact trailing historical holdout from a completed snapshot.

        The completed snapshot month is the final realized-return month.  The
        immediately preceding month is the last OOS signal month, and exactly
        ``oos_months`` signals are counted backwards from there.  Discovery is
        separated by one return-support month, so it cannot consume an OOS row.
        """
        if oos_months < 1:
            raise ValueError("OOS 기간은 1개월 이상이어야 합니다")
        discovery_cutoff = _date(
            discovery_data_cutoff, label="discovery data cutoff",
        )
        snapshot = _date(snapshot_cutoff, label="snapshot cutoff")
        snapshot_month = snapshot.to_period("M")
        signal_end = snapshot_month - 1
        signal_start = signal_end - (int(oos_months) - 1)
        discovery_return_end = signal_start - 1
        discovery_signal_end = discovery_return_end - 1
        observed_discovery_month = discovery_cutoff.to_period("M")
        if observed_discovery_month != discovery_return_end:
            raise ValueError(
                "discovery data cutoff 월은 OOS 시작 직전 return-support 월이어야 "
                f"합니다: expected={discovery_return_end}, "
                f"observed={observed_discovery_month}"
            )
        if discovery_cutoff > snapshot:
            raise ValueError("discovery data cutoff는 snapshot cutoff보다 늦을 수 없습니다")
        return cls(
            discovery_data_cutoff=str(discovery_cutoff.date()),
            snapshot_cutoff=str(snapshot.date()),
            discovery_signal_end=discovery_signal_end,
            discovery_return_end=discovery_return_end,
            oos_signal_start=signal_start,
            oos_signal_end=signal_end,
            oos_return_start=signal_start + 1,
            oos_return_end=snapshot_month,
            closure_month=snapshot_month + 1,
            oos_months=int(oos_months),
            mode=HISTORICAL_HOLDOUT_MODE,
            snapshot_completed_month=snapshot_month,
        )

    @classmethod
    def from_prospective_snapshot(
        cls,
        *,
        discovery_data_cutoff: str,
        snapshot_cutoff: str,
        oos_start: str | pd.Period,
        oos_months: int,
    ) -> "CampaignWindow":
        """Freeze definitions now and reserve a future, never-observed OOS.

        The creation snapshot contains discovery only.  ``oos_start`` must be
        later than its completed month; callers normally choose the month after
        the current partial month so no in-progress signal can leak into design.
        """
        if oos_months < 1:
            raise ValueError("OOS 기간은 1개월 이상이어야 합니다")
        discovery_cutoff = _date(
            discovery_data_cutoff, label="discovery data cutoff",
        )
        snapshot = _date(snapshot_cutoff, label="snapshot cutoff")
        if discovery_cutoff != snapshot:
            raise ValueError(
                "prospective campaign의 discovery cutoff와 생성 snapshot은 "
                "같아야 합니다"
            )
        snapshot_month = snapshot.to_period("M")
        start = pd.Period(oos_start, freq="M")
        if start <= snapshot_month:
            raise ValueError(
                f"prospective OOS 시작 {start}는 생성 snapshot 월 "
                f"{snapshot_month}보다 뒤여야 합니다"
            )
        signal_end = start + int(oos_months) - 1
        return_end = signal_end + 1
        return cls(
            discovery_data_cutoff=str(discovery_cutoff.date()),
            snapshot_cutoff=str(snapshot.date()),
            discovery_signal_end=snapshot_month - 1,
            discovery_return_end=snapshot_month,
            oos_signal_start=start,
            oos_signal_end=signal_end,
            oos_return_start=start + 1,
            oos_return_end=return_end,
            closure_month=return_end + 1,
            oos_months=int(oos_months),
            mode=PROSPECTIVE_HOLDOUT_MODE,
            snapshot_completed_month=snapshot_month,
        )

    @classmethod
    def create(
        cls,
        *,
        oos_start: str | pd.Period,
        oos_months: int,
        discovery_data_cutoff: str | None = None,
        snapshot_cutoff: str | None = None,
        data_cutoff: str | None = None,
    ) -> "CampaignWindow":
        """Compatibility constructor for callers with an explicit OOS start.

        New campaign creation should use :meth:`from_completed_snapshot` so the
        last completed data month, rather than a caller-selected start, anchors
        the holdout.  ``data_cutoff`` is the deprecated name for
        ``discovery_data_cutoff``.
        """
        if oos_months < 1:
            raise ValueError("OOS 기간은 1개월 이상이어야 합니다")
        if discovery_data_cutoff is not None and data_cutoff is not None:
            explicit = _date(
                discovery_data_cutoff, label="discovery data cutoff",
            )
            legacy = _date(data_cutoff, label="data cutoff")
            if explicit != legacy:
                raise ValueError(
                    "discovery_data_cutoff와 legacy data_cutoff가 다릅니다"
                )
        cutoff_value = discovery_data_cutoff or data_cutoff
        cutoff = _date(cutoff_value, label="discovery data cutoff")
        cutoff_month = cutoff.to_period("M")
        start = pd.Period(oos_start, freq="M")
        if start <= cutoff_month:
            raise ValueError(
                f"OOS signal 시작 {start}는 discovery return 종료 "
                f"{cutoff_month}보다 뒤여야 합니다"
            )
        signal_end = start + int(oos_months) - 1
        return_end = signal_end + 1
        if snapshot_cutoff is None:
            # Legacy prospective callers do not have an observed snapshot yet.
            # Represent their fixed final return month explicitly without
            # weakening the new manifest validator, which always uses
            # ``from_completed_snapshot``.
            snapshot = return_end.to_timestamp(how="end").normalize()
        else:
            snapshot = _date(snapshot_cutoff, label="snapshot cutoff")
            if snapshot.to_period("M") != return_end:
                raise ValueError(
                    "snapshot cutoff 월은 마지막 OOS realized-return 월이어야 "
                    f"합니다: expected={return_end}, "
                    f"observed={snapshot.to_period('M')}"
                )
        return cls(
            discovery_data_cutoff=str(cutoff.date()),
            snapshot_cutoff=str(snapshot.date()),
            discovery_signal_end=cutoff_month - 1,
            discovery_return_end=cutoff_month,
            oos_signal_start=start,
            oos_signal_end=signal_end,
            oos_return_start=start + 1,
            oos_return_end=return_end,
            closure_month=return_end + 1,
            oos_months=int(oos_months),
            mode=HISTORICAL_HOLDOUT_MODE,
            snapshot_completed_month=snapshot.to_period("M"),
        )

    @property
    def data_cutoff(self) -> str:
        """Deprecated alias for callers not yet migrated to the explicit name."""
        return self.discovery_data_cutoff

    @property
    def consumed_start(self) -> pd.Period:
        return self.oos_signal_start

    @property
    def consumed_stop(self) -> pd.Period:
        """Exclusive end of the OOS signal+return support."""
        return self.oos_return_end + 1

    def validate_oos_end(self, oos_end: str | pd.Period) -> None:
        observed = pd.Period(oos_end, freq="M")
        if observed != self.oos_signal_end:
            raise ValueError(
                f"고정 OOS는 정확히 {self.oos_months} signal개월이어야 합니다: "
                f"expected_end={self.oos_signal_end}, observed_end={observed}"
            )

    def snapshot_manifest(self) -> dict:
        return {
            "data_cutoff": self.snapshot_cutoff,
            "completed_month": str(self.snapshot_completed_month),
        }

    def discovery_manifest(self) -> dict:
        return {
            "data_cutoff": self.discovery_data_cutoff,
            "signal_end": str(self.discovery_signal_end),
            "return_end": str(self.discovery_return_end),
        }

    def oos_manifest(self) -> dict:
        return {
            "mode": self.mode,
            "status": "SEALED",
            "start": str(self.oos_signal_start),
            "signal_end": str(self.oos_signal_end),
            "min_months": self.oos_months,
            "return_start": str(self.oos_return_start),
            "return_end": str(self.oos_return_end),
            "required_data_month": str(self.oos_return_end),
            "closure_month": str(self.closure_month),
            "earliest_reveal_month": str(self.closure_month),
            "earliest_data_month": str(self.closure_month),
            "revealed_at": None,
        }


def validate_manifest(campaign: dict, *, expected_oos_months: int) -> CampaignWindow:
    """Authenticate every stored epoch-1.5 boundary from its frozen inputs."""
    snapshot = campaign.get("snapshot") or {}
    discovery = campaign.get("discovery") or {}
    oos = campaign.get("oos") or {}
    if int(oos.get("min_months", 0)) != int(expected_oos_months):
        raise ValueError(
            f"campaign OOS는 현재 ruleset의 정확한 {expected_oos_months}개월이어야 합니다"
        )
    mode = oos.get("mode")
    try:
        if mode == PROSPECTIVE_HOLDOUT_MODE:
            window = CampaignWindow.from_prospective_snapshot(
                discovery_data_cutoff=discovery.get("data_cutoff"),
                snapshot_cutoff=snapshot.get("data_cutoff"),
                oos_start=oos.get("start"),
                oos_months=expected_oos_months,
            )
        elif mode == HISTORICAL_HOLDOUT_MODE:
            window = CampaignWindow.from_completed_snapshot(
                discovery_data_cutoff=discovery.get("data_cutoff"),
                snapshot_cutoff=snapshot.get("data_cutoff"),
                oos_months=expected_oos_months,
            )
        else:
            raise ValueError(f"지원하지 않는 OOS mode입니다: {mode!r}")
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "campaign snapshot/discovery/OOS 경계 무결성 검증에 실패했습니다"
        ) from exc
    expected_snapshot = window.snapshot_manifest()
    expected_discovery = window.discovery_manifest()
    expected_oos = window.oos_manifest()
    comparable_snapshot = {
        key: snapshot.get(key) for key in expected_snapshot
    }
    comparable_oos = {
        key: oos.get(key)
        for key in expected_oos
        if key != "revealed_at"
    }
    if (
        comparable_snapshot != expected_snapshot
        or discovery != expected_discovery
        or comparable_oos != {
            key: value
            for key, value in expected_oos.items()
            if key != "revealed_at"
        }
    ):
        raise ValueError(
            "campaign snapshot/discovery/OOS 경계 무결성 검증에 실패했습니다"
        )
    return window
