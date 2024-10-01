import os
from main import *
#import pygame as py
#from pygame.locals import *

def test_high_speed_collision():
    py.init()
    py.display.set_caption('2D LOS Sim')

    display = (200,800)

    screen = py.display.set_mode(display)

    controller = None

    drone = Drone(100, 0, controller)
    drone.WRAP = False
    platform = CollidableWall(100,700,100,35)

    all_sprites = py.sprite.Group()
    all_sprites.add(drone)
    all_sprites.add(platform)

    collidable_sprites = py.sprite.Group()
    collidable_sprites.add(platform)

    clock = py.time.Clock()
    fps = 60
    cycles_per_test = 100
    for k in range(10):
        passing = True
        i = 0
        drone.COLLISTION_DIVIDER = k + 1
        while passing:
            for q in range(35):
                drone.position = vector(100.0,100.0+float(q))
                drone.velocity = vector(0.0,float(i))
                drone.acceleration = vector(0.0,0.0)
                for j in range(100):
                    previous_position = drone.position.copy()
                    #clock.tick(fps)
                    drone.update_position(py.key.get_pressed(), collidable_sprites)
                    all_sprites.update()

                    screen.fill((180,180,180))
                    drone.render(screen)

                    all_sprites.draw(screen)

                    py.display.flip()
                    if drone.position.y < previous_position.y:
                        break
                    if j >= cycles_per_test - 1:
                        passing = False
            if not passing:
                logger.info("Using {} divider(s), failed at initial velocity: {:.2f}mph".format(k+1, i*2.2369362921))
            i += 1
        

test_high_speed_collision()