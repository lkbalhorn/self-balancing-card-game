from pygame.locals import *
from card import Card
from gameboard import *
import csv
from card import *
from LkGUI import *
from player_pc import *
from DeckChooser import *
import random
import collections

def RunDeckBuilder(window):
    # Similar to Play Game, this is structured as an independent program with its own main loop

    # Create main window
    # window = Window(1000,800,'Deck Builder','Huangshan_Valley.jpg')
    view = []

    # Load Card and Deck data
    card_dictionary = import_card_library()
    deck_dictionary = import_decks()

    # Create Card Objects
    cards = []
    Colors = ColorScheme()
    for row in card_dictionary:
        data = card_dictionary[row]
        c = load_card(data[0], None, card_dictionary)
        c.location = 'collection'
        if c.include:
            cards.append(c)
            c.location = 'collection'
            c.visible = True
            c.is_revealed = True
            c.is_hidden = False
            c.looks_hidden = True
            c.size = 'big'
            c.color = Colors[c.color_name]
            c.w = 195
            c.h = 260

    # Sort Cards by Color
    card_colors = set([c.color_name for c in cards])
    color_groups = {color: [] for color in card_colors}
    color_list = [i for i in card_colors]
    color_list.sort()
    color_list.remove('Neutral')
    color_list = ['Neutral'] + color_list
    for g in color_groups:
        color_groups[g] = [c for c in cards if c.color_name == g]

    # Sort Cards by Mana Cost first, Name second
    for key in color_groups:
        color_groups[key].sort(key = lambda x: x.name)
        color_groups[key].sort(key = lambda x: x.cost)

    # Create Buttons
    left_widgets = []
    for name in ['New Deck', 'Load Deck', 'Save Deck', 'Clear Deck', 'Cancel Changes', 'Delete Deck', 'Back']:
        new = Sprite(name=name, text=name, w=150, h=80, color=Colors['Wood'])
        view.append(new)
        left_widgets.append(new)
    deck_label = TextBox(name='Deck Label', text='Deck Name', w=350, h=50, color=Colors['Wood'], y=-500) # Starts Offscreen

    deck_summary = load_card('Wisp', None, card_dictionary)
    deck_summary.size = 'flat'
    deck_summary.color = Colors['Wood']
    deck_summary.name = 'Deck Summary'
    deck_summary.is_static = True

    # Set up pages
    page_turns = 0
    color_turns = 0
    cards_per_page = 8
    current_page = []
    old_page = []
    turn_direction = (0, 0)

    # Set up loop variables:
    keys_ready = True
    active_deck = None
    summary_font = pygame.font.SysFont("arial", 18)
    summary_images = []
    deck_contents = []
    change = 20
    window.carry_on = True


    # Main Loop ----------------------------------------------------------------------------------------- Main Loop
    while window.carry_on:

        # Part 1 - Check Inputs ------------------------------------------------------------------------- Check Inputs
        pos = pygame.mouse.get_pos()
        events = pygame.event.get()

        # Close or Resize the Window
        if window.upkeep(events):
            change = 20

        # Click Actions
        for event in events:
            if event.type == pygame.KEYDOWN:
                change = 20
            if event.type == pygame.MOUSEBUTTONDOWN:  # For button press animation
                change = 20
            if event.type == pygame.MOUSEBUTTONUP:
                change = 20
                # Get a list of clicked sprites under cursor
                clicked_items = [s for s in set(view + current_page + deck_contents) if s.collide(pos)]
                for c in clicked_items:
                    if c.name == 'New Deck':  # This is the New Deck button
                        active_deck = Deck(None)
                        active_deck.name = 'New Deck'
                        deck_label.text = 'New Deck'
                        deck_label.draw_image()
                        taken_IDs = [deck_dictionary[key][0] for key in deck_dictionary]
                        while active_deck.ID in taken_IDs:
                            active_deck.ID = '{:10.6f}'.format(random.random())
                    elif c.name == 'Load Deck' or c.name == 'Cancel Changes':  # Load Deck
                        if c.name == 'Load Deck':
                            new_ID = run_deck_chooser(window)
                        else:
                            new_ID = active_deck.ID
                        if new_ID is not None:
                            active_deck = Deck(None)
                            active_deck.ID = deck_dictionary[new_ID][0]
                            active_deck.name = deck_dictionary[new_ID][1]
                            new_contents = deck_dictionary[new_ID][6:]
                            new_contents = [i for i in new_contents if i in card_dictionary]
                            for name in new_contents:
                                n = load_card(name, None, card_dictionary)
                                if n:
                                    n.size = 'flat'
                                    active_deck.append(n)
                                    n.location = active_deck
                                    n.color = Colors[n.color_name]
                                    n.draw_image()
                            deck_label.text = active_deck.name
                            deck_label.draw_image()

                    elif c.name == 'Save Deck': # Save Deck
                        save_decklist(active_deck)
                    elif c.name == 'Clear Deck':  # Clear Deck
                        active_deck.contents = []
                    elif c.name == 'Delete Deck':
                        save_decklist(active_deck, delete=True)
                        active_deck = None
                    elif c.name == 'Deck Label':
                        c.toggle()
                        change = 10
                        if c.text != '':
                            active_deck.name = deck_label.text
                    elif c.name == 'Deck Summary':
                        pass

                    elif active_deck is not None and c.is_card:
                        if event.button == 1:  # Left Click:
                            c = load_card(c.name, None, card_dictionary)
                            c.size = 'flat'
                            if c.name in [i.name for i in active_deck.contents]:
                                c.is_static = True
                            active_deck.append(c)
                            c.location = active_deck
                            c.color = Colors[c.color_name]
                            c.draw_image()


                        if event.button == 3:  # Right Click:
                            # Remove a card with the same name from the deck, if present
                            for i in active_deck:
                                if c.name == i.name:
                                    active_deck.remove(i)
                                    break

                    elif c.name == 'Back':
                        window.carry_on = False

        deck_label.input_text(events)


        keys = pygame.key.get_pressed()
        if keys_ready:
            old_page = (color_turns, page_turns)
            if keys[pygame.K_UP]:
                color_turns = max(color_turns - 1, 0)
            if keys[pygame.K_DOWN]:
                color_turns = min(color_turns + 1, len(color_groups) - 1)
            if keys[pygame.K_RIGHT]:
                page_turns += 1
            if keys[pygame.K_LEFT]:
                page_turns = max(page_turns - 1, 0)
            while page_turns*cards_per_page >= len(color_groups[color_list[color_turns]]):
                page_turns -= 1
            turn_direction = (color_turns - old_page[0], page_turns - old_page[1])
        if keys[pygame.K_UP] or keys[pygame.K_DOWN] or keys[pygame.K_LEFT] or keys[pygame.K_RIGHT]:
            keys_ready = False
            change = 20
        else:
            keys_ready = True

        # Update Deck List and names
        if active_deck:
            active_deck.name = deck_label.text
        deck_dictionary = import_decks()

        # Visual Updates ----------------------------------------------------------------------- Visual Updates
        if change:
            # Position Cards on Current Page
            current_color = color_list[color_turns]
            old_page = list(current_page)
            current_page = (color_groups[current_color][0 + cards_per_page * page_turns: cards_per_page * (page_turns + 1)])
            align(current_page, 1, 250)
            distribute(current_page, 0, low=250, spacing=10)
            if len(current_page) > 4:
                align(current_page[4:], 1, 530)
                distribute(current_page[4:], 0, low=250, spacing=10)

            # Position Widgets
            align(left_widgets, 0, 150)
            distribute(left_widgets, 1, low=50, spacing=10)
            if active_deck is not None and deck_label not in view:
                view.append(deck_label)
                view.append(deck_summary)
            elif active_deck is None and deck_label in view:
                view.remove(deck_label)
                view.remove(deck_summary)

            # Update deck list on screen
            if active_deck is not None:
                deck_contents = active_deck.contents
                deck_contents.sort(key=lambda x: x.name)
                deck_contents.sort(key=lambda x: x.cost)
                # Stack Duplicates
                card_names = [c.name for c in deck_contents]
                for i in deck_contents:
                    i.quantity = 1
                for i in range(len(card_names) - 1):
                    if card_names[i] == card_names[i + 1]:
                        deck_contents[i+1].quantity += deck_contents[i].quantity
                        deck_contents[i].quantity = 0
                deck_contents = [i for i in deck_contents if i.quantity > 0]
                deck_contents = [deck_label, deck_summary] + deck_contents
                align(deck_contents, 0, window.w - 50, skew=1)
                distribute(deck_contents, 1, low=60, spacing=0.01)
            else:
                deck_contents = []

            # Update Deck Summary
            if active_deck is not None:
                deck_summary.cost = (
                    sum(i.cost for i in active_deck.contents) / len(active_deck.contents)
                    if active_deck.contents else 0)
                deck_summary.handicap = round(sum(i.handicap for i in active_deck.contents), 0)
                deck_summary.quantity = len(active_deck.contents)
                n_cards = 3 - (deck_summary.handicap - 150) / 20
                deck_summary.long_name = 'Starts with %1.1f Cards' % n_cards

            # Page Turn animations
            if turn_direction != (0, 0):
                shift = 500
                for i in current_page:
                    i.x = int(i.x_target + turn_direction[1] * shift)
                    i.y = int(i.y_target + turn_direction[0] * shift)
                for i in old_page:
                    i.x_target = int(i.x - turn_direction[1] * shift)
                    i.y_target = int(i.y - turn_direction[0] * shift)
                turn_direction = (0, 0)

            # Manage Spring Animations
            for i in current_page + deck_contents:
                if not i.is_static:
                    if change > 1:
                        i.x += (i.x_target - i.x) * 0.4
                        i.y += (i.y_target - i.y) * 0.4
                    else:
                        i.x = i.x_target
                        i.y = i.y_target

            # Apply Button Press Animation
            for i in view:
                if i.collide(pos) and pygame.mouse.get_pressed()[0]:
                    i.over_alpha = 100
                    i.over_fill = True
                    i.highlight = True
                    i.over_tint = shade(i.color, shade_fraction=0.25)
                else:
                    i.highlight = False

            # Draw items on screen
            window.quick_background('Huangshan_Valley.jpg')
            window.quick_draw((view + current_page + old_page + deck_contents), change=change)
            pygame.display.flip()

            change -= 1

        # Number of frames per secong e.g. 60
        window.clock.tick(60)

def save_decklist(active_deck, delete=False):
    import time
    deck_dictionary = import_decks()
    if active_deck is not None:
        if delete:
            del deck_dictionary[active_deck.ID]
        elif active_deck.ID in deck_dictionary:
            deck_dictionary[active_deck.ID][6:] = [c.name for c in active_deck.contents]
            deck_dictionary[active_deck.ID][1] = active_deck.name
        else:
            deck_dictionary[active_deck.ID] = [active_deck.ID, active_deck.name, 0, 0, 50, time.time()] + [c.name for c in active_deck.contents]
            deck_dictionary[active_deck.ID][1] = active_deck.name
        file_rows = [deck_dictionary[key] for key in deck_dictionary]
        with open('SBCCG_Deck_List.csv','w', newline='') as csvfile:
            writer = csv.writer(csvfile, dialect='excel')
            writer.writerows(file_rows)

def main():
    window = Window(1000, 800, 'SBCCG P1 View', 'Huangshan_Valley.jpg')
    RunDeckBuilder(window)


if __name__ == "__main__":
    main()