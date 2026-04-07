import asyncio
import pygame
import sys

# Simple test to verify pygame-web works
async def main():
    pygame.init()
    screen = pygame.display.set_mode((480, 640))
    pygame.display.set_caption("Test")
    clock = pygame.time.Clock()
    
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
        
        screen.fill((0, 100, 200))  # Blue background
        pygame.draw.rect(screen, (0, 255, 0), (240, 320, 50, 50))  # Green square
        pygame.display.flip()
        clock.tick(60)
        await asyncio.sleep(0)

if __name__ == "__main__":
    asyncio.run(main())