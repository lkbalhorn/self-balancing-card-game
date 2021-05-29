from sprite import *
import asyncio
import time
import os


class Window:
    # Does all the stuff you want done automatically in a visual presentation
    def __init__(self, w, h, title):
        # Set up visual display
        w = 1550
        h = 800

        self.w = w
        self.h = h
        self.xc = self.w / 2
        self.yc = self.h / 2 - 25

        os.environ['SDL_VIDEO_CENTERED'] = '1'  # You have to call this before pygame.init()
        pygame.init()
        self.screen = pygame.display.set_mode((self.w, self.h), pygame.RESIZABLE)
        pygame.display.set_caption(title)

        self.loop = asyncio.get_event_loop()
        self.exit_tasks = []

        self.carry_on = True  # Closes window or frame when false

        self.background_w = 1500
        self.background_h = 960

        self.sprite_images = {}  # Images stored by object ID allow sprites to be serialized and sent
        self.sprite_templates = {}
        self.sprite_artwork = {}
        self.sprite_traits = {}  # Stores key data by id number to determine if sprites need to be updated
        self.media_path = '..//media//'

        self.last_click = (0, (0, 0), 0)
        self.last_unclick = (0, (0, 0), 0)
        self.last_motion = (0, (0, 0), (0, 0), 0)
        self.last_pos = (0, 0)

        self.redraw = True
        self.sprite_positions = []

        self.delay = 1
        min_refresh = self.loop.create_task(self.min_refresh())
        self.exit_tasks.append(min_refresh)

        self.server = '127.00.00.01'
        self.port = '5678'
        self.inbox = []
        self.outbox = []
        self.connected = False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.carry_on = False
        pygame.display.quit()
        pygame.quit()
        self.loop.run_until_complete(self.wait_for_loop())
        self.loop.close()

    async def wait_for_loop(self):
        for item in self.exit_tasks:
            await item

    def get_inputs(self, view):
        pos = pygame.mouse.get_pos()
        events = pygame.event.get()
        hovered_ids = [s.id for s in view if s.collide(pos)]
        mouse = pygame.mouse.get_pressed()
        self.upkeep(events, pos)
        return events, hovered_ids, pos, mouse

    def update_screen(self, sprites, background):
        self.update_sprites(sprites)
        if self.redraw:
            self.draw_background(background)
            self.draw_sprites(sprites)
            pygame.display.flip()
            self.redraw = False

    def upkeep(self, events, pos):
        for event in events:
            if event.type == pygame.QUIT:
                self.carry_on = False
            elif event.type == VIDEORESIZE:
                self.screen = pygame.display.set_mode((event.w, event.h,),
                                                      pygame.RESIZABLE)
                self.w = pygame.display.Info().current_w
                self.h = pygame.display.Info().current_h
                self.xc = self.w / 2
                self.yc = self.h / 2 + 25
                self.redraw = True
            elif event.type == MOUSEBUTTONDOWN:
                self.last_click = (time.time(), pos, event.button)
            elif event.type == MOUSEBUTTONUP:
                self.last_unclick = (time.time(), pos, event.button)
            elif event.type == MOUSEMOTION:
                self.last_motion = (time.time(), pos, event.rel, event.buttons)
            self.last_pos = pos

    def draw_background(self, filename):
        self.screen.fill((0, 0, 0))
        image = self.load_artwork(filename, screen_size=True)  # Keeps archived, so the file is only loaded once
        if image:
            x, y = self.xc - image.get_width() / 2, 0
            self.screen.blit(image, (x, y))

    def draw_sprites(self, view):
        layered_sprites = sorted(view, key=lambda x: x.layer)
        for v in layered_sprites:
            if not v.host:
                self.screen.blit(self.sprite_images[v.id], (v.x, v.y))
                v.decorate(self.screen)
                # for s in v.subsprites:
                #     self.screen.blit(self.sprite_images[s.id], (v.x + s.x, v.y + s.y))

    def update_sprites(self, view):

        # Check if sprite positions have changed, and if so redraw screen
        sprite_positions = [(s.id, s.x, s.y, s.highlight, s.over_alpha) for s in view]
        if sprite_positions != self.sprite_positions:
            self.redraw = True
            self.sprite_positions = sprite_positions

        # Check if sprite key traits have changed, and if so redraw sprites
        for v in view:
            for s in v.subsprites + [v]:
                if s.id not in self.sprite_traits:
                    self.sprite_traits[s.id] = {}

                old_dict = self.sprite_traits[s.id]
                new_dict = {t: s.__dict__[t] for t in s.image_traits if hasattr(s, t)}
                if old_dict != new_dict:
                    # Redraw Image
                    artwork = self.load_artwork(s.filename) if hasattr(s, 'filename') else False
                    template = self.sprite_templates[s.id] if s.id in self.sprite_templates else False
                    if s.id not in self.sprite_templates:
                        if s.template_filename:
                            template = self.load_artwork(s.template_filename)
                        else:
                            self.sprite_templates[s.id] = False  # Serves as a placeholder, DrawImage will return a template
                    if s.subsprites:
                        extras = [self.sprite_images[i.id] for i in s.subsprites]
                    else: extras = []
                    self.sprite_images[s.id], self.sprite_templates[s.id] = s.draw_image(
                        artwork=artwork, template=template, extras=extras)

                    self.redraw = True
                    self.sprite_traits[s.id] = new_dict

    def load_artwork(self, filename, screen_size=False):
        # Checks archives for a file, and loads it if necessary.  Returns the image and stores it for later use.
        if not filename:
            return False
        if filename in self.sprite_artwork:
            return self.sprite_artwork[filename]
        if filename != '':
            try:
                image = pygame.image.load('..//media//' + filename)
                if screen_size:
                    image = pygame.transform.scale(image, (self.background_w, self.background_h))
                self.sprite_artwork[filename] = image
                return image
            except OSError:
                return False
        return False

    async def preload_artwork(self, filenames):
        for filename in filenames:
            if filename not in self.sprite_artwork and filename != '':
                try:
                    image = await pygame.image.load('..//media//' + filename)
                    image = pygame.transform.scale(image, (self.background_w, self.background_h))
                    self.sprite_artwork[filename] = image
                except Exception as e:
                    pass
            await asyncio.sleep(0.001)  # Pass back control

    async def min_refresh(self):
        while self.carry_on:
            await asyncio.sleep(self.delay)
            self.redraw = True

    def align_sprites(self, sprites, align_dim, align_ref, align_pos, align_skew,
                      dist_dim, dist_ref, low=0, center=0, high=0, spacing=0, fixed_size=False):
        if not sprites:
            return
        try:
            # Align Sprites
            for i in sprites:
                if align_dim == 0:
                    i.x_target = align_pos - i.w * align_skew + self.w * align_ref
                else:
                    i.y_target = align_pos - i.h * align_skew + self.h * align_ref

            # Distribute Sprites
            # Calculate Values
            if fixed_size:
                size_sum = fixed_size * len(sprites)
            elif dist_dim == 0:  # distribute along x
                size_sum = sum([i.w for i in sprites])
            else:
                size_sum = sum([i.h for i in sprites])
            n_sprites = len(sprites)

            if n_sprites > 1:
                if low and center:
                    high = 2 * center - low
                    spacing = (high - low - size_sum) / (n_sprites - 1)
                elif low and high:
                    center = (high + low) / 2
                    spacing = (high - low - size_sum) / (n_sprites - 1)
                elif center and high:
                    low = 2 * center - high
                    spacing = (high - low - size_sum) / (n_sprites - 1)
                elif low and spacing:
                    high = low + size_sum + spacing * (n_sprites - 1)
                    center = (high + low) / 2
                elif high and spacing:
                    low = high - size_sum - spacing * (n_sprites - 1)
                    center = (high + low) / 2
                else:
                    # Default to center and spacing since that makes the most sense
                    high = center + (size_sum + spacing * (n_sprites - 1)) / 2
                    low = 2 * center - high

            # Assign positions
            if dist_dim == 0:
                current_pos = low + self.w * dist_ref
                for i in sprites:
                    i.x_target = int(current_pos)
                    if fixed_size:
                        current_pos += (spacing + fixed_size)
                    else:
                        current_pos += (spacing + i.w)
            else:
                current_pos = low + self.h * dist_ref
                for i in sprites:
                    i.y_target = int(current_pos)
                    if fixed_size:
                        current_pos += (spacing + fixed_size)
                    else:
                        current_pos += (spacing + i.h)


            # Move static sprites to target position
            for i in sprites:
                if i.is_static and not i.host:
                    i.x = i.x_target
                    i.y = i.y_target

            # Spring Animation
            for i in sprites:
                if not i.is_static:
                    i.x = i.x + (i.x_target - i.x)

            # Move subsprites to target position
            for i in sprites:
                for j in i.subsprites:
                    j.x = j.x_target + j.host.x
                    j.y = j.y_target + j.host.y
                    j.layer = j.host.layer + 0.5
        except AttributeError as e:
            print('Error While Aligning', sprites)
            print(e)





