from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import math
import random
import sys

# ==========================================
# 1. CONSTANTS (Matched to TS File)
# ==========================================
WINDOW_W, WINDOW_H = 800, 600

# Dimensions (Scaled down slightly for OpenGL unit consistency)
FIELD_W = 400
FIELD_D = 800
FIELD_FLOOR = 0

PADDLE_W_BASE = 80
PADDLE_H = 15
PADDLE_D = 15
BALL_RADIUS = 8

MAX_SCORE = 11
DASH_COOLDOWN_MAX = 120

# Colors (Converted from Hex to RGB Float)
C_P1 = [0.0, 1.0, 1.0]      # Cyan
C_P2 = [1.0, 0.0, 0.33]     # Pink
C_BALL = [1.0, 1.0, 1.0]
C_GRID = [0.1, 0.1, 0.2]    # Dark Blue
C_TEXT = [1.0, 1.0, 1.0]
C_GIANT = [1.0, 0.84, 0.0]  # Gold
C_MULTI = [0.0, 1.0, 0.0]   # Green

# ==========================================
# 2. GLOBAL STATE
# ==========================================
class GameState:
    def __init__(self):
        self.mode = 'MENU' # MENU, PLAYING, GAME_OVER
        self.is_pvp = False
        self.paused = False
        self.winner = 0
        self.keys = set()
        
        # Camera
        self.camera_mode = 0 # 0: Broadcast, 1: TopDown, 2: FPS
        self.shake = 0.0
        
        # Game Objects
        self.balls = []
        self.particles = []
        self.texts = []
        self.powerup = None
        
        # Players
        self.p1 = self.create_player(1)
        self.p2 = self.create_player(2)
        
        # Meta
        self.rally = 0
        self.last_serve = 1
        self.frame_count = 0

    def create_player(self, id):
        z = -FIELD_D/2 + 40 if id == 1 else FIELD_D/2 - 40
        return {
            'x': 0, 'z': z,
            'w': PADDLE_W_BASE,
            'score': 0,
            'dash_cd': 0,
            'streak': 0,
            'is_giant': False,
            'giant_timer': 0
        }

game = GameState()

# ==========================================
# 3. HELPER FUNCTIONS
# ==========================================
def lerp(start, end, t):
    return start * (1 - t) + end * t

def spawn_ball(server_id):
    direction = 1 if server_id == 1 else -1
    game.balls.append({
        'x': 0, 'y': BALL_RADIUS, 
        'z': -FIELD_D/2 + 100 if server_id == 1 else FIELD_D/2 - 100,
        'vx': (random.random() - 0.5) * 6,
        'vz': direction * 9.0, # Speed from TS
        'color': C_BALL,
        'trail': []
    })

def spawn_powerup():
    if game.powerup: return
    game.powerup = {
        'x': (random.random() - 0.5) * FIELD_W * 0.8,
        'z': (random.random() - 0.5) * FIELD_D * 0.5,
        'type': 'GIANT' if random.random() > 0.5 else 'MULTIBALL',
        'active': True,
        'rot': 0.0
    }

def add_text(text, x, z, color, scale=1.0):
    game.texts.append({
        'text': text, 'x': x, 'y': 20, 'z': z,
        'color': color, 'scale': scale, 'life': 60
    })

def add_particles(x, z, color, count=10):
    for _ in range(count):
        game.particles.append({
            'x': x, 'y': 10, 'z': z,
            'vx': (random.random() - 0.5) * 8,
            'vy': (random.random() * 5) + 2,
            'vz': (random.random() - 0.5) * 8,
            'life': random.randint(20, 50),
            'color': color,
            'size': random.uniform(2, 5)
        })

def start_game(pvp):
    game.is_pvp = pvp
    game.mode = 'PLAYING'
    game.p1 = game.create_player(1)
    game.p2 = game.create_player(2)
    game.balls = []
    game.particles = []
    game.texts = []
    game.powerup = None
    game.rally = 0
    spawn_ball(1)

# ==========================================
# 4. UPDATE LOOP (Physics & Logic)
# ==========================================
def update():
    if game.mode != 'PLAYING' or game.paused: return
    
    game.frame_count += 1
    
    # --- 1. Player Logic ---
    MOVE_SPD = 6
    DASH_SPD = 14
    
    # P1 Input
    spd1 = MOVE_SPD
    if game.p1['dash_cd'] > 0: game.p1['dash_cd'] -= 1
    
    if 'q' in game.keys and game.p1['dash_cd'] == 0:
        spd1 = DASH_SPD
        game.p1['dash_cd'] = DASH_COOLDOWN_MAX
        add_text("DASH!", game.p1['x'], game.p1['z'], C_P1, 0.8)
        
    if 'a' in game.keys: game.p1['x'] -= spd1
    if 'd' in game.keys: game.p1['x'] += spd1
    
    # P2 Input / AI
    spd2 = MOVE_SPD
    if game.p2['dash_cd'] > 0: game.p2['dash_cd'] -= 1
    
    if game.is_pvp:
        if '\r' in game.keys and game.p2['dash_cd'] == 0: # Enter key
            spd2 = DASH_SPD
            game.p2['dash_cd'] = DASH_COOLDOWN_MAX
            add_text("DASH!", game.p2['x'], game.p2['z'], C_P2, 0.8)
        if 'l' in game.keys: game.p2['x'] += spd2 # Using L/J for arrow simulation if needed, or mapping arrows
        # Map Arrows
        if 100 in game.keys: game.p2['x'] -= spd2 # Left Arrow code
        if 102 in game.keys: game.p2['x'] += spd2 # Right Arrow code
    else:
        # AI Logic
        target = 0
        # Find closest ball coming towards P2
        threats = [b for b in game.balls if b['vz'] > 0]
        if threats:
            t = min(threats, key=lambda b: abs(b['z'] - game.p2['z']))
            # Add artificial reaction error
            err = math.sin(game.frame_count * 0.05) * 40
            target = t['x'] + err
        
        if game.p2['x'] < target - 10: game.p2['x'] += spd2 * 0.8
        elif game.p2['x'] > target + 10: game.p2['x'] -= spd2 * 0.8

    # Clamp & Giant Logic
    for p in [game.p1, game.p2]:
        p['x'] = max(-FIELD_W/2 + p['w']/2, min(FIELD_W/2 - p['w']/2, p['x']))
        
        target_w = PADDLE_W_BASE * 1.5 if p['is_giant'] else PADDLE_W_BASE
        p['w'] = lerp(p['w'], target_w, 0.1)
        
        if p['is_giant']:
            p['giant_timer'] -= 1
            if p['giant_timer'] <= 0: p['is_giant'] = False

    # --- 2. Ball Physics ---
    for b in game.balls[:]:
        # Trail
        b['trail'].append((b['x'], b['y'], b['z']))
        if len(b['trail']) > 12: b['trail'].pop(0)
        
        b['x'] += b['vx']
        b['z'] += b['vz']
        
        # Walls
        if b['x'] < -FIELD_W/2 + BALL_RADIUS or b['x'] > FIELD_W/2 - BALL_RADIUS:
            b['vx'] *= -1
            game.shake = 5
            
        # P1 Collision
        if (b['z'] - BALL_RADIUS < game.p1['z'] + PADDLE_D and 
            b['z'] > game.p1['z'] - PADDLE_D and
            abs(b['x'] - game.p1['x']) < game.p1['w']/2 + BALL_RADIUS):
            
            b['vz'] = abs(b['vz']) * 1.05
            hit_off = (b['x'] - game.p1['x']) / (game.p1['w']/2)
            b['vx'] += hit_off * 4
            
            game.rally += 1
            game.shake = 10
            add_particles(b['x'], b['z'], C_P1)
            add_text("SMASH!", b['x'], b['z'], C_P1)

        # P2 Collision
        if (b['z'] + BALL_RADIUS > game.p2['z'] - PADDLE_D and 
            b['z'] < game.p2['z'] + PADDLE_D and
            abs(b['x'] - game.p2['x']) < game.p2['w']/2 + BALL_RADIUS):
            
            b['vz'] = -abs(b['vz']) * 1.05
            hit_off = (b['x'] - game.p2['x']) / (game.p2['w']/2)
            b['vx'] += hit_off * 4
            
            game.rally += 1
            game.shake = 10
            add_particles(b['x'], b['z'], C_P2)
            add_text("SMASH!", b['x'], b['z'], C_P2)
            
        # Scoring
        if b['z'] < -FIELD_D/2 - 50: handle_score(2, b)
        elif b['z'] > FIELD_D/2 + 50: handle_score(1, b)

    # --- 3. Powerups ---
    if not game.powerup and random.random() < 0.002: spawn_powerup()
    
    if game.powerup:
        game.powerup['rot'] += 2
        p = game.powerup
        
        # Check collision with balls
        for b in game.balls:
            dist = math.sqrt((b['x'] - p['x'])**2 + (b['z'] - p['z'])**2)
            if dist < 25 + BALL_RADIUS:
                # Activate
                owner = game.p1 if b['vz'] > 0 else game.p2 # Who hit it last roughly
                
                if p['type'] == 'GIANT':
                    owner['is_giant'] = True
                    owner['giant_timer'] = 600
                    add_text("GIANT!", p['x'], p['z'], C_GIANT, 1.5)
                else:
                    spawn_ball(1 if b['vz'] > 0 else 2)
                    add_text("MULTIBALL!", p['x'], p['z'], C_MULTI, 1.5)
                
                game.powerup = None
                game.shake = 20
                break

    # --- 4. Multiball Mayhem ---
    if game.rally == 5 and len(game.balls) == 1:
        spawn_ball(1 if game.balls[0]['vz'] > 0 else 2)
        add_text("MAYHEM!", 0, 0, [1,0,1], 2.0)
        game.rally += 1 # prevent loop

    # --- 5. FX ---
    game.shake *= 0.9
    
    for p in game.particles[:]:
        p['x'] += p['vx']
        p['y'] += p['vy']
        p['z'] += p['vz']
        p['vy'] -= 0.5 # Gravity
        p['life'] -= 1
        if p['life'] <= 0: game.particles.remove(p)
        
    for t in game.texts[:]:
        t['y'] += 1
        t['life'] -= 1
        if t['life'] <= 0: game.texts.remove(t)

def handle_score(winner_id, ball):
    if ball in game.balls: game.balls.remove(ball)
    game.shake = 30
    
    if winner_id == 1:
        game.p1['score'] += 1
        game.p1['streak'] += 1
        game.p2['streak'] = 0
        if game.p1['streak'] == 3: add_text("P1 FIRE!", 0, -200, C_P1, 2.0)
    else:
        game.p2['score'] += 1
        game.p2['streak'] += 1
        game.p1['streak'] = 0
        if game.p2['streak'] == 3: add_text("P2 FIRE!", 0, 200, C_P2, 2.0)

    if game.p1['score'] >= MAX_SCORE or game.p2['score'] >= MAX_SCORE:
        game.mode = 'GAME_OVER'
        game.winner = 1 if game.p1['score'] >= MAX_SCORE else 2
        return

    # Respawn if empty
    if len(game.balls) == 0:
        game.last_serve = 2 if winner_id == 1 else 1
        game.rally = 0
        # Simple delay hack: create a timer or just spawn
        spawn_ball(game.last_serve)

# ==========================================
# 5. RENDERING
# ==========================================
def draw_rect_3d(x, y, z, w, h, d, color):
    glPushMatrix()
    glTranslatef(x, y, z)
    glScalef(w, h, d)
    glColor3fv(color)
    glutSolidCube(1.0)
    glPopMatrix()

def draw_string_3d(x, y, z, text, color):
    glColor3fv(color)
    glRasterPos3f(x, y, z)
    for char in text:
        glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(char))

def draw_ui_2d():
    glMatrixMode(GL_PROJECTION); glPushMatrix(); glLoadIdentity()
    gluOrtho2D(0, WINDOW_W, 0, WINDOW_H)
    glMatrixMode(GL_MODELVIEW); glPushMatrix(); glLoadIdentity()
    
    # Draw Scores
    glColor3fv(C_P1)
    glRasterPos2f(50, WINDOW_H - 50)
    for c in f"{game.p1['score']}": glutBitmapCharacter(GLUT_BITMAP_TIMES_ROMAN_24, ord(c))
    
    glColor3fv(C_P2)
    glRasterPos2f(WINDOW_W - 80, WINDOW_H - 50)
    for c in f"{game.p2['score']}": glutBitmapCharacter(GLUT_BITMAP_TIMES_ROMAN_24, ord(c))
    
    # Dash Bars
    # (Simplified as lines for immediate mode)
    if game.mode == 'PLAYING':
        # P1 Bar
        pct1 = 1.0 - (game.p1['dash_cd'] / DASH_COOLDOWN_MAX)
        glColor3fv(C_P1)
        glBegin(GL_QUADS)
        glVertex2f(50, WINDOW_H - 60); glVertex2f(50 + 100*pct1, WINDOW_H - 60)
        glVertex2f(50 + 100*pct1, WINDOW_H - 70); glVertex2f(50, WINDOW_H - 70)
        glEnd()
        
        # P2 Bar
        pct2 = 1.0 - (game.p2['dash_cd'] / DASH_COOLDOWN_MAX)
        glColor3fv(C_P2)
        glBegin(GL_QUADS)
        glVertex2f(WINDOW_W - 150, WINDOW_H - 60); glVertex2f(WINDOW_W - 150 + 100*pct2, WINDOW_H - 60)
        glVertex2f(WINDOW_W - 150 + 100*pct2, WINDOW_H - 70); glVertex2f(WINDOW_W - 150, WINDOW_H - 70)
        glEnd()

        # Match Point
        if game.p1['score'] == MAX_SCORE-1 or game.p2['score'] == MAX_SCORE-1:
            if (game.frame_count // 20) % 2 == 0:
                glColor3f(1, 0, 0)
                glRasterPos2f(WINDOW_W/2 - 60, WINDOW_H - 80)
                for c in "MATCH POINT": glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(c))

    # Menu / Game Over
    if game.mode == 'MENU':
        glColor3f(1, 1, 1)
        glRasterPos2f(WINDOW_W/2 - 100, WINDOW_H/2 + 50)
        for c in "SUPER 3D PONG DELUXE": glutBitmapCharacter(GLUT_BITMAP_TIMES_ROMAN_24, ord(c))
        glRasterPos2f(WINDOW_W/2 - 80, WINDOW_H/2)
        for c in "Press 1: Single Player": glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(c))
        glRasterPos2f(WINDOW_W/2 - 80, WINDOW_H/2 - 30)
        for c in "Press 2: PvP Local": glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(c))
    
    if game.mode == 'GAME_OVER':
        glColor3fv(C_P1 if game.winner == 1 else C_P2)
        msg = f"PLAYER {game.winner} WINS!"
        glRasterPos2f(WINDOW_W/2 - 80, WINDOW_H/2)
        for c in msg: glutBitmapCharacter(GLUT_BITMAP_TIMES_ROMAN_24, ord(c))
        
        glColor3f(1,1,1)
        glRasterPos2f(WINDOW_W/2 - 90, WINDOW_H/2 - 40)
        for c in "Press SPACE to Return": glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(c))

    glPopMatrix(); glMatrixMode(GL_PROJECTION); glPopMatrix(); glMatrixMode(GL_MODELVIEW)

def display():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()
    
    # 1. Camera
    shake_x = (random.random() - 0.5) * game.shake
    shake_y = (random.random() - 0.5) * game.shake
    
    if game.camera_mode == 0: # Broadcast
        gluLookAt(-400 + shake_x, 600 + shake_y, 0, 0, 0, 0, 0, 1, 0)
    elif game.camera_mode == 1: # Top Down
        gluLookAt(0, 1000, 1, 0, 0, 0, 0, 1, 0)
    elif game.camera_mode == 2: # FPS
        gluLookAt(game.p1['x'], 150, game.p1['z'] + 100, 0, 50, -400, 0, 1, 0)

    # 2. Floor Grid
    glLineWidth(1)
    glBegin(GL_LINES)
    glColor3fv(C_GRID)
    # Longitude
    for x in range(int(-FIELD_W/2), int(FIELD_W/2) + 1, 50):
        glVertex3f(x, 0, -FIELD_D/2); glVertex3f(x, 0, FIELD_D/2)
    # Latitude
    for z in range(int(-FIELD_D/2), int(FIELD_D/2) + 1, 50):
        glVertex3f(-FIELD_W/2, 0, z); glVertex3f(FIELD_W/2, 0, z)
    glEnd()

    # 3. Game Objects
    if game.mode != 'MENU':
        # Paddles
        c1 = [1, 0.6, 0] if game.p1['streak'] >= 3 else C_P1
        draw_rect_3d(game.p1['x'], 10, game.p1['z'], game.p1['w'], PADDLE_H, PADDLE_D, c1)
        
        c2 = [1, 0.6, 0] if game.p2['streak'] >= 3 else C_P2
        draw_rect_3d(game.p2['x'], 10, game.p2['z'], game.p2['w'], PADDLE_H, PADDLE_D, c2)
        
        # Powerup
        if game.powerup:
            draw_rect_3d(game.powerup['x'], 20, game.powerup['z'], 20, 20, 20, C_GIANT if game.powerup['type']=='GIANT' else C_MULTI)
        
        # Balls
        for b in game.balls:
            # Shadow
            glPushMatrix()
            glTranslatef(b['x'], 1, b['z'])
            glScalef(1, 0.1, 1)
            glColor3f(0, 0, 0)
            glutSolidSphere(BALL_RADIUS, 8, 8)
            glPopMatrix()
            
            # Ball
            glPushMatrix()
            glTranslatef(b['x'], b['y'], b['z'])
            glColor3fv(b['color'])
            glutSolidSphere(BALL_RADIUS, 12, 12)
            glPopMatrix()
            
            # Trail
            glLineWidth(2)
            glBegin(GL_LINE_STRIP)
            for i, p in enumerate(b['trail']):
                alpha = i / len(b['trail'])
                glColor4f(b['color'][0], b['color'][1], b['color'][2], alpha)
                glVertex3f(p[0], p[1], p[2])
            glEnd()
            
        # Particles
        glPointSize(3)
        glBegin(GL_POINTS)
        for p in game.particles:
            glColor3fv(p['color'])
            glVertex3f(p['x'], p['y'], p['z'])
        glEnd()
        
        # Texts
        for t in game.texts:
            draw_string_3d(t['x'], t['y'], t['z'], t['text'], t['color'])

    # 4. UI
    draw_ui_2d()
    glutSwapBuffers()

# ==========================================
# 6. INPUT
# ==========================================
def timer(v):
    update()
    glutPostRedisplay()
    glutTimerFunc(16, timer, 0)

def key_down(key, x, y):
    try:
        k = key.decode('utf-8').lower()
        game.keys.add(k)
        
        if k == 'c': game.camera_mode = (game.camera_mode + 1) % 3
        if k == 'p': game.paused = not game.paused
        if k == '\x1b': sys.exit(0) # ESC
        
        # Menu Selection
        if game.mode == 'MENU':
            if k == '1': start_game(False)
            if k == '2': start_game(True)
        
        if game.mode == 'GAME_OVER' and k == ' ':
            game.mode = 'MENU'
            
    except: pass

def key_up(key, x, y):
    try:
        k = key.decode('utf-8').lower()
        if k in game.keys: game.keys.remove(k)
    except: pass

def special_down(key, x, y):
    game.keys.add(key) # Stores int for arrows

def special_up(key, x, y):
    if key in game.keys: game.keys.remove(key)

# ==========================================
# 7. MAIN
# ==========================================
def main():
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(WINDOW_W, WINDOW_H)
    glutCreateWindow(b"Super 3D Pong Deluxe")
    
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glClearColor(0.05, 0.05, 0.05, 1.0)
    
    glMatrixMode(GL_PROJECTION)
    gluPerspective(60, WINDOW_W/WINDOW_H, 1, 2000)
    glMatrixMode(GL_MODELVIEW)
    
    glutDisplayFunc(display)
    glutKeyboardFunc(key_down)
    glutKeyboardUpFunc(key_up)
    glutSpecialFunc(special_down)
    glutSpecialUpFunc(special_up)
    glutTimerFunc(16, timer, 0)
    
    print("Started!")
    glutMainLoop()

if __name__ == "__main__":
    main()