import zri

REQUIRES = []


def pile_xor(piles):
    x = 0
    for p in piles:
        x ^= p
    return x


def find_move(piles):
    ns = pile_xor(piles)
    if ns == 0:
        return None
    for i in range(len(piles)):
        target = piles[i] ^ ns
        if target < piles[i]:
            return [i, piles[i] - target]
    return None


def biggest(piles):
    best = 0
    for i in range(1, len(piles)):
        if piles[i] > piles[best]:
            best = i
    return best


def all_zero(piles):
    for p in piles:
        if p > 0:
            return False
    return True


def run():
    zri.init()

    while True:
        # Setup: enter pile count and sizes
        num = zri.get_digit(2, 9)
        piles = []
        for i in range(num):
            size = zri.get_digit(1, 9)
            piles.append(size)

        # Advise who should go first based on nim-sum
        if pile_xor(piles) != 0:
            zri.haptic_ready()
        else:
            zri.haptic_nack()
        performer_turn = zri.get_confirm()

        # Go dark for the performance
        zri.stealth()

        # Game loop
        while not all_zero(piles):
            if performer_turn:
                # Compute and signal optimal move via haptic
                move = find_move(piles)
                if move is not None:
                    pi, take = move
                else:
                    pi = biggest(piles)
                    take = 1
                    zri.haptic_nack()
                    zri.sleep_ms(300)

                zri.haptic_digit(pi + 1)
                zri.haptic_gap()
                zri.haptic_digit(take)

                zri.wait_press()
                piles[pi] -= take

                if all_zero(piles):
                    zri.haptic_ready()
                    zri.wait_press()
                    break

                performer_turn = False
            else:
                # Opponent's turn: enter their move
                while True:
                    p = zri.get_digit(1, len(piles)) - 1
                    if piles[p] > 0:
                        break
                    zri.haptic_nack()
                    zri.sleep_ms(400)

                took = zri.get_digit(1, piles[p])
                piles[p] -= took

                zri.stealth()

                if all_zero(piles):
                    zri.haptic_end()
                    zri.wait_press()
                    break

                performer_turn = True

        if not zri.get_confirm():
            break

    zri.done()
