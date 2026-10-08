from app.config import Settings, get_settings


def test_settings_defaults():
    settings = get_settings()
    assert isinstance(settings, Settings)
    assert settings.app_name == "DripsLens"
    assert settings.refresh_interval_hours == 6.0
    assert settings.cache_ttl_seconds == 300
