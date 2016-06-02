
import random


def short_id(length):
    CHARSET = 'CDEHKMPRSTUWXY2458'
    get_character = CHARSET.__getitem__
    random_numbers = (random.randrange(len(CHARSET)) for i in range(length))
    return ''.join(map(get_character, random_numbers))
