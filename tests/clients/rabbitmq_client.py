"""
Test client for RabbitMQ rating service using FastStream.

Usage:
    uv run python -m tests.clients.rabbitmq_client
"""

import uuid
from datetime import datetime, timezone

from faststream.rabbit import RabbitBroker

from src.domain.models.requests import (
    EffectiveRatingRequest,
    MatchResult,
    Player,
    PlayerRole,
    MatchTeam,
    MatchPlayer,
    RatingSettings,
)
from src.domain.models.common import ResponseMessage
from src.domain.models.responses import EffectiveRatingResponse, MatchResultResponse


def get_rabbit_url() -> str:
    from src.env_config import env
    return env.rabbit.url


class RatingServiceTestClient:
    def __init__(self, url: str | None = None):
        self.url = url or get_rabbit_url()
        self.broker = RabbitBroker(self.url)

    async def __aenter__(self) -> "RatingServiceTestClient":
        await self.broker.connect()
        return self

    async def __aexit__(self, *args) -> None:
        await self.broker.stop()

    async def calculate_effective_ratings(
        self,
        draft_id: uuid.UUID,
        players: list[Player],
        settings: RatingSettings | None = None,
    ) -> ResponseMessage[EffectiveRatingResponse]:
        request = EffectiveRatingRequest(
            draft_id=draft_id,
            players=players,
            settings=settings or RatingSettings(),
        )
        response = await self.broker.request(
            request,
            queue="rating.effective.calculate",
        )
        return ResponseMessage[EffectiveRatingResponse].model_validate_json(response.body)

    async def process_match_result(
        self,
        match_id: uuid.UUID,
        teams: list[MatchTeam],
        team_ranks: list[float],
        players: list[MatchPlayer],
        settings: RatingSettings | None = None,
    ) -> ResponseMessage[MatchResultResponse]:
        request = MatchResult(
            match_id=match_id,
            match_time=datetime.now(timezone.utc),
            teams=teams,
            team_ranks=team_ranks,
            players=players,
            settings=settings or RatingSettings(),
        )
        response = await self.broker.request(
            request,
            queue="rating.match.process",
        )
        return ResponseMessage[MatchResultResponse].model_validate_json(response.body)


async def create_test_players(count: int = 4) -> list[Player]:
    players = []
    for i in range(count):
        member_id = uuid.uuid4()
        role_id = uuid.uuid4()
        players.append(Player(
            member_id=member_id,
            roles={
                role_id: PlayerRole(
                    priority=i,
                    open_rating=1500,
                )
            },
        ))
    return players


async def create_test_match(
    player_count: int = 4,
) -> tuple[uuid.UUID, list[MatchTeam], list[float], list[MatchPlayer]]:
    match_id = uuid.uuid4()
    teams = [
        MatchTeam(team_id=uuid.uuid4(), player_ids=[]),
        MatchTeam(team_id=uuid.uuid4(), player_ids=[]),
    ]
    players = []

    for i in range(player_count):
        member_id = uuid.uuid4()
        role_id = uuid.uuid4()
        team_idx = i % 2
        teams[team_idx].player_ids.append(member_id)
        players.append(MatchPlayer(
            member_id=member_id,
            role_id=role_id,
            open_rating=1500,
        ))

    team_ranks = [1.0, 2.0] if player_count >= 2 else [1.0]

    return match_id, teams, team_ranks, players


async def run_tests():
    print("Connecting to RabbitMQ...")
    async with RatingServiceTestClient() as client:
        print("Connected successfully!\n")

        print("=" * 60)
        print("TEST 1: Calculate Effective Ratings")
        print("=" * 60)
        players = await create_test_players(count=4)
        draft_id = uuid.uuid4()

        print(f"Draft ID: {draft_id}")
        print(f"Players: {len(players)}")
        for p in players:
            print(f"  - {p.member_id}: {list(p.roles.values())[0].open_rating}")

        response = await client.calculate_effective_ratings(draft_id, players)
        print(f"\nStatus: {response.status}")

        if response.status == 200:
            data = response.message
            if isinstance(data, EffectiveRatingResponse):
                print(f"Draft ID: {data.draft_id}")
                print(f"Created at: {data.created_at}")
                print("Player ratings:")
                for player in data.players:
                    print(f"  - {player.member_id}:")
                    print(f"      Open rating: {player.open_rating}")
                    print(f"      Effective rating: {player.effective_rating}")
                    print(f"      Hidden rating: {player.hidden_rating}")
            else:
                print(f"Unexpected message type: {type(data)}")
        else:
            print(f"Error: {response.message}")

        print("\n" + "=" * 60)
        print("TEST 2: Process Match Result")
        print("=" * 60)
        match_id, teams, team_ranks, match_players = await create_test_match(player_count=4)

        print(f"Match ID: {match_id}")
        print(f"Teams: {len(teams)}")
        print(f"Team ranks: {team_ranks}")
        print(f"Players: {len(match_players)}")
        for p in match_players:
            print(f"  - {p.member_id}: {p.open_rating}")

        response = await client.process_match_result(
            match_id=match_id,
            teams=teams,
            team_ranks=team_ranks,
            players=match_players,
        )
        print(f"\nStatus: {response.status}")

        if response.status == 200:
            data = response.message
            if isinstance(data, MatchResultResponse):
                print(f"Match ID: {data.match_id}")
                print(f"Created at: {data.created_at}")
                print("Player updates:")
                for update in data.player_updates:
                    print(f"  - {update.member_id}:")
                    print(f"      Old: {update.old_open_rating} -> New: {update.new_open_rating}")
                    print(f"      Delta: {update.open_rating_delta}")
            else:
                print(f"Unexpected message type: {type(data)}")
        else:
            print(f"Error: {response.message}")

        print("\n" + "=" * 60)
        print("ALL TESTS COMPLETED")
        print("=" * 60)


def main():
    import asyncio
    print("Rating Service RabbitMQ Test Client")
    print("=" * 60)
    asyncio.run(run_tests())


if __name__ == "__main__":
    main()
