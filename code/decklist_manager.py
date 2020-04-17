import json
from gameboard import *

# Copy current decklist into JSON

deck_dictionary = import_decks()
print(deck_dictionary)

if False:
    output_dict = {}
    for key, data in deck_dictionary.items():
        output_dict[key] = {
            'id': key,
            'name': data[1],
            'wins': data[2],
            'losses': data[3],
            'strength': data[4],
            'last_access': data[5],
            'card_names': data[6:],
            'extra_card_names': []
        }
    for key, data in output_dict.items():
        print(data)

    with open('../csv/Decklist.txt', 'w') as outfile:
        json.dump(output_dict, outfile)

    with open('../csv/Decklist.txt', 'r') as infile:
        check = json.load(infile)

    for key, data in check.items():
        print(data)