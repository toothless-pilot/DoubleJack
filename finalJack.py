"""
Doublejack — a Blackjack variant with a Doublejack bonus round.

CS5 Final Project
Author: Alex Kim, Rushil Jaiswal, and Suhas Beeravelli

Gameplay:
    - Standard Blackjack rules, target 21, dealer hits below 17.
    - Players bet poptarts (the in-game currency) instead of dollars.
    - If the dealer's first round hits exactly 21, players are offered the
      chance to play "Doublejack" — a follow-on round with target 42 where
      payouts and losses are doubled.
    - AI players use Hi-Lo card counting to size bets.

The code is organized as a single Doublejack class that owns all per-table
state, plus a startGame() entry point that handles player setup.
"""

import random
import time

# ----------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------

# Card face -> point value. Aces are 11 by default; countHand() downgrades
# them to 1 as needed to avoid busting.
CARD_VALUES = {
    "A": 11, "K": 10, "Q": 10, "J": 10, "10": 10,
    "9": 9, "8": 8, "7": 7, "6": 6, "5": 5,
    "4": 4, "3": 3, "2": 2,
}

# Hi-Lo counting values for the card-counting AI.
# High cards (10-A) are -1, low cards (2-6) are +1, neutral (7-9) are 0.
COUNTING_VALUES = {
    "A": -1, "K": -1, "Q": -1, "J": -1, "10": -1,
    "9": 0, "8": 0, "7": 0,
    "6": 1, "5": 1, "4": 1, "3": 1, "2": 1,
}

# A single 52-card deck (4 of each face).
SINGLE_DECK = [card for card in CARD_VALUES for _ in range(4)]

# We play with a 6-deck shoe and reshuffle when fewer than ~1.5 decks remain.
NUM_DECKS_IN_SHOE = 6
RESHUFFLE_THRESHOLD = 78  # cards remaining

# AI opponent name pool. Sampled (not mutated) so reruns work.
POKER_PLAYERS = [
    "Phil Ivey", "Daniel Negreanu", "Doyle Brunson",
    "Phil Hellmuth", "Johnny Chan",
]

# Player status codes.
STATUS_PLAYING = 1
STATUS_BUST = 0
STATUS_STAND = 2
STATUS_NATURAL = 3  # natural blackjack / doublejack on first two cards

# Player type codes.
TYPE_AI = 0
TYPE_HUMAN = 1

# Card back glyph used when hiding the dealer's hole card.
HIDDEN_CARD = "🂠"

# Pacing — keep short so testing isn't painful.
SHORT_PAUSE = 0.6
MEDIUM_PAUSE = 1.2
LONG_PAUSE = 1.8

# Visual separator
SEP = "─" * 50


def prompt_int(message, min_value=None, max_value=None):
    """Ask the user for an integer, re-prompting until they give a valid one.

    Optional min_value / max_value bound the accepted range (inclusive).
    Returns the validated int.
    """
    while True:
        raw = input(message).strip()
        try:
            value = int(raw)
        except ValueError:
            print(f"  '{raw}' isn't a whole number. Try again.")
            continue
        if min_value is not None and value < min_value:
            print(f"  Please enter a number ≥ {min_value}.")
            continue
        if max_value is not None and value > max_value:
            print(f"  Please enter a number ≤ {max_value}.")
            continue
        return value


def prompt_choice(message, valid_choices):
    """Ask the user for a string choice, re-prompting until valid.

    valid_choices is a list of acceptable single-letter answers (case-
    insensitive). Returns the choice in upper-case.
    """
    valid_upper = [c.upper() for c in valid_choices]
    while True:
        raw = input(message).strip().upper()
        if raw in valid_upper:
            return raw
        print(f"  Please enter one of: {'/'.join(valid_upper)}")


def prompt_nonempty(message):
    """Ask the user for a non-empty string, re-prompting until valid."""
    while True:
        raw = input(message).strip()
        if raw:
            return raw
        print("  Please enter something (no blanks).")


# ----------------------------------------------------------------------
# Game class
# ----------------------------------------------------------------------

class Doublejack:
    """One Blackjack/Doublejack table with one dealer and N players."""

    def __init__(self, player_data, showCount=False):
        """Build a fresh table.

        player_data is a list of [name, starting_poptarts, type] entries
        where type is TYPE_HUMAN (1) or TYPE_AI (0).
        showCount, when True, prints the Hi-Lo running/true count and
        per-round stats so the player can watch the card-counting AI.
        """
        self.shoe = SINGLE_DECK * NUM_DECKS_IN_SHOE
        random.shuffle(self.shoe)

        # Game-mode state. These are mutated when entering Doublejack and
        # reset back to Blackjack defaults at the end of every payout.
        self.target = 21
        self.payoutMultiplier = 1
        self.gameName = "Blackjack"

        # Per-player bookkeeping. Built once from player_data.
        self.numPlayers = len(player_data)
        self.playerNames = [p[0] for p in player_data]
        self.playerHands = {p[0]: [] for p in player_data}
        # staticPlayerPoptarts is the starting balance — used for the
        # final summary so we can show net winnings.
        self.staticPlayerPoptarts = {p[0]: p[1] for p in player_data}
        self.playerPoptarts = {p[0]: p[1] for p in player_data}
        self.playerBets = {p[0]: 0 for p in player_data}
        self.playerStatus = {p[0]: STATUS_PLAYING for p in player_data}
        self.playerType = {p[0]: p[2] for p in player_data}

        self.dealerHand = []

        # Names of players who must sit out the next round (e.g. busted
        # in Blackjack and so are not eligible for the Doublejack bonus).
        # Cleared automatically when the round it applies to begins.
        self.sittingOut = set()

        # Card-counting AI state
        self.runningCount = 0
        self.trueCount = 0

        # Optional stats display.
        self.showCount = showCount
        self.roundsPlayed = 0     # incremented every completed round
        self.handsDealt = 0       # cards drawn during this game (any kind)

        # Set externally for AI-vs-AI mode: an integer number of rounds
        # to auto-play before stopping. None means human-driven mode.
        self.aiOnlyRounds = None

    # ------------------------------------------------------------------
    # Deck / counting helpers
    # ------------------------------------------------------------------

    def randomCard(self):
        """Draw one card from the shoe and update the running count."""
        card = random.choice(self.shoe)
        self.shoe.remove(card)
        self.runningCount += COUNTING_VALUES[card]
        self.handsDealt += 1
        return card

    def countHand(self, hand):
        """Return the best (highest non-busting if possible) total of a hand.

        Aces start as 11 and demote to 1 one at a time while the total
        exceeds the current target.
        """
        total = sum(CARD_VALUES[card] for card in hand)
        num_aces = hand.count("A")
        while num_aces > 0 and total > self.target:
            total -= 10
            num_aces -= 1
        return total

    def deckCapacity(self):
        """Reshuffle the shoe if it's running low; resets the count."""
        if len(self.shoe) < RESHUFFLE_THRESHOLD:
            print("\n" + SEP)
            print("Reshuffling deck…")
            print(SEP)
            time.sleep(MEDIUM_PAUSE)
            self.shoe = SINGLE_DECK * NUM_DECKS_IN_SHOE
            random.shuffle(self.shoe)
            self.runningCount = 0
            self.trueCount = 0

    # ------------------------------------------------------------------
    # Round setup
    # ------------------------------------------------------------------

    def dealCards(self):
        """Deal the opening two cards.

        Both dealer and every eligible player get two fresh cards. In
        Doublejack (the bonus round), the dealer also gets two more cards
        on top of his prior 21, but players are dealt fresh hands so they
        can play toward 42 from a clean start. Players in self.sittingOut
        are skipped (e.g. busted in Blackjack so ineligible for the bonus).
        """
        if self.gameName == "Doublejack":
            # Dealer gets 2 more cards on top of his existing 21.
            self.dealerHand += [self.randomCard() for _ in range(2)]
            # Eligible players get two fresh cards.
            for name in self.playerNames:
                if name in self.sittingOut:
                    continue
                if self.playerPoptarts[name] > 0:
                    self.playerHands[name] = [self.randomCard() for _ in range(2)]
            return

        self.dealerHand = [self.randomCard() for _ in range(2)]
        for name in self.playerNames:
            if self.playerPoptarts[name] > 0:
                self.playerHands[name] = [self.randomCard() for _ in range(2)]

    def collectBets(self):
        """Prompt each eligible player (or AI) for their bet this round.

        Players are skipped (with a message) if they are out of poptarts
        or if they were marked to sit out this round (e.g. busted in
        Blackjack, so ineligible for the Doublejack bonus).
        """
        for name in self.playerNames:
            if self.playerPoptarts[name] <= 0:
                print(f"{name} has no poptarts left — sitting out.\n")
                continue
            if name in self.sittingOut:
                print(f"{name} busted in the prior hand — sitting out the bonus.\n")
                continue

            if self.playerType[name] == TYPE_HUMAN:
                self._collectHumanBet(name)
            else:
                self._collectAIBet(name)

            time.sleep(SHORT_PAUSE)
            print()

    def _collectHumanBet(self, name):
        """Read and validate one human player's bet."""
        # Maximum bet is bounded by what the player can afford to LOSE,
        # which in Doublejack mode is twice the bet — so divide by the
        # multiplier to get the legal ceiling.
        max_bet = int(self.playerPoptarts[name] // self.payoutMultiplier)
        print(f"\n{name}'s turn to bet — you have {self.playerPoptarts[name]} 🍓 poptarts.")
        if self.payoutMultiplier > 1:
            print(f"  (Doublejack round: max bet is {max_bet} since losses double.)")
        bet = prompt_int(
            f"  Place your bet (1–{max_bet}): ",
            min_value=1,
            max_value=max_bet,
        )
        self.playerBets[name] = bet
        print(f"  {name} bets {bet} 🍓.")

    def _collectAIBet(self, name):
        """Compute and place an AI player's bet using true-count sizing.

        Base bet is 20% of bankroll. When the true count is positive
        (deck favors the player), bet scales up by 0.5x per count point.
        When negative, bet stays at the base — the AI is willing to skew
        bigger but never smaller than its baseline.
        """
        base = round(self.playerPoptarts[name] * 0.20)
        # Floor at 1 so the AI never bets 0 with a small bankroll.
        base = max(base, 1)
        # Scale up with positive true count (Hi-Lo card counting bias).
        bet = base + 0.5 * base * max(self.trueCount, 0)
        # Cap by what the AI can afford to lose (multiplier-aware).
        max_bet = self.playerPoptarts[name] // self.payoutMultiplier
        bet = int(min(max_bet, bet))
        bet = max(1, bet) if max_bet >= 1 else 0
        self.playerBets[name] = bet
        print(f"{name} bets {bet} 🍓.")

    # ------------------------------------------------------------------
    # Display helpers
    # ------------------------------------------------------------------

    def printPlayerHands(self):
        """Print every active player's current hand."""
        print(SEP)
        for name in self.playerNames:
            if name in self.sittingOut:
                continue
            if self.playerHands[name]:
                hand = self.playerHands[name]
                total = self.countHand(hand)
                print(f"  {name}: {hand}  (total: {total})")
        print(SEP)

    def printCountStats(self):
        """Display Hi-Lo card-counting state and per-game measurements.

        Only prints when self.showCount is True. This surfaces the
        algorithmic creative element (Hi-Lo counting) that otherwise
        runs invisibly inside _collectAIBet. The "AI bet bias" tells
        you how the count is currently nudging AI bet sizing.
        """
        if not self.showCount:
            return
        decks_remaining = max(len(self.shoe) / 52, 0.5)
        # Bet bias used inside _collectAIBet: 1 + 0.5 * max(trueCount, 0).
        bet_bias = 1 + 0.5 * max(self.trueCount, 0)
        print("  ┌─ Hi-Lo card-counting tracker ─────────────────")
        print(f"  │  Rounds played : {self.roundsPlayed}")
        print(f"  │  Cards dealt   : {self.handsDealt}")
        print(f"  │  Shoe remaining: {len(self.shoe)} cards (~{decks_remaining:.1f} decks)")
        print(f"  │  Running count : {self.runningCount:+d}")
        print(f"  │  True count    : {self.trueCount:+.2f}")
        print(f"  │  AI bet bias   : ×{bet_bias:.2f}  "
              f"({'favors player' if self.trueCount > 1 else 'neutral / favors house'})")
        print("  └────────────────────────────────────────────────")

    def printDealerHand(self):
        """Show the dealer's hand with the hole card hidden."""
        if self.gameName == "Blackjack":
            shown = [self.dealerHand[0], HIDDEN_CARD]
        else:
            # In Doublejack the dealer already has 2 visible cards from
            # the prior round; only the freshest card is hidden.
            shown = self.dealerHand[:-1] + [HIDDEN_CARD]
        print(f"  Dealer shows: {shown}")
        print(SEP)

    # ------------------------------------------------------------------
    # Per-player turn
    # ------------------------------------------------------------------

    def checkLimit(self, name):
        """Update playerStatus based on current hand vs target.

        A "natural" (1.5x payout) is only awarded if the player hit the
        target on their original two-card deal. Reaching the target by
        hitting later is treated as a normal stand.
        """
        hand = self.playerHands[name]
        total = self.countHand(hand)
        if total > self.target:
            self.playerStatus[name] = STATUS_BUST
        elif total == self.target and len(hand) == 2:
            self.playerStatus[name] = STATUS_NATURAL
        else:
            self.playerStatus[name] = STATUS_STAND

    def receiveInput(self, name):
        """Run a human player's turn: hit/stand loop with input validation."""
        while True:
            hand = self.playerHands[name]
            total = self.countHand(hand)
            print(f"\n  {name}'s hand: {hand}  (total: {total})")
            choice = prompt_choice(
                f"  HIT or STAND? [H/S] ",
                ["H", "S"],
            )

            if choice == "H":
                hand.append(self.randomCard())
                new_total = self.countHand(hand)
                print(f"  {name} hits — now {hand} (total: {new_total}).")
                time.sleep(SHORT_PAUSE)
                if new_total > self.target:
                    print(f"  {name} BUSTS at {new_total}!")
                    time.sleep(MEDIUM_PAUSE)
                    return
                if new_total == self.target:
                    print(f"  {name} stands at {new_total}.")
                    time.sleep(MEDIUM_PAUSE)
                    return
            else:  # STAND
                print(f"  {name} stands at {total}.")
                time.sleep(MEDIUM_PAUSE)
                return

    def AITurn(self, name):
        """AI player's turn: rule-based strategy using a peek at dealer's up-card."""
        while True:
            hand = self.playerHands[name]
            total = self.countHand(hand)

            if total > self.target:
                print(f"  {name} BUSTS at {total} with {hand}.")
                time.sleep(MEDIUM_PAUSE)
                return

            # Hit on weak totals.
            if total <= self.target - 10:
                hand.append(self.randomCard())
                print(f"  {name} hits — now {hand} (total: {self.countHand(hand)}).")
                time.sleep(SHORT_PAUSE)
                continue

            # Stand on strong totals.
            if total >= self.target - 4:
                print(f"  {name} stands at {total} with {hand}.")
                time.sleep(MEDIUM_PAUSE)
                return

            # Mid-zone: peek at dealer's visible card. If dealer can't bust
            # easily, take another card; otherwise stand.
            dealer_visible_total = self.countHand(self.dealerHand[:-1])
            if dealer_visible_total <= self.target - 15:
                print(f"  {name} stands at {total} with {hand}.")
                time.sleep(MEDIUM_PAUSE)
                return
            hand.append(self.randomCard())
            print(f"  {name} hits — now {hand} (total: {self.countHand(hand)}).")
            time.sleep(SHORT_PAUSE)

    # ------------------------------------------------------------------
    # Dealer turn & payouts
    # ------------------------------------------------------------------

    def dealerTurn(self):
        """Run the dealer's turn after all players are done.

        Dealer hits until reaching target-4 (i.e. 17 in Blackjack, 38 in
        Doublejack — the simulation in the appendix explains why 38).
        """
        print(f"\n  Dealer reveals: {self.dealerHand} (total: {self.countHand(self.dealerHand)})")
        time.sleep(MEDIUM_PAUSE)

        while True:
            total = self.countHand(self.dealerHand)
            if total > self.target:
                print(f"  Dealer BUSTS at {total}.")
                break
            if total >= self.target - 4:
                print(f"  Dealer stands at {total}.")
                break
            self.dealerHand.append(self.randomCard())
            print(f"  Dealer hits — now {self.dealerHand} (total: {self.countHand(self.dealerHand)}).")
            time.sleep(SHORT_PAUSE)

        time.sleep(MEDIUM_PAUSE)
        print(SEP)
        # Recompute true count for next round's AI bet sizing.
        decks_remaining = max(len(self.shoe) / 52, 0.5)
        self.trueCount = self.runningCount / decks_remaining

    def payout(self):
        """Resolve every player's bet against the dealer's final hand."""
        dealer_total = self.countHand(self.dealerHand)
        dealer_busted = dealer_total > self.target

        print(f"\n  ── Payouts ({self.gameName}) ──")
        for name in self.playerNames:
            if self.playerBets[name] == 0:
                # This player sat out (no poptarts).
                continue

            bet = self.playerBets[name]
            player_total = self.countHand(self.playerHands[name])
            status = self.playerStatus[name]

            if status == STATUS_NATURAL:
                # Player hit the target on the first two cards.
                if dealer_total != self.target:
                    # Natural pays 1.5x base, then scaled by mode multiplier.
                    winnings = int(bet * 1.5 * self.payoutMultiplier)
                    self.playerPoptarts[name] += winnings
                    print(f"  {name} hits a natural {self.gameName}! +{winnings} 🍓")
                else:
                    print(f"  {name} and dealer both hit {self.target} — push.")
            elif status == STATUS_STAND:
                if dealer_busted:
                    winnings = bet * self.payoutMultiplier
                    self.playerPoptarts[name] += winnings
                    print(f"  Dealer busts — {name} wins +{winnings} 🍓")
                elif player_total > dealer_total:
                    winnings = bet * self.payoutMultiplier
                    self.playerPoptarts[name] += winnings
                    print(f"  {name} ({player_total}) beats dealer ({dealer_total}) — +{winnings} 🍓")
                elif player_total < dealer_total:
                    losses = bet * self.payoutMultiplier
                    self.playerPoptarts[name] -= losses
                    print(f"  {name} ({player_total}) loses to dealer ({dealer_total}) — −{losses} 🍓")
                else:
                    print(f"  {name} pushes with dealer at {player_total}.")
            else:  # STATUS_BUST
                if dealer_busted:
                    # House rule: simultaneous bust is a push.
                    print(f"  {name} and dealer both bust — push.")
                else:
                    losses = bet * self.payoutMultiplier
                    self.playerPoptarts[name] -= losses
                    print(f"  {name} busted — −{losses} 🍓")

            self.playerBets[name] = 0
            self.playerStatus[name] = STATUS_PLAYING

        # Reset to Blackjack defaults so next round starts clean.
        self.gameName = "Blackjack"
        self.target = 21
        self.payoutMultiplier = 1
        time.sleep(MEDIUM_PAUSE)
        print(SEP)

    # ------------------------------------------------------------------
    # Round control
    # ------------------------------------------------------------------

    def continueGame(self):
        """Decide whether to start another round.

        In Doublejack mode this auto-continues (the bonus round is
        triggered, not chosen). In AI-vs-AI mode we run a fixed number
        of rounds with no prompts. Otherwise we ask the table.
        """
        # If everyone is broke, the game is over.
        if all(self.playerPoptarts[name] <= 0 for name in self.playerNames):
            print("\nEveryone is out of poptarts. Game over!")
            return False

        if self.gameName == "Doublejack":
            return True

        # AI-vs-AI mode: no prompts, just play N rounds.
        if self.aiOnlyRounds is not None:
            if self.roundsPlayed >= self.aiOnlyRounds:
                print(f"\nAI-vs-AI demo complete after {self.roundsPlayed} rounds.")
                return False
            print(f"\n── Round {self.roundsPlayed + 1} of {self.aiOnlyRounds} ──")
            return True

        choice = prompt_choice("\nStart a new round? [Y/N] ", ["Y", "N"])
        print()
        return choice == "Y"

    def checkDoublejack(self):
        """If the dealer hit 21, offer the bonus to surviving players.

        Players who busted in the Blackjack round are out — they're
        marked to sit out the Doublejack hand. The bonus is only offered
        if at least one human survived with poptarts left to bet.
        """
        # Clear any leftover sit-outs from a previous round before deciding.
        self.sittingOut = set()

        if self.countHand(self.dealerHand) != 21:
            return

        # Identify busted (and thus ineligible) players. Use card_values
        # raw sum > 21 since payout already reset status flags.
        ineligible = set()
        for name in self.playerNames:
            # If they sat the round out (no bet, no hand), they're out too.
            if not self.playerHands[name]:
                ineligible.add(name)
                continue
            if self.countHand(self.playerHands[name]) > 21:
                ineligible.add(name)

        # A surviving human can opt in. In AI-only mode, no humans
        # exist, so the AIs auto-decide based on the true count: if
        # the count favors the player, they take the bonus.
        eligible_humans = [
            n for n in self.playerNames
            if self.playerType[n] == TYPE_HUMAN
            and n not in ineligible
            and self.playerPoptarts[n] > 0
        ]
        eligible_ais = [
            n for n in self.playerNames
            if self.playerType[n] == TYPE_AI
            and n not in ineligible
            and self.playerPoptarts[n] > 0
        ]

        if not eligible_humans and not eligible_ais:
            return

        # In human-driven modes (singleplayer / multiplayer), if every
        # human busted out of the bonus, just skip it. Letting the AIs
        # auto-decide and play the bonus while the human watches isn't
        # really a meaningful interaction. Only AI-vs-AI mode gets the
        # auto-decision branch.
        any_humans_at_table = any(
            self.playerType[n] == TYPE_HUMAN for n in self.playerNames
        )
        if any_humans_at_table and not eligible_humans:
            print("\n  ⚡ Dealer hit 21, but no eligible humans — bonus skipped.")
            return

        print("\n  ⚡ Dealer hit 21! Doublejack bonus is available.")
        print("     (Target 42, 2x payouts, 2x losses.)")
        if ineligible:
            sat_out = ", ".join(sorted(ineligible))
            print(f"     (Busted players sit out: {sat_out}.)")

        if eligible_humans:
            choice = prompt_choice(
                "     Play the Doublejack bonus round? [Y/N] ", ["Y", "N"],
            )
            accept = (choice == "Y")
        else:
            # AI-vs-AI mode: take the bonus whenever the count is favorable.
            accept = self.trueCount > 0
            print(f"     AI table {'accepts' if accept else 'declines'} "
                  f"the bonus (true count = {self.trueCount:+.2f}).")

        if accept:
            self.gameName = "Doublejack"
            self.target = 42
            self.payoutMultiplier = 2
            self.sittingOut = ineligible

    def gameSummary(self):
        """Print final net win/loss for every player."""
        print("\n" + SEP)
        print("  FINAL TALLY")
        print(SEP)
        for name in self.playerNames:
            net = self.playerPoptarts[name] - self.staticPlayerPoptarts[name]
            ending = self.playerPoptarts[name]
            if net >= 0:
                print(f"  {name}: +{net} 🍓 (ending balance: {ending})")
            else:
                print(f"  {name}: −{abs(net)} 🍓 (ending balance: {ending})")
        print(SEP)

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def hostGame(self):
        """Run rounds until the table quits or everyone is broke.

        The first round runs unconditionally; we only prompt to continue
        after a round has finished. Doublejack bonus rounds chain
        automatically (continueGame returns True if gameName is set).
        """
        first_round = True
        while first_round or self.continueGame():
            # Announce round 1 in AI-vs-AI mode (subsequent rounds get
            # announced by continueGame).
            if first_round and self.aiOnlyRounds is not None:
                print(f"\n── Round 1 of {self.aiOnlyRounds} ──")
            first_round = False

            # If everyone went broke during the prior round, stop.
            if all(self.playerPoptarts[n] <= 0 for n in self.playerNames):
                print("\nEveryone is out of poptarts. Game over!")
                break

            self.deckCapacity()
            self.printCountStats()  # opt-in: shows Hi-Lo state before bets
            self.collectBets()
            self.dealCards()

            # Auto-detect players dealt a natural (target on 2 cards).
            # They skip the play loop and are paid 1.5x at payout time.
            for name in self.playerNames:
                if name in self.sittingOut:
                    continue
                if self.playerBets[name] == 0:
                    continue
                if (len(self.playerHands[name]) == 2
                        and self.countHand(self.playerHands[name]) == self.target):
                    self.playerStatus[name] = STATUS_NATURAL
                    print(f"  {name} is dealt a natural {self.gameName}!")

            for name in self.playerNames:
                self.printPlayerHands()
                self.printDealerHand()
                # Skip sitting-out players (busted into Doublejack).
                if name in self.sittingOut:
                    continue
                # Skip players who didn't bet (no poptarts).
                if self.playerBets[name] == 0:
                    continue
                if self.playerStatus[name] != STATUS_PLAYING:
                    continue
                if self.playerType[name] == TYPE_HUMAN:
                    self.receiveInput(name)
                else:
                    self.AITurn(name)
                self.checkLimit(name)

            self.dealerTurn()
            self.payout()
            self.checkDoublejack()
            self.roundsPlayed += 1

        self.gameSummary()


# ----------------------------------------------------------------------
# Setup / entry point
# ----------------------------------------------------------------------

def setupSinglePlayer():
    """Build player_data for a singleplayer game (1 human + N AIs)."""
    name = prompt_nonempty("Enter your name: ")
    poptarts = prompt_int("Enter your starting poptarts: ", min_value=1)
    player_data = [[name, poptarts, TYPE_HUMAN]]

    num_npcs = prompt_int(
        f"Number of AI opponents [1–{len(POKER_PLAYERS)}]: ",
        min_value=1,
        max_value=len(POKER_PLAYERS),
    )
    # Sample AI names without mutating the global pool.
    ai_names = random.sample(POKER_PLAYERS, num_npcs)
    for ai_name in ai_names:
        player_data.append([ai_name, poptarts, TYPE_AI])
    return player_data


def setupMultiplayer():
    """Build player_data for a multiplayer game (all humans)."""
    count = prompt_int("Number of human players [2–6]: ", min_value=2, max_value=6)
    player_data = []
    for i in range(1, count + 1):
        print()
        name = prompt_nonempty(f"Player {i} name: ")
        poptarts = prompt_int(f"Player {i} starting poptarts: ", min_value=1)
        player_data.append([name, poptarts, TYPE_HUMAN])
    return player_data


def setupAIvsAI():
    """Build player_data for a fully-automated AI-vs-AI demo game.

    Picks 2–5 AI players from POKER_PLAYERS and gives them an equal
    starting bankroll. No humans. The table runs a fixed number of
    rounds and then ends — the user just watches.
    """
    num_ais = prompt_int(
        f"Number of AI players [2–{len(POKER_PLAYERS)}]: ",
        min_value=2,
        max_value=len(POKER_PLAYERS),
    )
    poptarts = prompt_int("Starting poptarts per AI: ", min_value=1)
    ai_names = random.sample(POKER_PLAYERS, num_ais)
    return [[ai_name, poptarts, TYPE_AI] for ai_name in ai_names]


def startGame():
    """Top-level entry point: pick a mode, build the table, host the game."""
    print("\n" + SEP)
    print("  Welcome to DOUBLEJACK 🍓")
    print("  Beat the dealer at 21 — and if the dealer hits 21,")
    print("  ride the bonus round all the way to 42.")
    print(SEP + "\n")

    print("Game modes:")
    print("  [S] Singleplayer — you vs. AIs")
    print("  [M] Multiplayer  — humans only")
    print("  [A] AI vs. AI    — auto-run demo, no human input")
    mode = prompt_choice("Pick a mode [S/M/A]: ", ["S", "M", "A"])
    print()

    if mode == "S":
        player_data = setupSinglePlayer()
        ai_only = False
    elif mode == "M":
        player_data = setupMultiplayer()
        ai_only = False
    else:
        player_data = setupAIvsAI()
        ai_only = True

    # Optional: turn on the Hi-Lo card-counting tracker display.
    print()
    show_count_choice = prompt_choice(
        "Show the Hi-Lo card-counting tracker each round? [Y/N] ",
        ["Y", "N"],
    )
    show_count = show_count_choice == "Y"

    # AI-vs-AI: how many rounds should the demo run?
    if ai_only:
        ai_rounds = prompt_int(
            "Number of rounds to auto-play [1–50]: ",
            min_value=1, max_value=50,
        )
    else:
        ai_rounds = None

    print("\n" + SEP)
    print("  Players:")
    for entry in player_data:
        kind = "human" if entry[2] == TYPE_HUMAN else "AI"
        print(f"    {entry[0]} ({kind}) — {entry[1]} 🍓")
    print(SEP + "\n")
    time.sleep(MEDIUM_PAUSE)

    table = Doublejack(player_data, showCount=show_count)
    table.aiOnlyRounds = ai_rounds  # None unless AI-vs-AI mode
    table.hostGame()


if __name__ == "__main__":
    startGame()


# ----------------------------------------------------------------------
# APPENDIX: simulation used to pick the dealer's Doublejack stand value.
# ----------------------------------------------------------------------
"""
def _simulate_bust_rate(stand_at, num_trials, target):
    sim_shoe = SINGLE_DECK * NUM_DECKS_IN_SHOE
    busts = 0
    for _ in range(num_trials):
        if len(sim_shoe) < RESHUFFLE_THRESHOLD:
            sim_shoe = SINGLE_DECK * NUM_DECKS_IN_SHOE
        hand = []
        for _ in range(2):
            c = random.choice(sim_shoe)
            sim_shoe.remove(c)
            hand.append(c)

        def total(h):
            t = sum(CARD_VALUES[c] for c in h)
            aces = h.count("A")
            while aces > 0 and t > target:
                t -= 10
                aces -= 1
            return t

        while total(hand) < stand_at:
            c = random.choice(sim_shoe)
            sim_shoe.remove(c)
            hand.append(c)
        if total(hand) > target:
            busts += 1
    return busts / num_trials

# Blackjack (target 21):
#   stand_at=17 → ~0.285 bust rate
# Doublejack (target 42):
#   stand_at=38 → ~0.290 bust rate  ← chosen for parity with 17/21
"""