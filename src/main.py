import pygame as py
from pygame.locals import *
import pygame_gui as pygui
vector = py.math.Vector2

import math

import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.propagate = True
logger.info("Logging level is set to {}".format(logging.getLevelName(logger.level)))
logger.debug("INIT")

WIDTH = 1600
HEIGHT = 900
WORLDWIDTH = 1600
WORLDHEIGHT = 900

FPS = 60

WHITE = (255,255,255)
BLACK = (0  ,0  ,0  )

##OBJECTS
def collided(sprite, other):
    return other.hitbox.colliderect(sprite.rect)

class CollidableWall(py.sprite.Sprite):
    def __init__(self, x, y, width, height):
        py.sprite.Sprite.__init__(self)
        self.position = vector(x,y)

        self.image = py.Surface((width,height))
        py.draw.rect(self.image, (0,0,0), (x,y,width,height))
        self.rect = self.image.get_rect()
        self.rect.center = (x,y)

        self.hitbox = self.rect.inflate(25, 25)

        #self.hitbox
        
    def update_position(self, x, y):
        pass

    def render(self, surface):
        pass

class Drone(py.sprite.Sprite):
    SETPOINT_RATE_LIMIT_MIN = -1998.0
    SETPOINT_RATE_LIMIT_MAX = 1998.0

    RC_RATE_INCREMENTAL = 14.54

    def __init__(self, x, y, controller):
        self.i = 0
        py.sprite.Sprite.__init__(self)
        self.image_original = py.image.load(r'src\Assets\Drone.png')
        self.image_original_scaled = py.transform.scale(self.image_original, (25,11))
        #self.image_original.fill((0,255,0))
        self.image = self.image_original_scaled.copy()
        self.rect = self.image.get_rect()
        self.rect.center = (x,y)

        self.controller = controller

        self.rate_method = "Betaflight"
        
        # Thrust kinematics for proppeller through air: F = .5 * r * A * [Ve ^2 - V0 ^2]
        # where F is total thrust
        # r is the air density
        # V0 is the velocity of the craft
        # Ve is the exit velocity of air coming from prop
        # A is propeller disk area

        # 2D kinematic definitions
        # Vectors
        self.reset_position = vector(x,y)
        self.pre_collision_position = vector(x,y)
        self.position = self.reset_position.copy()
        self.previous_position = self.position.copy()
        self.velocity = vector(0,0)
        self.acceleration = vector(0,0)
        self.angle = 0

        # Constants
        self.GRAVITY = 9.81/FPS
        self.F_EXIT_AIRSPEED = 8.5 * FPS#m/s
        self.F_FRICTION = 0.00915
        self.RATE = 300 / FPS
        self.RC_RATE = 1.5
        self.RC_SUPER = 0.5
        self.RC_EXPO = 0.1
        self.COLLISTION_DIVIDER = 5
        self.HIGH_SPEED_COLLISION_GATE = 0

        # Flags
        self.MAX_FORCE = 0
        self.RESET = False
        self.STOPPED = False
        self.WRAP = True

    def set_rate_method(self, method):
        self.rate_method = method

    def update_rates(self, rate, super, expo):
        self.RC_RATE = rate
        self.RC_SUPER = super
        self.RC_EXPO = expo

    def constrainf(self, amt, low, high):
        if amt < low:
            return low
        elif amt > high:
            return high
        else:
            return amt

    def applyBetaflightRates(self, rcCommandf, rcCommandfAbs):
        expof = self.RC_EXPO / 100.0
        rcCommandf = rcCommandf * math.pow(rcCommandfAbs,3) * expof + rcCommandf * (1 - expof)

        rcRate = self.RC_RATE / 100.0
        if rcRate > 2.0:
            rcRate += self.RC_RATE_INCREMENTAL * (rcRate - 2.0)
        angleRate = 200.0 * rcRate * rcCommandf
        
        rcSuperfactor = self.RC_SUPER / self.constrainf(1.0 - (rcCommandfAbs * (1.0 / 100.0)), 0.01, 1.0)
        angleRate *= rcSuperfactor

        return angleRate

    def applyActualRates(self, rcCommandf, rcCommandfAbs):
        expof = self.RC_EXPO / 100.0
        expof = rcCommandfAbs * (math.pow(rcCommandf, 5) * expof + rcCommandf * (1 - expof))

        centerSensitivity = self.RC_RATE * 10.0
        stickMovement = max(0, self.RC_SUPER * 10.0 - centerSensitivity)
        angleRate = rcCommandf * centerSensitivity + stickMovement * expof

        return angleRate
    
    def reset(self):
        self.RESET = True

    def quad_collision_check(self, collision_sprites):
        """use n equidistant points between the previous position and new position"""
        start = self.pre_collision_position.copy()
        stop = self.position.copy()
        dir = start.angle_to(stop)
        mag = start.distance_to(stop)
        quad_step = mag / self.COLLISTION_DIVIDER
        unit_vector = vector(0.0,1.0)
        unit_vector.rotate_ip(dir)
        quad_step_vector = unit_vector * quad_step
        new_pos = self.pre_collision_position.copy()
        for i in range(self.COLLISTION_DIVIDER):
            new_pos = new_pos + quad_step_vector
            collided_sprites = py.sprite.spritecollide(self, collision_sprites, False, collided)
            wall_collision_fudge = 1
            high_speed = self.velocity.magnitude() > self.HIGH_SPEED_COLLISION_GATE
            resolution_speed = 0.4 if high_speed else 0
            if collided_sprites:
                for sprite in collided_sprites:
                    self.mask = py.mask.from_surface(self.image)
                    collision_point = py.sprite.collide_mask(self,sprite)
                    if sprite.rect.left - self.rect.width/2 < new_pos.x < sprite.rect.left + self.rect.width/2 and self.velocity.x > 0 and sprite.rect.bottom + wall_collision_fudge > new_pos.y > sprite.rect.top + wall_collision_fudge and collision_point:
                        #if entering left wall
                        new_pos.x = sprite.rect.left - collision_point[0] / 2 #sprite.rect.left - self.rect.width / 2
                        self.velocity.x *= -resolution_speed
                        self.velocity.y *= 0.8
                        return new_pos
                    elif sprite.rect.right + self.rect.width/2 > new_pos.x > sprite.rect.right - self.rect.width/2 and self.velocity.x < 0 and sprite.rect.bottom + wall_collision_fudge > new_pos.y > sprite.rect.top + wall_collision_fudge and collision_point:
                        #if entering right wall
                        new_pos.x = sprite.rect.right + collision_point[0] + self.mask.centroid()[0]#sprite.rect.right + self.rect.width / 2
                        self.velocity.x *= -resolution_speed
                        self.velocity.y *= 0.8
                        return new_pos
                    elif sprite.rect.top - self.rect.height/2 < new_pos.y < sprite.rect.top + self.rect.height/2 and self.velocity.y > 0 and collision_point:
                        new_pos.y = sprite.rect.top - collision_point[1] / 2#sprite.rect.top - self.rect.height / 2
                        self.velocity.y *= -resolution_speed
                        self.velocity.x *= 0.8
                        return new_pos
                    elif sprite.rect.bottom + self.rect.height/2 > new_pos.y > sprite.rect.bottom - self.rect.height/2 and self.velocity.y < 0 and collision_point:
                        new_pos.y = sprite.rect.bottom + self.rect.height / 2
                        self.velocity.y *= -resolution_speed
                        self.velocity.x *= 0.8
                        return new_pos
        return self.position


    def update_position(self, pressed_keys, collision_sprites):
        if pressed_keys[K_UP] or pressed_keys[K_LEFT] or pressed_keys[K_RIGHT]:
            #print("hit")
            self.STOPPED = False
        self.previous_position = self.position.copy()
        if self.controller:
            Throttle = self.controller.get_axis(2)
            Yaw = self.controller.get_axis(3)
            Pitch = self.controller.get_axis(1)
            raw_roll = self.controller.get_axis(0)
            if self.rate_method == "Betaflight":
                Roll = self.applyBetaflightRates(raw_roll, abs(raw_roll)) * 6.6
            elif self.rate_method == "Actual":
                Roll = self.applyActualRates(raw_roll, abs(raw_roll)) * 6.6
        else:
            if pressed_keys[py.K_UP]:
                Throttle = 1.0
            else: Throttle = -1.0
            Yaw = 0.0
            Pitch = 0.0
            Roll = 0.0
        self.i += 1

        self.acceleration = vector(0,self.GRAVITY)
        F = 0
        accel = 0

        unit_vector = vector(0,1)
        unit_vector.rotate(self.angle)
        F = 0.5 * 1.2 * math.pi * 0.0042 * (self.F_EXIT_AIRSPEED + self.velocity.dot(unit_vector))
        if F > self.MAX_FORCE: self.MAX_FORCE = F
        accel = vector(0, F*4/0.54).rotate(-self.angle)

        self.acceleration = self.acceleration - (accel / 60) * ((Throttle+1)/2)
        if pressed_keys[py.K_LEFT]:
            self.angle += self.RATE
        if pressed_keys[py.K_RIGHT]:
            self.angle -= self.RATE
        self.angle += -Roll
        self.angle = self.angle % 360

        self.position = self.quad_collision_check(collision_sprites)

        if not self.STOPPED:
            self.acceleration -= self.velocity * self.F_FRICTION
            self.velocity += self.acceleration
            self.pre_collision_position = self.position.copy()
            self.position += self.velocity + 0.5 * self.acceleration

        if self.WRAP:
            if self.position.x > WIDTH:
                self.position.x = 0
            elif self.position.x < 0:
                self.position.x = WIDTH
            if self.position.y > HEIGHT:
                self.position.y = 0
            elif self.position.y < 0:
                self.position.y = HEIGHT

        if self.RESET:
            logger.debug("resetting from: {} at speed: {}".format(self.position, self.velocity))
            self.acceleration = vector(0,0)
            self.velocity = vector(0,0)
            self.position = self.reset_position.copy()
            self.angle = 0
            self.RESET = False


        if self.i >= 120:
            logger.debug("acceleration: {:.2f}ms-2,\tangle: {:.2f}m/s,\tspeed: {:.2f}mph,\tMax force: {:.2f}Kgms-2".format(accel.magnitude(), self.angle, self.velocity.magnitude()*2.2369362921, self.MAX_FORCE))
            #logger.debug("Roll: {}, Pitch: {}, Yaw: {}, Throttle: {}".format(Roll, Pitch, Yaw, Throttle))
            self.i = 0

    def render(self, surface):
        self.image = py.transform.rotate(self.image_original_scaled, self.angle)
        self.rect = self.image.get_rect(center=self.position)

class StickDot(py.sprite.Sprite):
    def __init__(self, left_right):
        py.sprite.Sprite.__init__(self)
        self.image = py.Surface((20,20))
        self.image.fill((255,255,255))
        self.image.set_colorkey((255,255,255))
        py.draw.circle(self.image, (0,0,0), (10,10), 10)
        self.rect = self.image.get_rect()

        self.position = vector(0,0)

        self.left_right = left_right
    
    def update_position(self, controller):
        offset_x = WIDTH - 200 if self.left_right == "Left" else 200
        offset_y = 200
        i = (0,1) if self.left_right == "Left" else (3,2)
        self.position.x = offset_x+controller.get_axis(i[0])*100
        self.position.y = 200+controller.get_axis(i[1])*100*-1
    
    def render(self, screen):
        offset_x = WIDTH - 300 if self.left_right == "Left" else 100
        offset_y = 100
        self.rect = self.image.get_rect(center=self.position)
        py.draw.rect(screen, (0,0,0), (offset_x-10,offset_y-10, 220,220), 2)   
##OBJECT

if __name__ == '__main__':
    ##INIT
    py.init()
    py.display.set_caption('2D LOS Sim')

    py.joystick.init()
    joysticks = [py.joystick.Joystick(x) for x in range(py.joystick.get_count())]
    if joysticks:
        controller = joysticks[0]
        controller.init()
    else:
        controller = None

    all_sprites = py.sprite.Group()
    collision_sprites = py.sprite.Group()

    display = (WIDTH,HEIGHT)

    screen = py.display.set_mode(display)

    background = py.Surface((WORLDWIDTH,WORLDHEIGHT))
    camera = vector(0,0)
    lock_camera = True

    ui_manager = pygui.UIManager(display)
    reset_button = pygui.elements.UIButton(relative_rect=py.Rect((10,10), (100,50)), text='Reset', manager=ui_manager)
    rates_item_list = ["Betaflight","Actual(Na)"]
    rates_type_selector = pygui.elements.UIDropDownMenu(relative_rect=py.Rect((110,10), (100,50)), options_list=rates_item_list, starting_option="Betaflight", expansion_height_limit=1000, manager=ui_manager)
    rcRate_input = pygui.elements.UITextEntryLine(relative_rect=py.Rect((210,10), (100,50)), initial_text='1.5', manager=ui_manager)
    rcSuperFactor_input = pygui.elements.UITextEntryLine(relative_rect=py.Rect((310,10), (100,50)), initial_text='0.5', manager=ui_manager)
    rcExpo_input = pygui.elements.UITextEntryLine(relative_rect=py.Rect((410,10), (100,50)), initial_text='0.1', manager=ui_manager)
    update_rates_button = pygui.elements.UIButton(relative_rect=py.Rect((510,10), (100,50)), text='Update Rates', manager=ui_manager)

    lock_camera_button = pygui.elements.UIButton(relative_rect=py.Rect((WIDTH-140,10), (130,50)), text='Unlock Camera', manager=ui_manager)

    allowed_chars = ["0","1","2","3","4","5","6","7","8","9","."]
    rcRate_input.set_allowed_characters(allowed_chars)
    rcSuperFactor_input.set_allowed_characters(allowed_chars)
    rcExpo_input.set_allowed_characters(allowed_chars)

    clock = py.time.Clock()

    player_character = Drone(WIDTH/2,HEIGHT*0.75, controller)
    landing_platform = CollidableWall(WIDTH/2, HEIGHT*0.9, WIDTH*0.8, 35)

    gate_1_L = CollidableWall(WIDTH-400, HEIGHT-400, 40, 40)
    gate_1_R = CollidableWall(WIDTH-200, HEIGHT-400, 40, 40)

    collision_sprites.add(landing_platform)
    collision_sprites.add(gate_1_L)
    collision_sprites.add(gate_1_R)

    if controller:
        L_controller_dot = StickDot("Left")
        R_controller_dot = StickDot("Right")
        all_sprites.add(L_controller_dot)
        all_sprites.add(R_controller_dot)
    all_sprites.add(player_character)
    all_sprites.add(landing_platform)
    all_sprites.add(gate_1_L)
    all_sprites.add(gate_1_R)

    done = False
    ##INIT

    ##GAMELOOP
    logger.debug("GAMELOOP")
    while(not done):
        time_delta = clock.tick(FPS)/1000.0

        ##EVENT HANDLER
        for event in py.event.get():
            if event.type == py.QUIT:
                done = True
            elif event.type == py.KEYUP:
                #logger.debug(event.unicode)
                if event.key == py.K_0:
                    player_character.reset()
            elif event.type == pygui.UI_BUTTON_PRESSED:
                if event.ui_element == reset_button:
                    player_character.reset()
                elif event.ui_element == update_rates_button:
                    new_rate = float(rcRate_input.get_text())
                    new_super = float(rcSuperFactor_input.get_text())
                    new_expo = float(rcExpo_input.get_text())
                    player_character.update_rates(new_rate, new_super, new_expo)
                    #logger.debug("UI Button Pressed")
                elif event.ui_element == lock_camera_button:
                    lock_camera = not lock_camera
                    lock_camera_button.set_text("Unlock Camera" if lock_camera else "Lock Camera")
            elif event.type == pygui.UI_DROP_DOWN_MENU_CHANGED:
                if event.ui_element == rates_type_selector:
                    player_character.set_rate_method(event.dict['text'])
            ui_manager.process_events(event)

        ui_manager.update(time_delta)
        ##EVENT HANDLER

        ##CONTROL POLL
        keys = py.key.get_pressed()
        ##CONTROL POLL

        ##PHYSICS
        player_character.update_position(keys, collision_sprites)
        if controller:
            L_controller_dot.update_position(controller)
            R_controller_dot.update_position(controller)
        all_sprites.update()
        ##PHYSICS

        ##CAMERA
        offset = vector(WIDTH/2,HEIGHT/2)
        camera = player_character.position.copy()
        ##CAMERA

        ##RENDER
        screen.fill((255,255,255))
        background.fill((180,180,180))
        player_character.render(background)
        if controller:
            L_controller_dot.render(background)
            R_controller_dot.render(background)
        all_sprites.draw(background)
        if lock_camera:
            screen.blit(background)
        else:
            screen.blit(background, -camera+offset)

            screen.blit(background, -camera+vector(offset.x,-offset.y)) #top
            screen.blit(background, -camera+vector(offset.x,+offset.y*3)) #bottom

            screen.blit(background, -camera+vector(-offset.x,offset.y)) #left
            screen.blit(background, -camera+vector(+offset.x*3,offset.y)) #right

            screen.blit(background, -camera+vector(-offset.x,-offset.y)) #top_left
            screen.blit(background, -camera+vector(+offset.x*3,-offset.y)) #top_right

            screen.blit(background, -camera+vector(-offset.x,offset.y*3)) #bottom_left
            screen.blit(background, -camera+vector(+offset.x*3,offset.y*3)) #bottom_right
        ui_manager.draw_ui(screen)
        py.display.flip()
        ##RENDER

    logger.debug("QUITTING")
    py.quit()