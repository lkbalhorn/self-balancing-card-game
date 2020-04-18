# card_effects
# This file creates a Subclass for each kind of Card, all of which inherit
# from the class Card.  The __init__ from the parent Card class is used.
# These subclasses add Trigger and Action methods specific to that type
# of card.

from card import *
import random
from globals import *
import sys
import functools


# New Action Format --------------------------------------------------------------------------New Action Format
class Action:
    def __init__(self, source=None, target=None, amount=None, player=False, active_card=None, second_target=None,
                 targets=[], string=None, flag=None, trigger=None, **kwargs):
        self.player = player
        self.source = source if source else None
        self.target = target
        self.second_target = second_target
        if targets:
            self.targets = targets
        elif active_card:
            self.targets = list(active_card.targets) if active_card else []
        else:
            self.targets = []
        self.amount = amount
        self.id = str(id(self))
        self.class_name = self.__class__.__name__

        self.player = player
        self.active_card = active_card
        self.trigger = trigger
        self.priority = self.source.priority if hasattr(self.source, 'priority') else 0

        self.string = string
        self.flag = flag
        self.extras = kwargs
        self.parent = self.__class__.__bases__[0].__name__
        if self.parent in ['BasicAction', 'PlayerAction', 'Reaction', 'Interrupt', 'CoAction', 'ConditionalAction']:
            self.type = self.parent
        else:
            self.type = self.__class__.__name__
        self.is_card = False
        self.is_repeat = False
        self.past_interrupts = []
        self.is_resolved = False  # Currently only for CoActions

        self.key_attributes = ['player', 'source', 'target', 'second_target', 'targets', 'amount',
                               'active_card', 'trigger', 'priority',
                               'string', 'flag', 'extras', 'parent', 'type', 'is_repeat', 'class_name'
                               ]

    def resolve(self):
        return None
    
    def reaction(self, *args):
        return None
    
    def __repr__(self):
        if self != self.source and self != self.target:
            return '%s(%s, %s)' % (self.__class__.__name__, self.source, self.target)
        elif self == self.source:
            return '%s(recursive source)' % self.__class__.__name__
        else:
            return '%s(recursive target)' % self.__class__.__name__

    def safe_resolve(self, basic_actions=[]):
        try:
            if self.type in [ 'BasicAction', 'PlayerAction', 'CoAction', 'ConditionalAction']:
                new_actions = self.resolve()
            elif self.type == 'Reaction':
                new_actions = self.source.reaction(self.target, self.trigger)
            elif self.type == 'Interrupt':
                new_actions = self.source.interrupt(self.trigger)
            elif self.type == 'Enter':
                new_actions = self.source.enter()
            else:
                new_actions = None

            if new_actions is None:
                return []
            elif hasattr(new_actions, '__iter__'):
                return list(new_actions)
            else:
                return [new_actions]
        except Exception as e:
            print('Safe Resolve Error', self, e)
            print(self.__dict__)
            raise

    def encode(self):
        new_dict = {}
        for attr in self.key_attributes:
            value = self.__dict__[attr]
            if value == self:
                new_dict[attr] = 'recursive'
            elif hasattr(value, 'name') and value.name == 'Center Box':
                new_dict[attr] = 'Center Box'
            elif hasattr(value, 'id'):  # User-Created Class
                new_dict[attr] = 'ID' + value.id
            elif type(value) == list:
                if not value:
                    new_dict[attr] = []
                elif hasattr(value[0], 'name') and value[0].name == 'Center Box':
                    new_dict[attr] = ['Center Box']
                elif hasattr(value[0], 'id'):
                    new_dict[attr] = ['ID' + i.id for i in value]
                else:
                    new_dict[attr] = [i for i in value]
            else:
                new_dict[attr] = value
        return new_dict

    def decode(self, simple_dict, object_dict):
        if not simple_dict:
            return None
        class_name = simple_dict['class_name']
        subclass = functools.reduce(getattr, class_name.split("."), sys.modules[__name__])
        new = subclass()
        for attr in new.key_attributes:
            value = simple_dict[attr]
            try:
                if value == 'recursive':
                    new.__dict__[attr] = new
                elif type(value) is str and value[:2] == 'ID':
                    new.__dict__[attr] = object_dict[value[2:]]
                elif type(value) is list:
                    if not value:
                        new.__dict__[attr] = []
                    elif type(value[0]) is str and value[0][:2] == 'ID':
                        new.__dict__[attr] = [object_dict[i[2:]] for i in value]
                    else:
                        new.__dict__[attr] = [i for i in value]
                else:
                    new.__dict__[attr] = value
            except KeyError:
                # print('KeyError while decoding action %s attribute %s' % (new.__repr__(), attr))
                pass
        return new

    def clone(self):
        new = self.__class__()
        for name in self.key_attributes:
            new.__dict__[name] = self.__dict__[name]
        return new


class BasicAction(Action):
    pass


class CoAction(Action):
    pass


class ConditionalAction(Action):
    pass


class PlayerAction(Action):
    pass


class Reaction(Action):
    pass
    
    
class Interrupt(Action):
    pass





# Player Actions  --------------------------------------------------------------------- player Actions
class PlayCard(PlayerAction):
    def resolve(self):
        # Return the three parts of playing a card, in a specific order:
        new_basic_actions = []
        new_card = self.active_card
        if new_card.cost is not None:
            new_basic_actions.append(ChangeMana(new_card, new_card.player, -1 * new_card.cost))
        if new_card.type in ['Minion', 'Structure', 'Item', 'Skill']:
            new_basic_actions.append(SummonCard(new_card, new_card, second_target=self.targets[0]))
        elif new_card.type == 'Spell':
            # Discard the card
            new_basic_actions.append(DiscardFromHand(new_card, new_card))
        if hasattr(new_card, 'enter'):
            # new_basic_actions = new_basic_actions + new_card.enter(self.targets)
            new_basic_actions.append(Enter(new_card, targets=self.targets))
        new_card.status = 'new'
        return new_basic_actions


class UseAbility(PlayerAction):
    def resolve(self):
        new_basic_actions = []
        active_card = self.active_card
        if active_card.ability_cost is not None:
            new_basic_actions.append(ChangeMana(active_card, active_card.player, -1 * active_card.ability_cost))
        new_basic_actions = new_basic_actions + active_card.ability(self.targets)
        if 'Repeatable' not in active_card.special:
            active_card.is_tapped = True
        return new_basic_actions


class Attack(PlayerAction):
    def resolve(self):
        attacker = self.active_card
        defender = self.targets[0]
        # new_basic_actions = []
        # new_basic_actions.append(DealDamage(attacker, defender, amount=attacker.attack))
        # if hasattr(defender, 'attack') and defender.attack > 0 and 'Ranged' not in attacker.special:
        #     new_basic_actions.append(DealDamage(defender, attacker, amount=defender.attack))
        # if defender.name == 'Hero':
        #     attacker.x_animate = (defender.player.x - attacker.x) / 2  # Relative Coordinates
        #     attacker.y_animate = (defender.player.y - attacker.y) / 2  # Relative Coordinates
        # else:
        #     attacker.x_animate = (defender.x - attacker.x) / 2  # Relative Coordinates
        #     attacker.y_animate = (defender.y - attacker.y) / 2  # Relative Coordinates
        # attacker.move_timer = 5
        attacker.is_tapped = True
        return [Fight(source=attacker, target=defender)]
        # return new_basic_actions


class Fight(CoAction):
    def resolve(self):
        attacker = self.source
        defender = self.target
        new_basic_actions = []
        new_basic_actions.append(DealDamage(attacker, defender, amount=attacker.attack))
        if (hasattr(defender, 'attack') and defender.attack > 0 and
                    'Ranged' not in attacker.special and defender.name != 'Hero'):
            new_basic_actions.append(DealDamage(defender, attacker, amount=defender.attack))
        return new_basic_actions


class Enter(CoAction):
    def resolve(self):
        return self.source.enter(self.targets)


class NextTurn(PlayerAction):
    def resolve(self):
        old = self.source
        new = self.source.opponent
        if new.is_active and not old.is_active:  # Duplicate next turn
            return []
        else:
            return [EndTurn(old, old, turn=self.extras['turn']), NewLayer(old, old),
                    StartTurn(old, new, turn=self.extras['turn']), NewLayer(old, old),
                    DrawCards(new, new, amount=1),
                    ChangeIncome(new, new, amount=1),
                    ChangeMana(new, new, amount=new.income - new.mana + 1),
                    ChangeStatus(new, new)]


# Standard Effects ----------------------------------------------------------------------------- Standard Effects
class DealDamage(BasicAction):
    def resolve(self):
        if hasattr(self.target, 'health'):
            self.target.health -= self.amount
            self.target.last_hit = self.source


class Heal(BasicAction):
    def resolve(self):
        if hasattr(self.target, 'health'):
            self.target.health += self.amount
            self.target.last_hit = self.source


class MakeDead(BasicAction):
    def resolve(self):
        self.target.is_alive = False
        self.target.move_anywhere(self.target.player.discard)


class AddSpecial(BasicAction):
    def resolve(self):
        if hasattr(self.target, 'special'):
            self.target.special.append(self.string)


class DrawCards(BasicAction):
    def resolve(self):
        if len(self.target.hand) + self.amount > 10:
            self.amount = 10 - len(self.target.hand)  # This should be a standard reaction later
        if self.amount < 0:
            self.amount = 0
        for c in self.target.deck[:self.amount]:
            c.move_anywhere(self.target.hand)


class ChangeMana(BasicAction):
    def resolve(self):
        if self.target.mana < mana_cap:
            self.target.mana += self.amount


class ChangeIncome(BasicAction):
    def resolve(self):
        self.target.income += self.amount


class ChangeStats(BasicAction):
    def resolve(self):
        # "Amount" is a tuple of attack and health
        self.target.attack += self.amount[0]
        self.target.health += self.amount[1]


class ChangeStock(BasicAction):
    def resolve(self):
        self.target.stock += self.amount


class FullHeal(BasicAction):
    def resolve(self):
        self.target.health = self.target.max_health


class RemoveSpecial(BasicAction):
    def resolve(self):
        self.target.special.remove(self.string)


class ChangeDuration(BasicAction):
    def resolve(self):
        self.target.duration += self.amount


class SetStats(BasicAction):
    def resolve(self):
        # "Amount" is a tuple of attack and health
        self.target.attack = self.amount[0]
        self.target.health = self.amount[1]


class ChangeCost(BasicAction):
    def resolve(self):
        if self.target.cost + self.amount >= 0:
            self.target.cost += self.amount
        else:
            self.target.cost = 0


class MoveCard(BasicAction):
    def resolve(self):
        pass


class DrawSpecific(BasicAction):
    def resolve(self):
        if len(self.target.player.hand) <= 10:
            self.target.move_anywhere(self.target.player.hand)


class SummonCard(BasicAction):
    def resolve(self):
        active_card = self.target # The target here is the card being played
        if active_card.type in ['Minion', 'Structure']:
            # Place card on board
            if self.second_target:
                space = self.second_target # The secondary target is the destination for the card
            else:
                space = active_card.player.spaceboard.random_open_space()
                if not space:
                    return
            active_card.move_anywhere(space)
            # active_card.status = 'new'
            active_card.is_new = True
        elif active_card.type in ['Skill', 'Item']:
            active_card.move_anywhere(active_card.player.tableau)
            # active_card.status = 'new'
            active_card.is_new = True
        else:
            # Discard card as it is used
            active_card.move_anywhere(active_card.player.discard)


class SummonNear(ConditionalAction):
    def resolve(self):
        active_card = self.target
        board = self.player.board
        column = self.extras['column']
        possible_spaces = [i for i in self.player.spaceboard if i.status == 'open' and i.has_adjacent_card()]
        distances = [abs(column - i.column - 0.1) for i in possible_spaces]
        sorted_spaces = [y for _, y in sorted(zip(distances, possible_spaces))]
        if sorted_spaces:
            target_space = sorted_spaces[0]
            return [SummonCard(self.source, active_card, second_target=target_space)]
        return []


class SummonNewCard(BasicAction):
    # Target should be a player
    def resolve(self):
        player = self.target
        open_space = player.spaceboard.random_open_space()
        if open_space:
            new = load_card(self.string, player)
            new.move_anywhere(open_space)
            new.status = 'new'


class AddNewToDeck(BasicAction):
    # Target should be a player
    def resolve(self):
        player = self.target
        deck = player.deck
        new = load_card(self.string, player)
        new.move_anywhere(deck, position=self.flag)


class ShuffleDeck(BasicAction):
    def resolve(self):
        self.target.shuffle()


class AddNewToHand(BasicAction):
    # Target should be a player
    def resolve(self):
        player = self.target
        hand = player.hand
        new = load_card(self.string, player)
        new.move_anywhere(hand)


class AddNewToEmblems(BasicAction):
    # Target should be a player
    def resolve(self):
        player = self.target
        new = load_card(self.string, player)
        new.move_anywhere(player.Emblemboard)


class TransformCard(BasicAction):
    # Target should be a player
    def resolve(self):
        player = self.target.player
        space = self.target.space
        new = load_card(self.string, player)
        self.target.move_anywhere(self.target.player.exile)
        new.move_anywhere(space)
        new.status = 'new'
        if self.amount:
            if len(self.amount) == 1:
                 new.cost = self.amount
            elif len(self.amount) == 2:
                new.attack, new.health = self.amount


class DiscardFromHand(BasicAction):
    def resolve(self):
        self.target.move_anywhere(self.target.player.discard)


class DiscardFromBoard(BasicAction):
    def resolve(self):
        self.target.move_anywhere(self.target.player.discard)


class DiscardFromDeck(BasicAction):
    def resolve(self):
        self.target.move_anywhere(self.target.player.discard)


class StartGame(BasicAction):
    # This only exists to trigger reactions and interrupts that happen at the start of the game.
    def resolve(self):
        pass


class ChangeStatus(BasicAction):
    # Updates statuses of cards at the start of a new turn
    def resolve(self):
        new = self.target
        for c in (new.board.contents + new.tableau.contents + [new.hero]):
            c.is_new = False
            c.is_tapped = False


class EndTurn(BasicAction):
    def resolve(self):
        self.target.is_active = False


class StartTurn(BasicAction):
    def resolve(self):
        self.target.is_active = True


class NewLayer(BasicAction):
    # Serves as a marker in a string of BasicActions that the program should resolve all other actions before continuing
    def resolve(self):
        pass


class PlayCardFlag(BasicAction):
    # This only exists to trigger reactions and interrupts that happen when a card is played.
    def resolve(self):
        pass






# Rule Cards - Apply rules as reactions and interrupts -----------------------------------------------------------------
class RampageKeyword(Card):
    # Rampage Reaction
    def get_reaction(self, basic_action):
        if basic_action.source.is_card and 'Rampage' in basic_action.source.special:
            if basic_action.__class__.__name__ == 'DealDamage' and basic_action.target.is_card:
                if basic_action.amount >= basic_action.target.health:
                    if basic_action.source.player.is_active:
                        basic_action.source.status = 'available'  # This makes it a "coaction" as opposed to a reaction
                        return Reaction(self, basic_action.source)

    def reaction(self, target, trigger):
        target.status = 'available'
        return None

class ChargeKeyword(Card):
    def get_reaction(self, basic_action):
        if basic_action.__class__.__name__ == 'SummonCard' and 'Charge' in basic_action.target.special:
            return Reaction(self, target=basic_action.target)

    def reaction(self, target, trigger):
        target.status = 'available'
        return None


class StarKeyword(Card):
    def get_reaction(self, basic_action):
        if basic_action.class_name == 'StartGame':
            return Reaction(self, basic_action.target)

    def reaction(self, target, trigger):
        basic_actions = []
        for p in [target, target.opponent]:
            for c in p.deck:
                if 'Star' in c.special:
                    basic_actions.append(SummonCard(c, target=c))
            for c in p.hand:
                if 'Star' in c.special:
                    basic_actions.append(SummonCard(c, target=c))
                    basic_actions.append(DrawCards(source=c, target=c.player, amount=1))
        return basic_actions


class ImmuneKeyword(Card):
    # Immune: can't take damage.  May have other aspects in the future.
    def get_interrupt(self, basic_action):
        if basic_action.__class__.__name__ == 'DealDamage':
            if 'Immune' in basic_action.target.special:
                return Interrupt(self, 0, basic_action)
        return False

    def interrupt(self, trigger):
        # Remove trigger
        return []


class CheckDeath(Card):
    def get_reaction(self, basic_action):
        if basic_action.__class__.__name__ == 'DealDamage':
            if basic_action.target.name != 'Hero':  # Separate function for that
                return Reaction(self, basic_action.target, trigger=basic_action.source)

    def reaction(self, target, trigger):
        if target.is_alive and target.health <= 0:
            target.is_alive = False
            target.move_anywhere(target.player.discard)


class ReduceDurations(Card):
    def get_reaction(self, basic_action):
        if basic_action.__class__.__name__ == 'EndTurn':
            return Reaction(self, basic_action.source)

    def reaction(self, target, trigger):
        new_basic_actions = []
        for c in (target.cards_in_play() + target.opponent.cards_in_play()):
            if c.duration > 0:
                new_basic_actions.append(ChangeDuration(self, c, amount=-0.5))
        return new_basic_actions


class CheckHeroDeath(Card):
    def get_reaction(self, basic_action):
        if basic_action.__class__.__name__ == 'DealDamage':
            if basic_action.target.name == 'Hero':
                if basic_action.amount >= basic_action.target.health:
                    return Reaction(self, basic_action.target, trigger=basic_action)
        if basic_action.__class__.__name__ == 'EndTurn':
            if self.aura_list:
                return Reaction(self, basic_action.target, trigger=basic_action)

    def reaction(self, target, trigger):
        if trigger.__class__.__name__ == 'DealDamage':  # Reacting to hero death
            if 'Immune' not in target.special:
                target.special.append('Immune')
                self.aura_list.append(target)
            return [ChangeStock(self, target, amount=-1),
                    FullHeal(self, target),
                    ]
        elif trigger.__class__.__name__ == 'EndTurn':  # Remove Immunity
            for h in self.aura_list:
                h.special.remove('Immune')
            self.aura_list = []


class QuickenAll(Card):
    def get_reaction(self, basic_action):
        if basic_action.__class__.__name__ == 'StartTurn' and basic_action.extras['turn'] > 0:
            return Reaction(self, basic_action.target)

    def reaction(self, target, trigger):
        return [ChangeCost(target=c, amount=-1) for c in target.hand]


# standard_reactions = [RampageReaction(), CheckDeath(), ChargeReaction(), StarReaction(), QuickenAll()]
rule_cards = [RampageKeyword(), ChargeKeyword(), StarKeyword(), ReduceDurations(), ImmuneKeyword(),
              CheckDeath(), CheckHeroDeath()]


# Archetype Cards ----------------------------------------------------------------------------- Archetype Cards
# These cards have relatively simple actions that other cards can copy in part or whole
class Burn(Card):
    def enter(self, targets):
        return [DealDamage(self, targets[0], self.amount)]

    def legal_hand_target(self, target):
        if target.location == target.player.board or target.name == 'Hero':
                return True
        return False


class AoeBoard(Card):
    def enter(self, targets):
        new_basic_actions = []
        for c in self.player.opponent.board.contents:
            if hasattr(c, 'health'):
                new_basic_actions.append(DealDamage(self, c, self.amount))
        return new_basic_actions


class AoeMinions(Card):
    def enter(self, targets):
        new_basic_actions = []
        for c in self.player.opponent.board.contents:
            if hasattr(c, 'health') and c.type == 'Minion':
                new_basic_actions.append(DealDamage(self, c, self.amount))
        return new_basic_actions


class HealHero(Card):
    def enter(self, targets):
        return [Heal(self, self.player, amount=self.amount)]


class Supply(Card):
    def enter(self, targets):
        return [DrawCards(self, self.player, self.amount)]


class Coin(Card):
    def enter(self, targets):
        return [ChangeMana(self, self.player, self.amount)]


class Sword(Card):
    def aura(self):
        if self.location == self.player.tableau:
            if self.player.hero not in self.aura_list:
                self.aura_list.append(self.player.hero)
                self.player.hero.attack += self.amount
        else:
            for c in self.aura_list:
                c.attack -= self.amount
            self.aura_list = []


# Individual Cards ----------------------------------------------------------------------------- Individual Cards
class WildDragon(Card):
    # Rampage Reaction
    def get_reaction(self, basic_action):
        if basic_action.__class__.__name__ == 'DealDamage' and basic_action.target.is_card:
            if basic_action.source == self:
                if basic_action.amount >= basic_action.target.health:
                    if self.player.is_active:
                        self.status = 'available'  # This makes it a "coaction" as opposed to a reaction
                        return Reaction(self)

    def reaction(self, target, trigger):
        self.status = 'available'
        return []


class ArcaneScribe(Card):
    def get_reaction(self, basic_action):
        if basic_action.source == self.player and basic_action.__class__.__name__ == 'PlayCardFlag':
            return Reaction(self, target=basic_action.target.name)
        return False

    def reaction(self, target, trigger):
        return [AddNewToDeck(self, target)]


class TreasureHunter(Card):
    # Raid Ability
    def get_reaction(self, basic_action):
        if basic_action.source == self and basic_action.target == self.player.opponent.hero:
            return Reaction(self)
        return False

    def reaction(self, target, trigger):
        return [AddNewToHand(self, self.player, string='Treasure')]


class Smuggler(Card):
    def get_enter(self, targets):
        return Enter(self)

    def enter(self, targets):
        new_basic_actions = [DrawCards(self, self.player, 1)]
        return new_basic_actions


class Turncoat(Card):
    def get_enter(self, targets):
        return Enter(self, 0)

    def enter(self, targets):
        new_basic_actions = [DrawCards(self, self.player.opponent, 1)]
        return new_basic_actions


class Apprentice(Card):
    def get_reaction(self, basic_action):
        if basic_action.__class__.__name__ == 'DealDamage':
            if basic_action.target == self:
                return Reaction(self)
        return False

    def reaction(self, target, trigger):
        return [DrawCards(self, self.player, 1)]


class FireShaman(Card):
    def get_reaction(self, basic_action):
        if self.location == self.player.board:
            if basic_action.__class__.__name__ in  ['DrawCards', 'DrawSpecific']:
                if basic_action.target == self.player:
                    return Reaction(self, trigger=basic_action)
        return False

    def reaction(self, target, trigger):
        new_basic_actions = []
        for c in self.player.board.contents + self.player.opponent.board.contents:
            if c != self:
                for i in range(trigger.amount):
                    new_basic_actions.append(DealDamage(self, c, 1))
        return new_basic_actions


class BookBurner(Card):
    def get_reaction(self, basic_action):
        if self.location == self.player.board:
            if basic_action.__class__.__name__ == 'DiscardFromHand':
                if basic_action.target.location == self.player.hand:
                    return Reaction(self, trigger=basic_action)
        return False

    def reaction(self, target, trigger):
        return [DealDamage(self, self.player.opponent.hero, amount=1)]


class WarElephant(Card):
    def get_interrupt(self, basic_action):
        if basic_action.__class__.__name__ == 'DealDamage':
            if basic_action.target == self:
                return Interrupt(self, 0, basic_action)
        return False

    def interrupt(self, trigger):
        trigger.amount -= 1
        return [trigger]


class LuckyCoin(Card):
    def enter(self, targets):
        return [ChangeMana(self, self.player, amount=self.amount)]

    def get_interrupt(self, basic_action):
        if basic_action.__class__.__name__ == 'StartGame':
            return Interrupt(self, 0, basic_action)

    def interrupt(self, trigger):
        self.player.deck.contents.sort(key=lambda c: c.name == 'LuckyCoin', reverse=True)
        return [trigger]


class MammothHunter(Card):
    def enter(self, targets):
        self.toggle_active = True
        return []

    def aura(self):
        if not self.player.is_active:
            self.toggle_active = False

    def get_interrupt(self, basic_action):
        if self.toggle_active:
            if basic_action.__class__.__name__ == 'DealDamage':
                if basic_action.target == self:
                    return Interrupt(self, 0, basic_action)
        return False

    def interrupt(self, trigger):
        trigger.amount = 0
        return [trigger]


class CityOfJade(Card):
    def get_interrupt(self, basic_action):
        if self.location == self.player.board:
            if basic_action.__class__.__name__ == 'DealDamage':
                if basic_action.source.type == 'Spell':
                    if basic_action.source.player == self.player:
                        return Interrupt(self, 0, basic_action)
        return False

    def interrupt(self, trigger):
        trigger.amount += 1
        return [trigger]


class LightningRod(Card):
    def get_interrupt(self, basic_action):
        if self.location == self.player.board:
            if basic_action.__class__.__name__ == 'DealDamage':
                if basic_action.source.type == 'Spell':
                    if basic_action.target.player == self.player:
                        return Interrupt(self, target=basic_action, trigger=basic_action)
            return False

    def interrupt(self, trigger):
        trigger.target = self
        return [trigger]


class NoviceShieldmaster(Card):
    def get_interrupt(self, basic_action):
        if basic_action.source.is_card and basic_action.source.type == 'Spell':
            if basic_action.source.player == self.player.opponent:
                if basic_action.__class__.__name__ == 'Enter':
                    return Interrupt(self, 0, basic_action)
        return False

    def interrupt(self, trigger):
        # Do not return Trigger, which is the Enter effect.  Instead return MakeDead action.
        return [MakeDead(self, self)]


class Muk(Card):
    def get_reaction(self, basic_action):
        if basic_action.__class__.__name__ == 'DealDamage':
            if basic_action.target == self:
                return Reaction(self)
        return False

    def reaction(self, target, trigger):
        new = load_card('Blob', self.player)
        return [SummonNear(self, new, player=self.player, column=self.space.column)]


class FifthBrigade(Card):
    def legal_hand_target(self, target):
        if (target.__class__.__name__ == 'Space' and target.has_adjacent_card()
                and target.status == 'open' and target.player == self.player):
            return True
        return False

    def enter(self, targets):
        column = targets[0].column
        basic_actions = []
        for i in range(5):
            new = load_card('Soldier', self.player)
            basic_actions.append(SummonNear(self, new, player=self.player, column=column))
        return basic_actions


class LivingBrambles(Card):
    def legal_hand_target(self, target):
        if (target.__class__.__name__ == 'Space' and target.has_adjacent_card()
                and target.status == 'open' and target.player == self.player):
            return True
        return False

    def enter(self, targets):
        column = targets[0].column
        basic_actions = []
        for i in range(3):
            new = load_card('Bramble', self.player)
            basic_actions.append(SummonNear(self, new, player=self.player, column=column))
        return basic_actions


class Spider(Card):
    def enter(self, targets):
        column = targets[0].column
        basic_actions = []
        for i in range(2):
            new = load_card('Spiderling', self.player)
            basic_actions.append(SummonNear(self, new, player=self.player, column=column))
        return basic_actions


class ArcherWall(Card):
    def legal_hand_target(self, target):
        if (target.__class__.__name__ == 'Space' and target.has_adjacent_card()
                and target.status == 'open' and target.player == self.player):
            return True
        return False

    def enter(self, targets):
        column = targets[0].column
        basic_actions = []
        for i in range(5):
            new = load_card('Archer', self.player)
            basic_actions.append(SummonNear(self, new, player=self.player, column=column))
        return basic_actions


class Swordmaker(Card):
    def get_reaction(self, basic_action):
        if self.location.type == 'board':
            if basic_action.__class__.__name__ == 'SummonCard':
                if basic_action.target.player == self.player:
                    return Reaction(self, target=basic_action.target)
        return False

    def reaction(self, target, trigger):
        return ChangeStats(self, target, amount=(1, 0))


class Forge(Card):
    def get_reaction(self, basic_action):
        if self.location.type == 'board':
            if basic_action.__class__.__name__ == 'SummonCard':
                if basic_action.target.player == self.player:
                    return Reaction(self, target=basic_action.target)
        return False

    def reaction(self, target, trigger):
        return [ChangeStats(self, target, amount=(0, 1))]

    def reaction(self, target, trigger):
        return [ChangeStats(self, target, amount=(0, 1))]


class Cobra(Card):
    def get_reaction(self, basic_action):
        if basic_action.__class__.__name__ == 'DealDamage':
            if basic_action.source == self:
                if hasattr(basic_action.target, 'is_alive') and basic_action.target.is_alive:
                    return Reaction(self, target=basic_action.target)
        return False

    def reaction(self, target, trigger):
        return [MakeDead(self, target)]


class Sentry(Card):
    def get_reaction(self, basic_action):
        if basic_action.__class__.__name__ == 'StartGame':
            return Reaction(self)

    def reaction(self, target, trigger):
        return [SummonNear(self, self, player=self.player, column=0)]


class CarrionFlies(Card):
    def get_reaction(self, basic_action):
        if basic_action.target.location == self.player.board:
            if basic_action.__class__.__name__ == 'MakeDead':
                return Reaction(self)
            if basic_action.__class__.__name__ == 'DealDamage' and basic_action.amount > basic_action.target.health:
                return Reaction(self)

    def reaction(self, target, trigger):
        basic_actions = []
        if self.location == self.player.deck:
            open_space = self.player.spaceboard.random_open_space()
            if open_space:
                basic_actions.append(SummonCard(self, self, second_target=open_space))
                open_space.status = 'full'
        return basic_actions


class OakFather(Card):
    def enter(self, targets):
        return [ChangeIncome(self, self.player, amount=5)]
    

class Sprint(Card):
    def legal_board_target(self, target):
        if target.is_card and target.location == self.player.hand:
            return True

    def ability(self, targets):
        print('sprint ability')
        return [DiscardFromHand(self, targets[0]), ChangeMana(self, self.player, amount=1)]
    
    
class Rest(Card):
    def ability(self, targets):
        return [DrawCards(self, self.player, amount=1)]


class Flare(Card):
    def enter(self, targets):
        new_basic_actions = []
        for c in self.player.board.contents + self.player.opponent.board.contents:
            if hasattr(c,'health'):
                new_basic_actions.append(DealDamage(self, c, 1))
        return new_basic_actions


class Vortex(Card):
    def enter(self, targets):
        new_basic_actions = []
        for c in self.player.board.contents + self.player.opponent.board.contents:
            new_basic_actions.append(MakeDead(self, c))
        return new_basic_actions


class Grow(Card):
    def enter(self, targets):
        new_basic_actions = []
        for c in self.player.board.contents:
            if c.type == 'Minion':
                new_basic_actions.append(ChangeStats(self, c, (1,1)))
        return new_basic_actions


class Showdown(Card):
    def enter(self, targets):
        return [ChangeStats(self, targets[0], amount=(4, 4)),
                AddSpecial(self, targets[0], string='Rampage')]

    def legal_hand_target(self, target):
        if target.is_card:
            if target.location.type == 'board':
                if len(self.targets) <= self.n_hand_targets:
                    return True
        return False


class Greatsword(Card):
    def enter(self, targets):
        return [ChangeStats(self, targets[0], amount=(3, 3))]

    def legal_hand_target(self, target):
        if target.is_card:
            if target.location.type == 'board':
                if len(self.targets) <= self.n_hand_targets:
                    return True
        return False


class Shipwreck(Card):
    def enter(self, targets):
        return [MakeDead(self, targets[0])]

    def legal_hand_target(self,target):
        if target.is_card:
            if target.location.type == 'board':
                if len(self.targets) <= self.n_hand_targets:
                    return True
        return False





class Gold(Card):
    def enter(self, targets):
        return [ChangeMana(self, self.player, 2)]


class Ramp(Card):
    def enter(self, targets):
        return [ChangeIncome(self, self.player, 1)]


class Lightning(Card):
    def enter(self, targets):
        new_basic_actions = []
        # Check Targets
        for t in targets:
            new_basic_actions.append(DealDamage(self, t, 2))
        return new_basic_actions

    def legal_hand_target(self,target):
        if target.is_card:
            if target.location.type == 'board':
                if hasattr(target,'health'):
                    if len(self.targets) <= self.n_hand_targets:
                        return True
        elif target.name == 'Hero':
            return True


class Mansion(Card):
    def aura(self):
        if self.location == self.player.board:
            for c in (self.player.hand.contents):
                if c not in self.aura_list:
                    if c.type == 'Spell' and c.cost > 0:
                        self.aura_list.append(c)
                        c.cost -= 1
            for c in self.aura_list:
                if c.location.type != 'hand':
                    self.aura_list.remove(c)
                    c.cost += 1
        else:
            for c in self.aura_list:
                c.cost += 1
            self.aura_list = []


class ResonanceStone(Card):
    def aura(self):
        if self.location == self.player.board:
            for c in (self.player.hand.contents + self.player.opponent.hand.contents):
                if c not in self.aura_list:
                    self.aura_list.append(c)
                    c.cost += 1
            for c in self.aura_list:
                if c.location.type != 'hand':
                    self.aura_list.remove(c)
                    c.cost -= 1
        else:
            for c in self.aura_list:
                c.cost -= 1
            self.aura_list = []


class AncientGrove(Card):
    def aura(self):
        if self.location == self.player.board:
            for p in (self.player, self.player.opponent):
                if p not in self.aura_list:
                        self.aura_list.append(p)
                        p.income += 1
        else:
            for p in self.aura_list:
                p.income -= 1
            self.aura_list = []


class Wall(Card):
    def aura(self):
        if self.location == self.player.board:
            for c in (self.player.board.contents):
                if c != self and c not in self.aura_list:
                    self.aura_list.append(c)
                    c.health += 2
            for c in self.aura_list:
                if c.location.type != 'board':
                    self.aura_list.remove(c)
                    c.health -= 2
        else:
            for c in self.aura_list:
                c.health -= 2
            self.aura_list = []

class FirstLight(Card):
    def enter(self, targets):
        basic_actions = []
        for c in self.player.hand:
            basic_actions.append(ChangeCost(self, c, amount=-1))
        return basic_actions


class Kraken(Card):
    def enter(self, targets):
        new_basic_actions = []
        for c in self.player.opponent.board.contents:
            if c.is_card and c.type == 'Minion':
                new_basic_actions.append(DealDamage(self, c, 2))
        return new_basic_actions


class WoodArcher(Card):
    def legal_hand_target(self,target):
        if not self.targets:
            if target.location == self.player.spaceboard and target.status == 'open':
                return True
        if len(self.targets) == 1:
            if target.location.type == 'board' or target.name == 'Hero':
                return True
        return False

    def enter(self, targets):
        return [DealDamage(self, targets[1], self.amount)] if len(targets) > 1 else []


class StrangeTraveler(Card):
    def enter(self, targets):
        if len(targets) == 2:
            return [TransformCard(self, targets[1], string='StrangeTraveler')]
        else:
            return []

    def legal_hand_target(self, target):
        if target.name == 'Hero':
            return False
        if not self.targets:
            if target.location == self.player.spaceboard and target.status == 'open':
                return True
        if len(self.targets) == 1:
            if hasattr(target.location, 'type') and target.location.type == 'board':
                return True
        return False


class Seedling(Card):
    def enter(self, targets):
        if len(targets) == 2:
            return [TransformCard(self, self, string=targets[1].name, amount=(1,1))]
        else:
            return []

    def legal_hand_target(self, target):
        if not self.targets:
            if target.location == self.player.spaceboard and target.status == 'open':
                return True
        if len(self.targets) == 1:
            if hasattr(target.location, 'type') and target.location.type == 'board':
                return True
        return False


class BuilderAnt(Card):
    def enter(self, targets):
        if len(targets) == 2:
            return [AddNewToDeck(self, self.player, string=targets[1].name),
                    AddNewToDeck(self, self.player, string=targets[1].name)]
        else:
            return []

    def legal_hand_target(self, target):
        if not self.targets:
            if target.location == self.player.spaceboard and target.status == 'open':
                return True
        if len(self.targets) == 1:
            if hasattr(target.location, 'type') and target.location.type == 'board':
                return True
        return False


class Starlight(Card):
    def enter(self, targets):
        deck = self.player.deck.contents
        new_cards = deck[:2] if len(deck) >= 2 else deck
        basic_actions = []
        for c in new_cards:
            basic_actions.append(DrawSpecific(self, c))
            basic_actions.append(ChangeCost(self, c, amount=-1))
        return basic_actions

class GrandDiscovery(Card):
    def enter(self, targets):
        deck = self.player.deck.contents
        new_cards = deck[:4] if len(deck) >= 4 else deck
        basic_actions = []
        for c in new_cards:
            basic_actions.append(DrawSpecific(self, c))
            basic_actions.append(ChangeCost(self, c, amount=1))
        return basic_actions

class MermaidHealer(Card):
    def legal_hand_target(self,target):
        if not self.targets:
            if target.location == self.player.spaceboard and target.status == 'open':
                return True
        if len(self.targets) == 1:
            if target.is_card and hasattr(target, 'attack') and target.location.type == 'board':
                return True
        return False

    def enter(self, targets):
        if len(targets) > 1:
            return [ChangeStats(self, targets[1], amount=(0, 3))]
        else:
            return []

class Blacksmith(Card):
    def legal_hand_target(self,target):
        if not self.targets:
            if target.location == self.player.spaceboard and target.status == 'open':
                return True
        if len(self.targets) == 1:
            if target.is_card and hasattr(target, 'attack') and target.location == self.player.board:
                return True
        return False

    def enter(self, targets):
        if len(targets) > 1:
            return [ChangeStats(self, targets[1], amount=(1, 1))]
        else:
            return []

class Slayer(Card):
    def legal_hand_target(self,target):
        if not self.targets:
            if target.location == self.player.spaceboard and target.status == 'open':
                return True
        if len(self.targets) == 1:
            if target.location == self.player.opponent.board:
                return True
        return False

    def enter(self, targets):
        if len(targets) > 1:
            return [MakeDead(self, targets[1])]
        return []  # Probably not needed


class EagleEyeRaven(Card):
    def enter(self, targets):
        cards = [i for i in self.player.opponent.hand.contents if not i.is_revealed]
        if cards:
            cards[0].is_revealed = True
        return []


class MasterSpy(Card):
    def enter(self, targets):
        for c in self.player.opponent.hand:
            c.is_revealed = True
        return []


class WorldBending(Card):
    def enter(self, targets):
        new_basic_actions = []
        for c in self.player.hand:
            if c != self:
                new_basic_actions.append(AddNewToDeck(self, self.player, string=c.name, flag='Random'))
        return new_basic_actions

class SwiftCaravel(Card):
    def enter(self, targets):
        return [AddNewToDeck(self, self.player.opponent, string='Blockade', flag='Top')]


class Embargo(Card):
    def enter(self, targets):
        return [AddNewToDeck(self, self.player.opponent, string='Embargo', flag='Top')]


class Tariff(Card):
    def enter(self, targets):
        return [AddNewToDeck(self, self.player.opponent, string='Tariff', flag='Top'),
                DrawCards(self, target=self.player, amount=1)]


class TradeWar(Card):
    def enter(self, targets):
        return [AddNewToDeck(self, self.player.opponent, string='TradeWar', flag='Top'),
                AddNewToDeck(self, self.player.opponent, string='TradeWar', flag='Top')]


class Logic(Card):
    def legal_hand_target(self, target):
        if not self.targets:
            if target.name == 'Center Box':
                return True
        elif target.location == self.player.hand:
            if target != self:
                return True
        return False

    def enter(self, targets):
        new_basic_actions = []
        for c in targets[1:]:
            new_basic_actions.append(DiscardFromHand(self, c))
        new_basic_actions.append(DrawCards(self, self.player, 4))
        return new_basic_actions


class FranticScholar(Card):
    def legal_hand_target(self, target):
        if not self.targets:
            if target.location == self.player.spaceboard and target.status == 'open':
                return True
        elif target.location == self.player.hand:
            if target != self:
                return True
        return False

    def enter(self, targets):
        new_basic_actions = []
        for c in targets[1:]:
            new_basic_actions.append(DiscardFromHand(self, c))
        new_basic_actions.append(DrawCards(self, self.player, 1))
        return new_basic_actions

class WizenedScholar(Card):
    def legal_hand_target(self, target):
        if not self.targets:
            if target.location == self.player.spaceboard and target.status == 'open':
                return True
        elif target.location == self.player.hand:
            if target != self:
                return True
        return False

    def enter(self, targets):
        new_basic_actions = []
        for c in targets[1:]:
            new_basic_actions.append(DiscardFromHand(self, c))
        new_basic_actions.append(DrawCards(self, self.player, 2))
        return new_basic_actions


class Fireworks(Card):
    def enter(self, targets):
        return [DealDamage(self, targets[0], 2),
                AddNewToDeck(self, self.player, string='Fireworks')]

    def legal_hand_target(self,target):
        if target.is_card:
            if target.location.type == 'board':
                if hasattr(target,'health'):
                    if len(self.targets) <= self.n_hand_targets:
                        return True
        elif target.name == 'Hero':
            return True
        return False


class Banditry(Card):
    def enter(self, targets):
        new_basic_actions = []
        amount = int(len(self.player.opponent.deck) / 2)
        for i in range(amount):
            new_basic_actions.append(DiscardFromDeck(self, self.player.opponent.deck[i]))
        return new_basic_actions


class GroveTender(Card):
    def enter(self, targets):
        return [AddNewToEmblems(self, self.player, string='Refreshed')]


class Sunmaker(Card):
    def enter(self, targets):
        new_basic_actions = []
        for c in self.player.deck:
            if c.type == 'Spell':
                new_basic_actions.append(ChangeCost(self,c, amount=-1))
        return new_basic_actions


class ATimeForPlanting(Card):
    def enter(self, targets):
        pass


class FlameShot(Card):
    def legal_hand_target(self, target):
        if not self.targets:
            if hasattr(target.location, 'type') and target.location.type == 'board':
                return True
            elif target.name == 'Hero':
                return True
        elif len(self.targets) == 1:
            if target.location == self.player.hand:
                return True
        return False

    def enter(self, targets):
        new_basic_actions = [DealDamage(self, targets[0], amount=4)]
        if len(targets) == 2:
            new_basic_actions.append(DiscardFromHand(self, targets[1]))
        return new_basic_actions


class Overwhelm(Card):
    def legal_hand_target(self, target):
        if not self.targets:
            if hasattr(target.location, 'type') and target.location.type == 'board':
                return True
        elif len(self.targets) == 1:
            if target.location == self.player.hand:
                return True
        return False

    def enter(self, targets):
        new_basic_actions = [MakeDead(self, targets[0])]
        if len(targets) == 2:
            new_basic_actions.append(DiscardFromHand(self, targets[1]))
        return new_basic_actions


class FlameGolem(Card):
    def legal_hand_target(self, target):
        if not self.targets:
            if target.location == self.player.spaceboard:
                return True
        elif len(self.targets) == 1:
            if target.location == self.player.hand:
                return True
        return False

    def enter(self, targets):
        if len(targets) == 2:
            return [DiscardFromHand(self, targets[1])]
        return []


class ForestDefender(Card):
    def legal_attack(self, target):
        if self.attack >= 1:
            if target.name == 'Hero':  # Can't attack heros
                return False
            elif target.location == self.player.opponent.board:  # Must be a card
                # Can't attack non-adjacent enemies
                if abs(self.space.column - target.space.column) > 1 and target != target.player.hero:
                    return False
                return True
        return False


class Practice(Card):
    def enter(self, targets):
        self.is_tapped = False

    def get_interrupt(self, basic_action):
        source = basic_action.source
        if source.is_card and source.player == self.player and source.type == 'Spell':
            if not basic_action.is_repeat:
                return Interrupt(self, 0, basic_action)
        return False

    def interrupt(self, trigger):
        new = trigger.clone()
        new.is_repeat = True
        self.is_tapped = True
        return [new]

class Adaptation(Card):
    def get_reaction(self, basic_action):
        if basic_action.source == self.player and basic_action.__class__.__name__ == 'PlayCardFlag':
            return Reaction(self, target=basic_action.target.name)
        return False

    def reaction(self, target, trigger):
        return [AddNewToDeck(self, target)]


class FireElemental(Card):
    def get_reaction(self, basic_action):
        if self.location == self.player.board:
            if basic_action.__class__.__name__ == 'EndTurn' and basic_action.target == self.player:
                return Reaction()

    def reaction(self, target, trigger):
        new_basic_actions = []
        for c in self.player.opponent.board.contents:
            if abs(c.space.column - self.space.column) >= 1:
                new_basic_actions.append(DealDamage(self, c, amount=1))
        return new_basic_actions


class FlameWall(Card):
    def get_reaction(self, basic_action):
        if self.location == self.player.board:
            if basic_action.__class__.__name__ == 'EndTurn' and basic_action.target == self.player.opponent:
                return Reaction(self)

    def reaction(self, target, trigger):
        new_basic_actions = []
        for c in self.player.opponent.board.contents:
            if abs(c.space.column - self.space.column) <= 1:
                new_basic_actions.append(DealDamage(self, c, amount=1))
        return new_basic_actions


class IceWall(Card):
    def aura(self):
        if self.location == self.player.board:
            for c in self.player.opponent.board.contents:
                if c not in self.aura_list:
                    if hasattr(c, 'attack') and c.attack > 0:
                        if abs(self.space.column - c.space.column) <= 1:
                            self.aura_list.append(c)
                            c.attack -= 1

            for c in self.aura_list:
                if c.location.type != 'board' or abs(self.space.column - c.space.column) > 1:
                    self.aura_list.remove(c)
                    c.attack += 1
        else:
            for c in self.aura_list:
                c.attack += 1
            self.aura_list = []


class StaticArc(Card):
    def ability(self, targets):
        n_possible_targets = len(self.player.opponent.board.contents)
        rnd = random.randint(0, n_possible_targets)
        if rnd == n_possible_targets:
            return [DealDamage(self, self.player.opponent.hero, amount=1)]
        else:
            return [DealDamage(self, self.player.opponent.board.contents[rnd], amount=1)]


class CityWalls(Card):
    def aura(self):
        if self.location == self.player.board:
            for c in self.player.board.contents:
                if c != self and c not in self.aura_list:
                    self.aura_list.append(c)
                    c.health += self.amount

            for c in self.aura_list:
                if c.location != self.player.board:
                    self.aura_list.remove(c)
                    c.health -= self.amount
        else:
            for c in self.aura_list:
                c.health -= self.amount
            self.aura_list = []


class CrystalTower(Card):
    def aura(self):
        if self.location == self.player.board:
            for c in self.player.hand.contents + self.player.opponent.hand.contents:
                if c.type == 'Spell' and c not in self.aura_list:
                    self.aura_list.append(c)
                    c.cost += self.amount

            for c in self.aura_list:
                if c.location != self.player.board:
                    self.aura_list.remove(c)
                    c.cost -= self.amount
        else:
            for c in self.aura_list:
                c.cost -= self.amount
            self.aura_list = []


class Barbarian(Card):
    def aura(self):
        if self.location == self.player.board:
            for c in self.player.hand.contents:
                if c.type == 'Spell' and c not in self.aura_list:
                    self.aura_list.append(c)
                    c.cost += self.amount
                    print(c, 'added to aura list for barbarian')

            for c in self.aura_list:
                if c.location != self.player.hand:
                    self.aura_list.remove(c)
                    c.cost -= self.amount
        else:
            for c in self.aura_list:
                c.cost -= self.amount
            self.aura_list = []


class MinorIllusion(Card):
    def legal_board_target(self, target):
        if target.location == self.player.spaceboard:
            if target.status == 'open':
                return True
        return False

    def ability(self, targets):
        new = load_card('Illusion', self.player)
        return [SummonCard(self, new, second_target=targets[0])]


class Lunge(Card):
    def ability(self, targets):
        if not self.toggle_active:
            self.toggle_active = True
            return [ChangeStats(self, self.player.hero, (self.amount, 0)),
                    ChangeDuration(self, self, amount=0.5)]
        return []

    def get_reaction(self, basic_action):
        if basic_action.__class__.__name__ == 'ChangeDuration' and basic_action.target == self:
            if self.toggle_active:
                return Reaction(self)

    def reaction(self, target, trigger):
        if self.toggle_active and self.duration <= 0:
            self.toggle_active = False
            return [ChangeStats(self, self.player.hero, (-self.amount, 0))]
        return []


class PalmStrike(Card):
    def aura(self):
        if self.location == self.player.hand:
            for c in self.player.tableau:
                if c not in self.aura_list:
                    if c.type == 'Item':
                        self.aura_list.append(c)
                        self.cost += 1

            for c in self.aura_list:
                if c.location != self.player.tableau:
                    self.aura_list.remove(c)
                    self.cost -= 1
        else:
            for c in self.aura_list:
                self.cost -= 1
            self.aura_list = []

    def enter(self, targets):
        return [Fight(self.player.hero, targets[0])]

    def legal_hand_target(self, target):
        if self.player.hero.legal_attack(target):
            return True
        return False


class ShadyConnections(Card):
    def aura(self):
        if self.location == self.player.tableau:
            if self.player.hero not in self.aura_list:
                self.aura_list.append(self.player.hero)
                self.player.income += self.amount
        else:
            for c in self.aura_list:
                c.income -= self.amount
            self.aura_list = []


class AttackStat(Card):
    def aura(self):
        if self.location == self.player.tableau:
            if self.player.hero not in self.aura_list:
                self.aura_list.append(self.player.hero)
                self.player.attack += self.amount
        else:
            for c in self.aura_list:
                c.attack -= self.amount
            self.aura_list = []


class HealthStat(Card):
    def aura(self):
        if self.location == self.player.tableau:
            if self.player.hero not in self.aura_list:
                self.aura_list.append(self.player.hero)
                self.player.health += self.amount
        else:
            for c in self.aura_list:
                c.health -= self.amount
            self.aura_list = []