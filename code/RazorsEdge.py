from window import *
from game_menus import *

def main():
    with Window(1500, 800, "Razor's Edge") as window:
        menu = MainMenu(window)
        loop = window.loop
        loop.run_until_complete(async_main(window, menu, loop))


async def async_main(window, menu, loop):
    while window.carry_on:
        delay = loop.create_task(asyncio.sleep(1/60))
        page = menu.get_current_page()
        page.update_positions(window)
        events, hovered_objects, pos, mouse = window.get_inputs(page.view())
        page.process_inputs(events, hovered_objects, pos, mouse)

        menu.client.manage_connection(loop)
        page.manage_connection(loop)
        page.play_snapshots(loop)
        page.update_positions(window)
        page.upkeep()

        window.update_sprites(page.view())
        if window.redraw:
            window.draw_background((page.background, 255))
            window.draw_sprites(page.view())
            pygame.display.flip()
            window.redraw = False

        await delay

    t1 = loop.create_task(menu.client.terminate(loop))
    await t1
    gameplay_logger.info('Program Closed \n\n')

if __name__ == "__main__":
    main()