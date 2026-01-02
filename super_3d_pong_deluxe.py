from OpenGL.GL import *
from OpenGL. GLUT import *
from OpenGL.GLU import *
import math
import random
import sys
import time


# ============================================================
#                     GAME SETTINGS
# ============================================================

# Window size
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600

# Playing field size
FIELD_WIDTH = 400
FIELD_DEPTH = 800

# Paddle settings
PADDLE_WIDTH = 80
PADDLE_HEIGHT = 15
PADDLE_DEPTH = 15

# Ball settings
BALL_SIZE = 8

# Game rules
POINTS_TO_WIN = 11
DASH_COOLDOWN_TIME = 120

# Movement speeds
NORMAL_SPEED = 6
DASH_SPEED = 14

# Colors (Red, Green, Blue)
COLOR_PLAYER_1 = [0.0, 1.0, 1.0]      # Cyan
COLOR_PLAYER_2 = [1.0, 0.0, 0.33]     # Pink
COLOR_BALL = [1.0, 1.0, 1.0]          # White
COLOR_GRID = [0.1, 0.1, 0.2]          # Dark blue
COLOR_GIANT_POWERUP = [1.0, 0.84, 0.0] # Gold
COLOR_MULTI_POWERUP = [0.0, 1.0, 0.0]  # Green
COLOR_ON_FIRE = [1.0, 0.6, 0.0]       # Orange

# Timer 
last_frame_time = time. time()
FRAME_TIME = 16 / 1000  # 16ms in seconds

# ============================================================
#                     GAME DATA
# ============================================================

game = {
    # Game state
    "state": "MENU",           # MENU, PLAYING, or GAME_OVER
    "is_two_player":  False,
    "is_paused": False,
    "winner": None,
    
    # Input
    "keys_pressed": set(),
    
    # Camera
    "camera_mode": 0,          # 0=Side, 1=Top, 2=FirstPerson
    "screen_shake": 0,
    
    # Players (will be set by create_player)
    "player_1": None,
    "player_2":  None,
    
    # Game objects (lists)
    "balls": [],
    "particles": [],
    "floating_texts": [],
    "powerup": None,
    
    # Stats
    "rally_count": 0,
    "frame_count": 0,
}


# ============================================================
#                     CREATE FUNCTIONS
# ============================================================

def create_player(player_number):
    """Create a new player dictionary"""
    
    # Player 1 starts at near end, Player 2 at far end
    if player_number == 1:
        z_position = -FIELD_DEPTH / 2 + 40
    else:
        z_position = FIELD_DEPTH / 2 - 40
    
    return {
        "number": player_number,
        "x": 0,
        "z": z_position,
        "width":  PADDLE_WIDTH,
        "score": 0,
        "win_streak": 0,
        "dash_cooldown": 0,
        "is_giant": False,
        "giant_time_left": 0,
    }


def create_ball(serving_player):
    """Create a new ball dictionary"""
    
    # Ball starts near the serving player
    if serving_player == 1:
        z_position = -FIELD_DEPTH / 2 + 100
        direction = 1    # Move towards Player 2
    else:
        z_position = FIELD_DEPTH / 2 - 100
        direction = -1   # Move towards Player 1
    
    return {
        "x": 0,
        "y":  BALL_SIZE,
        "z": z_position,
        "speed_x": (random.random() - 0.5) * 6,
        "speed_z": direction * 9.0,
        "color": COLOR_BALL,
        "trail": [],
    }


def create_particle(x, z, color):
    """Create a single particle for visual effects"""
    return {
        "x": x,
        "y": 10,
        "z": z,
        "speed_x": (random.random() - 0.5) * 8,
        "speed_y": random.random() * 5 + 2,
        "speed_z": (random.random() - 0.5) * 8,
        "color": color,
        "life": random.randint(20, 50),
    }


def create_floating_text(text, x, z, color, size=1.0):
    """Create floating text that rises and fades"""
    return {
        "text": text,
        "x":  x,
        "y": 20,
        "z": z,
        "color": color,
        "size": size,
        "life": 60,
    }


def create_powerup():
    """Create a powerup at a random position"""
    
    # Random position in middle of field
    x = (random.random() - 0.5) * FIELD_WIDTH * 0.8
    z = (random.random() - 0.5) * FIELD_DEPTH * 0.5
    
    # Random type
    if random.random() > 0.5:
        powerup_type = "GIANT"
    else:
        powerup_type = "MULTIBALL"
    
    return {
        "x": x,
        "z": z,
        "type": powerup_type,
        "rotation": 0,
    }


# ============================================================
#                     PLAYER FUNCTIONS
# ============================================================

def move_player_left(player, speed):
    """Move paddle left visually (affected by camera)"""
    if game["camera_mode"] == 2:
        player["x"] += speed
    else:
        player["x"] -= speed
    keep_player_in_bounds(player)


def move_player_right(player, speed):
    """Move paddle right visually (affected by camera)"""
    if game["camera_mode"] == 2:
        player["x"] -= speed
    else:
        player["x"] += speed
    keep_player_in_bounds(player)


def move_player_towards(player, target_x, speed):
    """Move paddle towards a target x position (for AI)"""
    if player["x"] < target_x - 10:
        player["x"] += speed
    elif player["x"] > target_x + 10:
        player["x"] -= speed
    keep_player_in_bounds(player)


def keep_player_in_bounds(player):
    """Make sure player doesn't go outside the field"""
    
    left_limit = -FIELD_WIDTH / 2 + player["width"] / 2
    right_limit = FIELD_WIDTH / 2 - player["width"] / 2
    
    if player["x"] < left_limit: 
        player["x"] = left_limit
    
    if player["x"] > right_limit:
        player["x"] = right_limit


def try_player_dash(player):
    """Try to use dash.  Returns True if successful."""
    
    if player["dash_cooldown"] == 0:
        player["dash_cooldown"] = DASH_COOLDOWN_TIME
        return True
    
    return False


def update_player(player):
    """Update player state each frame"""
    
    # Count down dash cooldown
    if player["dash_cooldown"] > 0:
        player["dash_cooldown"] -= 1
    
    # Count down giant powerup
    if player["is_giant"]:
        player["giant_time_left"] -= 1
        if player["giant_time_left"] <= 0:
            player["is_giant"] = False
    
    # Smoothly change paddle width
    if player["is_giant"]:
        target_width = PADDLE_WIDTH * 1.5
    else:
        target_width = PADDLE_WIDTH
    
    # Gradual size change (10% per frame)
    player["width"] = player["width"] + (target_width - player["width"]) * 0.1


def make_player_giant(player):
    """Give player the giant paddle powerup"""
    player["is_giant"] = True
    player["giant_time_left"] = 600  # About 10 seconds


def get_player_color(player):
    """Get the color for a player's paddle"""
    
    # Orange if on a hot streak
    if player["win_streak"] >= 3:
        return COLOR_ON_FIRE
    
    # Otherwise, their normal color
    if player["number"] == 1:
        return COLOR_PLAYER_1
    else:
        return COLOR_PLAYER_2


# ============================================================
#                     BALL FUNCTIONS
# ============================================================

def move_ball(ball):
    """Move the ball one step"""
    
    # Save position for trail effect
    ball["trail"].append((ball["x"], ball["y"], ball["z"]))
    
    # Keep trail short (max 12 positions)
    if len(ball["trail"]) > 12:
        ball["trail"].pop(0)
    
    # Move ball by its speed
    ball["x"] += ball["speed_x"]
    ball["z"] += ball["speed_z"]


def check_ball_wall_bounce(ball):
    """Check if ball hit a side wall.  Returns True if it bounced."""
    
    left_wall = -FIELD_WIDTH / 2 + BALL_SIZE
    right_wall = FIELD_WIDTH / 2 - BALL_SIZE
    
    if ball["x"] < left_wall or ball["x"] > right_wall:
        ball["speed_x"] *= -1  # Reverse direction
        return True
    
    return False


def check_ball_paddle_hit(ball, player):
    """Check if ball hit a player's paddle. Returns True if hit."""
    
    # Check if ball is at the paddle's depth (z position)
    ball_front = ball["z"] - BALL_SIZE
    ball_back = ball["z"] + BALL_SIZE
    paddle_front = player["z"] - PADDLE_DEPTH
    paddle_back = player["z"] + PADDLE_DEPTH
    
    at_paddle_depth = (ball_front < paddle_back) and (ball_back > paddle_front)
    
    # Check if ball is within paddle width (x position)
    distance_from_center = abs(ball["x"] - player["x"])
    hit_range = player["width"] / 2 + BALL_SIZE
    within_paddle = distance_from_center < hit_range
    
    # Did it hit? 
    if at_paddle_depth and within_paddle:
        
        # Bounce the ball
        if player["number"] == 1:
            # Hit by Player 1: send towards Player 2
            ball["speed_z"] = abs(ball["speed_z"]) * 1.05
        else:
            # Hit by Player 2: send towards Player 1
            ball["speed_z"] = -abs(ball["speed_z"]) * 1.05
        
        # Add spin based on where it hit the paddle
        hit_offset = (ball["x"] - player["x"]) / (player["width"] / 2)
        ball["speed_x"] += hit_offset * 4
        
        return True
    
    return False


def is_ball_past_player_1(ball):
    """Check if ball went past Player 1 (Player 2 scores)"""
    return ball["z"] < -FIELD_DEPTH / 2 - 50


def is_ball_past_player_2(ball):
    """Check if ball went past Player 2 (Player 1 scores)"""
    return ball["z"] > FIELD_DEPTH / 2 + 50


# ============================================================
#                     POWERUP FUNCTIONS
# ============================================================

def update_powerup(powerup):
    """Make the powerup spin"""
    powerup["rotation"] += 2


def get_powerup_color(powerup):
    """Get powerup color based on type"""
    
    if powerup["type"] == "GIANT":
        return COLOR_GIANT_POWERUP
    else:
        return COLOR_MULTI_POWERUP


def is_ball_touching_powerup(ball, powerup):
    """Check if a ball is touching the powerup"""
    
    # Calculate distance between ball and powerup
    dx = ball["x"] - powerup["x"]
    dz = ball["z"] - powerup["z"]
    distance = math. sqrt(dx * dx + dz * dz)
    
    return distance < 25 + BALL_SIZE


# ============================================================
#                     PARTICLE & TEXT FUNCTIONS
# ============================================================

def update_particle(particle):
    """Move a particle and apply gravity"""
    
    particle["x"] += particle["speed_x"]
    particle["y"] += particle["speed_y"]
    particle["z"] += particle["speed_z"]
    
    # Gravity pulls it down
    particle["speed_y"] -= 0.5
    
    # Reduce life
    particle["life"] -= 1


def is_particle_dead(particle):
    """Check if particle should disappear"""
    return particle["life"] <= 0


def update_floating_text(text):
    """Make text float upward"""
    text["y"] += 1
    text["life"] -= 1


def is_text_dead(text):
    """Check if text should disappear"""
    return text["life"] <= 0


# ============================================================
#                     HELPER FUNCTIONS
# ============================================================

def add_particles_at(x, z, color, count=10):
    """Create a burst of particles at a position"""
    
    for i in range(count):
        particle = create_particle(x, z, color)
        game["particles"].append(particle)


def add_floating_text_at(text, x, z, color, size=1.0):
    """Show floating text at a position"""
    
    floating_text = create_floating_text(text, x, z, color, size)
    game["floating_texts"].append(floating_text)


def spawn_ball(serving_player):
    """Add a new ball to the game"""
    
    ball = create_ball(serving_player)
    game["balls"].append(ball)


def maybe_spawn_powerup():
    """Maybe spawn a powerup (small random chance)"""
    
    # Only spawn if there isn't one already
    if game["powerup"] is not None:
        return
    
    # 0.2% chance per frame
    if random.random() < 0.002:
        game["powerup"] = create_powerup()


# ============================================================
#                     GAME CONTROL FUNCTIONS
# ============================================================

def reset_game():
    """Reset game to menu state"""
    
    game["state"] = "MENU"
    game["is_two_player"] = False
    game["is_paused"] = False
    game["winner"] = None
    game["keys_pressed"] = set()
    game["camera_mode"] = 0
    game["screen_shake"] = 0
    game["player_1"] = create_player(1)
    game["player_2"] = create_player(2)
    game["balls"] = []
    game["particles"] = []
    game["floating_texts"] = []
    game["powerup"] = None
    game["rally_count"] = 0
    game["frame_count"] = 0


def start_game(two_player_mode):
    """Start a new game"""
    
    reset_game()
    game["is_two_player"] = two_player_mode
    game["state"] = "PLAYING"
    spawn_ball(1)  # Player 1 serves first


def score_point(winner_number, ball):
    """Handle when a player scores a point"""
    
    # Remove the ball that went out
    if ball in game["balls"]:
        game["balls"].remove(ball)
    
    # Screen shake! 
    game["screen_shake"] = 30
    
    # Update scores
    if winner_number == 1:
        game["player_1"]["score"] += 1
        game["player_1"]["win_streak"] += 1
        game["player_2"]["win_streak"] = 0
        
        # Show "on fire" message for hot streak
        if game["player_1"]["win_streak"] == 3:
            add_floating_text_at("P1 FIRE!", 0, -200, COLOR_PLAYER_1, 2.0)
    else:
        game["player_2"]["score"] += 1
        game["player_2"]["win_streak"] += 1
        game["player_1"]["win_streak"] = 0
        
        if game["player_2"]["win_streak"] == 3:
            add_floating_text_at("P2 FIRE!", 0, 200, COLOR_PLAYER_2, 2.0)
    
    # Check for winner
    if game["player_1"]["score"] >= POINTS_TO_WIN:
        game["state"] = "GAME_OVER"
        game["winner"] = 1
        return
    
    if game["player_2"]["score"] >= POINTS_TO_WIN:
        game["state"] = "GAME_OVER"
        game["winner"] = 2
        return
    
    # Spawn new ball if no balls left (loser serves)
    if len(game["balls"]) == 0:
        game["rally_count"] = 0
        
        if winner_number == 1:
            spawn_ball(2)  # Player 2 serves
        else:
            spawn_ball(1)  # Player 1 serves


# ============================================================
#                     INPUT HANDLING
# ============================================================

def handle_player_1_input():
    """Move Player 1 based on keyboard input"""
    
    player = game["player_1"]
    speed = NORMAL_SPEED
    
    # Check for dash (Q key)
    if "q" in game["keys_pressed"]:
        if try_player_dash(player):
            speed = DASH_SPEED
            add_floating_text_at("DASH!", player["x"], player["z"], COLOR_PLAYER_1, 0.8)
    
    # Move left (A key)
    if "a" in game["keys_pressed"]:
        move_player_left(player, speed)
    
    # Move right (D key)
    if "d" in game["keys_pressed"]:
        move_player_right(player, speed)


def handle_player_2_input():
    """Move Player 2 (human or AI)"""
    
    player = game["player_2"]
    speed = NORMAL_SPEED
    
    if game["is_two_player"]:
        # Human controls
        handle_player_2_human(player, speed)
    else:
        # AI controls
        handle_player_2_ai(player, speed)


def handle_player_2_human(player, speed):
    """Handle human input for Player 2"""
    
    # Check for dash (Enter key)
    if "\r" in game["keys_pressed"]:
        if try_player_dash(player):
            speed = DASH_SPEED
            add_floating_text_at("DASH!", player["x"], player["z"], COLOR_PLAYER_2, 0.8)
    
    # Arrow keys (stored as numbers)
    LEFT_ARROW = 100
    RIGHT_ARROW = 102
    
    if LEFT_ARROW in game["keys_pressed"]:
        move_player_left(player, speed)
    
    if RIGHT_ARROW in game["keys_pressed"]:
        move_player_right(player, speed)


def handle_player_2_ai(player, speed):
    """AI Logic that tries to hit the ball"""
    
    # Default: go to center
    target_x = 0
    
    # Find balls coming towards Player 2
    incoming_balls = []
    for ball in game["balls"]:
        if ball["speed_z"] > 0:  # Moving towards Player 2
            incoming_balls.append(ball)
    
    # Track the closest incoming ball
    if len(incoming_balls) > 0:
        # Find closest ball
        closest_ball = incoming_balls[0]
        for ball in incoming_balls:
            if abs(ball["z"] - player["z"]) < abs(closest_ball["z"] - player["z"]):
                closest_ball = ball
        
        # Add some error so AI isn't perfect
        error = math.sin(game["frame_count"] * 0.05) * 40
        target_x = closest_ball["x"] + error
    
    # Move towards target (slightly slower than human)
    ai_speed = speed * 0.8
    
    move_player_towards(player, target_x, ai_speed)

# ============================================================
#                     MAIN UPDATE FUNCTION
# ============================================================

def update_game():
    """Update everything (called every frame)"""
    
    # Only update when playing and not paused
    if game["state"] != "PLAYING": 
        return
    
    if game["is_paused"]: 
        return
    
    game["frame_count"] += 1
    
    # Update players
    handle_player_1_input()
    handle_player_2_input()
    update_player(game["player_1"])
    update_player(game["player_2"])
    
    # Update balls
    update_all_balls()
    
    # Update powerups
    maybe_spawn_powerup()
    update_powerup_collision()
    
    # Multiball mayhem at 5 hits! 
    check_mayhem_trigger()
    
    # Update visual effects
    update_all_effects()


def update_all_balls():
    """Update all balls in the game"""
    
    # Make a copy of list to safely remove items
    balls_copy = game["balls"][:]
    
    for ball in balls_copy:
        move_ball(ball)
        
        # Check wall bounce
        if check_ball_wall_bounce(ball):
            game["screen_shake"] = 5
        
        # Check paddle hits
        if check_ball_paddle_hit(ball, game["player_1"]):
            game["rally_count"] += 1
            game["screen_shake"] = 10
            add_particles_at(ball["x"], ball["z"], COLOR_PLAYER_1)
            add_floating_text_at("SMASH!", ball["x"], ball["z"], COLOR_PLAYER_1)
        
        if check_ball_paddle_hit(ball, game["player_2"]):
            game["rally_count"] += 1
            game["screen_shake"] = 10
            add_particles_at(ball["x"], ball["z"], COLOR_PLAYER_2)
            add_floating_text_at("SMASH!", ball["x"], ball["z"], COLOR_PLAYER_2)
        
        # Check scoring
        if is_ball_past_player_1(ball):
            score_point(2, ball)  # Player 2 scores
        elif is_ball_past_player_2(ball):
            score_point(1, ball)  # Player 1 scores


def update_powerup_collision():
    """Check if any ball touched the powerup"""
    
    if game["powerup"] is None: 
        return
    
    update_powerup(game["powerup"])
    
    for ball in game["balls"]: 
        if is_ball_touching_powerup(ball, game["powerup"]):
            
            # Who gets it?  Whoever hit the ball last
            if ball["speed_z"] > 0:
                owner = game["player_1"]
            else:
                owner = game["player_2"]
            
            # Apply the powerup
            powerup = game["powerup"]
            
            if powerup["type"] == "GIANT":
                make_player_giant(owner)
                add_floating_text_at("GIANT!", powerup["x"], powerup["z"], COLOR_GIANT_POWERUP, 1.5)
            else:
                # Multiball:  spawn another ball
                if ball["speed_z"] > 0:
                    spawn_ball(1)
                else:
                    spawn_ball(2)
                add_floating_text_at("MULTIBALL!", powerup["x"], powerup["z"], COLOR_MULTI_POWERUP, 1.5)
            
            game["screen_shake"] = 20
            game["powerup"] = None
            break


def check_mayhem_trigger():
    """Trigger multiball mayhem at 5 rally hits"""
    
    if game["rally_count"] == 5 and len(game["balls"]) == 1:
        # Spawn ball going same direction
        if game["balls"][0]["speed_z"] > 0:
            spawn_ball(1)
        else:
            spawn_ball(2)
        
        add_floating_text_at("MAYHEM!", 0, 0, [1, 0, 1], 2.0)
        
        # Prevent triggering again
        game["rally_count"] += 1


def update_all_effects():
    """Update particles and floating text"""
    
    # Reduce screen shake
    game["screen_shake"] *= 0.9
    
    # Update particles
    particles_copy = game["particles"][:]
    for particle in particles_copy: 
        update_particle(particle)
        if is_particle_dead(particle):
            game["particles"].remove(particle)
    
    # Update floating texts
    texts_copy = game["floating_texts"][:]
    for text in texts_copy:
        update_floating_text(text)
        if is_text_dead(text):
            game["floating_texts"]. remove(text)


# ============================================================
#                     DRAWING FUNCTIONS
# ============================================================

def draw_box(x, y, z, width, height, depth, color):
    """Draw a 3D box"""
    
    glPushMatrix()
    glTranslatef(x, y, z)
    glScalef(width, height, depth)
    glColor3fv(color)
    glutSolidCube(1.0)
    glPopMatrix()


def draw_sphere(x, y, z, radius, color):
    """Draw a 3D sphere"""
    
    glPushMatrix()
    glTranslatef(x, y, z)
    glColor3fv(color)
    glutSolidSphere(radius, 12, 12)
    glPopMatrix()


def draw_text_3d(x, y, z, text, color):
    """Draw text in 3D space"""
    
    glColor3fv(color)
    glRasterPos3f(x, y, z)
    for char in text:
        glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(char))


def draw_text_2d(x, y, text, color, font=GLUT_BITMAP_HELVETICA_18):
    """Draw text on screen (2D)"""
    
    glColor3fv(color)
    glRasterPos2f(x, y)
    for char in text: 
        glutBitmapCharacter(font, ord(char))


def draw_floor_grid():
    """Draw the playing field grid"""
    
    glLineWidth(1)
    glBegin(GL_LINES)
    glColor3fv(COLOR_GRID)
    
    # Vertical lines
    for x in range(-FIELD_WIDTH // 2, FIELD_WIDTH // 2 + 1, 50):
        glVertex3f(x, 0, -FIELD_DEPTH // 2)
        glVertex3f(x, 0, FIELD_DEPTH // 2)
    
    # Horizontal lines
    for z in range(-FIELD_DEPTH // 2, FIELD_DEPTH // 2 + 1, 50):
        glVertex3f(-FIELD_WIDTH // 2, 0, z)
        glVertex3f(FIELD_WIDTH // 2, 0, z)
    
    glEnd()


def draw_ball_with_trail(ball):
    """Draw a ball with its motion trail"""
    
    # Shadow on ground
    glPushMatrix()
    glTranslatef(ball["x"], 1, ball["z"])
    glScalef(1, 0.1, 1)
    glColor3f(0, 0, 0)
    glutSolidSphere(BALL_SIZE, 8, 8)
    glPopMatrix()
    
    # The ball
    draw_sphere(ball["x"], ball["y"], ball["z"], BALL_SIZE, ball["color"])
    
    # Trail
    if len(ball["trail"]) > 0:
        glLineWidth(2)
        glBegin(GL_LINE_STRIP)
        for i, position in enumerate(ball["trail"]):
            alpha = i / len(ball["trail"])
            glColor4f(ball["color"][0], ball["color"][1], ball["color"][2], alpha)
            glVertex3f(position[0], position[1], position[2])
        glEnd()


def draw_all_particles():
    """Draw all particles"""
    
    glPointSize(3)
    glBegin(GL_POINTS)
    for particle in game["particles"]:
        glColor3fv(particle["color"])
        glVertex3f(particle["x"], particle["y"], particle["z"])
    glEnd()


def draw_dash_bar(x, y, player, color):
    """Draw a player's dash cooldown bar"""
    
    bar_width = 100
    fill_percent = 1.0 - (player["dash_cooldown"] / DASH_COOLDOWN_TIME)
    
    glColor3fv(color)
    glBegin(GL_QUADS)
    glVertex2f(x, y)
    glVertex2f(x + bar_width * fill_percent, y)
    glVertex2f(x + bar_width * fill_percent, y - 10)
    glVertex2f(x, y - 10)
    glEnd()

def draw_menu_screen():
    """Draw the main menu"""
    
    draw_text_2d(WINDOW_WIDTH/2 - 100, WINDOW_HEIGHT/2 + 100,
                 "SUPER 3D PONG DELUXE", [1, 1, 1], GLUT_BITMAP_TIMES_ROMAN_24)
    
    draw_text_2d(WINDOW_WIDTH/2 - 80, WINDOW_HEIGHT/2 + 50,
                 "Press 1:  Single Player", [1, 1, 1])
    
    draw_text_2d(WINDOW_WIDTH/2 - 80, WINDOW_HEIGHT/2 + 20,
                 "Press 2: PvP Local", [1, 1, 1])
    
    draw_text_2d(50, 120,
                 "Controls:", [1, 1, 1])
    
    draw_text_2d(50, 95,
                 "Player 1: A/D to move, Q to dash", [0.7, 0.7, 0.7])
    
    draw_text_2d(50, 70,
                 "Player 2: Arrow keys, Enter to dash", [0.7, 0.7, 0.7])
    
    draw_text_2d(50, 45,
                 "C = Change camera    ESC = Pause", [0.7, 0.7, 0.7])

def draw_game_over_screen():
    """Draw the game over screen"""
    
    # Winner color
    if game["winner"] == 1:
        color = COLOR_PLAYER_1
    else:
        color = COLOR_PLAYER_2
    
    draw_text_2d(WINDOW_WIDTH/2 - 80, WINDOW_HEIGHT/2,
                 "PLAYER " + str(game["winner"]) + " WINS! ",
                 color, GLUT_BITMAP_TIMES_ROMAN_24)
    
    draw_text_2d(WINDOW_WIDTH/2 - 90, WINDOW_HEIGHT/2 - 40,
                 "Press SPACE to Return", [1, 1, 1])


def draw_playing_ui():
    """Draw the in-game UI"""
    
    # Scores
    draw_text_2d(50, WINDOW_HEIGHT - 50,
                 str(game["player_1"]["score"]),
                 COLOR_PLAYER_1, GLUT_BITMAP_TIMES_ROMAN_24)
    
    draw_text_2d(WINDOW_WIDTH - 80, WINDOW_HEIGHT - 50,
                 str(game["player_2"]["score"]),
                 COLOR_PLAYER_2, GLUT_BITMAP_TIMES_ROMAN_24)
    
    # Dash bars
    draw_dash_bar(50, WINDOW_HEIGHT - 70, game["player_1"], COLOR_PLAYER_1)
    draw_dash_bar(WINDOW_WIDTH - 150, WINDOW_HEIGHT - 70, game["player_2"], COLOR_PLAYER_2)

    # Live Rally Counter (center top)
    if game["rally_count"] > 0:
        # Color intensifies as rally grows
        intensity = min(1.0, game["rally_count"] / 10.0)
        rally_color = [1.0, 1.0 - intensity * 0.5, 1.0 - intensity]  # White to orange
        
        draw_text_2d(WINDOW_WIDTH/2 - 30, WINDOW_HEIGHT - 50,
                     "RALLY: " + str(game["rally_count"]),
                     rally_color)
    
    # Match point warning (blinking)
    at_match_point = (game["player_1"]["score"] == POINTS_TO_WIN - 1 or
                      game["player_2"]["score"] == POINTS_TO_WIN - 1)
    
    if at_match_point:
        blink_on = (game["frame_count"] // 20) % 2 == 0
        if blink_on:
            draw_text_2d(WINDOW_WIDTH/2 - 60, WINDOW_HEIGHT - 80,
                         "MATCH POINT", [1, 0, 0])

    # Pause indicator
    if game["is_paused"]:
        draw_text_2d(WINDOW_WIDTH/2 - 40, WINDOW_HEIGHT/2,
                     "PAUSED", [1, 1, 1], GLUT_BITMAP_TIMES_ROMAN_24)
        draw_text_2d(WINDOW_WIDTH/2 - 60, WINDOW_HEIGHT/2 - 30,
                     "Press ESC to resume", [0.7, 0.7, 0.7])


def draw_ui():
    """Draw all 2D UI elements"""
    
    # Switch to 2D mode
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, WINDOW_WIDTH, 0, WINDOW_HEIGHT)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    
    # Draw appropriate screen
    if game["state"] == "MENU":
        draw_menu_screen()
    elif game["state"] == "GAME_OVER":
        draw_game_over_screen()
    elif game["state"] == "PLAYING":
        draw_playing_ui()
    
    # Switch back to 3D mode
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)


def setup_camera():
    """Position the camera based on current mode"""
    
    # Add screen shake
    shake_x = (random.random() - 0.5) * game["screen_shake"]
    shake_y = (random.random() - 0.5) * game["screen_shake"]
    
    if game["camera_mode"] == 0: 
        # Broadcast view (from the side)
        gluLookAt(-400 + shake_x, 600 + shake_y, 0,
                  0, 0, 0,
                  0, 1, 0)
    
    elif game["camera_mode"] == 1:
        # Top-down view
        gluLookAt(0, 1000, 1,
                  0, 0, 0,
                  0, 1, 0)
    
    elif game["camera_mode"] == 2:
        # First-person (behind Player 1)
        p1 = game["player_1"]
        gluLookAt(p1["x"], 150, p1["z"] - 300,
                  p1["x"], 50, 400,
                  0, 1, 0)


# ============================================================
#                     MAIN DISPLAY FUNCTION
# ============================================================

def display():
    """Main drawing function (called every frame)"""
    
    # Clear screen
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()
    
    # Set up camera
    setup_camera()
    
    # Draw floor
    draw_floor_grid()
    
    # Draw game objects (not on menu)
    if game["state"] != "MENU":
        
        # Draw paddles
        p1 = game["player_1"]
        draw_box(p1["x"], 10, p1["z"],
                 p1["width"], PADDLE_HEIGHT, PADDLE_DEPTH,
                 get_player_color(p1))
        
        p2 = game["player_2"]
        draw_box(p2["x"], 10, p2["z"],
                 p2["width"], PADDLE_HEIGHT, PADDLE_DEPTH,
                 get_player_color(p2))
        
        # Draw powerup
        if game["powerup"] is not None:
            pu = game["powerup"]
            draw_box(pu["x"], 20, pu["z"],
                     20, 20, 20,
                     get_powerup_color(pu))
        
        # Draw balls
        for ball in game["balls"]: 
            draw_ball_with_trail(ball)
        
        # Draw particles
        draw_all_particles()
        
        # Draw floating texts
        for text in game["floating_texts"]:
            draw_text_3d(text["x"], text["y"], text["z"],
                         text["text"], text["color"])
    
    # Draw 2D UI on top
    draw_ui()
    
    # Show the frame
    glutSwapBuffers()


# ============================================================
#                     KEYBOARD INPUT
# ============================================================

def on_key_press(key, x, y):
    """Handle key press"""
    
    try:
        key_char = key.decode("utf-8").lower()
        game["keys_pressed"]. add(key_char)
        
        # Camera toggle (C key)
        if key_char == "c":
            game["camera_mode"] = (game["camera_mode"] + 1) % 3
        
        # Quit (ESC key)
        if key == b'\x1b' and game["state"] == "PLAYING":
            game["is_paused"] = not game["is_paused"]
        
        # Menu selection
        if game["state"] == "MENU": 
            if key_char == "1":
                start_game(two_player_mode=False)
            if key_char == "2": 
                start_game(two_player_mode=True)
        
        # Return to menu from game over
        if game["state"] == "GAME_OVER":
            if key_char == " ":
                reset_game()
    
    except:
        pass

def on_key_release(key, x, y):
    """Handle key release"""
    
    try:
        key_char = key.decode("utf-8").lower()
        if key_char in game["keys_pressed"]:
            game["keys_pressed"].remove(key_char)
    except:
        pass


def on_special_key_press(key, x, y):
    """Handle special keys (arrows)"""
    game["keys_pressed"].add(key)


def on_special_key_release(key, x, y):
    """Handle special key release"""
    
    if key in game["keys_pressed"]: 
        game["keys_pressed"].remove(key)


# ============================================================
#                     GAME LOOP
# ============================================================

def game_loop():
    """Main loop - runs about 60 times per second"""
    global last_frame_time
    
    current_time = time.time()
    delta_time = current_time - last_frame_time
    
    if delta_time >= FRAME_TIME:
        last_frame_time = current_time
        update_game()
        glutPostRedisplay()

# ============================================================
#                     START THE GAME
# ============================================================

def main():
    """Initialize and run the game"""
    
    # Set up initial game state
    reset_game()
    
    # Initialize OpenGL window
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(WINDOW_WIDTH, WINDOW_HEIGHT)
    glutCreateWindow(b"Super 3D Pong Deluxe")
    
    # Enable 3D features
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glClearColor(0.05, 0.05, 0.05, 1.0)
    
    # Set up 3D view
    glMatrixMode(GL_PROJECTION)
    gluPerspective(60, WINDOW_WIDTH / WINDOW_HEIGHT, 1, 2000)
    glMatrixMode(GL_MODELVIEW)
    
    # Connect our functions to OpenGL
    glutDisplayFunc(display)
    glutKeyboardFunc(on_key_press)
    glutKeyboardUpFunc(on_key_release)
    glutSpecialFunc(on_special_key_press)
    glutSpecialUpFunc(on_special_key_release)
    glutIdleFunc(game_loop)
    
    # Start the game! 
    glutMainLoop()


# Run the game
if __name__ == "__main__":
    main()
