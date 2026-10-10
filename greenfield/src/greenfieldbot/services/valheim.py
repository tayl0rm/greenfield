import asyncio
import logging

import a2s

logger = logging.getLogger(__name__)

# Valheim Steam server query settings.
A2S_PORT = 2457
A2S_QUERY_TIMEOUT = 5.0


async def get_player_info(host: str):
    """
    Query Valheim through A2S.

    Returns the server information on success, or None if the query fails
    or returns an invalid player count.
    """
    try:
        info = await asyncio.to_thread(
            a2s.info,
            (host, A2S_PORT),
            timeout=A2S_QUERY_TIMEOUT,
        )

        player_count = getattr(info, "player_count", None)

        if (
            not isinstance(player_count, int)
            or isinstance(player_count, bool)
            or player_count < 0
        ):
            logger.warning(
                "A2S returned an invalid player count from %s:%d: %r",
                host,
                A2S_PORT,
                player_count,
            )
            return None

        logger.debug(
            "A2S query succeeded for %s:%d: %d/%s players",
            host,
            A2S_PORT,
            player_count,
            getattr(info, "max_players", "unknown"),
        )

        return info

    except Exception as exc:
        logger.warning(
            "A2S query failed for %s:%d: %s",
            host,
            A2S_PORT,
            exc,
        )
        return None
