from datetime import time
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.campaign import CampaignCreate


def test_campaign_defaults_match_requirements() -> None:
    campaign = CampaignCreate(name="Outreach", job_profile_id=uuid4())

    assert campaign.daily_limit == 50
    assert campaign.followup_interval_days == 4
    assert campaign.max_followups == 2
    assert campaign.sending_window_start == time(9)
    assert campaign.sending_window_end == time(18)


def test_campaign_rejects_only_one_window_boundary() -> None:
    with pytest.raises(ValidationError):
        CampaignCreate(
            name="Outreach",
            job_profile_id=uuid4(),
            sending_window_start=None,
            sending_window_end=time(18),
        )
