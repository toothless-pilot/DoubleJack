import random

cards_values = {"K":10,"Q":10,"J":10,"10":10,"9":9,"8":8,"7":7,"6":6,"5":5,"4":4,"3":3,"2":2} #"A":11 removed ace, will implement later

deck = [card for card in cards_values for i in range(4)]

class DoubleJack():
    def __init__(self, playerData): # player_data should be [[name1,budget1],[name2,budget1],...]
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
        card = random.choice(self.shoe)
        self.shoe.remove(card)
        return card

    def resetShoe(self):
        self.shoe = deck*6
    
    def dealCards(self):
        self.dealerHand = [self.randomCard() for i in range(2)]
        for name in self.playerNames:
                if self.playerBudget[name] > 0:
                    self.playerHands[name] = [self.randomCard() for i in range(2)]

    def collectBets(self):
        for name in self.playerNames:
            if self.playerBudget[name] > 0:
                print(f"{name}'s move. Your budget is {self.playerBudget[name]}.")
                bet = int(input(f"Place your bet: "))
                while bet > self.playerBudget[name]:
                    bet = int(input(f"Your budget is {self.playerBudget[name]}. Try placing a smaller bet: "))
                self.playerBet[name] = bet
            

    def countHand(self, hand):
        return sum(cards_values[card] for card in hand)

    def checkLimit(self,name): #0 = bust, 1 = playing, 2 = stand, 3 = blackjack
        if self.countHand(self.playerHands[name]) == 21:
            self.playerStatus[name] = 3
        elif self.countHand(self.playerHands[name]) > 21:
            self.playerStatus[name] = 0
    
    def printDealerHand(self):
        print(f"Dealer has {[random.choice(self.dealerHand),"🂠"]}")

    def receiveInput(self,name):
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
        while self.countHand(self.dealerHand) < 17:
            self.dealerHand += [self.randomCard()]
        print(f"Dealer has {self.dealerHand}, giving {self.countHand(self.dealerHand)}")

    def deckCapacity(self):
        if len(self.shoe) < 78:
            self.resetShoe()
            return True

    def endGame(self):
        if 1 not in self.playerStatus.values():
            return True
        else:
            return False
    
    def payout(self):
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
        decision = input("Do you want to play this round? [Y/N]")
        if decision.upper() == "Y":
            return True
        if decision.upper() == "N":
            return False
    
    def gameSummary(self):
        for name in self.playerNames:
            if self.playerBudget[name] - self.staticPlayerBudget[name] > 0:
                print(f"{name} wins {self.playerBudget[name] - self.staticPlayerBudget[name]}, ending with {self.playerBudget[name]}")
            else:
                print(f"{name} loses {self.staticPlayerBudget[name] - self.playerBudget[name]}, ending with {self.playerBudget[name]}")
                

    def hostBlackJack(self):
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