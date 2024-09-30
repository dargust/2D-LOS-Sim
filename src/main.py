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
FPS = 60

WHITE = (255,255,255)
BLACK = (0  ,0  ,0  )

##OBJECTS
class CollidableWall(py.sprite.Sprite):
    def __init__(self, x, y, width, height):
        py.sprite.Sprite.__init__(self)
        self.position = vector(x,y)

        self.image = py.Surface((width,height))
        py.draw.rect(self.image, (0,0,0), (x,y,width,height))
        self.rect = self.image.get_rect()
        self.rect.center = (x,y)
        
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

        # Flags
        self.MAX_FORCE = 0
        self.RESET = False
        self.STOPPED = False

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

    def quad_collision_check(self, n, collision_sprites):
        """use n equidistant points between the previous position and new position"""
        start = self.pre_collision_position.copy()
        stop = self.position.copy()
        dir = start.angle_to(stop)
        mag = start.distance_to(stop)
        quad_step = mag / n
        unit_vector = vector(0,1)
        unit_vector.rotate_ip(dir)
        quad_step_vector = unit_vector * quad_step
        new_pos = self.pre_collision_position.copy()
        for i in range(n):
            new_pos = new_pos + quad_step_vector
            collided_sprites = py.sprite.spritecollide(self, collision_sprites, False)
            wall_collision_fudge = 1
            high_speed = self.velocity.magnitude() > 2
            resolution_speed = 0.7 if high_speed else 0
            if collided_sprites:
                for sprite in collided_sprites:
                    if sprite.rect.left - self.rect.width/2 < new_pos.x < sprite.rect.left + self.rect.width/2 and sprite.rect.bottom + wall_collision_fudge > new_pos.y > sprite.rect.top + wall_collision_fudge:
                        #if entering left wall
                        new_pos.x = sprite.rect.left - self.rect.width / 2
                        self.velocity.x *= -resolution_speed
                        self.velocity.y *= 0.8
                        return new_pos
                    elif sprite.rect.right + self.rect.width/2 > new_pos.x > sprite.rect.right - self.rect.width/2 and sprite.rect.bottom + wall_collision_fudge > new_pos.y > sprite.rect.top + wall_collision_fudge:
                        #if entering left wall
                        new_pos.x = sprite.rect.right + self.rect.width / 2
                        self.velocity.x *= -resolution_speed
                        self.velocity.y *= 0.8
                        return new_pos
                    elif sprite.rect.top - self.rect.height/2 < new_pos.y < sprite.rect.top + self.rect.height/2:
                        new_pos.y = sprite.rect.top - self.rect.height / 2
                        self.velocity.y *= -resolution_speed
                        self.velocity.x *= 0.8
                        return new_pos
                    elif sprite.rect.bottom + self.rect.height/2 > new_pos.y > sprite.rect.bottom - self.rect.height/2:
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
        if controller:
            Throttle = controller.get_axis(2)
            Yaw = controller.get_axis(3)
            Pitch = controller.get_axis(1)
            raw_roll = controller.get_axis(0)
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

        self.position = self.quad_collision_check(10, collision_sprites)

        if not self.STOPPED:
            self.acceleration -= self.velocity * self.F_FRICTION
            self.velocity += self.acceleration
            self.pre_collision_position = self.position.copy()
            self.position += self.velocity + 0.5 * self.acceleration

        if self.position.x > WIDTH+20:
            self.position.x = -10
        elif self.position.x < -20:
            self.position.x = WIDTH+10
        if self.position.y > HEIGHT+20:
            self.position.y = -10
        elif self.position.y < -20:
            self.position.y = HEIGHT-10

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

ui_manager = pygui.UIManager(display)
reset_button = pygui.elements.UIButton(relative_rect=py.Rect((10,10), (100,50)), text='Reset', manager=ui_manager)
rates_item_list = ["Betaflight","Actual(Na)"]
rates_type_selector = pygui.elements.UIDropDownMenu(relative_rect=py.Rect((110,10), (100,50)), options_list=rates_item_list, starting_option="Betaflight", expansion_height_limit=1000, manager=ui_manager)
rcRate_input = pygui.elements.UITextEntryLine(relative_rect=py.Rect((210,10), (100,50)), initial_text='1.5', manager=ui_manager)
rcSuperFactor_input = pygui.elements.UITextEntryLine(relative_rect=py.Rect((310,10), (100,50)), initial_text='0.5', manager=ui_manager)
rcExpo_input = pygui.elements.UITextEntryLine(relative_rect=py.Rect((410,10), (100,50)), initial_text='0.1', manager=ui_manager)
update_rates_button = pygui.elements.UIButton(relative_rect=py.Rect((510,10), (100,50)), text='Update Rates', manager=ui_manager)

allowed_chars = ["0","1","2","3","4","5","6","7","8","9","."]
rcRate_input.set_allowed_characters(allowed_chars)
rcSuperFactor_input.set_allowed_characters(allowed_chars)
rcExpo_input.set_allowed_characters(allowed_chars)

clock = py.time.Clock()

player_character = Drone(WIDTH/2,HEIGHT*0.75, controller)
landing_platform = CollidableWall(WIDTH/2, HEIGHT*0.9, WIDTH*0.8, 35)
#landing_platform2 = CollidableWall(WIDTH/2, HEIGHT*0.8+60, 80, 80)
collision_sprites.add(landing_platform)
#collision_sprites.add(landing_platform2)

if controller:
    L_controller_dot = StickDot("Left")
    R_controller_dot = StickDot("Right")
    all_sprites.add(L_controller_dot)
    all_sprites.add(R_controller_dot)
all_sprites.add(player_character)
all_sprites.add(landing_platform)
#all_sprites.add(landing_platform2)

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

    ##CAMERA

    ##RENDER
    screen.fill((180,180,180))
    player_character.render(screen)
    if controller:
        L_controller_dot.render(screen)
        R_controller_dot.render(screen)
    all_sprites.draw(screen)
    ui_manager.draw_ui(screen)
    py.display.flip()
    ##RENDER

logger.debug("QUITTING")
py.quit()