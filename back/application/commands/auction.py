from __future__ import annotations

from application.commands.bus import CONTROLLER_AND_DISPLAY, CommandSpec
from application.commands.payloads import AuctionBidCommand, TeamCommand

AUCTION_COMMANDS = (
    CommandSpec("auction.start", lambda config, *_: config.start_auction()),
    CommandSpec(
        "auction.buzzer",
        lambda config, command, context: config.register_auction_buzzer(command.team, context.now_ms),
        TeamCommand,
        CONTROLLER_AND_DISPLAY,
    ),
    CommandSpec(
        "auction.select",
        lambda config, command, _: config.select_auction_bid(command.team, command.target_count),
        AuctionBidCommand,
    ),
    CommandSpec("auction.launch", lambda config, _, context: config.launch_auction_attempt(context.now_ms)),
    CommandSpec("auction.increment", lambda config, _, context: config.change_auction_count(1, context.now_ms)),
    CommandSpec("auction.decrement", lambda config, _, context: config.change_auction_count(-1, context.now_ms)),
    CommandSpec("auction.next-theme", lambda config, *_: config.next_auction_theme()),
)
