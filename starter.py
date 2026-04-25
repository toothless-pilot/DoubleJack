import random

cards_values = {"K":10,"Q":10,"J":10,"10":10,"9":9,"8":8,"7":7,"6":6,"5":5,"4":4,"3":3,"2":2} #"A":11 removed ace, will implement later

deck = [card for card in cards_values for i in range(4)]

class DoubleJack():
    """A multiplayer text-based blackjack game simulating a casino environment.
    
    Supports an arbitrary number of players, each with their own budget, playing
    against a dealer across multiple rounds. Uses a 6-deck shoe that automatically
    resets when running low. Tracks per-player hands, budgets, bets, and status
    throughout the session and prints a final summary of winnings/losses.
    """
    def __init__(self, playerData): # player_data should be [[name1,budget1],[name2,budget1],...]
        """Initialize the game state with the given players."""
        self.shoe = deck*6
        self.numPlayers = len(playerData)
        self.playerNames = [playerData[i][0] for i in range(self.numPlayers)]
        self.playerHands = {playerData[i][0]:[] for i in range(self.numPlayers)}
        self.staticPlayerBudget = {playerData[i][0]:playerData[i][1] for i in range(self.numPlayers)} #for game summary
        self.playerBudget = {playerData[i][0]:playerData[i][1] for i in range(self.numPlayers)}
        self.playerBet = {playerData[i][0]:0 for i in range(self.numPlayers)}
        self.playerStatus = {playerData[i][0]:1 for i in range(self.numPlayers)}
        self.dealerHand = []

    def randomCard(self):
        """Draw a random card from the shoe and remove it. Returns the card."""
        card = random.choice(self.shoe)
        self.shoe.remove(card)
        return card

    def resetShoe(self):
        """Reset the shoe back to a full 6-deck stack."""
        self.shoe = deck*6
    
    def dealCards(self):
        """Deal two cards to the dealer and to each player with a non-zero budget.
        
        Players with a budget of 0 are skipped (they're out of the game).
        """
        self.dealerHand = [self.randomCard() for i in range(2)]
        for name in self.playerNames:
                if self.playerBudget[name] > 0:
                    self.playerHands[name] = [self.randomCard() for i in range(2)]

    def collectBets(self):
        """Prompt each active player to place a bet for the round.
        
        Re-prompts if the player tries to bet more than their current budget.
        Skips players whose budget is 0.
        """
        for name in self.playerNames:
            if self.playerBudget[name] > 0:
                print(f"{name}'s move. Your budget is {self.playerBudget[name]}.")
                bet = int(input(f"Place your bet: "))
                while bet > self.playerBudget[name]:
                    bet = int(input(f"Your budget is {self.playerBudget[name]}. Try placing a smaller bet: "))
                self.playerBet[name] = bet
            

    def countHand(self, hand):
        """Sum the point values of the cards in a hand.
        
        Args:
            hand: A list of card strings.
        
        Returns:
            The integer total based on cards_values.
        """
        return sum(cards_values[card] for card in hand)

    def checkLimit(self,name): #0 = bust, 1 = playing, 2 = stand, 3 = blackjack
        """Update a player's status based on their hand total.
        
        Sets status to 3 (blackjack) if the count is exactly 21, or 0 (bust)
        if the count exceeds 21. Otherwise leaves status unchanged.
        
        Args:
            name: The player's name (key into playerHands and playerStatus).
        """
        if self.countHand(self.playerHands[name]) == 21:
            self.playerStatus[name] = 3
        elif self.countHand(self.playerHands[name]) > 21:
            self.playerStatus[name] = 0
    
    def printDealerHand(self):
        """Print the dealer's visible hand with one card hidden as a face-down icon."""
        print(f"Dealer has {[random.choice(self.dealerHand),"🂠"]}")

    def receiveInput(self,name):
        """Prompt a player to hit or stand until they bust, stand, or hit 21.
        
        On 'H', draws another card and continues looping. On 'S', sets the
        player's status to 3 (blackjack) if their count is 21, otherwise 2
        (stand), and exits. Breaks out automatically if the player busts.
        
        Args:
            name: The player whose turn it is.
        """
        while True:
            choice = input(f"{name}'s move. Do you wish to HIT or STAND? Your cards are {self.playerHands[name]}, giving you a total count of {self.countHand(self.playerHands[name])} | [H/S]")
            if choice.upper() == "H":
                self.playerHands[name] += [self.randomCard()]
            elif choice.upper() == "S":
                self.playerStatus[name] = 3 if self.countHand(self.playerHands[name]) == 21 else 2
                break

            if self.countHand(self.playerHands[name]) > 21:
                print(f"{name} busts!")
                break

    
    def dealerTurn(self):
        """Play out the dealer's turn, hitting until the count reaches 17 or higher.
        
        Prints the final dealer hand and total when done.
        """
        while self.countHand(self.dealerHand) < 17:
            self.dealerHand += [self.randomCard()]
        print(f"Dealer has {self.dealerHand}, giving {self.countHand(self.dealerHand)}")

    def deckCapacity(self):
        """Reset the shoe if fewer than 78 cards remain.
        
        Returns:
            True if the shoe was reset, otherwise None.
        """
        if len(self.shoe) < 78:
            self.resetShoe()
            return True

    def endGame(self):
        """Check whether the current round is over.
        
        A round ends when no player still has status 1 (actively playing).
        
        Returns:
            True if no players are still playing, False otherwise.
        """
        if 1 not in self.playerStatus.values():
            return True
        else:
            return False
    
    def payout(self):
        """Resolve bets for every player based on their final status and hand.
        
        Blackjack (status 3) pays 1.5x. A standing player (status 2) wins 1x
        if their count beats the dealer, loses 1x if the dealer beats them,
        and pushes on a tie. Busts (status 0) lose their bet. Updates each
        player's budget, then resets bet to 0 and status to 1 for the next round.
        """
        for name in self.playerNames:
            if self.playerStatus[name] == 3: #blackjack
                self.playerBet[name] *= 1.5
                print(f"{name} hits a blackjack, winning {self.playerBet[name]}!")
            elif self.playerStatus[name] == 2:
                if self.countHand(self.playerHands[name]) > self.countHand(self.dealerHand): #player wins
                    self.playerBet[name] *= 1
                    print(f"{name} wins with a count of {self.countHand(self.playerHands[name])}, winning {self.playerBet[name]}.")
                elif self.countHand(self.playerHands[name]) < self.countHand(self.dealerHand): #player loses
                    self.playerBet[name] *= -1
                    print(f"{name} loses with a count of {self.countHand(self.playerHands[name])}, losing {self.playerBet[name]}.")
                else: #tie
                    self.playerBet[name] = 0
                    print(f"{name} ties with the dealer!")
            else:
                self.playerBet[name] *= -1
                print(f"{name} loses with a count of {self.countHand(self.playerHands[name])}, losing {self.playerBet[name]}.")
            
            self.playerBudget[name] += self.playerBet[name]
            self.playerBet[name] = 0
            self.playerStatus[name] = 1
    
    def continueGame(self):
        """Ask whether to play another round.
        
        Returns:
            True if the user enters 'Y', False if they enter 'N'.
        """
        decision = input("Do you want to play this round? [Y/N]")
        if decision.upper() == "Y":
            return True
        if decision.upper() == "N":
            return False
    
    def gameSummary(self):
        """Print each player's net winnings or losses against their starting budget."""
        for name in self.playerNames:
            if self.playerBudget[name] - self.staticPlayerBudget[name] > 0:
                print(f"{name} wins {self.playerBudget[name] - self.staticPlayerBudget[name]}, ending with {self.playerBudget[name]}")
            else:
                print(f"{name} loses {self.staticPlayerBudget[name] - self.playerBudget[name]}, ending with {self.playerBudget[name]}")
                

    def hostBlackJack(self):
        """Run the full blackjack game loop until the user opts to stop.
        
        Each iteration: checks shoe capacity, collects bets, deals cards,
        runs through player turns until the round ends, plays the dealer's
        turn, and pays out. When the user declines to continue, prints the
        final game summary.
        
        Returns:
            The result of gameSummary() (which is None — the summary is printed).
        """
        while self.continueGame():
            self.deckCapacity()
            self.collectBets()
            self.dealCards()
            while not self.endGame():
                self.printDealerHand()
                for name in self.playerNames:
                    if self.playerBudget[name] > 0:
                        if self.playerStatus[name] == 1:
                            self.receiveInput(name)
                            self.checkLimit(name)
            self.dealerTurn()
            self.payout()
        return self.gameSummary()
    

t1 = DoubleJack([["alex",100],["suhas",200],["rushil",250]])
t1.hostBlackJack()