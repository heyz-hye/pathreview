"""Tests for api/routes/health.py"""

from unittest.mock import AsyncMock, patch

import pytest

from api.routes.health import health_check


@pytest.mark.unit
class TestHealthCheck:
    """Test suite for the /health route's database probe."""

    @pytest.fixture
    def mock_db_session(self) -> AsyncMock:
        """Create a mock async database session."""
        session = AsyncMock()
        session.execute = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_postgres_check_passes_textual_sql(self, mock_db_session: AsyncMock) -> None:
        """db.execute should be called with a TextClause, not a raw string."""
        with patch("core.config.settings") as mock_settings, patch("redis.Redis") as mock_redis_cls:
            mock_settings.redis_host = "localhost"
            mock_settings.redis_port = 6379
            mock_settings.vector_db_url = None
            mock_redis_cls.return_value.ping.return_value = True

            await health_check(db=mock_db_session)

        mock_db_session.execute.assert_called_once()
        executed_arg = mock_db_session.execute.call_args[0][0]
        assert not isinstance(executed_arg, str)
        assert str(executed_arg) == "SELECT 1"

    @pytest.mark.asyncio
    async def test_postgres_reported_healthy_when_probe_succeeds(
        self, mock_db_session: AsyncMock
    ) -> None:
        """A successful db.execute should mark postgres as healthy."""
        with patch("core.config.settings") as mock_settings, patch("redis.Redis") as mock_redis_cls:
            mock_settings.redis_host = "localhost"
            mock_settings.redis_port = 6379
            mock_settings.vector_db_url = None
            mock_redis_cls.return_value.ping.return_value = True

            result = await health_check(db=mock_db_session)

        assert result["dependencies"]["postgres"] == "healthy"
