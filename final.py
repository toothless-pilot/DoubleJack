"""
Doublejack — a Blackjack variant with a Doublejack bonus round.

CS5 Final Project
 - Alex Kim, Rushil Jaiswal, and Suhas Beeravelli

Gameplay:
 - Standard Blackjack rules, target 21, dealer hits below 17.
 - Players bet poptarts (the in-game currency) instead of dollars.
 - If the dealer's first round hits exactly 21, players are offered the
   chance to play Doublejack, a follow-on round with target 42 where
   payouts are doubled.
 - In Doublejack, dealer hits below 38.
 - AI uses hi-lo card counting to size bets.
"""

import random
import time

card_values = {"A":11,"K":10,"Q":10,"J":10,"10":10,"9":9,"8":8,"7":7,"6":6,"5":5,"4":4,"3":3,"2":2}

counting_values = {"A":-1,"K":-1,"Q":-1,"J":-1,"10":-1,"9":0,"8":0,"7":0,"6":1,"5":1,"4":1,"3":1,"2":1}

deck = [card for card in card_values for i in range(4)]

poker_players = ["Phil Ivey", "Daniel Negreanu", "Doyle Brunson", "Phil Hellmuth", "Johnny Chan"]

class Doublejack():
    def __init__(self, playerData): # player_data should be [[name1,budget1,type1],[name2,budget2,type2],...]
        self.shoe = deck*6
        self.target = 21
        self.payoutMultiplier = 1
        self.gameName = "Blackjack"
        self.numPlayers = len(playerData)
        self.playerNames = [playerData[i][0] for i in range(self.numPlayers)]
        self.playerHands = {playerData[i][0]:[] for i in range(self.numPlayers)}
        self.staticPlayerBudget = {playerData[i][0]:playerData[i][1] for i in range(self.numPlayers)} #for game summary
        self.playerBudget = {playerData[i][0]:playerData[i][1] for i in range(self.numPlayers)}
        self.playerBets = {playerData[i][0]:0 for i in range(self.numPlayers)}
        self.playerStatus = {playerData[i][0]:1 for i in range(self.numPlayers)}
        self.dealerHand = []
        self.playerType = {playerData[i][0]:playerData[i][2] for i in range(self.numPlayers)} #0 = ai, 1 = human

        #Card Counting AI
        self.runningCount = 0
        self.trueCount = 0

    def randomCard(self):
        """
        Picks a random card from the shoe and remove that card from the shoe
        """
        card = random.choice(self.shoe)
        self.shoe.remove(card)
        self.runningCount += counting_values[card]
        return card
    
    def countHand(self, hand):
        """
        Takes a blackjack hand as input and returns the total count of the hand. Aces are initially
        handled as 11 then each reduced to 1 until the hand drops below the target (i.e. 21 or 42)
        """
        total = sum([card_values[card] for card in hand])

        #Ace exception
        numAces = hand.count("A")
        while numAces > 0 and total > self.target:
            total -= 10
            numAces -= 1
        return total
    
    def dealCards(self):
        """
        Deals two hands to the player and dealer. Player budget must be above 0. Deals 2 additional card
        to dealer during doublejack.
        """
        if self.gameName == "Doublejack":
            self.dealerHand += [self.randomCard() for i in range(2)]
            return
        #self.dealerHand = ["A","K"] #Doublejack testing
        self.dealerHand = [self.randomCard() for i in range(2)]
        for name in self.playerNames:
                if self.playerBudget[name] > 0:
                    self.playerHands[name] = [self.randomCard() for i in range(2)]
    
    def collectBets(self):
        """
        Collects a bet below their budget if the player if human. If the player is AI, it sets
        the base bet at 1/10th of the AI's budget and adjust the bet according to the True count.
        """
        for name in self.playerNames:
            if self.playerType[name] == 1:
                if self.playerBudget[name] > 0:
                    print(f"{name}'s move. Your budget is {self.playerBudget[name]} poptarts.")
                    bet = int(input(f"Place your bet (in poptarts): "))
                    while bet > self.playerBudget[name]:
                        bet = int(input(f"Your budget is {self.playerBudget[name]} poptarts. Try placing a smaller bet: "))
                    self.playerBets[name] = bet
                    time.sleep(1.5)
                    print("\n"*20)
            else:
                if self.playerBudget[name] > 0:
                    bet = round(self.playerBudget[name]/10)
                    bet += 0.5*bet*max(self.trueCount,0)
                    bet = min([self.playerBudget[name], bet]) #one directional
                    self.playerBets[name] = int(bet)
                    print(f"{name} bets {int(bet)} poptarts")
                    time.sleep(1.5)
                    print("\n"*20)

    def printPlayerHands(self):
        """
        print the player's hands
        """
        for name in self.playerNames:
            print(f"{name} has {self.playerHands[name]}")
        print("-"*40)
    
    def printDealerHand(self):
        """
        print the dealer's hands
        """
        if self.gameName == "Blackjack":
            print(f"Dealer has {[self.dealerHand[0],"🂠"]}")
        else:
            print(f"Dealer has {self.dealerHand[:-1]+["🂠"]}")
        print("-"*40)

    def checkLimit(self,name): #0 = bust, 1 = playing, 2 = stand, 3 = blackjack/doublejack
        """
        Takes as input players name and assigns a status according to their current hand count
        """
        if self.countHand(self.playerHands[name]) == self.target:
            self.playerStatus[name] = 3
        elif self.countHand(self.playerHands[name]) > self.target:
            self.playerStatus[name] = 0
        else:
            self.playerStatus[name] = 2

    def receiveInput(self,name):
        """
        Takes as input player name and receives the person's input on whether they wants to hit or stand
        """
        while True:
            choice = input(f"{name}'s move. Do you wish to HIT or STAND? Your cards are {self.playerHands[name]}, giving you a total count of {self.countHand(self.playerHands[name])} | [H/S]")
            if choice.upper() == "H":
                time.sleep(0.5)
                self.playerHands[name] += [self.randomCard()]
            elif choice.upper() == "S":
                self.playerStatus[name] = 3 if self.countHand(self.playerHands[name]) == self.target else 2
                print(f"{name} stands with {self.playerHands[name]} — total count of {self.countHand(self.playerHands[name])}")
                time.sleep(1.5)
                print("\n"*20)
                break

            if self.countHand(self.playerHands[name]) > self.target:
                print(f"{name} busts with {self.playerHands[name]} — total count of {self.countHand(self.playerHands[name])}!")
                time.sleep(1.5)
                print("\n"*20)
                break
    
    def deckCapacity(self):
        """
        Resets the shoe if the shoe if over 75% of the cards in the shoe have been played
        """
        if len(self.shoe) < 78:
            self.shoe = deck*6
            print("\n"*20)
            print("Reshuffling Deck")
            time.sleep(2.5)
            print("\n"*20)
            self.runningCount = 0
            self.trueCount = 0
    
    def continueGame(self):
        """
        Recieves player input on whether they want to continue playing the game
        """
        if self.gameName == "Doublejack":
            return True
        print("\n")
        choice = input("Do you want to start a new round? [Y/N]")
        if choice.upper() == "Y":
            print("\n"*20)
            return True
        else:
            print("\n"*20)
            return False
    
    def payout(self):
        """
        Determines the payout for the player by comparing the count of the player's hand and dealer's hand.
        If the gamemode is Doublejack, all payout is doubled. Resets player's bets and status and adds/subtracts
        the payout amount of the player's budget
        """
        for name in self.playerNames:
            if self.playerStatus[name] == 3: #blackjack
                if self.countHand(self.dealerHand) != self.target: #player wins
                    self.playerBets[name] = int(self.playerBets[name] * 1.5 * self.payoutMultiplier)
                    print(f"{name} hits a {self.gameName}, winning {self.playerBets[name]} poptarts!")
                else: #both player & dealer have blackjack
                    self.playerBets[name] = 0
                    print(f"Both {name} and dealer have a {self.gameName}, resulting in a tie.")
            elif self.playerStatus[name] == 2:
                if self.countHand(self.dealerHand) > self.target:
                    self.playerBets[name] *= 1 * self.payoutMultiplier
                    print(f"Dealer busts! {name} wins {self.playerBets[name]} poptarts!")
                elif self.countHand(self.playerHands[name]) > self.countHand(self.dealerHand): #player wins
                    self.playerBets[name] *= 1 * self.payoutMultiplier
                    print(f"{name} wins with a count of {self.countHand(self.playerHands[name])}, winning {self.playerBets[name]} poptarts!")
                elif self.countHand(self.playerHands[name]) < self.countHand(self.dealerHand): #player loses
                    self.playerBets[name] *= -1
                    print(f"{name} loses with a count of {self.countHand(self.playerHands[name])}, losing {abs(self.playerBets[name])} poptarts.")
                else: #tie
                    self.playerBets[name] = 0
                    print(f"{name} ties with the dealer!")
            else:
                if self.countHand(self.dealerHand) > self.target:
                    print(f"Both {name} and dealer busts, its a tie!")
                    self.playerBets[name] = 0
                else:
                    self.playerBets[name] *= -1
                    print(f"{name} loses with a count of {self.countHand(self.playerHands[name])}, losing {abs(self.playerBets[name])} poptarts.")

            self.playerBudget[name] += self.playerBets[name]
            self.playerBets[name] = 0
            self.playerStatus[name] = 1
        self.gameName = "Blackjack"
        self.target = 21
        self.payoutMultiplier = 1
        
        time.sleep(2.5)
        print("-"*20)
    
    def gameSummary(self):
        """
        Prints the end-of-game statistics for each player, which tells the player how much poptarts
        they won/lost and their final budget.
        """
        for name in self.playerNames:
            if self.playerBudget[name] - self.staticPlayerBudget[name] >= 0:
                print(f"{name} wins {self.playerBudget[name] - self.staticPlayerBudget[name]} poptarts, ending with {self.playerBudget[name]} poptarts!")
            else:
                print(f"{name} loses {self.staticPlayerBudget[name] - self.playerBudget[name]} poptarts, ending with {self.playerBudget[name]} poptarts.")

    def checkDoublejack(self):
        """
        Checks if the dealer has 21. If dealer has 21, activate Doublejack variant by doubling payout multipler
        and increasing target threshold to 42.
        """
        if self.countHand(self.dealerHand) == 21:
            choice = input("Dealer hits 21. Giving you the option to play Doublejack. [Y/N]")
            if choice.upper() == "Y":
                print("\n")
                self.gameName = "Doublejack"
                self.target = 42
                self.payoutMultiplier = 2
    
    def dealerTurn(self):
        """
        Determines whether dealer should hit/stand according to the standard rules of blackjack and Doublejack.
        Dealer stands on 17 or above for blackjack and 38 or above for doublejack. Any hand below that the dealer
        must hit.
        """
        print(f"Dealer shows {self.dealerHand}")
        while True:
            if self.countHand(self.dealerHand) >= self.target-4:
                if self.countHand(self.dealerHand) > self.target:
                    print(f"Dealer busts with {self.dealerHand} — total count of {self.countHand(self.dealerHand)}")
                    time.sleep(2.5)
                    print("-"*20)
                    break
                else:
                    print(f"Dealer stands with {self.dealerHand} — total count of {self.countHand(self.dealerHand)}")
                    time.sleep(2.5)
                    print("-"*20)
                    break
            self.dealerHand += [self.randomCard()]
            print(f"Dealer hits, showing {self.dealerHand} — total count of {self.countHand(self.dealerHand)}.")
            time.sleep(1)
        self.trueCount = self.runningCount/(len(self.shoe)/52)

    def AITurn(self, name):
        """
        Determines the move that the AI will make according to a simplified version of "standard blackjack strategy chart".
        Extended standard strategy to doublejack by applying strategy logic to 42 threshold.
        """
        while True:
            if self.countHand(self.playerHands[name]) > self.target:
                print(f"{name} busts with {self.playerHands[name]} — total count of {self.countHand(self.playerHands[name])}")
                time.sleep(2.5)
                print("\n"*20)
                break
            elif self.countHand(self.playerHands[name]) <= self.target-10:
                self.playerHands[name] += [self.randomCard()]
                print(f"{name} hits, showing {self.playerHands[name]} — total count of {self.countHand(self.playerHands[name])}")
                time.sleep(1)
            elif self.countHand(self.playerHands[name]) >= self.target-4:
                print(f"{name} stands with {self.playerHands[name]} — total count of {self.countHand(self.playerHands[name])}")
                time.sleep(2.5)
                print("\n"*20)
                break
            else:
                if self.countHand(self.dealerHand[:-1]) <= self.target-15: #target-4-1-10
                    print(f"{name} stands with {self.playerHands[name]} — total count of {self.countHand(self.playerHands[name])}")
                    time.sleep(2.5)
                    print("\n"*20)
                    break
                else:
                    self.playerHands[name] += [self.randomCard()]
                    print(f"{name} hits, showing {self.playerHands[name]} — total count of {self.countHand(self.playerHands[name])}")
                    time.sleep(1)

    def hostGame(self):
        """
        Hosts the game of doublejack
        """
        while self.continueGame():
            self.deckCapacity()
            self.collectBets()
            self.dealCards()
            for name in self.playerNames:
                self.printPlayerHands()
                self.printDealerHand()
                if self.playerBudget[name] > 0:
                    if self.playerStatus[name] == 1:
                        if self.playerType[name]:
                            self.receiveInput(name)
                        else:
                            self.AITurn(name)
                        self.checkLimit(name)
            self.dealerTurn()
            self.payout()
            self.checkDoublejack()
        return self.gameSummary()

def startGame():
    """
    Starts the game of doublejack and receiving player input on gamemode, name, budget, 
    # of players (for multiplayer), and # of NPC (for singleplayer)
    """

    print("\n" + "-"*50)
    print("  Welcome to DOUBLEJACK")
    print("  Beat the dealer at 21 — and if the dealer hits 21,")
    print("  ride the bonus round up to 42.")
    print("-"*50 + "\n")

    print("Game modes:")
    print("  [S] Singleplayer — you vs. AIs")
    print("  [M] Multiplayer  — humans only")
    gamemode = input("Select gamemode [S/M]:")
    print("\n")
    playerData = []
    if gamemode.upper() == "S":
        #playerData
        name = input("Enter your name: ")
        budget = int(input("Enter the number of poptarts that you have: "))
        playerData += [[name, budget,1]]
        
        #AIData
        numPlayers = int(input("Enter the number of NPCs [1-5]:"))
        for i in range(numPlayers):
            AIName = random.choice(poker_players)
            poker_players.remove(AIName)
            playerData += [[AIName,budget,0]]

    elif gamemode.upper() == "M":
        playerCount = int(input("Enter the number of players: "))
        for i in range(1,playerCount+1):
            name = input(f"Enter player{i}'s name: ")
            budget = int(input(f"Enter the number of poptarts player{i} has: "))
            playerData += [[name, budget,1]]
            time.sleep(2.5)
            print("\n")
        print("\n")
    
    table = Doublejack(playerData)
    table.hostGame()

startGame()

#t1 = Doublejack([["alex",100,1],["rushil",150,1]])
#t1.hostGame()

#t2= Doublejack([["alex",100,1],["AI",100,0]])
#t2.hostGame()

'''
#simulation to det dealer stand threshold for Doublejack

def countHand(hand,target):
    total = sum([card_values[card] for card in hand])
    numAces = hand.count("A")
    while numAces > 0 and total > target:
        total -= 10
        numAces -= 1
    return total

def simulation(N,numTrials,target):
    sim_shoe = deck*6
    count = 0
    for i in range(numTrials):
        if len(sim_shoe) < 78:
            sim_shoe = deck*6
        hand = []
        for i in range(2):
            card = random.choice(sim_shoe)
            sim_shoe.remove(card)
            hand += [card]
        while countHand(hand,target) < N:
            card = random.choice(sim_shoe)
            sim_shoe.remove(card)
            hand += [card]
        if countHand(hand,target) > target:
            count += 1
    return count/numTrials

bustRatesBlackjack = [[N,simulation(N,100000,21)] for N in range(12,21)]
print(bustRatesBlackjack)
#[[12, 0.0], [13, 0.03293], [14, 0.07665], [15, 0.13307], [16, 0.20091], [17, 0.28527], [18, 0.37905], [19, 0.49464], [20, 0.62034]]

bustRatesDoublejack = [[N,simulation(N,100000,42)] for N in range(33,42)]
print(bustRatesDoublejack)
#[[33, 0.0], [34, 0.0355], [35, 0.07975], [36, 0.13584], [37, 0.20735], [38, 0.29005], [39, 0.39106], [40, 0.5091], [41, 0.64626]]

#Dobulejack dealer stand threshold should be set at 38 (closest bust rate to Blackjack) 

'''
