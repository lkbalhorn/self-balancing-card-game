import csv

def SaveData(winner, loser):
    # Define Constants
    prop = 0.5
    popularity = 0.1
    with open('SBCCG_Card_Library.csv', 'r+', newline='') as card_library:
        card_library.seek(0)
        card_table = csv.reader(card_library, dialect='excel')
        new_rows = []
        winner_cards = [c.name for c in winner.Deck]
        loser_cards = [c.name for c in loser.Deck]
        for row in card_table:
            if '' not in row[:4]:  # First four columns have values = real entry
                new = row
                try:
                    new[8] = float(row[8])
                    # update handicaps for win and popularity.  Singles and doubles count equally - easier to calibrate
                    if row[0] in winner_cards:
                        new[8] += prop
                        new[8] += popularity
                    if row[0] in loser_cards:
                        new[8] -= prop
                        new[8] += popularity
                except ValueError:
                    pass
                finally:
                    new_rows.append(new)

        # Set average handicap to 5
        values = [row[8] for row in new_rows if '' not in row[:4]]
        average = sum(values)/len(values)
        for row in new_rows:
            if '' not in row[:4]:
                row[8] += (5 - average)

    # Overwrite csv
    with open('SBCCG_Card_Library.csv', 'w+', newline='') as card_library_writing:
        writer = csv.writer(card_library_writing, dialect='excel')
        writer.writerows(new_rows)

    # Edit Decklist Records
    deck_rows = []
    with open('SBCCG_Deck_List.csv', newline = '') as deck_file:
        deck_table = csv.reader(deck_file, dialect = 'excel')
        for row in deck_table:
            new_row = row
            ID = row[0]
            deckname = row[1]
            if deckname == winner.Deck.name:
                new_row[2] = int(new_row[2]) + 1
                # Baisian Stats
                new_row[4] = round(100*(int(new_row[2])+10)/
                                   (int(new_row[2])+int(new_row[3])+20),2)
            if deckname == loser.Deck.name:
                new_row[3] = int(new_row[3]) + 1
                new_row[4] = round(100*(int(new_row[2])+10)/
                                   (int(new_row[2])+int(new_row[3])+20),2)
            deck_rows.append(new_row)
    # Overwrite csv
    with open('SBCCG_Deck_List.csv','w', newline='') as deck_file_writing:
        writer = csv.writer(deck_file_writing, dialect = 'excel')
        writer.writerows(deck_rows)

