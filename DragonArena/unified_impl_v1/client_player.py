import time
import sys
import os
import messaging
import protected
import random
sys.path.insert(1, os.path.join(sys.path[0], '../game-interface'))
from DragonArenaNew import Creature, Knight, Dragon, DragonArena


class Player:
    pass


class TickingPlayer(Player):
    """ Bogus player class that just spams request. solely for testing
    """

    @staticmethod
    def main_loop(protected_dragon_arena, my_id):
        assert isinstance(protected_dragon_arena,
                          protected.ProtectedDragonArena)
        print('ticking player main loop')
        try:
            while True:  # while game.playing
                print('tick')
                time.sleep(random.random())
                yield messaging.M_R_HEAL(my_id, my_id)
        except GeneratorExit:
            # clean up generator
            return


class HumanPlayer(Player):
    """ main_loop() is a generator that `yield`s request messages.
        (client outgoing thread is calling and will forward yielded messages)
    the game is over then the generator returns
    """

    @staticmethod
    def main_loop(protected_dragon_arena, my_id):
        assert isinstance(protected_dragon_arena,
                          protected.ProtectedDragonArena)
        # TODO implement. look at BotPlayer for inspiration
        raise NotImplemented


class BotPlayer(Player):

    @staticmethod
    def _choose_action_return_message(da, my_id):
        """ given the dragon arena 'da', make a decision on the next
        action for the bot to take. formulate this as a Message (request) from
        the set {MOVE, ATTACK, HEAL} and return it as your action
        """
        must_heal = filter(lambda k: k.get_hp() / float(k.max_hp()) < 0.5,
                           da.heal_candidates(my_id))
        if must_heal:
            yield messaging.M_R_HEAL(my_id, must_heal[0])
        can_attack = da.attack_candidates(my_id)
        if can_attack:
            yield messaging.M_R_ATTACK(my_id, can_attack[0])
        # else get moving

        dragon_locations = da.get_dragon_locations()

        def manhattan_distance(loc1, loc2):
            return abs(loc1[0] - loc2[0]) + abs(loc1[1] - loc2[1])

        def min_distance_to_dragon(loc):
            return reduce(min, map(lambda z: manhattan_distance(loc, z),
                                   dragon_locations))

        my_loc = x, y = da.get_location(my_id)

        current_min = min_distance_to_dragon(my_loc)

        adjacent = filter(da.is_valid_location,
                          [(x+1, y), (x-1, y), (x, y+1), (x, y-1)])

        with_dists = map(lambda z: (z, min_distance_to_dragon(z)),
                         adjacent)

        with_dists.sort(key=lambda z: z[1])

        available_improving = \
            filter(lambda t: da.is_not_occupied(t[0]) and t[1] < current_min,
                   with_dists)

        if available_improving:
            # we can improve by going to an available location
            yield messaging.M_R_MOVE(my_id, available_improving[0][1])
        else:
            # none of the available locations improve. try an improving
            # location that is occupied at the moment and hope for the best
            yield messaging.M_R_MOVE(my_id, with_dists[0][1])

    @staticmethod
    def main_loop(protected_dragon_arena, my_id):
        assert isinstance(protected_dragon_arena,
                          protected.ProtectedDragonArena)
        print('bot player main loop')
        print('my id', my_id)
        # has self._game_state_copy
        try:
            while True:  # while game.playing    # Roy: And I'm not dead?
                time.sleep(0.5)
                with protected_dragon_arena as da:
                    choice = BotPlayer._choose_action_return_message(da, my_id)
                # `with` expired. dragon arena unlocked
                yield choice
        except GeneratorExit:
            # clean up generator
            return
