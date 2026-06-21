import pygame
import random
import math
import sys
import os

#ctrl + f 搜索
# 解决屏幕缩放导致的右下角黑边、裁切问题
if sys.platform == 'win32':
    try:
        import ctypes
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

# ==========================================
# 1. 初始化与全局设置
# ==========================================
pygame.init()
pygame.font.init()

infoObject = pygame.display.Info()
SCREEN_WIDTH, SCREEN_HEIGHT = infoObject.current_w, infoObject.current_h
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN | pygame.HWSURFACE | pygame.DOUBLEBUF)
pygame.display.set_caption("绝境突围：无尽肉鸽")

FPS = 60
BLACK, WHITE = (0, 0, 0), (255, 255, 255)
RED, GREEN, BLUE = (255, 68, 68), (144, 238, 144), (135, 206, 235)
YELLOW, PURPLE, GRAY = (255, 215, 0), (138, 43, 226), (100, 100, 100)
DARK_GRAY = (80, 80, 80)
BOSS_COLOR = (139, 0, 0)
ORANGE = (255, 165, 0)
PALE_YELLOW = (255, 255, 150)
DARK_GREEN = (0, 100, 0) 
CYAN = (0, 255, 255)
# 搜索改数值  金币,总金币,层数   coins, total_coins, current_floor, acquired_talents, shop_page = 0, 0, 1, [], 0
TILE_SIZE = 60
MAP_COLS, MAP_ROWS = 80, 80
game_map, room_list = [], []
explored_map = []  
tile_variant_map = [] 

font_name = "SimHei" if "simhei" in pygame.font.get_fonts() else "Arial"
font_base = pygame.font.SysFont(font_name, 18)
font_large = pygame.font.SysFont(font_name, 26, bold=True)
font_title = pygame.font.SysFont(font_name, 50, bold=True)

difficulty_mult = {"hp": 1.0, "dmg": 1, "spd": 1.0, "range_hp": 1.0, "range_spd": 1.0}
debuffs = {"vision_reduce": 0, "buff_disable": 0, "last_shield_hit": 0}
screen_shake = 0 
pause_tab = 0 

# ==========================================
# 2. 辅助资源加载函数
# ==========================================
def get_res_path(path):
    external_mod_path = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), path)
    if os.path.exists(external_mod_path): return external_mod_path
    if os.path.exists(path): return path
    if hasattr(sys, '_MEIPASS'): return os.path.join(sys._MEIPASS, path)
    return path

def load_frames(image_paths, fallback_color, size, shape="rect"):
    frames = []
    for path in image_paths:
        real_path = get_res_path(path)
        if os.path.exists(real_path): 
            frames.append(pygame.transform.scale(pygame.image.load(real_path).convert_alpha(), size))
    if not frames:
        s = pygame.Surface(size, pygame.SRCALPHA)
        if shape == "circle": pygame.draw.circle(s, fallback_color, (size[0]//2, size[1]//2), min(size)//2)
        else: pygame.draw.rect(s, fallback_color, (0,0, size[0], size[1]), border_radius=5)
        frames.append(s)
    return frames

# ==========================================
# 3. 特效与实体
# ==========================================
class DamageText(pygame.sprite.Sprite):
    def __init__(self, x, y, damage_val, is_heal=False, custom_color=None, is_text=False):
        super().__init__()
        self.x, self.y = x, y
        if custom_color: self.color = custom_color
        else: self.color = GREEN if is_heal else PALE_YELLOW
            
        if is_text: self.text = str(damage_val)
        else: self.text = f"+{int(damage_val)}" if is_heal else f"-{int(damage_val)}"
            
        self.lifetime, self.timer = 60, 0

    def update(self):
        self.timer += 1; self.y -= 1
        if self.timer >= self.lifetime: self.kill()

    def draw(self, surface, camera_x, camera_y):
        alpha = int(255 * (1 - self.timer / self.lifetime))
        txt_surf = font_large.render(self.text, True, self.color)
        txt_surf.set_alpha(alpha)
        surface.blit(txt_surf, (self.x - camera_x - txt_surf.get_width()//2, self.y - camera_y))

class ExplosionEffect(pygame.sprite.Sprite):
    def __init__(self, x, y, damage, radius=None):
        super().__init__()
        self.x, self.y = x, y
        self.max_radius = radius if radius else damage * 1.5
        size = (int(self.max_radius * 2), int(self.max_radius * 2))
        
        # 🖼️👉 【可替换贴图：爆炸效果】
        self.frames = load_frames(["爆炸1.png", "爆炸2.png", "爆炸3.png", "爆炸4.png"], (255, 100, 0, 150), size, "circle")
        self.lifetime = 30
        self.timer = 0

    def update(self):
        self.timer += 1
        if self.timer >= self.lifetime: 
            self.kill()

    def draw(self, surface, camera_x, camera_y):
        if not self.frames: return
        frame_idx = min(int((self.timer / self.lifetime) * len(self.frames)), len(self.frames) - 1)
        img = self.frames[frame_idx]
        draw_x = self.x - self.max_radius - camera_x
        draw_y = self.y - self.max_radius - camera_y
        surface.blit(img, (draw_x, draw_y))

class LaserBeamEffect(pygame.sprite.Sprite):
    def __init__(self, x, y, angle, length, is_skill):
        super().__init__()
        self.x, self.y = x, y
        self.angle, self.length = angle, length
        self.lifetime = 15
        self.timer = 0
        self.color = (255, 80, 80) if not is_skill else (180, 50, 255)

    def update(self):
        self.timer += 1
        if self.timer >= self.lifetime: self.kill()

    def draw(self, surface, camera_x, camera_y):
        alpha = int(255 * (1 - self.timer / self.lifetime))
        s = pygame.Surface((int(self.length), 40), pygame.SRCALPHA)
        pygame.draw.rect(s, (*self.color, alpha), (0, 10, int(self.length), 20), border_radius=10)
        pygame.draw.rect(s, (255, 255, 255, alpha), (0, 15, int(self.length), 10), border_radius=5)
        
        rotated = pygame.transform.rotate(s, math.degrees(-self.angle))
        rect = rotated.get_rect(center=(self.x - camera_x + math.cos(self.angle)*(self.length/2), 
                                        self.y - camera_y + math.sin(self.angle)*(self.length/2)))
        surface.blit(rotated, rect.topleft)

class MeleeSwingEffect(pygame.sprite.Sprite):
    def __init__(self, start_x, start_y, attack_range, angle, weapon_img, is_skill_active, boss_override_color=None):
        super().__init__()
        self.x, self.y, self.range = start_x, start_y, attack_range
        self.lifetime, self.timer = 15, 0 
        self.weapon_img = weapon_img
        self.is_skill = is_skill_active
        self.boss_color = boss_override_color
        self.angle_left = angle - math.pi/2.5  
        self.angle_right = angle + math.pi/2.5

    def update(self):
        self.timer += 1
        if self.timer >= self.lifetime: self.kill()

    def draw(self, surface, camera_x, camera_y):
        s = pygame.Surface((self.range*2, self.range*2), pygame.SRCALPHA)
        progress = self.timer / self.lifetime
        current_angle = self.angle_left + (self.angle_right - self.angle_left) * progress
        alpha = int(255 * (1 - progress))
        
        if self.boss_color: fill_color = (*self.boss_color, alpha)
        else: fill_color = (180, 50, 255, alpha) if self.is_skill else (220, 220, 220, int(alpha*0.8))
        points = [(self.range, self.range)]
        for a in range(int(math.degrees(self.angle_left)), int(math.degrees(current_angle)) + 1, 3):
            rad = math.radians(a)
            points.append((self.range + math.cos(rad) * self.range, self.range + math.sin(rad) * self.range))
        if len(points) > 2:
            pygame.draw.polygon(s, fill_color, points)
            pygame.draw.lines(s, (255, 255, 255, alpha), False, points[1:], max(2, int(self.range/15)))

        if self.weapon_img:
            degree = math.degrees(-current_angle)
            w_img = self.weapon_img
            if self.is_skill:
                w_img = w_img.copy()
                w_img.fill((200, 150, 255), special_flags=pygame.BLEND_RGB_MULT) 
            if math.cos(current_angle) < 0: w_img = pygame.transform.flip(w_img, False, True)
            rotated_img = pygame.transform.rotate(w_img, degree)
            offset = w_img.get_width() / 2 + 10 
            w_rect = rotated_img.get_rect(center=(self.range + math.cos(current_angle)*offset, self.range + math.sin(current_angle)*offset))
            s.blit(rotated_img, w_rect)
        surface.blit(s, (self.x - self.range - camera_x, self.y - self.range - camera_y))

class FlameEffect(pygame.sprite.Sprite):
    def __init__(self, start_x, start_y, attack_range, angle, is_skill=False):
        super().__init__()
        self.x, self.y, self.range = start_x, start_y, attack_range
        self.lifetime, self.timer = 15, 0 
        self.is_skill = is_skill
        self.angle_left = angle - math.pi/4
        self.angle_right = angle + math.pi/4
        
        # 🖼️👉 【可替换贴图：喷射火焰特效】
        self.frames = load_frames(["flame1.png", "flame2.png", "flame3.png", "flame4.png"], (255, 100, 100, 0), (self.range*2, self.range*2), "rect")

    def update(self):
        self.timer += 1
        if self.timer >= self.lifetime: self.kill()

    def draw(self, surface, camera_x, camera_y):
        s = pygame.Surface((self.range*2, self.range*2), pygame.SRCALPHA)
        points = [(self.range, self.range)]
        for a in range(int(math.degrees(self.angle_left)), int(math.degrees(self.angle_right)) + 1, 2):
            rad = math.radians(a)
            points.append((self.range + math.cos(rad) * self.range, self.range + math.sin(rad) * self.range))
        color = (180, 50, 255, 120) if self.is_skill else (255, 100, 100, 120)
        if len(points) > 2: pygame.draw.polygon(s, color, points)
        
        if self.frames and self.frames[0].get_alpha() != 0:
            frame_idx = min(int((self.timer / self.lifetime) * len(self.frames)), len(self.frames)-1)
            angle_center = self.angle_left + (self.angle_right - self.angle_left)/2
            degree = math.degrees(-angle_center)
            img = self.frames[frame_idx]
            if self.is_skill:
                img = img.copy()
                img.fill((200, 150, 255), special_flags=pygame.BLEND_RGB_MULT)
            rotated_img = pygame.transform.rotate(img, degree)
            img_rect = rotated_img.get_rect(center=(self.range, self.range))
            s.blit(rotated_img, img_rect)
        surface.blit(s, (self.x - self.range - camera_x, self.y - self.range - camera_y))

class BossAoeEffect(pygame.sprite.Sprite):
    def __init__(self, x, y, radius, damage, player):
        super().__init__()
        self.x, self.y, self.radius, self.damage, self.player = x, y, radius, damage, player
        self.warning_time = 60    
        self.lifetime = 1260   
        self.timer = 0
        self.has_image = os.path.exists(get_res_path("boss_aoe.png"))
        
        # 🖼️👉 【可替换贴图：BOSS的范围伤害】
        self.image_surf = load_frames(["boss_aoe.png"], (0,0,0,0), (radius*2, radius*2), "circle")[0]

    def update(self):
        self.timer += 1
        if self.timer > self.warning_time:
            if math.hypot(self.player.rect.centerx - self.x, self.player.rect.centery - self.y) <= self.radius:
                if self.timer % 30 == 0: self.player.take_damage(self.damage)
                self.player.poison_timer = max(self.player.poison_timer, 10)
        if self.timer >= self.lifetime: self.kill()

    def draw(self, surface, camera_x, camera_y):
        draw_x, draw_y = self.x - camera_x, self.y - camera_y
        s = pygame.Surface((self.radius*2, self.radius*2), pygame.SRCALPHA)
        if self.timer < self.warning_time:
            pygame.draw.circle(s, (255, 0, 0, 80), (self.radius, self.radius), int(self.radius * (self.timer / self.warning_time)))
            pygame.draw.circle(s, (255, 0, 0, 200), (self.radius, self.radius), self.radius, 2)
        else:
            alpha = 180 if self.lifetime - self.timer > 60 else int(180 * ((self.lifetime - self.timer) / 60))
            if self.has_image:
                self.image_surf.set_alpha(alpha)
                s.blit(self.image_surf, (0,0))
            else:
                pygame.draw.circle(s, (255, 50, 0, alpha), (self.radius, self.radius), self.radius)
                pygame.draw.circle(s, (255, 200, 0, alpha//2), (self.radius, self.radius), self.radius - 10)
        surface.blit(s, (draw_x - self.radius, draw_y - self.radius))

class BossSwordAuraBullet(pygame.sprite.Sprite):
    def __init__(self, x, y, angle, damage, speed, range_scale):
        super().__init__()
        self.b_type = 3
        self.size = int(range_scale)
        self.image = pygame.Surface((self.size * 2, self.size * 2), pygame.SRCALPHA)
        
        # 🖼️👉 【二段特殊Boss攻击波：可更换弧形贴图】 
        points = []
        for a in range(-60, 61, 5): 
            rad = math.radians(a)
            px = self.size + math.cos(rad) * (self.size * 0.5) 
            py = self.size + math.sin(rad) * (self.size * 0.5)
            points.append((px, py))
        
        if len(points) >= 2: 
            pygame.draw.lines(self.image, (255, 100, 100, 200), False, points, 10)
        #剑气的碰撞体积
        self.image = pygame.transform.rotate(self.image, math.degrees(-angle))
        self.rect = self.image.get_rect(center=(x, y)).inflate(-int(self.size * 1.2), -int(self.size * 1.2))
        self.rect = self.image.get_rect(center=(x, y))
        self.speed, self.damage = speed * difficulty_mult["spd"], int(damage)
        self.vx, self.vy = math.cos(angle) * self.speed, math.sin(angle) * self.speed
        self.bounces = 0 
        self.timer = 180 

    def update(self):
        self.rect.x += self.vx
        self.rect.y += self.vy
        self.timer -= 1
        if is_wall(self.rect.centerx, self.rect.centery) or self.timer <= 0:
            self.kill()

class Sandbag(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        # 🖼️👉 【可替换贴图：木桩 】
        self.idle_img = load_frames(["sandbag_idle.png"], ORANGE, (60, 90), "rect")[0]
        self.hit_img = load_frames(["sandbag_hit.png"], RED, (60, 90), "rect")[0]
        
        self.image = self.idle_img
        self.rect = self.image.get_rect(center=(x, y))
        self.hit_timer = 0
        self.total_damage = 0
        self.start_time = 0
        self.last_hit_time = 0
        
    def take_damage(self, amount, effects_group=None, **kwargs): 
        self.hit_timer = 8
        self.image = self.hit_img
        current_time = pygame.time.get_ticks()
        if current_time - self.last_hit_time > 2000:
            self.total_damage = 0
            self.start_time = current_time
        self.total_damage += amount
        self.last_hit_time = current_time

        if effects_group is not None:
            effects_group.add(DamageText(self.rect.centerx, self.rect.top, amount))
        
    def update(self):
        if self.hit_timer > 0:
            self.hit_timer -= 1
            if self.hit_timer <= 0:
                self.image = self.idle_img
                
    def draw_dps(self, surface, camera_x, camera_y):
        if self.last_hit_time > 0 and pygame.time.get_ticks() - self.last_hit_time <= 2000:
            time_active = max((self.last_hit_time - self.start_time) / 1000.0, 0.1) 
            dps = self.total_damage / time_active
            
            bg_rect = pygame.Rect(self.rect.centerx - camera_x - 80, self.rect.top - camera_y - 80, 160, 65)
            pygame.draw.rect(surface, (30, 30, 30, 200), bg_rect, border_radius=5)
            pygame.draw.rect(surface, ORANGE, bg_rect, 2, border_radius=5)
            
            txt1 = font_base.render(f"时间: {time_active:.1f}s", True, WHITE)
            txt2 = font_base.render(f"总伤: {int(self.total_damage)}", True, YELLOW)
            txt3 = font_base.render(f"秒伤: {int(dps)}", True, RED)
            
            surface.blit(txt1, (bg_rect.x + 5, bg_rect.y + 5))
            surface.blit(txt2, (bg_rect.x + 5, bg_rect.y + 25))
            surface.blit(txt3, (bg_rect.x + 5, bg_rect.y + 45))

class ThrownGrenade(pygame.sprite.Sprite):
    def __init__(self, x, y, tx, ty, damage, base_damage, player, enemies, effects, crates=None, items=None, w_imgs=None, coins=None):
        super().__init__()
        # 🖼️👉 【可替换贴图：手榴弹（支持帧动画替换）】
        self.frames = load_frames(["grenade.png"], DARK_GREEN, (30, 30), "circle")
        self.image = self.frames[0]
        
        self.base_x, self.base_y = float(x), float(y) 
        self.z = 0 
        self.rect = self.image.get_rect(center=(x, y))

        self.tx, self.ty = tx, ty
        self.damage = int(damage)
        self.base_damage = base_damage
        self.player = player
        self.enemies = enemies
        self.effects = effects
        self.crates = crates
        self.items = items
        self.w_imgs = w_imgs
        self.coins_group = coins
        self.speed = 12
        self.anim_frame = 0 
        
        angle = math.atan2(ty - y, tx - x)
        self.vx = math.cos(angle) * self.speed
        self.vy = math.sin(angle) * self.speed
        self.travel_dist = math.hypot(tx - x, ty - y)
        self.current_dist = 0
        
        self.flight_ticks = max(1.0, self.travel_dist / self.speed)
        self.vz = 8.0 
        self.gravity = (2.0 * self.vz) / self.flight_ticks
        self.is_exploded = False

    def update(self):
        if self.is_exploded: return

        self.anim_frame += 0.5 
        self.image = self.frames[int(self.anim_frame) % len(self.frames)]

        self.base_x += self.vx
        self.base_y += self.vy
        self.current_dist += self.speed
        
        self.z += self.vz
        self.vz -= self.gravity
        
        self.rect.centerx = int(self.base_x)
        self.rect.centery = int(self.base_y - max(0, self.z))

        if self.current_dist >= self.travel_dist or (self.z <= 0 and self.current_dist > self.speed * 2) or is_wall(self.base_x, self.base_y):
            self.explode()
            self.kill()

    def explode(self):
        self.is_exploded = True
        base_radius = int((50 + self.base_damage * 0.5) * self.player.explosion_radius_mult) 
        if getattr(self.player, "has_large_explosion", False):
            base_radius *= 2
        
        center_bx, center_by = int(self.base_x), int(self.base_y)    
        self.effects.add(ExplosionEffect(center_bx, center_by, self.damage, base_radius))
        rect = pygame.Rect(int(center_bx - base_radius), int(center_by - base_radius), int(base_radius * 2), int(base_radius * 2))
        
        for enemy in self.enemies:
            if rect.colliderect(enemy.rect):
                if math.hypot(enemy.rect.centerx - center_bx, enemy.rect.centery - center_by) <= base_radius:
                    enemy.take_damage(self.damage)
                    self.effects.add(DamageText(enemy.rect.centerx, enemy.rect.top, self.damage))
                    
        if self.crates is not None:
            for crate in self.crates:
                if rect.colliderect(crate.rect):
                    if math.hypot(crate.rect.centerx - center_bx, crate.rect.centery - center_by) <= base_radius:
                        crate.take_damage(self.damage, self.items, self.effects, self.w_imgs, self.coins_group)

# ==========================================
# 4. 角色主体
# ==========================================
class Player(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        
        # 🖼️👉 【可替换贴图：角色】
        self.idle_frames = load_frames(["角色站立.png"], GREEN, (60, 60), "circle")
        self.death_frames = load_frames(["player_death.png"], GRAY, (60, 60), "rect")
        self.run_frames = load_frames(["角色跑步1.png","角色站立.png", "角色跑步2.png"], GREEN, (60, 60), "circle")
        
        # 🖼️👉 【可替换贴图：复活动画】
        self.revive_frames = load_frames(["player_revive1.png", "player_revive2.png"], YELLOW, (80, 80), "circle")
        
        self.frames, self.current_frame, self.image = self.idle_frames, 0, self.idle_frames[0]
        self.rect = self.image.get_rect(center=(x, y))
        self.facing_right = True
        
        self.max_hp, self.hp, self.invincible_timer, self.speed = 5, 5, 0, 6
        self.max_shield, self.shield, self.last_shield_damage = 2, 2, 0
        self.poison_timer = 0 
        self.revive_anim_timer = 0 
        
        self.bonus_ranged_mult = 1.0  
        self.bonus_melee_mult = 1.0  
        self.bonus_explosion_mult = 1.0  
        self.bonus_range_mult = 1.0  
        self.bonus_cd_reduction = 0 
        self.bonus_scatter = 0         
        self.charge_speed_mult = 1.0   
        self.has_revive = False     
        self.just_revived = False   
        self.has_large_explosion = False 
        self.has_orbit_shield = False
        self.orbit_shield_active = False
        self.orbit_shield_timer = 0

        self.laser_charge_start_time = 0
        self.laser_charge_duration = 0
        self.is_laser_charging = False
        
        self.weapon_slots, self.current_weapon = 2, 0
        self.weapons = [
            {"type": "pistol", "name": "普通手枪", "damage": 25, "cd": 300},
            {"type": "melee", "name": "近战小刀", "damage": 30, "range": 80, "cd": 400}
        ]
        
        self.stolen_weap_idx = -1
        
        self.skill_duration_max, self.skill_cd_max = 7 * 60, 10 * 60       
        self.skill_timer, self.skill_cd = 0, 0
        self.has_bounce, self.has_magnet, self.has_explosion = False, False, False
        self.explosion_damage_base = 20  
        self.explosion_radius_mult = 1.0 
        self.last_shoot_time = 0
        self.melee_swing_timer = 0
        self.charge_start_time = 0
        self.charge_duration = 0

    def update(self, is_dead=False, dx=0, dy=0):
        if is_dead: self.image = self.death_frames[0]; return
        
        # 复活时屏幕效果
        if self.revive_anim_timer > 0:
            self.revive_anim_timer -= 1
            progress = (60 - self.revive_anim_timer) / 60
            f_idx = min(int(progress * len(self.revive_frames)), len(self.revive_frames) - 1)
            self.image = self.revive_frames[f_idx]
            return

        if self.skill_timer > 0: 
            self.skill_timer -= 1
            if self.skill_timer == 0: self.skill_cd = self.skill_cd_max
        elif self.skill_cd > 0: self.skill_cd -= 1
        
        if self.orbit_shield_timer > 0:
            self.orbit_shield_timer -= 1
            if self.orbit_shield_timer == 0: self.orbit_shield_active = False
            
        if self.melee_swing_timer > 0: self.melee_swing_timer -= 1
        if self.shield < self.max_shield and pygame.time.get_ticks() - self.last_shield_damage > 5000:
            self.shield = min(self.max_shield, self.shield + 0.2)
        if self.invincible_timer > 0: self.invincible_timer -= 1

        if dx != 0 or dy != 0:
            self.frames = self.run_frames
            self.current_frame = (self.current_frame + 0.2) % len(self.frames)
        else:
            self.frames = self.idle_frames
            self.current_frame = 0

        self.image = self.frames[int(self.current_frame)].copy()
        if self.poison_timer > 0: self.image.fill((50, 200, 50), special_flags=pygame.BLEND_RGB_MULT)
        if self.invincible_timer > 0 and (self.invincible_timer // 5) % 2 == 0: self.image.set_alpha(100)
        if dx > 0: self.facing_right = True
        elif dx < 0: self.facing_right = False
        if not self.facing_right: self.image = pygame.transform.flip(self.image, True, False)

    def activate_skill(self):
        if self.skill_cd <= 0 and self.skill_timer <= 0:
            self.skill_timer = self.skill_duration_max
            if self.has_orbit_shield:
                self.orbit_shield_active = True
                self.orbit_shield_timer = 15 * 60

    def take_damage(self, damage, custom_effects_ref=None):
        if getattr(self, "orbit_shield_active", False):
            self.orbit_shield_active = False
            self.orbit_shield_timer = 0
            if custom_effects_ref is not None:
                custom_effects_ref.add(DamageText(self.rect.centerx, self.rect.top - 20, "抵抗击飞", custom_color=(100,200,255), is_text=True))
            return False

        damage = int(damage)
        self.last_shield_damage = pygame.time.get_ticks()
        if self.shield > 0:
            dmg_taken = min(self.shield, damage)
            self.shield -= dmg_taken
            if damage - dmg_taken > 0: self.hp -= (damage - dmg_taken)
        else: self.hp -= damage
        
        if self.hp <= 0:
            #护盾数值设置
            if getattr(self, "has_revive", False):
                self.hp = self.max_hp
                self.has_revive = False
                self.invincible_timer = 120
                self.just_revived = True
                self.revive_anim_timer = 60
                return False 
            return True 
        
        self.invincible_timer = 60
        return False

    def switch_weapon(self, direction):
        if len(self.weapons) > 0: self.current_weapon = (self.current_weapon + direction) % len(self.weapons); self.charge_start_time = 0; self.laser_charge_start_time = 0

    def process_attack(self, mouse_held, mx, my, camera_x, camera_y, bullets_group, enemy_bullets_group, effects_group, global_weapon_images, enemies_group, grenades_group, crates_group=None, items_group=None, coins_group=None):
        if not self.weapons: return []
        
        mouse_held_right = pygame.mouse.get_pressed()[2]
        current_time = pygame.time.get_ticks()

        if self.stolen_weap_idx == self.current_weapon:
            self.is_laser_charging = False
            self.laser_charge_start_time = 0
            self.laser_charge_duration = 0
            self.charge_start_time = 0 
            self.charge_duration = 0
            
            if (mouse_held or mouse_held_right) and pygame.time.get_ticks() % 60 == 0:
                effects_group.add(DamageText(self.rect.centerx, self.rect.top - 25, "此武器已被缴械", custom_color=(255,50,50), is_text=True))
            return []
        weapon = self.weapons[self.current_weapon]
        cd_multiplier = max(0.1, 1.0 - (self.bonus_cd_reduction / 100.0))
        actual_cd = int(weapon["cd"] * cd_multiplier)
        actual_base_dmg = weapon["damage"] 
        actual_dmg = actual_base_dmg       
        
        if weapon["type"] in ["pistol", "bow"]: actual_dmg = int(actual_dmg * self.bonus_ranged_mult)
        elif weapon["type"] == "melee": actual_dmg = int(actual_dmg * self.bonus_melee_mult)
        elif weapon["type"] == "grenade": actual_dmg = int(actual_dmg * self.bonus_explosion_mult)
        
        actual_range = weapon.get("range", 0) * self.bonus_range_mult
        target_x, target_y = mx + camera_x, my + camera_y
        angle = math.atan2(target_y - self.rect.centery, target_x - self.rect.centerx)
        is_skill = self.skill_timer > 0
        attacks = []
        
        perp_angle = angle + math.pi/2
        base_shoot_x = self.rect.centerx + math.cos(angle) * 20
        base_shoot_y = self.rect.centery + math.sin(angle) * 20
        shoot_x = base_shoot_x + math.cos(perp_angle) * 8
        shoot_y = base_shoot_y + math.sin(perp_angle) * 8
        clone_x = base_shoot_x - math.cos(perp_angle) * 8
        clone_y = base_shoot_y - math.sin(perp_angle) * 8

        # --- 新增的长按右键死光突袭能力，任何阶段有效覆盖原始连射 ---
        # 【机制限制】：仅仅归纳只有底层逻辑中属于完全投射子弹体系的（远程轻重手枪，机枪或长弓）准许汇聚充能 
        can_laser = (weapon["type"] in ["pistol", "bow"])

        # --- 新增的长按右键死光突袭能力，任何阶段有效覆盖原始连射 ---
        if mouse_held_right and can_laser:
            self.is_laser_charging = True
            if self.laser_charge_start_time == 0: self.laser_charge_start_time = current_time
            self.laser_charge_duration = (current_time - self.laser_charge_start_time) * self.charge_speed_mult
            return attacks 
        else:
            self.is_laser_charging = False
            if self.laser_charge_start_time > 0:
                charge = self.laser_charge_duration
                self.laser_charge_start_time = 0
                self.laser_charge_duration = 0
                if charge > 400 and can_laser: # 限定按压最少400毫秒门槛
                    # 长度
                    laser_length = min(1500, 50 + (charge/3500.0) * 1200)
                    # 👇【全新动态伤害核心】：蓄力比例最高为1.0（即2.5秒达到满蓄力）
                    charge_ratio = min(1.0, charge / 5500.0)
                    # 基础倍率为 2倍，随着蓄力逐渐增加，满蓄力时额外增加 4倍（即最高能达到 6倍伤害）
                    damage_multiplier = 2.0 + charge_ratio * 8.0 
                    laser_dmg = int(actual_dmg * damage_multiplier)
                    effects_group.add(LaserBeamEffect(self.rect.centerx, self.rect.centery, angle, laser_length, is_skill))
                    attacks.append(("laser", self.rect.centerx, self.rect.centery, angle, laser_length, laser_dmg))
                    if is_skill:
                        effects_group.add(LaserBeamEffect(clone_x, clone_y, angle, laser_length, True))
                        attacks.append(("laser", clone_x, clone_y, angle, laser_length, laser_dmg))
                    return attacks
        
        # ----------- 往下是原本的标准各种武器发射判断 --------

        if weapon["type"] == "bow":
            if mouse_held:
                if self.charge_start_time == 0: self.charge_start_time = current_time
                self.charge_duration = (current_time - self.charge_start_time) * self.charge_speed_mult
                return [] 
            else:
                if self.charge_start_time > 0:
                    if current_time - self.last_shoot_time < actual_cd: 
                        self.charge_start_time = 0; return []
                    self.last_shoot_time = current_time
                    charge = min(self.charge_duration, 1500) 
                    self.charge_start_time, self.charge_duration = 0, 0
                    
                    base_arrows = 1 + int((charge / 1500) * 5)
                    total_arrows = base_arrows + self.bonus_scatter
                    spread = math.radians(15 * total_arrows) 
                    start_angle = angle - spread / 2
                    step = spread / max(1, total_arrows - 1) if total_arrows > 1 else 0
                    for i in range(total_arrows):
                        arr_angle = start_angle + step * i if total_arrows > 1 else angle
                        bullets_group.add(MagicArrow(shoot_x, shoot_y, arr_angle, actual_dmg, self, enemies_group, False))
                    if is_skill:
                        for i in range(total_arrows):
                            arr_angle = start_angle + step * i if total_arrows > 1 else angle
                            bullets_group.add(MagicArrow(clone_x, clone_y, arr_angle, actual_dmg, self, enemies_group, True))
                return []

        self.charge_start_time = 0 
        if not mouse_held: return []
        if current_time - self.last_shoot_time < actual_cd: return []
        self.last_shoot_time = current_time
        
        if weapon["type"] == "grenade":
            dist = math.hypot(target_x - shoot_x, target_y - shoot_y)
            if dist > 500:
                target_x = shoot_x + (target_x - shoot_x) * 500 / dist
                target_y = shoot_y + (target_y - shoot_y) * 500 / dist
            grenades_group.add(ThrownGrenade(shoot_x, shoot_y, target_x, target_y, actual_dmg, actual_base_dmg, self, enemies_group, effects_group, crates_group, items_group, global_weapon_images, coins_group))
            if is_skill: grenades_group.add(ThrownGrenade(clone_x, clone_y, target_x + random.randint(-50,50), target_y + random.randint(-50,50), actual_dmg, actual_base_dmg, self, enemies_group, effects_group, crates_group, items_group, global_weapon_images, coins_group))
            return []

        if weapon["type"] == "pistol":
            bullets_group.add(Bullet(shoot_x, shoot_y, angle, actual_dmg, self, False))
            if is_skill:
                extra = self.bonus_scatter
                total = 3 + extra
                spread = math.radians(10 * total)
                s_ang = angle - spread/2
                st = spread / (total - 1)
                for i in range(total): bullets_group.add(Bullet(clone_x, clone_y, s_ang + st * i, actual_dmg, self, True))
            elif self.bonus_scatter > 0:
                total = 1 + self.bonus_scatter
                spread = math.radians(10 * total)
                s_ang = angle - spread/2
                st = spread / (total - 1)
                for i in range(total): bullets_group.add(Bullet(shoot_x, shoot_y, s_ang + st * i, actual_dmg, self, False))
            return [] 
            
        elif weapon["type"] == "melee":
            self.melee_swing_timer = 12 
            effects_group.add(MeleeSwingEffect(shoot_x, shoot_y, actual_range, angle, global_weapon_images.get(weapon["name"]), False))
            attacks.append(("melee", shoot_x, shoot_y, angle, actual_range, actual_dmg))
            if is_skill:
                effects_group.add(MeleeSwingEffect(clone_x, clone_y, actual_range, angle, global_weapon_images.get(weapon["name"]), True))
                attacks.append(("melee", clone_x, clone_y, angle, actual_range, actual_dmg))
            attack_rect = pygame.Rect(shoot_x - actual_range, shoot_y - actual_range, actual_range * 2, actual_range * 2)
            for bullet in enemy_bullets_group:
                if attack_rect.colliderect(bullet.rect): bullet.kill()
                
        elif weapon["type"] == "flamethrower":
            effects_group.add(FlameEffect(shoot_x, shoot_y, actual_range, angle, False))
            attacks.append(("flame", shoot_x, shoot_y, angle, actual_range, actual_dmg))
            if is_skill:
                effects_group.add(FlameEffect(clone_x, clone_y, actual_range, angle, True))
                attacks.append(("flame", clone_x, clone_y, angle, actual_range, actual_dmg))
        return attacks

    def draw_weapon(self, surface, camera_x, camera_y, mx, my, global_weapon_images):
        if not self.weapons or self.melee_swing_timer > 0: return 
        if self.current_weapon == self.stolen_weap_idx: return
        
        weapon = self.weapons[self.current_weapon]
        weapon_name = weapon["name"]
        weapon_img = global_weapon_images.get(weapon_name)
        if not weapon_img: return
        
        wx, wy = self.rect.centerx, self.rect.centery
        target_x, target_y = mx + camera_x, my + camera_y
        angle = math.atan2(target_y - wy, target_x - wx)
        degree = math.degrees(-angle)
        
        if mx < SCREEN_WIDTH // 2: weapon_img = pygame.transform.flip(weapon_img, False, True)
        rotated_img = pygame.transform.rotate(weapon_img, degree)
        
        forward_offset = 20
        base_wx = wx - camera_x + math.cos(angle) * forward_offset
        base_wy = wy - camera_y + math.sin(angle) * forward_offset
        
        if self.skill_timer > 0:
            perp_angle = angle + math.pi/2
            side_offset = 10 
            w_x = base_wx + math.cos(perp_angle) * (side_offset/2) - 4
            w_y = base_wy + math.sin(perp_angle) * (side_offset/2) 
            c_x = base_wx - math.cos(perp_angle) * (side_offset/2) + 10
            c_y = base_wy - math.sin(perp_angle) * (side_offset/2) + 7
            clone_img = rotated_img.copy()
            clone_img.fill((200, 150, 255), special_flags=pygame.BLEND_RGB_MULT) 
            surface.blit(clone_img, clone_img.get_rect(center=(c_x, c_y)))
            surface.blit(rotated_img, rotated_img.get_rect(center=(w_x, w_y)))
        else: surface.blit(rotated_img, rotated_img.get_rect(center=(base_wx, base_wy)))
            
        if weapon["type"] == "bow" and self.charge_start_time > 0:
            charge_ratio = min(1.0, self.charge_duration / 1500.0)
            bar_w, bar_h = 40, 6
            bar_x = self.rect.centerx - camera_x - bar_w//2
            bar_y = self.rect.top - camera_y - 15
            pygame.draw.rect(surface, GRAY, (bar_x, bar_y, bar_w, bar_h))
            c_color = RED if charge_ratio >= 1.0 else YELLOW
            pygame.draw.rect(surface, c_color, (bar_x, bar_y, int(bar_w * charge_ratio), bar_h))
            
        if getattr(self, "is_laser_charging", False) and self.laser_charge_duration > 0 and weapon["type"] in ["pistol", "bow"]:
            # 【红点延拓动画修改拉低进度阈值倍缩配合同等于实体计算区倍速 (除于 2500)，体验逐渐发亮增深的效果】
            aim_len = min(1500, 50 + (self.laser_charge_duration/3500.0) * 1200)
            end_x = base_wx + math.cos(angle) * aim_len
            end_y = base_wy + math.sin(angle) * aim_len
            pygame.draw.line(surface, (255, 100, 100, 180), (base_wx, base_wy), (end_x, end_y), max(1, int(self.laser_charge_duration/300)))
class MagicArrow(pygame.sprite.Sprite):
    def __init__(self, x, y, angle, damage, player, enemies_group, is_skill=False):
        super().__init__()
        self.angle, self.speed, self.damage = angle, 12, int(damage)
        self.player, self.enemies = player, enemies_group
        self.bounces = 1 if player.has_bounce and debuffs["buff_disable"] == 0 else 0
        color = PURPLE if is_skill else (0, 255, 255)
        
        # 🖼️👉 【可替换贴图：魔法箭】
        self.original_img = load_frames(["magic_arrow.png"], color, (25, 8), "rect")[0]
        
        self.image = pygame.transform.rotate(self.original_img, math.degrees(-self.angle))
        self.rect = self.image.get_rect(center=(x, y))
        self.vx = math.cos(self.angle) * self.speed
        self.vy = math.sin(self.angle) * self.speed

    def update(self):
        closest_enemy, min_dist = None, 300 
        for e in self.enemies:
            d = math.hypot(e.rect.centerx - self.rect.centerx, e.rect.centery - self.rect.centery)
            if d < min_dist: closest_enemy, min_dist = e, d
                
        if closest_enemy:
            target_angle = math.atan2(closest_enemy.rect.centery - self.rect.centery, closest_enemy.rect.centerx - self.rect.centerx)
            diff = (target_angle - self.angle + math.pi) % (math.pi * 2) - math.pi
            self.angle += max(-0.15, min(0.15, diff))
            self.vx, self.vy = math.cos(self.angle) * self.speed, math.sin(self.angle) * self.speed
            self.image = pygame.transform.rotate(self.original_img, math.degrees(-self.angle))
            self.rect = self.image.get_rect(center=self.rect.center)

        self.rect.x += self.vx
        if is_wall(self.rect.centerx, self.rect.centery):
            if self.bounces > 0: self.rect.x -= self.vx; self.vx = -self.vx; self.angle = math.atan2(self.vy, self.vx); self.bounces -= 1
            else: self.kill(); return
        self.rect.y += self.vy
        if is_wall(self.rect.centerx, self.rect.centery):
            if self.bounces > 0: self.rect.y -= self.vy; self.vy = -self.vy; self.angle = math.atan2(self.vy, self.vx); self.bounces -= 1
            else: self.kill()

# ================= 物资掉落=================
class GroundItem(pygame.sprite.Sprite):
    def __init__(self, x, y, item_type, weapon_data=None, weapon_img=None):
        super().__init__()
        self.item_type, self.weapon_data = item_type, weapon_data
        if item_type == "potion":
            # 🖼️👉 【可替换贴图：血瓶】
            self.image = load_frames(["饮料瓶.png"], (255,105,180), (80,80), "circle")[0]
        else:
            if weapon_img:
                new_w, new_h = int(max(20, weapon_img.get_width() * 1.1)), int(max(10, weapon_img.get_height() * 1.1))
                self.image = pygame.transform.scale(weapon_img, (new_w, new_h))
            else:
                self.image = load_frames(["weapon_drop.png"], GRAY, (30,30), "rect")[0]
        self.rect = self.image.get_rect(center=(x, y))

    def draw_prompt(self, surface, camera_x, camera_y):
        txt = f"按[F]拾取: {self.weapon_data['name']}" if self.item_type == "weapon" else "按[F]拾取 [恢复补给]"
        surf = font_base.render(txt, True, WHITE)
        surface.blit(surf, (self.rect.centerx - camera_x - surf.get_width()//2, self.rect.y - camera_y - 25))

class WeaponStand(pygame.sprite.Sprite):
    def __init__(self, x, y, w_data, w_img):
        super().__init__()
        # 🖼️👉 【可替换贴图：特殊武器商店-武器基座/展台】
        self.base_img = load_frames(["weapon_stand.png"], GRAY, (60, 20), "rect")[0]
        self.w_data = w_data
        self.w_img = w_img
        if w_img:
            new_w, new_h = int(max(20, w_img.get_width() * 1.2)), int(max(10, w_img.get_height() * 1.2))
            self.scaled_w = pygame.transform.scale(w_img, (new_w, new_h))
        self.price = random.randint(40, 80)
        
        self.rect = pygame.Rect(x-30, y-10, 60, 60)
        self.rect.center = (x, y)
        self.time_offset = random.random() * math.pi * 2
        self.image = pygame.Surface((1,1), pygame.SRCALPHA)
        
    def draw_prompt(self, surface, camera_x, camera_y):
        txt = f"按[F] 购买 | $ {self.price} | {self.w_data['name']}"
        surf = font_base.render(txt, True, YELLOW)
        surface.blit(surf, (self.rect.centerx - camera_x - surf.get_width()//2, self.rect.y - camera_y - 30))

    def draw(self, surface, camera_x, camera_y):
        draw_x = self.rect.centerx - camera_x - self.base_img.get_width() // 2
        draw_y = self.rect.centery - camera_y - self.base_img.get_height() // 2 + 10
        surface.blit(self.base_img, (draw_x, draw_y))
        
        if hasattr(self, 'scaled_w'):
            w_draw_y = draw_y - 20 + math.sin(pygame.time.get_ticks() / 150 + self.time_offset) * 5
            surface.blit(self.scaled_w, (self.rect.centerx - camera_x - self.scaled_w.get_width()//2, w_draw_y))

class Crate(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        # 🖼️👉 【可替换贴图：普通箱子 】
        self.image = load_frames(["箱子.png"], (160, 100, 50), (80, 80), "rect")[0]
        self.rect = pygame.Rect(0, 0, 46, 46)
        self.rect.center = (x, y)
        self.hp = 30

    def take_damage(self, amount, items_group, effects_group, global_weapon_images, coins_group=None):
        if self.hp <= 0: return 
        self.hp -= int(amount)
        effects_group.add(DamageText(self.rect.centerx, self.rect.top, amount))
        if self.hp <= 0:
            self.kill()
            rand = random.random()
            if rand < 0.2:  
                items_group.add(GroundItem(self.rect.centerx, self.rect.centery, "potion"))
            elif rand < 0.7 and coins_group is not None:
                spawn_coins(self.rect.centerx, self.rect.centery, is_boss=True, floor=2, coins_group=coins_group)

    def draw(self, surface, camera_x, camera_y):
        draw_x = self.rect.centerx - camera_x - self.image.get_width() // 2
        draw_y = self.rect.centery - camera_y - self.image.get_height() // 2
        surface.blit(self.image, (draw_x, draw_y))            

class SpecialCrate(Crate):
    def __init__(self, x, y):
        super().__init__(x, y)
        # 🖼️👉 【可替换贴图：武器箱】
        self.image = load_frames(["特殊武器宝箱.png"], (255, 215, 0), (100, 100), "rect")[0] 
        self.rect = pygame.Rect(0, 0, 60, 60)
        self.rect.center = (x, y)
        self.hp = 50 
        
    def take_damage(self, amount, items_group, effects_group, global_weapon_images, coins_group=None):
        if self.hp <= 0: return 
        self.hp -= int(amount)
        effects_group.add(DamageText(self.rect.centerx, self.rect.top, amount))
        if self.hp <= 0:
            self.kill()
            w_type = random.choice([
                {"type": "pistol", "name": "强力手枪", "damage": 35, "cd": 250},
                {"type": "melee", "name": "近战小刀", "damage": 30, "range": 80, "cd": 400},
                {"type": "melee", "name": "大刀", "damage": 70, "range": 140, "cd": 800},
                {"type": "pistol", "name": "机关枪", "damage": 15, "cd": 100},
                {"type": "flamethrower", "name": "火焰枪", "damage": 15, "range": 150, "cd": 600},
                {"type": "bow", "name": "魔法弓", "damage": 65, "cd": 150},
                {"type": "grenade", "name": "手榴弹", "damage": 70, "cd": 600} 
            ])
            w_img = global_weapon_images.get(w_type["name"])
            items_group.add(GroundItem(self.rect.centerx, self.rect.centery, "weapon", w_type, w_img))

# ================= 敌人属性=================
class Enemy(pygame.sprite.Sprite):
    def __init__(self, x, y, hp, floor):
        super().__init__()
        #敌人实际血量计算    ↓
        self.max_hp = hp * difficulty_mult["hp"] * (1 + floor * 0.3)
        self.hp = self.max_hp
        self.speed = 2.0 + (floor * 0.2) * difficulty_mult["spd"]
        self.damage = max(1, int(1 * difficulty_mult["dmg"] * (1 + floor * 0.1)))
        
        # 🖼️👉 【可替换贴图：第一大关/通用 近战敌人】
        self.frames = load_frames(["enemy_run.png"], RED, (35, 35), "circle")
        
        self.image = self.frames[0]
        self.rect = self.image.get_rect(center=(x, y))
        self.is_exploded, self.burn_duration, self.burn_timer = False, 0, 0
        self.burn_dmg = 0

    def take_damage(self, amount, is_true_damage=False, **kwargs):
        if is_true_damage: self.hp -= amount
        else:
            if getattr(self, 'shield', 0) > 0:
                dmg_taken = min(self.shield, amount)
                self.shield -= dmg_taken
                self.hp -= (amount - dmg_taken)
            else: self.hp -= amount

    def update(self, px, py, crates_group=None, enemies_group=None, effects_group=None, player=None, **kwargs):
        dx, dy = px - self.rect.centerx, py - self.rect.centery
        dist = math.hypot(dx, dy)
        if dist > 0:
            vx, vy = (dx / dist) * self.speed, (dy / dist) * self.speed
            self.rect.centerx += vx
            if is_wall(self.rect.centerx + (15 if vx>0 else -15), self.rect.centery) or (crates_group and pygame.sprite.spritecollideany(self, crates_group)):
                self.rect.centerx -= vx
            self.rect.centery += vy
            if is_wall(self.rect.centerx, self.rect.centery + (15 if vy>0 else -15)) or (crates_group and pygame.sprite.spritecollideany(self, crates_group)):
                self.rect.centery -= vy

    def draw_hp(self, surface, camera_x, camera_y):
        pygame.draw.rect(surface, BLACK, (self.rect.x - camera_x, self.rect.y - camera_y - 10, 30, 5))
        pygame.draw.rect(surface, RED, (self.rect.x - camera_x, self.rect.y - camera_y - 10, 30 * max(0, self.hp / self.max_hp), 5))

    def explode(self, enemies_group, player, effects_group):
        if self.is_exploded or not player.has_explosion: return
        self.is_exploded = True
        
        final_ex_dmg = int(player.explosion_damage_base * player.bonus_explosion_mult) 
        radius = int(50 * player.explosion_radius_mult)
        if getattr(player, "has_large_explosion", False):
            radius *= 2 
            
        effects_group.add(ExplosionEffect(self.rect.centerx, self.rect.centery, final_ex_dmg, radius))
        check_x, check_y = int(self.rect.centerx - radius), int(self.rect.centery - radius)
        rect = pygame.Rect(check_x, check_y, int(radius * 2), int(radius * 2))
        
        for enemy in enemies_group:
            if enemy != self and rect.colliderect(enemy.rect):
                if math.hypot(enemy.rect.centerx - self.rect.centerx, enemy.rect.centery - self.rect.centery) <= radius:
                    enemy.take_damage(final_ex_dmg)
                    effects_group.add(DamageText(enemy.rect.centerx, enemy.rect.top, final_ex_dmg))

class RangedEnemy(Enemy):
    def __init__(self, x, y, hp, floor):
        super().__init__(x, y, hp * 0.6, floor)
        
        # 🖼️👉 【可替换贴图：第一大关/通用 远程敌人 】 
        self.frames = load_frames(["ranged_enemy.png"], BLUE, (30, 30), "circle")
        
        self.image = self.frames[0]
        self.attack_range, self.attack_cd, self.attack_timer, self.is_attacking = 400, max(80, 150 - floor * 5), 0, False

    def update(self, px, py, enemy_bullets_group=None, crates_group=None, enemies_group=None, effects_group=None, player=None, **kwargs):
        dist = math.hypot(px - self.rect.centerx, py - self.rect.centery)
        self.attack_timer += 1
        if dist < self.attack_range and self.attack_timer >= self.attack_cd:
            self.is_attacking = True; self.attack_timer = 0
            if enemy_bullets_group is not None:
                enemy_bullets_group.add(EnemyBullet(self.rect.centerx, self.rect.centery, math.atan2(py - self.rect.centery, px - self.rect.centerx), speed=5, damage=self.damage, b_type=0))
        else: self.is_attacking = False
        if not self.is_attacking and dist > 50: 
            super().update(px, py, crates_group=crates_group, enemies_group=enemies_group, effects_group=effects_group, player=player)

class HealerEnemy(Enemy):
    def __init__(self, x, y, hp, floor):
        super().__init__(x, y, hp * 0.8, floor)
        # 🖼️👉 【可替换贴图：第一大关/通用 回血敌人】 
        self.frames = load_frames(["healer_enemy.png"], PALE_YELLOW, (35, 35), "circle")
        
        # 🖼️👉 【可替换贴图：第一大关/通用 回血施法动画】
        self.heal_frames = load_frames(["healer_cast1.png", "healer_cast2.png"], CYAN, (35, 35), "rect")
        
        self.image = self.frames[0]
        self.heal_cd = 120 
        self.casting_timer = 0
        
    def update(self, px, py, crates_group=None, enemies_group=None, effects_group=None, player=None, **kwargs):
        if self.casting_timer > 0:
            self.casting_timer -= 1
            f_idx = min(int(((120 - self.casting_timer) / 120) * len(self.heal_frames)), len(self.heal_frames)-1)
            self.image = self.heal_frames[f_idx]
            
            if self.casting_timer <= 0:
                for en in enemies_group:
                    if en != self and en.hp > 0 and en.hp < en.max_hp:
                        heal_amt = en.max_hp * 0.30
                        en.hp = min(en.max_hp, en.hp + heal_amt)
                        if effects_group is not None:
                            effects_group.add(DamageText(en.rect.centerx, en.rect.top, heal_amt, is_heal=True))
                self.heal_cd = 300 
                self.image = self.frames[0]
            return
        else:
            self.image = self.frames[int(pygame.time.get_ticks() / 150) % len(self.frames)]

        if self.heal_cd > 0: self.heal_cd -= 1
        
        if self.heal_cd <= 0 and any(en.hp < en.max_hp and en.hp > 0 for en in enemies_group if en != self):
            self.casting_timer = 120 
            return
            
        dx, dy = px - self.rect.centerx, py - self.rect.centery
        dist = math.hypot(dx, dy)
        if dist < 400 and dist > 0:
            vx, vy = -(dx / dist) * self.speed, -(dy / dist) * self.speed
            self.rect.centerx += vx
            if is_wall(self.rect.centerx + (15 if vx>0 else -15), self.rect.centery) or (crates_group and pygame.sprite.spritecollideany(self, crates_group)):
                self.rect.centerx -= vx
            self.rect.centery += vy
            if is_wall(self.rect.centerx, self.rect.centery + (15 if vy>0 else -15)) or (crates_group and pygame.sprite.spritecollideany(self, crates_group)):
                self.rect.centery -= vy

class Boss(Enemy):
    def __init__(self, x, y, hp, floor, is_tutorial=False):
        super().__init__(x, y, hp, floor) 
        
        if is_tutorial:
            self.max_hp = 300
            self.hp = self.max_hp
            self.damage = 2

        self.floor = floor
        #护盾厚度设置
        self.max_shield = self.max_hp * 0.5  
        self.shield = self.max_shield
        self.shield_broken = False 
        
        self.is_senior = (floor % 10 == 0) and not is_tutorial

        if self.is_senior:
            # 🖼️👉 【可替换贴图：第一大关-高级 BOSS】 
            self.frames = load_frames(["boss_senior.png"], BOSS_COLOR, (120, 120), "rect")
            # 🖼️👉 【可替换贴图：第一大关-高级 BOSS施法前摇】
            self.cast_frames = load_frames(["boss_senior_cast1.png", "boss_senior_cast2.png"], (200, 0, 200), (120, 120), "rect")
            # 🖼️👉 【可替换贴图：第一大关-高级 Boss回血动画】
            self.boss_heal_frames = load_frames(["boss_senior_heal1.png", "boss_senior_heal2.png", "boss_senior_heal3.png"], (0, 255, 100), (120, 120), "rect")
        else:
            # 🖼️👉 【可替换贴图：第一大关-初级 BOSS】 
            self.frames = load_frames(["boss_junior.png"], BOSS_COLOR, (100, 100), "rect")
            # 🖼️👉 【可替换贴图：第一大关-初级 BOSS施法前摇】
            self.cast_frames = load_frames(["boss_junior_cast1.png", "boss_junior_cast2.png"], (200, 0, 200), (100, 100), "rect")
            # 🖼️👉 【可替换贴图：第一大关-初级 Boss回血动画】
            self.boss_heal_frames = load_frames(["boss_junior_heal1.png", "boss_junior_heal2.png", "boss_junior_heal3.png"], (0, 255, 100), (100, 100), "rect")
            
        self.image = self.frames[0]
        self.rect = self.image.get_rect(center=(x, y))
        self.shoot_timer = 0
        self.shoot_cd = max(20, 100 - floor * 5)
        self.skill_timer = 0
        self.skill_cd = max(150, 300 - floor * 8)
        self.dash_distance, self.aoe_radius, self.aoe_damage = 250, 200, max(3, self.damage * 2)
        
        self.dash_warning_timer, self.dash_target = 0, None
        self.casting_timer = 0
        self.boss_healing_timer = 0  
        self.casting_skill = None
        self.skill_text = ""

        if not self.is_senior:
            self.available_skills = ["dash", "summon"]
        else:
            self.available_skills = ["dash", "summon", "aoe", "boss_heal", "vision", "silence"]

        self.bullet_weights = [1.0, 0.0, 0.0]
        if floor >= 15: self.bullet_weights = [0.6, 0.4, 0.0]
        if floor >= 25: self.bullet_weights = [0.4, 0.3, 0.3]

    def update(self, px, py, enemy_bullets_group=None, effects_group=None, player=None, crates_group=None, enemies_group=None, **kwargs):
        if self.shield <= 0:
            self.shield_broken = True
            self.shield = 0
        if not self.shield_broken and self.shield < self.max_shield:
            #护盾恢复速度
            regen_speed = 500 + self.floor * 30 
            self.shield = min(self.max_shield, self.shield + regen_speed / 120)

        if getattr(self, "boss_healing_timer", 0) > 0:
            self.boss_healing_timer -= 1
            f_idx = min(int(((300 - self.boss_healing_timer)/300)*len(self.boss_heal_frames)), len(self.boss_heal_frames)-1)
            self.image = self.boss_heal_frames[f_idx]
            self.hp = min(self.max_hp, self.hp + (self.max_hp * 0.30) / 300.0)
            if self.boss_healing_timer % 30 == 0 and effects_group is not None:
                effects_group.add(DamageText(self.rect.centerx, self.rect.top, self.max_hp*0.2/10, is_heal=True))
                
            dx, dy = px - self.rect.centerx, py - self.rect.centery
            dist = math.hypot(dx, dy)
            if dist > 0:
                vx, vy = -(dx/dist)*self.speed*1.3, -(dy/dist)*self.speed*1.3
                self.rect.centerx += vx
                if is_wall(self.rect.centerx + (30 if vx>0 else -30), self.rect.centery): self.rect.centerx -= vx
                self.rect.centery += vy
                if is_wall(self.rect.centerx, self.rect.centery + (30 if vy>0 else -30)): self.rect.centery -= vy
                
            if self.boss_healing_timer <= 0:
                self.skill_text = ""
                self.image = self.frames[0]
            return

        if self.casting_timer > 0:
            self.casting_timer -= 1
            frame_idx = int((60 - self.casting_timer) / 60 * len(self.cast_frames))
            frame_idx = min(frame_idx, len(self.cast_frames)-1)
            self.image = self.cast_frames[frame_idx].copy()

            if self.casting_timer <= 0:
                skill_type = self.casting_skill
                if skill_type == "dash": self.dash_warning_timer, self.dash_target = 60, (px, py)
                elif skill_type == "boss_heal":
                    self.boss_healing_timer = 300 
                elif skill_type == "aoe": effects_group.add(BossAoeEffect(player.rect.centerx, player.rect.centery, self.aoe_radius, self.aoe_damage, player))
                elif skill_type == "vision": debuffs["vision_reduce"] = 300
                elif skill_type == "silence": debuffs["buff_disable"] = 300
                elif skill_type == "summon" and enemies_group is not None:
                    num_minions = min(6, 2 + self.floor // 10)
                    for _ in range(num_minions):
                        mx = self.rect.centerx + random.randint(-100, 100)
                        my = self.rect.centery + random.randint(-100, 100)
                        if random.random() < 0.5:
                            enemies_group.add(RangedEnemy(mx, my, 30 + self.floor*15, self.floor))
                        else:
                            enemies_group.add(Enemy(mx, my, 30 + self.floor*20, self.floor))
                if skill_type != "boss_heal": 
                    self.skill_text = "" 
            return 

        if self.dash_warning_timer > 0:
            self.dash_warning_timer -= 1
            self.image = self.frames[0].copy()
            if (self.dash_warning_timer // 5) % 2 == 0:
                self.image.fill((255, 255, 255, 150), special_flags=pygame.BLEND_RGBA_ADD)
            if self.dash_warning_timer <= 0 and self.dash_target:
                dist = math.hypot(self.dash_target[0] - self.rect.centerx, self.dash_target[1] - self.rect.centery)
                if dist > 0:
                    nx = self.rect.centerx + ((self.dash_target[0] - self.rect.centerx) / dist) * self.dash_distance
                    ny = self.rect.centery + ((self.dash_target[1] - self.rect.centery) / dist) * self.dash_distance
                    if not is_wall(nx, ny): self.rect.centerx, self.rect.centery = nx, ny
        else:
            self.image = self.frames[0]
            super().update(px, py, crates_group=crates_group, enemies_group=enemies_group, effects_group=effects_group, player=player)
            
        self.shoot_timer += 1
        if self.shoot_timer >= self.shoot_cd and enemy_bullets_group is not None:
            self.shoot_timer = 0
            angle = math.atan2(py - self.rect.centery, px - self.rect.centerx)
            b_type = random.choices([0, 1, 2], weights=self.bullet_weights)[0]
            for i in range(-3, 4):
                if i % 2 == 0: enemy_bullets_group.add(EnemyBullet(self.rect.centerx, self.rect.centery, angle + i * 0.15, speed=6, damage=self.damage, b_type=b_type, is_boss=True))
        
        self.skill_timer += 1
        if self.skill_timer >= self.skill_cd:
            self.skill_timer = 0
            self.casting_skill = random.choice(self.available_skills)
            self.casting_timer = 60 
            if self.casting_skill == "dash": self.skill_text = "【警告】 锁定冲刺"
            elif self.casting_skill == "aoe": self.skill_text = "【警告】 致命毒阵"
            elif self.casting_skill == "boss_heal": self.skill_text = "【警告】 生命恢复"
            elif self.casting_skill == "vision": self.skill_text = "【警告】 剥夺视野！"
            elif self.casting_skill == "silence": self.skill_text = "【警告】 沉默"
            elif self.casting_skill == "summon": self.skill_text = "【警告】 召唤仆从"

    def draw_hp(self, surface, camera_x, camera_y):
        pygame.draw.rect(surface, BLACK, (SCREEN_WIDTH//2 - 250, 20, 500, 25))
        hp_ratio = max(0, self.hp / self.max_hp)
        hp_width = 500 * hp_ratio
        pygame.draw.rect(surface, BOSS_COLOR, (SCREEN_WIDTH//2 - 250, 20, hp_width, 25))
        
        if self.max_shield > 0:
            shield_ratio = max(0, self.shield / self.max_shield)
            shield_width = 500 * shield_ratio
            pygame.draw.rect(surface, BLUE, (SCREEN_WIDTH//2 - 250, 20, shield_width, 25))
            
        pygame.draw.rect(surface, WHITE, (SCREEN_WIDTH//2 - 250, 20, 500, 25), 3)
        txt = font_large.render(f" Boss血量：{int(max(0, self.hp))}  护盾: {int(max(0, self.shield))}", True, WHITE)
        surface.blit(txt, (SCREEN_WIDTH//2 - txt.get_width()//2, 22))

        if getattr(self, "skill_text", "") != "":
            warning_txt = font_large.render(self.skill_text, True, RED)
            surface.blit(warning_txt, (SCREEN_WIDTH//2 - warning_txt.get_width()//2, 85))


# === 分层与进度的分关专用独立兵种类设定区 ===

class EnemyStage2(Enemy):
    def __init__(self, x, y, hp, floor):
        super().__init__(x, y, hp, floor)
        # 🖼️👉 【可替换贴图：第二大关 近战敌人】
        self.frames = load_frames(["enemy_run.png"], RED, (35, 35), "circle")
        self.image = self.frames[0]
        self.speed = 1.1 + (floor * 0.1) * difficulty_mult["spd"] 
        self.melee_cd = 100
        self.melee_timer = 0
        self.weapon_img = load_frames(["soldier_blade.png"], GRAY, (40, 15), "rect")[0]

    def update(self, px, py, crates_group=None, enemies_group=None, effects_group=None, player=None, **kwargs):
        dx, dy = px - self.rect.centerx, py - self.rect.centery
        dist = math.hypot(dx, dy)
        
        if dist > 55:
            vx, vy = (dx / dist) * self.speed, (dy / dist) * self.speed
            self.rect.centerx += vx
            if is_wall(self.rect.centerx + (15 if vx>0 else -15), self.rect.centery) or (crates_group and pygame.sprite.spritecollideany(self, crates_group)):
                self.rect.centerx -= vx
            self.rect.centery += vy
            if is_wall(self.rect.centerx, self.rect.centery + (15 if vy>0 else -15)) or (crates_group and pygame.sprite.spritecollideany(self, crates_group)):
                self.rect.centery -= vy
                
        self.melee_timer += 1
        if self.melee_timer >= self.melee_cd and dist < 85:
            self.melee_timer = 0
            ang = math.atan2(dy, dx)
            if effects_group is not None:
                effects_group.add(MeleeSwingEffect(self.rect.centerx, self.rect.centery, 70, ang, self.weapon_img, False, boss_override_color=(200,80,80)))

class ShieldEnemyStage2(Enemy):
    def __init__(self, x, y, hp, floor):
        super().__init__(x, y, hp, floor)
        # 🖼️👉 【可替换贴图：第二大关 盾兵 】 
        self.frames = load_frames(["enemy_run.png"], DARK_GRAY, (35, 35), "circle")
        self.image = self.frames[0]
        self.is_shield_soldier = True 
        self.shield_img = load_frames(["shield_black.png"], BLACK, (15, 50), "rect")[0]
        self.facing_angle = 0
        self.speed = 0.9 + (floor * 0.1) * difficulty_mult["spd"] 

    def update(self, px, py, crates_group=None, enemies_group=None, effects_group=None, player=None, **kwargs):
        super().update(px, py, crates_group=crates_group, enemies_group=enemies_group, effects_group=effects_group, player=player)
        self.facing_angle = math.atan2(py - self.rect.centery, px - self.rect.centerx)

    def draw_hp(self, surface, camera_x, camera_y):
        super().draw_hp(surface, camera_x, camera_y)
        sh = pygame.transform.rotate(self.shield_img, math.degrees(-self.facing_angle))
        ox = math.cos(self.facing_angle) * 18
        oy = math.sin(self.facing_angle) * 18
        rect = sh.get_rect(center=(self.rect.x - camera_x + self.rect.width//2 + ox, self.rect.y - camera_y + self.rect.height//2 + oy))
        surface.blit(sh, rect)

class HealerEnemyStage2(HealerEnemy):
    def __init__(self, x, y, hp, floor):
        super().__init__(x, y, hp, floor)
        # 🖼️👉 【可替换贴图：第二大关 回血敌人 及 动画 】 
        self.frames = load_frames(["healer_enemy.png"], PALE_YELLOW, (35, 35), "circle")
        self.heal_frames = load_frames(["healer_cast1.png", "healer_cast2.png"], CYAN, (35, 35), "rect")
        self.image = self.frames[0]

class BossStage2(Boss):
    def __init__(self, x, y, hp, floor, is_tutorial=False):
        super().__init__(x, y, hp, floor, is_tutorial)
        self.is_senior = (floor % 10 == 0) and not is_tutorial
        #BOSS贴图
        if self.is_senior:
            self.frames = load_frames(["boss_st2_senior.png"], BOSS_COLOR, (120, 120), "rect")
            # 贴图 👇  盾和冲刺
            self.available_skills = ["heavy_slash", "steal_weapon", "sword_aura_buff", "phantom_dash", "invincible_shield"]
        else:
            self.frames = load_frames(["boss_st2_junior.png"], BOSS_COLOR, (100, 100), "rect")
            self.available_skills = ["heavy_slash", "phantom_dash", "invincible_shield"]  

        self.image = self.frames[0]
        
        # 大刀占位贴图
        self.boss_blade_img = load_frames(["boss_blade.png"], (255, 100, 100), (140, 40), "rect")

        if type(self.boss_blade_img) is list:
            self.boss_blade_img = self.boss_blade_img[0]
        
        # BOSS 血量
        self.max_hp = 3500 * (1 + floor * 0.3) 
        self.hp = self.max_hp
        # boss 盾
        self.max_shield = self.max_hp * 0.3  
        self.shield = self.max_shield

        self.melee_cd = max(35, 90 - floor * 3)
        self.melee_timer = 0
        self.skill_cd = max(180, 450 - floor * 6)
        
        self.boss2_heavy_warn = 0 
        self.heavy_aim_angle = 0
        self.boss_stolen_active_timer = 0 
        self.stolen_weap_data = None 
        self.has_aura_buff = 0

        self.phantom_dash_warn = 0
        self.dash_land_x = x
        self.dash_land_y = y

        self.is_shield_soldier = False
        self.invincible_shield_timer = 0 
        self.facing_angle = 0
        # 图片  盾图
        self.huge_shield_img = load_frames(["shield_black.png"], BLACK, (40, 140), "rect")[0]

        
    def update(self, px, py, enemy_bullets_group=None, effects_group=None, player=None, crates_group=None, enemies_group=None, **kwargs):
        # 随时索敌玩家坐标从而用于偏转黑盾面向！
        self.facing_angle = math.atan2(py - self.rect.centery, px - self.rect.centerx)

        if self.shield <= 0:
            self.shield_broken = True; self.shield = 0
        if not self.shield_broken and self.shield < self.max_shield:
            regen_speed = 500 + self.floor * 30 
            self.shield = min(self.max_shield, self.shield + regen_speed / 120)

        if self.invincible_shield_timer > 0:
            self.invincible_shield_timer -= 1
            self.is_shield_soldier = True 
        else:
            self.is_shield_soldier = False 

        # ---------------- 特殊硬直与起跳锁敌状态 ----------------
        
        if self.phantom_dash_warn > 0:
            self.phantom_dash_warn -= 1
            if self.phantom_dash_warn <= 0:
                self.skill_text = ""
                self.rect.centerx = self.dash_land_x
                self.rect.centery = self.dash_land_y
                
                fall_atk_rng = 130
                fall_atk_dmg = self.damage * 2.0
                fall_ang = math.atan2(py - self.dash_land_y, px - self.dash_land_x)
                if effects_group is not None:
                    effects_group.add(MeleeSwingEffect(self.dash_land_x, self.dash_land_y, fall_atk_rng, fall_ang, self.boss_blade_img, True, boss_override_color=(255,80,80)))
                
                if player and math.hypot(player.rect.centerx - self.dash_land_x, player.rect.centery - self.dash_land_y) <= fall_atk_rng:
                    df = (math.atan2(player.rect.centery - self.dash_land_y, player.rect.centerx - self.dash_land_x) - fall_ang + math.pi) % (2*math.pi) - math.pi
                    if abs(df) <= math.pi/2.5:
                        player.take_damage(fall_atk_dmg, effects_group)
                        screen_shake = 15 
            return 
            
        if self.boss2_heavy_warn > 0:
            self.boss2_heavy_warn -= 1
            if self.boss2_heavy_warn <= 0:
                self.skill_text = ""
                boss_dmg = int(self.damage * 4.5)
                heavy_atk_rng = 220 
                if effects_group is not None:
                    effects_group.add(MeleeSwingEffect(self.rect.centerx, self.rect.centery, heavy_atk_rng, self.heavy_aim_angle, self.boss_blade_img, True, boss_override_color=(255,0,0)))
                if player:
                    pd = math.hypot(player.rect.centerx - self.rect.centerx, player.rect.centery - self.rect.centery)
                    if pd <= heavy_atk_rng:
                        pa = math.atan2(player.rect.centery - self.rect.centery, player.rect.centerx - self.rect.centerx)
                        df = (pa - self.heavy_aim_angle + math.pi) % (2*math.pi) - math.pi
                        if abs(df) <= math.pi/2.5:
                            player.take_damage(boss_dmg, effects_group)
                            screen_shake = 20
            return 

        # ---------------- 基础状态 / 缴械 / 平A移动控制 ----------------

        if self.boss_stolen_active_timer > 0:
            self.boss_stolen_active_timer -= 1
            if self.boss_stolen_active_timer % 90 == 0 and enemy_bullets_group is not None:
                 a2p = math.atan2(py - self.rect.centery, px - self.rect.centerx)
                 enemy_bullets_group.add(EnemyBullet(self.rect.centerx, self.rect.centery, a2p + random.uniform(-0.1, 0.1), speed=7, damage=self.damage*0.5, b_type=0, is_boss=True))
            if self.boss_stolen_active_timer <= 0:
                 self.stolen_weap_data = None
                 if player: player.stolen_weap_idx = -1 
        
        if self.has_aura_buff > 0: self.has_aura_buff -= 1

        dx, dy = px - self.rect.centerx, py - self.rect.centery
        dist = math.hypot(dx, dy)
        
        if dist > 85:
            vx, vy = (dx / dist) * self.speed * 0.45, (dy / dist) * self.speed * 0.45
            self.rect.centerx += vx
            if is_wall(self.rect.centerx + (30 if vx>0 else -30), self.rect.centery): self.rect.centerx -= vx
            self.rect.centery += vy
            if is_wall(self.rect.centerx, self.rect.centery + (30 if vy>0 else -30)): self.rect.centery -= vy

        self.melee_timer += 1
        fire_threshold = 550 if self.has_aura_buff > 0 else 140
        if self.melee_timer >= self.melee_cd and dist < fire_threshold:
            self.melee_timer = 0
            ang = math.atan2(dy, dx)
            if effects_group is not None:
                effects_group.add(MeleeSwingEffect(self.rect.centerx, self.rect.centery, 130, ang, self.boss_blade_img, False, boss_override_color=(255,100,100)))
            if player and dist <= 130:
                pa = math.atan2(dy, dx)
                df = (pa - ang + math.pi) % (2*math.pi) - math.pi
                if abs(df) <= math.pi/2.5: player.take_damage(self.damage * 1.5, effects_group)
                
            if self.has_aura_buff > 0 and enemy_bullets_group is not None:
                enemy_bullets_group.add(BossSwordAuraBullet(self.rect.centerx, self.rect.centery, ang, self.damage * 1.8, 8, 90))
                
        self.skill_timer += 1
        if self.skill_timer >= self.skill_cd:
            self.skill_timer = 0
            pick = random.choice(self.available_skills)
            
            if pick == "heavy_slash":
                self.boss2_heavy_warn = 120 
                self.heavy_aim_angle = math.atan2(py - self.rect.centery, px - self.rect.centerx)
                self.skill_text = "【大范围劈砍】"
            
            elif pick == "phantom_dash":
                self.phantom_dash_warn = 60  
                valid_spot = False
                target_dist = 60 
                for _ang in [0, 90, 180, 270, 45, 135]:
                    rad = math.radians(_ang)
                    tx = px + math.cos(rad) * target_dist
                    ty = py + math.sin(rad) * target_dist
                    if not is_wall(tx, ty): 
                        self.dash_land_x, self.dash_land_y = tx, ty
                        valid_spot = True
                        break
                
                if not valid_spot: self.dash_land_x, self.dash_land_y = px, py  
                self.skill_text = "【突进猛压】"

            # 👇 新护盾
            elif pick == "invincible_shield":
                self.invincible_shield_timer = 15 * 60   # 持续十五秒
                self.skill_text = "【坚固堡垒】免疫远攻"
                
            elif pick == "steal_weapon" and player and len(player.weapons) > 0:
                robbed_id = random.randint(0, len(player.weapons)-1)
                player.stolen_weap_idx = robbed_id 
                self.stolen_weap_data = player.weapons[robbed_id]
                self.boss_stolen_active_timer = 600
                self.skill_text = "【缴械】"
                if effects_group is not None: effects_group.add(DamageText(player.rect.centerx, player.rect.top-40, "被收缴禁用武装", custom_color=(255, 0, 0), is_text=True))
                
            elif pick == "sword_aura_buff":
                self.has_aura_buff = 600 
                self.skill_text = "【附带剑气狂斩】"

    def kill(self):
        super().kill()

    def draw_hp(self, surface, camera_x, camera_y):
        super().draw_hp(surface, camera_x, camera_y)
        
        # -------- 画那把举起来的大黑实体防御盾！ ---------
        if getattr(self, "invincible_shield_timer", 0) > 0:
            sh = pygame.transform.rotate(self.huge_shield_img, math.degrees(-self.facing_angle))
            # 根据其巨大躯体拉开了格挡身距距离到圆心的距离: 60
            ox = math.cos(self.facing_angle) * 60 
            oy = math.sin(self.facing_angle) * 60
            rect = sh.get_rect(center=(self.rect.centerx - camera_x + ox, self.rect.centery - camera_y + oy))
            surface.blit(sh, rect)
        
        if self.boss2_heavy_warn > 0:
            if (self.boss2_heavy_warn // 10) % 2 == 0:
                r_surf = pygame.Surface((440, 440), pygame.SRCALPHA)
                h_atk_range = 220
                al, ar = self.heavy_aim_angle - math.pi/2.5, self.heavy_aim_angle + math.pi/2.5
                pnts = [(h_atk_range, h_atk_range)]
                for a in range(int(math.degrees(al)), int(math.degrees(ar)) + 1, 4):
                    rd = math.radians(a)
                    pnts.append((h_atk_range + math.cos(rd) * h_atk_range, h_atk_range + math.sin(rd) * h_atk_range))
                if len(pnts) > 2: pygame.draw.polygon(r_surf, (255, 0, 0, 100), pnts)
                surface.blit(r_surf, (self.rect.centerx - h_atk_range - camera_x, self.rect.centery - h_atk_range - camera_y))
                
        if self.phantom_dash_warn > 0:
            blink_rad = 130 
            circ_sur = pygame.Surface((blink_rad*2, blink_rad*2), pygame.SRCALPHA)
            pygame.draw.circle(circ_sur, (255, 50, 50, 60), (blink_rad, blink_rad), blink_rad) 
            in_r = int(blink_rad * (self.phantom_dash_warn / 60))
            if in_r > 5:
                pygame.draw.circle(circ_sur, (255, 100, 100, 200), (blink_rad, blink_rad), in_r, 4) 
            
            pygame.draw.circle(circ_sur, (255, 80, 80, 180), (blink_rad, blink_rad), 5)
            pygame.draw.line(circ_sur, (255, 80, 80, 180), (blink_rad-10, blink_rad), (blink_rad+10, blink_rad), 2)
            pygame.draw.line(circ_sur, (255, 80, 80, 180), (blink_rad, blink_rad-10), (blink_rad, blink_rad+10), 2)
            surface.blit(circ_sur, (self.dash_land_x - blink_rad - camera_x, self.dash_land_y - blink_rad - camera_y))

class EnemyStage3(Enemy):
    def __init__(self, x, y, hp, floor):
        super().__init__(x, y, hp, floor)
        # 🖼️👉 【可替换贴图：第三大关 近战敌人】 
        self.frames = load_frames(["enemy_run.png"], RED, (35, 35), "circle")
        self.image = self.frames[0]

class RangedEnemyStage3(RangedEnemy):
    def __init__(self, x, y, hp, floor):
        super().__init__(x, y, hp, floor)
        # 🖼️👉 【可替换贴图：第三大关 远程敌人 】 
        self.frames = load_frames(["ranged_enemy.png"], BLUE, (30, 30), "circle")
        self.image = self.frames[0]

class HealerEnemyStage3(HealerEnemy):
    def __init__(self, x, y, hp, floor):
        super().__init__(x, y, hp, floor)
        # 🖼️👉 【可替换贴图：第三大关 回血敌人 】 
        self.frames = load_frames(["healer_enemy.png"], PALE_YELLOW, (35, 35), "circle")
        self.heal_frames = load_frames(["healer_cast1.png", "healer_cast2.png"], CYAN, (35, 35), "rect")
        self.image = self.frames[0]

class BossStage3(Boss):
    def __init__(self, x, y, hp, floor, is_tutorial=False):
        super().__init__(x, y, hp, floor, is_tutorial)
        
        self.is_senior = (floor % 10 == 0) and not is_tutorial
        
        if self.is_senior:
            # 🖼️👉 【可替换贴图：第三大关-高级 BOSS】 
            self.frames = load_frames(["boss_st3_senior.png"], BOSS_COLOR, (120, 120), "rect")
            self.cast_frames = load_frames(["boss_st3_senior_cast1.png", "boss_st3_senior_cast2.png"], (200, 0, 200), (120, 120), "rect")
            self.boss_heal_frames = load_frames(["boss_st3_senior_heal1.png", "boss_st3_senior_heal2.png", "boss_st3_senior_heal3.png"], (0, 255, 100), (120, 120), "rect")
            self.available_skills = ["dash", "summon", "aoe", "boss_heal", "vision", "silence"]
        else:
            # 🖼️👉 【可替换贴图：第三大关-初级 BOSS】 
            self.frames = load_frames(["boss_st3_junior.png"], BOSS_COLOR, (100, 100), "rect")
            self.cast_frames = load_frames(["boss_st3_junior_cast1.png", "boss_st3_junior_cast2.png"], (200, 0, 200), (100, 100), "rect")
            self.boss_heal_frames = load_frames(["boss_st3_junior_heal1.png", "boss_st3_junior_heal2.png", "boss_st3_junior_heal3.png"], (0, 255, 100), (100, 100), "rect")
            self.available_skills = ["dash", "summon"]
            
        self.image = self.frames[0]


class EnemyBullet(pygame.sprite.Sprite):
    def __init__(self, x, y, angle, speed, damage, b_type=0, is_boss=False):
        super().__init__()
        self.b_type = b_type
        draw_r = 15 if is_boss else 6
        rect_size = draw_r * 2
        
        self.image = pygame.Surface((rect_size, rect_size), pygame.SRCALPHA)
        if b_type == 1:
            pygame.draw.circle(self.image, RED, (draw_r, draw_r), draw_r); pygame.draw.circle(self.image, YELLOW, (draw_r, draw_r), int(draw_r/2)); self.bounces = 2
        elif b_type == 2:
            pygame.draw.circle(self.image, DARK_GREEN, (draw_r, draw_r), draw_r); pygame.draw.circle(self.image, GREEN, (draw_r, draw_r), int(draw_r/3)); self.bounces = 0
        else:
            pygame.draw.circle(self.image, ORANGE, (draw_r, draw_r), draw_r); self.bounces = 0
            
        self.rect = self.image.get_rect(center=(x, y))
        self.speed, self.damage = speed * difficulty_mult["spd"], int(damage)
        self.vx, self.vy = math.cos(angle) * self.speed, math.sin(angle) * self.speed

    def update(self):
        self.rect.x += self.vx
        if is_wall(self.rect.centerx, self.rect.centery):
            if self.bounces > 0: self.rect.x -= self.vx; self.vx = -self.vx; self.bounces -= 1
            else: self.kill(); return
        self.rect.y += self.vy
        if is_wall(self.rect.centerx, self.rect.centery):
            if self.bounces > 0: self.rect.y -= self.vy; self.vy = -self.vy; self.bounces -= 1
            else: self.kill()


class Bullet(pygame.sprite.Sprite):
    def __init__(self, x, y, angle, damage, player, is_skill=False):
        super().__init__()
        color = PURPLE if is_skill else WHITE
        self.frames = load_frames(["bullet.png"], color, (8, 8), "circle")
        self.image = self.frames[0]
        self.rect = self.image.get_rect(center=(x, y))
        self.damage = int(damage)
        self.player = player
        self.vx, self.vy = math.cos(angle) * 15, math.sin(angle) * 15
        self.bounces = 1 if player.has_bounce and debuffs["buff_disable"] == 0 else 0

    def update(self):
        self.rect.x += self.vx
        if is_wall(self.rect.centerx, self.rect.centery):
            if self.bounces > 0: self.rect.x -= self.vx; self.vx = -self.vx; self.bounces -= 1
            else: self.kill(); return
        self.rect.y += self.vy
        if is_wall(self.rect.centerx, self.rect.centery):
            if self.bounces > 0: self.rect.y -= self.vy; self.vy = -self.vy; self.bounces -= 1
            else: self.kill()

class Coin(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        # 🖼️👉 【可替换贴图：金币】
        self.frames = load_frames(["金币1.png", "金币2.png", "金币4.png"], YELLOW, (45, 45), "circle")
        self.current_frame = 0
        self.image = self.frames[0]
        self.rect = self.image.get_rect(center=(x, y))
        self.base_y, self.time_offset = y, random.random() * math.pi * 2

    def update(self, player):
        self.current_frame += 0.2
        self.image = self.frames[int(self.current_frame) % len(self.frames)]
        
        if player.has_magnet and debuffs["buff_disable"] == 0:
            dx, dy = player.rect.centerx - self.rect.centerx, player.rect.centery - self.rect.centery
            dist = math.hypot(dx, dy)
            if dist < 300: 
                self.rect.centerx += (dx / dist) * 10; self.rect.centery += (dy / dist) * 10
                return
        self.rect.centery = self.base_y + math.sin(pygame.time.get_ticks() / 150 + self.time_offset) * 5

class Portal(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        # 🖼️👉 【可替换贴图：传送门 】 
        self.frames = load_frames(["传送门1.png", "传送门2.png", "传送门3.png", "传送门4.png"], PURPLE, (120, 120), "circle")
        self.current_frame = 0
        self.image = self.frames[0]
        self.rect = pygame.Rect(0, 0, 60, 60)
        self.rect.center = (x, y)
        
    def update(self):
        self.current_frame += 0.2
        self.image = self.frames[int(self.current_frame) % len(self.frames)]
        
    def draw(self, surface, camera_x, camera_y):
        draw_x = self.rect.centerx - camera_x - self.image.get_width() // 2
        draw_y = self.rect.centery - camera_y - self.image.get_height() // 2
        surface.blit(self.image, (draw_x, draw_y)) 

class SpawnerWarning:
    def __init__(self, x, y, e_type="normal"):
        self.x, self.y, self.timer = x, y, 60
        self.e_type = e_type

# ==========================================
# 地图计算
# ==========================================
class Room:
    def __init__(self, x, y, w, h, is_start=False):
        self.x, self.y, self.w, self.h = x, y, w, h
        self.cx, self.cy = x + w // 2, y + h // 2
        self.cleared = is_start
        self.gates_coords = []
        self.enemy_count = random.randint(6, 10) if not is_start else 0
        self.ranged_enemy_ratio = 0.3

    def is_player_inside(self, px, py):
        m = 40
        return self.x*TILE_SIZE+m < px < (self.x+self.w)*TILE_SIZE-m and self.y*TILE_SIZE+m < py < (self.y+self.h)*TILE_SIZE-m

def generate_map(floor, tutorial=False):
    global game_map, room_list, explored_map, tile_variant_map
    game_map = [[4 for _ in range(MAP_COLS)] for _ in range(MAP_ROWS)]
    explored_map = [[False for _ in range(MAP_COLS)] for _ in range(MAP_ROWS)]
    tile_variant_map = [[random.randint(0, 100) for _ in range(MAP_COLS)] for _ in range(MAP_ROWS)]
    room_list = []
    
    if tutorial:
        gap = 4
        base_x = 2
        prev_r = None
        for i in range(5):
            is_start = (i == 0)
            if i == 4:
                r_w, r_h = 20, 20
            else:
                r_w, r_h = 8, 8
                
            x, y = base_x, MAP_ROWS // 2 - r_h // 2
             
            for r_idx in range(y, y+r_h):
                if 0 <= r_idx < MAP_ROWS:
                    for c_idx in range(x, x+r_w): 
                        if 0 <= c_idx < MAP_COLS:
                            game_map[r_idx][c_idx] = 1
                    
            r = Room(x, y, r_w, r_h, is_start)
            if i == 4: r.enemy_count = 0  
            else: r.enemy_count = min((i * 3) + 2, 8) if i < 4 else 0
                
            room_list.append(r)
            if prev_r:
                py_tunnel, r_cy = prev_r.cy, r.cy
                px_tunnel = prev_r.x + prev_r.w - 1  
                for h_x in range(px_tunnel, x + 1):
                    if 0 <= h_x < MAP_COLS and 0 <= py_tunnel < MAP_ROWS and 0 <= py_tunnel + 1 < MAP_ROWS:
                        game_map[py_tunnel][h_x] = 1
                        game_map[py_tunnel+1][h_x] = 1
                        
            prev_r = r
            base_x += r_w + gap

        finalize_walls()
        return room_list[0].cx * TILE_SIZE, room_list[0].cy * TILE_SIZE

    if floor % 5 == 0:
        w, h = 18, 18
        x, y = (MAP_COLS - w)//2, (MAP_ROWS - h)//2
        for r in range(y, y+h):
            for c in range(x, x+w): game_map[r][c] = 1
        room_list.append(Room(x, y, w, h, False))
        finalize_walls()
        return room_list[0].cx * TILE_SIZE, (room_list[0].y + 2) * TILE_SIZE
        
    has_shop = False
    shop_chance = 0.35 if floor % 5 != 0 and not tutorial else 0.0

    for _ in range(15):
        is_start = len(room_list) == 0
        is_shop_room = not is_start and not has_shop and random.random() < shop_chance
        
        if is_start: 
            w, h = random.randint(8, 10), random.randint(8, 10)
        elif is_shop_room:
            w, h = 9, 9  
        else:
            w, h = random.randint(14, 24), random.randint(14, 24)
            
        x, y = random.randint(2, MAP_COLS - w - 2), random.randint(2, MAP_ROWS - h - 2)
        if not any(not (x+w+3<r.x or x>r.x+r.w+3 or y+h+3<r.y or y>r.y+r.h+3) for r in room_list):
            for r_idx in range(y, y + h):
                for c_idx in range(x, x + w): game_map[r_idx][c_idx] = 1
            
            r = Room(x, y, w, h, is_start)
            r.ranged_enemy_ratio = min(0.35, 0.2 + floor * 0.05)
            
            if is_shop_room:
                r.is_shop = True
                has_shop = True
            elif not is_start:
                r.is_shop = False
                for _ in range(random.randint(8, 18)):
                    ox = random.randint(r.x + 2, r.x + r.w - 4)
                    oy = random.randint(r.y + 2, r.y + r.h - 4)
                    shape_type = random.randint(0, 1)
                    if shape_type == 0:
                        test_coords = [(cx, cy) for cy in range(oy-1, oy+3) for cx in range(ox-1, ox+3)]
                        draw_coords = [(ox,oy), (ox+1,oy), (ox,oy+1), (ox+1,oy+1)]
                    else:
                        test_coords = [(cx, cy) for cy in range(oy-1, oy+4) for cx in range(ox-1, ox+2)]
                        draw_coords = [(ox,oy), (ox,oy+1), (ox,oy+2)]
                    is_safe = True
                    for tc in test_coords:
                        if game_map[tc[1]][tc[0]] != 1:
                            is_safe = False; break
                    if is_safe:
                        for dc in draw_coords: game_map[dc[1]][dc[0]] = 3
            room_list.append(r)

    for i in range(1, len(room_list)):
        target = random.randint(0, i-2) if i > 2 and random.random() < 0.2 else i-1
        r1, r2 = room_list[i], room_list[target]
        if random.random() < 0.5:
            for x in range(min(r1.cx, r2.cx), max(r1.cx, r2.cx)+1): game_map[r1.cy][x] = game_map[r1.cy+1][x] = 1
            for y in range(min(r1.cy, r2.cy), max(r1.cy, r2.cy)+1): game_map[y][r2.cx] = game_map[y][r2.cx+1] = 1
        else:
            for y in range(min(r1.cy, r2.cy), max(r1.cy, r2.cy)+1): game_map[y][r1.cx] = game_map[y][r1.cx+1] = 1
            for x in range(min(r1.cx, r2.cx), max(r1.cx, r2.cx)+1): game_map[r2.cy][x] = game_map[r2.cy+1][x] = 1

    finalize_walls()
    return room_list[0].cx * TILE_SIZE, room_list[0].cy * TILE_SIZE

def generate_training_map():
    global game_map, room_list, explored_map, tile_variant_map
    game_map = [[4 for _ in range(MAP_COLS)] for _ in range(MAP_ROWS)]
    explored_map = [[True for _ in range(MAP_COLS)] for _ in range(MAP_ROWS)]
    tile_variant_map = [[random.randint(0, 100) for _ in range(MAP_COLS)] for _ in range(MAP_ROWS)]
    room_list = []
    w, h = 30, 30
    x, y = (MAP_COLS - w)//2, (MAP_ROWS - h)//2
    for r in range(y, y+h):
        for c in range(x, x+w): game_map[r][c] = 1
    room_list.append(Room(x, y, w, h, True))
    finalize_walls()
    return room_list[0].cx * TILE_SIZE, room_list[0].cy * TILE_SIZE

def finalize_walls():
    global game_map
    for r in range(MAP_ROWS):
        for c in range(MAP_COLS):
            if game_map[r][c] == 4:
                is_edge = False
                for dr in [-1, 0, 1]:
                    for dc in [-1, 0, 1]:
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < MAP_ROWS and 0 <= nc < MAP_COLS:
                            if game_map[nr][nc] in [1, 2, 3]: is_edge = True; break
                    if is_edge: break
                if is_edge: game_map[r][c] = 0

def is_wall(x, y):
    c, r = int(x // TILE_SIZE), int(y // TILE_SIZE)
    if r < 0 or r >= MAP_ROWS or c < 0 or c >= MAP_COLS: return True
    return game_map[r][c] in [0, 2, 3, 4]

def toggle_room_gates(room, close=True):
    if close:
        room.gates_coords = []
        for c in range(room.x, room.x + room.w):
            if 0 <= room.y-1 < MAP_ROWS and 0 <= c < MAP_COLS and game_map[room.y-1][c] == 1: 
                room.gates_coords.append((room.y-1, c))
            if 0 <= room.y+room.h < MAP_ROWS and 0 <= c < MAP_COLS and game_map[room.y+room.h][c] == 1: 
                room.gates_coords.append((room.y+room.h, c))
        for r in range(room.y, room.y + room.h):
            if 0 <= r < MAP_ROWS and 0 <= room.x-1 < MAP_COLS and game_map[r][room.x-1] == 1: 
                room.gates_coords.append((r, room.x-1))
            if 0 <= r < MAP_ROWS and 0 <= room.x+room.w < MAP_COLS and game_map[r][room.x+room.w] == 1: 
                room.gates_coords.append((r, room.x+room.w))
        for r, c in room.gates_coords: game_map[r][c] = 2
    else:
        for r, c in room.gates_coords: game_map[r][c] = 1

def draw_button(screen, text, x, y, w, h, color, hover_color, mx, my):
    rect = pygame.Rect(x, y, w, h)
    is_hover = rect.collidepoint(mx, my)
    pygame.draw.rect(screen, hover_color if is_hover else color, rect, border_radius=8)
    pygame.draw.rect(screen, WHITE, rect, 2, border_radius=8)
    txt_surf = font_large.render(text, True, BLACK if is_hover else WHITE)
    screen.blit(txt_surf, (x + w//2 - txt_surf.get_width()//2, y + h//2 - txt_surf.get_height()//2))
    return is_hover

def draw_hud(screen, player, skill_icon_img):
    pygame.draw.rect(screen, GRAY, (20, 20, 150, 20))
    pygame.draw.rect(screen, RED, (20, 20, 150 * max(0, player.hp/player.max_hp), 20))
    screen.blit(font_base.render(f"HP: {int(max(0, player.hp))}/{player.max_hp}", True, WHITE), (30, 22))
    
    pygame.draw.rect(screen, GRAY, (20, 50, 150, 20))
    pygame.draw.rect(screen, BLUE, (20, 50, 150 * max(0, player.shield/player.max_shield), 20))
    screen.blit(font_base.render(f"护盾: {player.shield:.1f}/{player.max_shield}", True, WHITE), (30, 52))
    screen.blit(font_large.render(f"金币: {coins}", True, YELLOW), (20, 80))
    
    icon_size = 40
    icon_x, icon_y = 30, SCREEN_HEIGHT - 80 
    
    pygame.draw.rect(screen, GRAY, (icon_x-2, icon_y-2, icon_size+4, icon_size+4), border_radius=5)
    screen.blit(skill_icon_img, (icon_x, icon_y))
    
    liquid_surface = pygame.Surface((icon_size, icon_size), pygame.SRCALPHA)
    
    if player.skill_timer > 0:
        ratio = player.skill_timer / player.skill_duration_max
        h = int(icon_size * ratio)
        pygame.draw.rect(liquid_surface, (100, 200, 255, 120), (0, icon_size - h, icon_size, h))
        skill_text, color = f"[空格] 生效中: {player.skill_timer//60}s", (100, 200, 255)
    elif player.skill_cd > 0:
        ratio = player.skill_cd / player.skill_cd_max
        h = int(icon_size * ratio)
        pygame.draw.rect(liquid_surface, (255, 255, 255, 150), (0, icon_size - h, icon_size, h))
        skill_text, color = f"冷却中: {player.skill_cd//60}s", GRAY
    else:
        skill_text, color = "[空格] 技能就绪", GREEN
        
    screen.blit(liquid_surface, (icon_x, icon_y))
    txt_surf = font_base.render(skill_text, True, color)
    screen.blit(txt_surf, (icon_x + icon_size + 10, icon_y + icon_size//2 - txt_surf.get_height()//2))

def draw_minimap(screen, player, mode, c_floor):
    map_w, map_h = MAP_COLS * 3, MAP_ROWS * 3
    start_x, start_y = SCREEN_WIDTH - map_w - 20, 20
    pygame.draw.rect(screen, (20, 20, 20, 180), (start_x, start_y, map_w, map_h))
    pygame.draw.rect(screen, GRAY, (start_x, start_y, map_w, map_h), 2)
    for r in range(MAP_ROWS):
        for c in range(MAP_COLS):
            if explored_map[r][c]:
                if game_map[r][c] == 1: pygame.draw.rect(screen, (120, 120, 120), (start_x + c*3, start_y + r*3, 3, 3))
                elif game_map[r][c] == 2: pygame.draw.rect(screen, RED, (start_x + c*3, start_y + r*3, 3, 3))
                elif game_map[r][c] == 3: pygame.draw.rect(screen, DARK_GRAY, (start_x + c*3, start_y + r*3, 3, 3))
                elif game_map[r][c] == 0: pygame.draw.rect(screen, (80, 80, 100), (start_x + c*3, start_y + r*3, 3, 3))
    px, py = int(player.rect.centerx // TILE_SIZE), int(player.rect.centery // TILE_SIZE)
    if 0 <= px < MAP_COLS and 0 <= py < MAP_ROWS: pygame.draw.rect(screen, GREEN, (start_x + px*3, start_y + py*3, 4, 4))
    
    if mode == "CAMPAIGN":
        bar_y = start_y + map_h + 10
        pygame.draw.rect(screen, DARK_GRAY, (start_x, bar_y, map_w, 20))
        ratio = min(1.0, c_floor / 30)
        pygame.draw.rect(screen, (50, 200, 50), (start_x, bar_y, int(map_w * ratio), 20))
        txt = font_base.render(f"进度: {min(c_floor, 30)}/30", True, WHITE)
        screen.blit(txt, (start_x + map_w//2 - txt.get_width()//2, bar_y + 10 - txt.get_height()//2))

def spawn_coins(x, y, is_boss, floor, coins_group):
    amount = (15 + floor * 3) if is_boss else (1 + floor // 3)
    for _ in range(amount):
        coins_group.add(Coin(x + random.randint(-20, 20), y + random.randint(-20, 20)))
   
def clear_all_systems_for_new_game():
    global is_battle_locked, current_room_index, spawn_pending, portal_spawned, debuffs, screen_shake
    is_battle_locked = False
    current_room_index = -1
    spawn_pending = False
    portal_spawned = False
    debuffs = {"vision_reduce": 0, "buff_disable": 0, "last_shield_hit": 0}
    screen_shake = 0


# ==========================================
# 6. 游戏入口
# ==========================================
def main():
    global clock, coins, total_coins, current_floor, camera_x, camera_y, debuffs, screen_shake, pause_tab
    global tile_variant_map, is_battle_locked, current_room_index, spawn_pending, portal_spawned
    
    clock = pygame.time.Clock()
    
    # 🖼️👉 【地表图】
    wall_imgs = [
        load_frames(["wall1.png"], (60, 60, 75), (TILE_SIZE, TILE_SIZE), "rect")[0],
        load_frames(["wall2.png"], (50, 50, 65), (TILE_SIZE, TILE_SIZE), "rect")[0],
        load_frames(["wall3.png"], (70, 70, 85), (TILE_SIZE, TILE_SIZE), "rect")[0]
    ]
    outer_wall_imgs = [
        load_frames(["outer_wall1.png"], (20, 20, 25), (TILE_SIZE, TILE_SIZE), "rect")[0],
    ]
    floor_imgs = [
        load_frames(["地板1.png"], (40, 40, 45), (TILE_SIZE, TILE_SIZE), "rect")[0],
        load_frames(["地板2.png"], (35, 35, 40), (TILE_SIZE, TILE_SIZE), "rect")[0],
        load_frames(["地板3.png"], (45, 45, 50), (TILE_SIZE, TILE_SIZE), "rect")[0]
    ]
    wall_inner_imgs = [
        load_frames(["wall_inner1.png"], DARK_GRAY, (TILE_SIZE, TILE_SIZE), "rect")[0],
        load_frames(["wall_inner2.png"], (70,70,70), (TILE_SIZE, TILE_SIZE), "rect")[0],
        load_frames(["wall_inner3.png"], (90,90,90), (TILE_SIZE, TILE_SIZE), "rect")[0]
    ]
    
    skill_icon_img = load_frames(["skill_icon.png"], PURPLE, (40, 40), "rect")[0]
    teleport_bg = load_frames(["teleport_bg.png"], (20, 10, 40), (SCREEN_WIDTH, SCREEN_HEIGHT), "rect")[0]
    # 🖼️👉 【护盾】    
    shield_part_img = load_frames(["护盾扇形.png"], BLUE, (35, 18), "rect")[0]
    if shield_part_img.get_rect().size == (35,18) and not os.path.exists(get_res_path("护盾扇形.png")):
        shield_part_img = pygame.Surface((35, 18), pygame.SRCALPHA)
        pygame.draw.ellipse(shield_part_img, (135,206,250, 200), (0,0, 35, 18))

    # 🖼️👉 【武器替换】
    global_weapon_images = {
        "普通手枪": load_frames(["普通手枪.png"], GRAY, (120, 70), "rect")[0],
        "强力手枪": load_frames(["heavy_pistol.png"], (100,100,100), (45, 16), "rect")[0],
        "近战小刀": load_frames(["近战小刀.png"], WHITE, (168, 80), "rect")[0],
        "大刀": load_frames(["大刀.png"], WHITE, (190,74), "rect")[0],
        "机关枪": load_frames(["machine_gun.png"], (80,80,80), (60, 20), "rect")[0],
        "火焰枪": load_frames(["flamethrower.png"], (255,69,0), (55, 16), "rect")[0],
        "魔法弓": load_frames(["magic_bow.png"], (138, 43, 226), (40, 70), "rect")[0],
        "手榴弹": load_frames(["grenade_icon.png"], DARK_GREEN, (20, 20), "circle")[0]
    }

    game_state, game_mode, coins, total_coins = "MENU", "ENDLESS", 0, 0
    current_floor, difficulty_name, death_timer, acquired_talents, shop_page = 1, "普通", 0, [], 0
    prev_state = "" 
    boss_alive = False
    teleport_timer = 0
    sandbags = pygame.sprite.Group()
    is_victory = False 

    def init_shop_items():
        return [
            {"id": "shield_max", "name": "提升护盾上限", "cost": 5, "level": 0, "max": 99, "cost_up": 15},
            {"id": "melee_range", "name": "提升扇形范围", "cost": 15, "level": 0, "max": 99, "cost_up": 20}, 
            {"id": "ranged_mult", "name": "提升远程伤害", "cost": 10, "level": 0, "max": 99, "cost_up": 5},
            {"id": "melee_mult", "name": "提升近战伤害", "cost": 15, "level": 0, "max": 99, "cost_up": 8},
            {"id": "fir", "name": "提升攻速", "cost": 15, "level": 0, "max": 6, "cost_up": 10},
            {"id": "spd", "name": "提升移动速度", "cost": 15, "level": 0, "max": 5, "cost_up": 10},
            {"id": "hp", "name": "恢复1点生命", "cost": 5, "level": 0, "max": 999, "cost_up": 0},
            {"id": "explosion", "name": "提升爆炸威力", "cost": 15, "level": 0, "max": 99, "cost_up": 15},
            {"id": "exp_range", "name": "提升爆炸范围", "cost": 15, "level": 0, "max": 15, "cost_up": 15}
        ]
    all_talents = [
        {"id": "bounce", "name": "反弹墙壁", "desc": "子弹触墙可反弹1次", "unique": True},
        {"id": "hp_up", "name": "生命涌动", "desc": "生命上限+2并回满血", "unique": False}, 
        {"id": "magnet", "name": "金币磁铁", "desc": "大范围自动吸附金币", "unique": True},
        {"id": "explosion", "name": "敌人爆炸", "desc": "击败敌人会发生爆炸", "unique": True},
        {"id": "weapon_slot", "name": "武器栏+1", "desc": "解锁额外武器栏位", "unique": True},
        {"id": "skill_up", "name": "技能专精", "desc": "主动技能持续时间翻倍", "unique": True},
        {"id": "revive", "name": "凤凰涅槃", "desc": "死亡时满血复活一次", "unique": True},
        {"id": "scatter_up", "name": "散射强化", "desc": "所有散射武器额外增加两条弹道", "unique": True},
        {"id": "charge_fast", "name": "蓄力极速", "desc": "弓箭等蓄力武器蓄力速度翻倍", "unique": True},
        {"id": "large_explosion", "name": "爆破鬼才", "desc": "所有的爆炸范围直接翻倍！", "unique": True},
        {"id": "orbit_shield", "name": "星轨护盾", "desc": "释放技能产生护盾，15秒内完全抵挡下一次受击", "unique": True}
    ]
    all_talents_dict = {t["id"]: t["name"] for t in all_talents} 

    current_talents = []

    def reset_floor(player_instance=None):
        nonlocal sandbags, is_victory
        sandbags.empty() 

        sx, sy = generate_map(current_floor, tutorial=(game_mode == "TUTORIAL"))
        p = Player(sx, sy) if player_instance is None else player_instance
        p.rect.center = (sx, sy)
        p.stolen_weap_idx = -1 
        crates_group = pygame.sprite.Group()
        pedestals_group = pygame.sprite.Group()
        
        # 整理分配特殊房区与生成摆件
        shop_room_idx = -1
        pool = []
        for i, r in enumerate(room_list):
            if i == 0: continue
            if getattr(r, 'is_shop', False): shop_room_idx = i
            else: pool.append(i)

        special_room_idx = -1 
        if current_floor % 5 != 0 and len(room_list) > 1 and game_mode != "TUTORIAL" and len(pool) > 0:
            special_room_idx = random.choice(pool)

        if shop_room_idx != -1:
            shop_room = room_list[shop_room_idx]
            shop_room.cleared = True
            shop_room.enemy_count = 0  
            shop_weapons = [
                {"type": "pistol", "name": "强力手枪", "damage": 35, "cd": 250},
                {"type": "melee", "name": "大刀", "damage": 70, "range": 140, "cd": 800},
                {"type": "pistol", "name": "机关枪", "damage": 15, "cd": 100},
                {"type": "flamethrower", "name": "火焰枪", "damage": 15, "range": 150, "cd": 600},
                {"type": "bow", "name": "魔法弓", "damage": 65, "cd": 150},
                {"type": "grenade", "name": "手榴弹", "damage": 70, "cd": 600} 
            ]
            stand_items = random.sample(shop_weapons, min(3, len(shop_weapons)))
            stand_positions_offX = [-120, 0, 120]
            cx, cy = shop_room.cx * TILE_SIZE, shop_room.cy * TILE_SIZE
            for s_i, stand_wpn in enumerate(stand_items):
                new_st = WeaponStand(cx + stand_positions_offX[s_i], cy - 20, stand_wpn, global_weapon_images.get(stand_wpn["name"]))
                pedestals_group.add(new_st)

        for i, r in enumerate(room_list):
            if i == 0: continue
            
            if getattr(r, 'is_shop', False):
                continue 

            if i == special_room_idx:
                crates_group.add(SpecialCrate(r.cx * TILE_SIZE + TILE_SIZE//2, r.cy * TILE_SIZE + TILE_SIZE//2))
            else:
                for _ in range(random.randint(1, 3)):
                    attempts = 0
                    cx, cy = random.randint(r.x+1, r.x+r.w-2), random.randint(r.y+1, r.y+r.h-2)
                    while game_map[cy][cx] != 1 and attempts < 10:
                        cx, cy = random.randint(r.x+1, r.x+r.w-2), random.randint(r.y+1, r.y+r.h-2)
                        attempts += 1
                    if game_map[cy][cx] == 1: crates_group.add(Crate(cx*TILE_SIZE + TILE_SIZE//2, cy*TILE_SIZE + TILE_SIZE//2))
        return p, pygame.sprite.Group(), pygame.sprite.Group(), pygame.sprite.Group(), pygame.sprite.Group(), pygame.sprite.Group(), [], False, pygame.sprite.Group(), crates_group, pygame.sprite.Group(), pygame.sprite.Group(), pedestals_group

    def init_training():
        nonlocal sandbags
        sx, sy = generate_training_map()
        p = Player(sx, sy)
        p.weapons = [
            {"type": "pistol", "name": "普通手枪", "damage": 25, "cd": 300},
            {"type": "pistol", "name": "强力手枪", "damage": 35, "cd": 250},
            {"type": "melee", "name": "近战小刀", "damage": 30, "range": 80, "cd": 400},
            {"type": "melee", "name": "大刀", "damage": 70, "range": 140, "cd": 700},
            {"type": "pistol", "name": "机关枪", "damage": 15, "cd": 100},
            {"type": "flamethrower", "name": "火焰枪", "damage": 15, "range": 150, "cd": 600}, 
            {"type": "bow", "name": "魔法弓", "damage": 65, "cd": 150},
            {"type": "grenade", "name": "手榴弹", "damage": 70, "cd": 600}
        ]
        p.weapon_slots = len(p.weapons)
        sandbags.empty()
        sandbags.add(Sandbag(sx, sy - 150))
        return p, pygame.sprite.Group(), pygame.sprite.Group(), pygame.sprite.Group(), pygame.sprite.Group(), pygame.sprite.Group(), [], False, pygame.sprite.Group(), pygame.sprite.Group(), pygame.sprite.Group(), pygame.sprite.Group(), pygame.sprite.Group()


    clear_all_systems_for_new_game()
    player, bullets, enemy_bullets, enemies, coins_group, portals, spawners, portal_spawned, effects, crates, items_group, grenades, pedestals = reset_floor()

    running = True
    while running:
        mx, my = pygame.mouse.get_pos()
        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11: pygame.display.toggle_fullscreen()
                if event.key in [pygame.K_p, pygame.K_ESCAPE]:
                    if game_state in ["PLAYING", "TRAINING"]:
                        prev_state = game_state
                        game_state = "PAUSED"
                        pause_tab = 0
                    elif game_state == "PAUSED":
                        game_state = prev_state

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if game_state == "MENU":
                    if play_hover: 
                        game_mode = "ENDLESS"
                        coins, total_coins, current_floor, acquired_talents, shop_page = 999999, 0, 20, [], 0
                        is_victory = False
                        clear_all_systems_for_new_game()
                        shop_items = init_shop_items()
                        player, bullets, enemy_bullets, enemies, coins_group, portals, spawners, portal_spawned, effects, crates, items_group, grenades, pedestals = reset_floor()
                        game_state = "PLAYING"
                    elif play_campaign_hover: 
                        game_mode = "CAMPAIGN"
                        coins, total_coins, current_floor, acquired_talents, shop_page = 0, 0, 1, [], 0
                        is_victory = False
                        clear_all_systems_for_new_game()
                        shop_items = init_shop_items()
                        player, bullets, enemy_bullets, enemies, coins_group, portals, spawners, portal_spawned, effects, crates, items_group, grenades, pedestals = reset_floor()
                        game_state = "PLAYING"
                    elif play_tutorial_hover:
                        game_mode = "TUTORIAL"
                        coins, total_coins, current_floor, acquired_talents, shop_page = 0, 0, 1, [], 0
                        is_victory = False
                        clear_all_systems_for_new_game()
                        shop_items = init_shop_items()
                        player, bullets, enemy_bullets, enemies, coins_group, portals, spawners, portal_spawned, effects, crates, items_group, grenades, pedestals = reset_floor()
                        game_state = "PLAYING"
                    elif train_hover:
                        game_mode = "TRAINING"
                        coins, total_coins, acquired_talents, shop_page = 99999, 99999, [], 0 
                        clear_all_systems_for_new_game()
                        portal_spawned = True 
                        shop_items = init_shop_items()
                        player, bullets, enemy_bullets, enemies, coins_group, portals, spawners, portal_spawned, effects, crates, items_group, grenades, pedestals = init_training()
                        game_state = "TRAINING"
                        
                    elif diff_hover: game_state = "DIFF"
                    elif intro_hover: game_state = "INTRO"
                    elif quit_hover: running = False
                    
                elif game_state == "PAUSED":
                    if btn_resume: game_state = prev_state
                    elif btn_restart:
                        if prev_state == "PLAYING":
                            coins, total_coins, current_floor, acquired_talents, shop_page = 0, 0, 1, [], 0
                            is_victory = False
                            clear_all_systems_for_new_game()
                            shop_items = init_shop_items()
                            player, bullets, enemy_bullets, enemies, coins_group, portals, spawners, portal_spawned, effects, crates, items_group, grenades, pedestals = reset_floor()
                            game_state = "PLAYING"
                        else:
                            clear_all_systems_for_new_game()
                            portal_spawned = True
                            player, bullets, enemy_bullets, enemies, coins_group, portals, spawners, portal_spawned, effects, crates, items_group, grenades, pedestals = init_training()
                            game_state = "TRAINING"
                    elif btn_main: game_state = "MENU"
                    elif btn_quit_pause: running = False
                    
                    if tab_stats_hover: pause_tab = 0
                    elif tab_weaps_hover: pause_tab = 1
                    elif tab_talents_hover: pause_tab = 2

                elif game_state == "DIFF":
                    if btn_easy: difficulty_mult.update({"hp":0.7, "dmg":0.7, "spd":0.8, "range_hp":0.7, "range_spd":0.8}); difficulty_name="简单"; game_state="MENU"
                    elif btn_norm: difficulty_mult.update({"hp":1.0, "dmg":1, "spd":1.0, "range_hp":1.0, "range_spd":1.0}); difficulty_name="普通"; game_state="MENU"
                    elif btn_hard: difficulty_mult.update({"hp":1.8, "dmg":2, "spd":1.3, "range_hp":1.5, "range_spd":1.2}); difficulty_name="困难"; game_state="MENU"
                elif game_state == "INTRO":
                    if btn_back: game_state = "MENU"
                elif game_state == "PORTAL_CONFIRM":
                    if btn_confirm_yes:
                        if game_mode == "TUTORIAL":
                            is_victory = True; game_state = "RESULT"
                        else:
                            game_state = "TELEPORTING"
                            teleport_timer = pygame.time.get_ticks()
                    elif btn_confirm_no:
                        safe_room = room_list[current_room_index]
                        found_safe_pos = False
                        for dy in range(-3, 4):
                            for dx in range(-3, 4):
                                rx = safe_room.cx + dx
                                ry = safe_room.cy + dy
                                if 0 <= rx < MAP_COLS and 0 <= ry < MAP_ROWS:
                                    if game_map[ry][rx] == 1:
                                        player.rect.centerx = int((rx + 0.5) * TILE_SIZE)
                                        player.rect.centery = int((ry + 0.5) * TILE_SIZE)
                                        found_safe_pos = True
                                        break
                            if found_safe_pos: break
                        if not found_safe_pos:
                            player.rect.centerx = safe_room.cx * TILE_SIZE
                            player.rect.centery = int((safe_room.cy + 1.5) * TILE_SIZE)
                            
                        game_state = "PLAYING"
                        
                elif game_state == "SHOP":
                    clicked = False
                    if prev_hover: shop_page -= 1; clicked = True
                    elif next_hover: shop_page += 1; clicked = True
                    for btn_rect, item, can_buy in shop_btns:
                        if btn_rect.collidepoint(mx, my) and can_buy:
                            clicked = True; coins -= item['cost']; item['level'] += 1; item['cost'] += item['cost_up']
                            
                            if item['id'] == 'ranged_mult': player.bonus_ranged_mult *= 1.1
                            elif item['id'] == 'melee_mult': player.bonus_melee_mult *= 1.1
                            elif item['id'] == 'melee_range': player.bonus_range_mult *= 1.1
                            elif item['id'] == 'spd': player.speed += 1
                            elif item['id'] == 'fir': player.bonus_cd_reduction += 10
                            elif item['id'] == 'hp': player.hp = min(player.max_hp, player.hp + 1); item['level'] -= 1
                            elif item['id'] == 'shield_max': player.max_shield += 1
                            elif item['id'] == 'explosion': player.bonus_explosion_mult *= 1.1
                            elif item['id'] == 'exp_range': player.explosion_radius_mult *= 1.1 
                            
                    if not clicked and not pygame.Rect((SCREEN_WIDTH-700)//2, (SCREEN_HEIGHT-500)//2, 700, 500).collidepoint(mx, my): 
                        game_state = prev_state if prev_state in ["PLAYING", "TRAINING"] else "PLAYING"
                        
                elif game_state == "TALENT":
                    for is_hover, t in talent_btns:
                        if is_hover:
                            if t['id'] == 'bounce': player.has_bounce = True
                            elif t['id'] == 'hp_up': player.max_hp += 2; player.hp = player.max_hp
                            elif t['id'] == 'magnet': player.has_magnet = True
                            elif t['id'] == 'explosion': player.has_explosion = True
                            elif t['id'] == 'weapon_slot':
                                player.weapon_slots += 1; player.weapons.append({"type": "pistol", "name": "备用手枪", "damage": 25, "cd": 250})
                            elif t['id'] == 'skill_up': player.skill_duration_max *= 2
                            elif t['id'] == 'revive': player.has_revive = True 
                            elif t['id'] == 'scatter_up': player.bonus_scatter += 2
                            elif t['id'] == 'charge_fast': player.charge_speed_mult *= 2.0
                            elif t['id'] == 'large_explosion': player.has_large_explosion = True 
                            elif t['id'] == 'orbit_shield': player.has_orbit_shield = True
                                
                            acquired_talents.append(t['id']); game_state = "PLAYING"
                elif game_state == "GAMEOVER_ANIM": pass 
                elif game_state == "RESULT" and btn_restart_res: game_state = "MENU"
                elif game_state == "RESULT" and btn_quit_res: running = False

            if event.type == pygame.KEYDOWN:
                if game_state in ["PLAYING", "TRAINING", "SHOP"]:
                    if event.key == pygame.K_TAB: 
                        if game_state == "SHOP": game_state = prev_state
                        else: prev_state = game_state; shop_page = 0; game_state = "SHOP"
                    elif event.key == pygame.K_1: player.switch_weapon(-1)
                    elif event.key == pygame.K_2: player.switch_weapon(1)
                    elif event.key == pygame.K_SPACE and game_state in ["PLAYING", "TRAINING"]: player.activate_skill()
                    elif event.key == pygame.K_f and game_state in ["PLAYING", "TRAINING"]:
                        interacted = False
                        
                        for st in pedestals:
                            if math.hypot(player.rect.centerx - st.rect.centerx, player.rect.centery - st.rect.centery) < 70:
                                if coins >= st.price:
                                    coins -= st.price
                                    effects.add(DamageText(player.rect.centerx, player.rect.top-10, "购买成功", custom_color=(0, 255, 0), is_text=True))
                                    if len(player.weapons) < player.weapon_slots:
                                        player.weapons.append(st.w_data)
                                        player.current_weapon = len(player.weapons) - 1
                                    else:
                                        w_img = global_weapon_images.get(player.weapons[player.current_weapon]["name"])
                                        items_group.add(GroundItem(player.rect.centerx, player.rect.centery, "weapon", player.weapons[player.current_weapon], w_img))
                                        player.weapons[player.current_weapon] = st.w_data
                                    st.kill()
                                else:
                                    effects.add(DamageText(player.rect.centerx, player.rect.top-10, "金币不足", custom_color=(255, 68, 68), is_text=True))
                                interacted = True
                                break
                        if interacted: continue

                        for item in items_group:
                            if math.hypot(player.rect.centerx - item.rect.centerx, player.rect.centery - item.rect.centery) < 60:
                                if item.item_type == "potion":
                                    player.hp = min(player.max_hp, player.hp + 2)
                                    effects.add(DamageText(player.rect.centerx, player.rect.top, 2, is_heal=True))
                                    item.kill()
                                elif item.item_type == "weapon":
                                    if len(player.weapons) < player.weapon_slots:
                                        player.weapons.append(item.weapon_data)
                                        player.current_weapon = len(player.weapons) - 1
                                    else:
                                        w_img = global_weapon_images.get(player.weapons[player.current_weapon]["name"])
                                        items_group.add(GroundItem(player.rect.centerx, player.rect.centery, "weapon", player.weapons[player.current_weapon], w_img))
                                        player.weapons[player.current_weapon] = item.weapon_data
                                    item.kill()
                                break 

        pygame.mouse.set_visible(game_state not in ["PLAYING", "TRAINING"])
        
        if game_state == "MENU":
            screen.fill((20, 20, 30))
            screen.blit(font_title.render("绝境突围：无尽肉鸽", True, YELLOW), (SCREEN_WIDTH//2 - 200, 150))
            play_hover = draw_button(screen, "无尽模式", SCREEN_WIDTH//2-100, 260, 200, 50, (50,150,50), (100,200,100), mx, my)
            play_campaign_hover = draw_button(screen, "闯关模式", SCREEN_WIDTH//2-100, 330, 200, 50, (150,100,50), (200,150,100), mx, my)
            play_tutorial_hover = draw_button(screen, "新手教程", SCREEN_WIDTH//2-100, 400, 200, 50, (50,150,150), (100,200,200), mx, my)
            train_hover = draw_button(screen, "训练营", SCREEN_WIDTH//2-100, 470, 200, 50, (150,50,150), (200,100,200), mx, my)
            diff_hover = draw_button(screen, "选择难度", SCREEN_WIDTH//2-100, 540, 200, 50, GRAY, (150,150,150), mx, my)
            intro_hover = draw_button(screen, "游戏说明", SCREEN_WIDTH//2-100, 610, 200, 50, (50,100,150), (100,150,200), mx, my)
            quit_hover = draw_button(screen, "退出游戏", SCREEN_WIDTH//2-100, 680, 200, 50, (150,50,50), (200,100,100), mx, my)
            
            screen.blit(font_base.render(f"当前难度： [{difficulty_name}]", True, GRAY), (SCREEN_WIDTH//2 - 180, 750))
            pygame.display.flip(); clock.tick(FPS); continue
            
        elif game_state == "DIFF":
            screen.fill((20,20,30)); screen.blit(font_title.render("选择难度：", True, WHITE), (SCREEN_WIDTH//2-380, 150))
            btn_easy = draw_button(screen, "简单模式", SCREEN_WIDTH//2-180, 300, 360, 60, (50,150,50), (100,200,100), mx, my)
            btn_norm = draw_button(screen, "普通模式", SCREEN_WIDTH//2-180, 400, 360, 60, (150,100,50), (200,150,100), mx, my)
            btn_hard = draw_button(screen, "困难模式", SCREEN_WIDTH//2-180, 500, 360, 60, (150,50,50), (200,100,100), mx, my)
            pygame.display.flip(); clock.tick(FPS); continue
            
        elif game_state == "INTRO":
            screen.fill((20,20,30))
            for i, line in enumerate(["玩法说明：", 
                                    "[ W ][ A ][ S ][ D ]移动 。鼠标控制瞄准。左键攻击", 
                                    "TAB 打开商店购买增益， F 交互道具和武器 ， 1/2切换当前手上的武器", 
                                    "空格释放技能，注意冷却CD",
                                    "选择天赋，购买增益，搭配增益效果击败敌人和BOSS"]
                                  ):
                screen.blit(font_large.render(line, True, YELLOW if i==0 else WHITE), (60, 150 + i*40))
            btn_back = draw_button(screen, "知道了", SCREEN_WIDTH//2-100, 600, 200, 50, GRAY, WHITE, mx, my)
            pygame.display.flip(); clock.tick(FPS); continue

        elif game_state == "TELEPORTING":
            screen.fill(BLACK)
            screen.blit(teleport_bg, (0, 0))
            txt = font_title.render("传送中.....", True, WHITE)
            screen.blit(txt, (SCREEN_WIDTH//2 - txt.get_width()//2, SCREEN_HEIGHT//2 - txt.get_height()//2))
            
            if pygame.time.get_ticks() - teleport_timer > 2000:
                current_floor += 1
                if game_mode == "CAMPAIGN" and current_floor > 30:
                    is_victory = True; game_state = "RESULT"
                    pygame.display.flip(); clock.tick(FPS); continue

                player, bullets, enemy_bullets, enemies, coins_group, portals, spawners, portal_spawned, effects, crates, items_group, grenades, pedestals = reset_floor(player)
                
 
                clear_all_systems_for_new_game()

                if (current_floor - 1) % 3 == 0:
                    available_talents = [t for t in all_talents if not (t.get('unique', True) and t['id'] in acquired_talents)]
                    current_talents = random.sample(available_talents, min(3, len(available_talents)))
                    game_state = "TALENT"
                else:
                    game_state = "PLAYING"
            pygame.display.flip(); clock.tick(FPS); continue

        if game_state in ["PLAYING", "TRAINING"]:
            if debuffs["vision_reduce"] > 0: debuffs["vision_reduce"] -= 1
            if debuffs["buff_disable"] > 0: debuffs["buff_disable"] -= 1
            if player.poison_timer > 0: player.poison_timer -= 1
            
            keys = pygame.key.get_pressed()
            dx, dy = 0, 0
            current_spd = player.speed * (0.5 if player.poison_timer > 0 else 1.0)
            if keys[pygame.K_a]: dx -= current_spd
            if keys[pygame.K_d]: dx += current_spd
            if keys[pygame.K_w]: dy -= current_spd
            if keys[pygame.K_s]: dy += current_spd

            # 长按蓄力状态阻挡行走
            if getattr(player, "is_laser_charging", False):
                dx, dy = 0, 0

            if dx != 0:
                player.rect.centerx += dx
                if is_wall(player.rect.centerx + (15 if dx>0 else -15), player.rect.centery) or pygame.sprite.spritecollideany(player, crates): player.rect.centerx -= dx
            if dy != 0:
                player.rect.centery += dy
                if is_wall(player.rect.centerx, player.rect.centery + (15 if dy>0 else -15)) or pygame.sprite.spritecollideany(player, crates): player.rect.centery -= dy
                
            player.update(dx=dx, dy=dy)

            camera_x, camera_y = player.rect.centerx - SCREEN_WIDTH // 2, player.rect.centery - SCREEN_HEIGHT // 2
            
            if screen_shake > 0:
                camera_x += random.randint(-screen_shake, screen_shake)
                camera_y += random.randint(-screen_shake, screen_shake)
                screen_shake -= 1
            
            vision_radius = 400 if debuffs["vision_reduce"] == 0 else 150
            vision_tiles = vision_radius // TILE_SIZE
            pr, pc = int(player.rect.centery // TILE_SIZE), int(player.rect.centerx // TILE_SIZE)
            for r in range(max(0, pr - vision_tiles), min(MAP_ROWS, pr + vision_tiles + 1)):
                for c in range(max(0, pc - vision_tiles), min(MAP_COLS, pc + vision_tiles + 1)):
                    if math.hypot(r - pr, c - pc) <= vision_tiles + 1: explored_map[r][c] = True

            def hit_target(target, attack_data):
                atk_type, sx, sy, atk_angle, atk_range, _ = attack_data
                dist = math.hypot(target.rect.centerx - sx, target.rect.centery - sy)
                if dist <= atk_range:
                    ang = math.atan2(target.rect.centery - sy, target.rect.centerx - sx)
                    diff = (ang - atk_angle + math.pi) % (2*math.pi) - math.pi
                    if atk_type == "melee": angle_limit = math.pi/2.5
                    elif atk_type == "flame": angle_limit = math.pi/4
                    elif atk_type == "laser": angle_limit = math.pi/20
                    else: angle_limit = math.pi/4
                    if abs(diff) <= angle_limit: return True
                return False

            mouse_pressed = pygame.mouse.get_pressed()[0]
            track_targets = list(enemies) + list(sandbags)
            
            attack_list = player.process_attack(mouse_pressed, mx, my, camera_x, camera_y, bullets, enemy_bullets, effects, global_weapon_images, track_targets, grenades, crates, items_group, coins_group)
            
            for atk_data in attack_list:
                atk_type, sx, sy, atk_angle, atk_range, dmg = atk_data
                
                for enemy in enemies:
                    if hit_target(enemy, atk_data):
                        enemy.take_damage(dmg) 
                        if atk_type == "melee" and not isinstance(enemy, Boss):
                            hit_ang = math.atan2(enemy.rect.centery - sy, enemy.rect.centerx - sx)
                            enemy.rect.centerx += math.cos(hit_ang) * 15
                            enemy.rect.centery += math.sin(hit_ang) * 15
                            screen_shake = 5
                        if atk_type == "flame":
                            enemy.burn_duration = 180  
                            enemy.burn_timer = 60      
                            enemy.burn_dmg = enemy.max_hp * 0.10 
                        if atk_type == "laser":
                            screen_shake = 3

                        effects.add(DamageText(enemy.rect.centerx, enemy.rect.top, dmg))
                        if enemy.hp <= 0:
                            enemy.explode(enemies, player, effects); enemy.kill()
                            spawn_coins(enemy.rect.centerx, enemy.rect.centery, isinstance(enemy, Boss), current_floor, coins_group)
                            
                for crate in crates:
                    if hit_target(crate, atk_data): crate.take_damage(dmg, items_group, effects, global_weapon_images, coins_group)
                
                for bag in sandbags:
                    if hit_target(bag, atk_data):
                        bag.take_damage(dmg, effects)
                        if atk_type == "melee": screen_shake = 6
                        if atk_type == "laser": screen_shake = 2

            if game_state == "PLAYING":
                current_stage = (current_floor - 1) // 10 + 1  
                
                room_info_text, room_info_color = f"第[{current_floor}]层 ", GREEN
                for i, room in enumerate(room_list):
                    if room.is_player_inside(player.rect.centerx, player.rect.centery) and not room.cleared and not is_battle_locked:
                        
                        if getattr(room, 'is_shop', False):
                            room.cleared = True
                            continue
                            
                        current_room_index, is_battle_locked, spawn_pending = i, True, True
                        toggle_room_gates(room, close=True)
                        if (current_floor % 5 == 0 and game_mode != "TUTORIAL") or (game_mode == "TUTORIAL" and i == 4):
                            room.enemy_count = 0; spawners.append(SpawnerWarning(room.cx*TILE_SIZE, room.cy*TILE_SIZE, "boss"))
                        else:
                            if game_mode != "TUTORIAL": room.enemy_count += current_floor * 2
                            
                            healers_allocated = min(3, max(0, room.enemy_count // 3 + 1)) if current_floor >= 15 and game_mode != "TUTORIAL" else 0
                            remain_enemy = max(0, room.enemy_count - healers_allocated)
                            normals_allocated = remain_enemy - int(remain_enemy * room.ranged_enemy_ratio)
                            ranged_allocated = int(remain_enemy * room.ranged_enemy_ratio)
                            
                            for _ in range(healers_allocated):
                                rx, ry = random.randint(room.x+1, room.x+room.w-2)*TILE_SIZE + TILE_SIZE//2, random.randint(room.y+1, room.y+room.h-2)*TILE_SIZE + TILE_SIZE//2
                                if not is_wall(rx, ry): spawners.append(SpawnerWarning(rx, ry, "healer"))
                                    
                            for _ in range(normals_allocated):
                                rx, ry = random.randint(room.x+1, room.x+room.w-2)*TILE_SIZE + TILE_SIZE//2, random.randint(room.y+1, room.y+room.h-2)*TILE_SIZE + TILE_SIZE//2
                                if not is_wall(rx, ry) and math.hypot(rx-player.rect.centerx, ry-player.rect.centery) > 250: spawners.append(SpawnerWarning(rx, ry, "normal"))
                                
                            for _ in range(ranged_allocated):
                                rx, ry = random.randint(room.x+1, room.x+room.w-2)*TILE_SIZE + TILE_SIZE//2, random.randint(room.y+1, room.y+room.h-2)*TILE_SIZE + TILE_SIZE//2
                                if not is_wall(rx, ry) and math.hypot(rx-player.rect.centerx, ry-player.rect.centery) > 300: spawners.append(SpawnerWarning(rx, ry, "ranged"))
                        break

                if is_battle_locked:
                    room_info_text, room_info_color = ("敌人来袭，消灭他们！", ORANGE) if spawn_pending else ("战斗中....", RED)
                    for s in spawners[:]:
                        s.timer -= 1
                        if s.timer <= 0:
                            if s.e_type == "boss":
                                boss_hp = 1200 + current_floor*500
                                is_tut = (game_mode=="TUTORIAL")
                                if current_stage == 1:
                                    enemies.add(Boss(s.x, s.y, boss_hp, current_floor, is_tut))
                                elif current_stage == 2:
                                    enemies.add(BossStage2(s.x, s.y, boss_hp, current_floor, is_tut))
                                else: 
                                    enemies.add(BossStage3(s.x, s.y, boss_hp, current_floor, is_tut))

                            elif s.e_type == "healer":
                                cur_hp = 30 + current_floor*10
                                if current_stage == 1: enemies.add(HealerEnemy(s.x, s.y, cur_hp, current_floor))
                                elif current_stage == 2: enemies.add(HealerEnemyStage2(s.x, s.y, cur_hp, current_floor))
                                else: enemies.add(HealerEnemyStage3(s.x, s.y, cur_hp, current_floor))
                                
                            elif s.e_type == "ranged":
                                cur_hp = 30 + current_floor*15
                                if current_stage == 1: enemies.add(RangedEnemy(s.x, s.y, cur_hp, current_floor))
                                elif current_stage == 2: enemies.add(ShieldEnemyStage2(s.x, s.y, cur_hp, current_floor))
                                else: enemies.add(RangedEnemyStage3(s.x, s.y, cur_hp, current_floor))
                            else: 
                                cur_hp = 30 + current_floor*20
                                if current_stage == 1: enemies.add(Enemy(s.x, s.y, cur_hp, current_floor))
                                elif current_stage == 2: enemies.add(EnemyStage2(s.x, s.y, cur_hp, current_floor))
                                else: enemies.add(EnemyStage3(s.x, s.y, cur_hp, current_floor))
                                
                            spawners.remove(s)
                            
                    if not spawners: spawn_pending = False
                    if not spawn_pending and not enemies:
                        room_list[current_room_index].cleared = True; is_battle_locked = False; toggle_room_gates(room_list[current_room_index], close=False)
                        
                if all(r.cleared for r in room_list) and not portal_spawned:
                    portals.add(Portal(room_list[current_room_index].cx * TILE_SIZE, room_list[current_room_index].cy * TILE_SIZE))
                    portal_spawned = True
                    
                if portal_spawned: room_info_text, room_info_color = "区域敌人已清除，找到传送门进入下一层", PURPLE

                boss_alive = False
                for enemy in enemies:
                    if enemy.burn_duration > 0:
                        enemy.burn_duration -= 1; enemy.burn_timer -= 1
                        if enemy.burn_timer <= 0:
                            enemy.take_damage(enemy.burn_dmg, is_true_damage=True) 
                            enemy.burn_timer = 60
                            effects.add(DamageText(enemy.rect.centerx, enemy.rect.top, enemy.burn_dmg, custom_color=(255, 100, 0))) 
                            if enemy.hp <= 0:
                                enemy.explode(enemies, player, effects); enemy.kill()
                                spawn_coins(enemy.rect.centerx, enemy.rect.centery, isinstance(enemy, Boss), current_floor, coins_group)
                    
                    if enemy.alive():
                        if isinstance(enemy, Boss): 
                            enemy.update(px=player.rect.centerx, py=player.rect.centery, enemy_bullets_group=enemy_bullets, effects_group=effects, player=player, crates_group=crates, enemies_group=enemies)
                            boss_alive = True
                        elif isinstance(enemy, HealerEnemy): 
                            enemy.update(px=player.rect.centerx, py=player.rect.centery, crates_group=crates, enemies_group=enemies, effects_group=effects)
                        elif isinstance(enemy, RangedEnemy) and not getattr(enemy, 'is_shield_soldier', False): 
                            enemy.update(px=player.rect.centerx, py=player.rect.centery, enemy_bullets_group=enemy_bullets, crates_group=crates)
                        else: 
                            enemy.update(px=player.rect.centerx, py=player.rect.centery, crates_group=crates, enemies_group=enemies, effects_group=effects, player=player)
            
            else:
                room_info_text, room_info_color = "-- 训 练 营 -- ", ORANGE

            bullets.update(); enemy_bullets.update(); effects.update(); sandbags.update(); coins_group.update(player); portals.update(); grenades.update()

            hits = pygame.sprite.groupcollide(enemies, bullets, False, True)
            for enemy, bullet_list in hits.items():
                for b in bullet_list:
                    if getattr(enemy, 'is_shield_soldier', False):
                        effects.add(DamageText(enemy.rect.centerx, enemy.rect.top-10, "免疫", custom_color=(150,150,150), is_text=True))
                        continue 
                    enemy.take_damage(b.damage)
                    effects.add(DamageText(enemy.rect.centerx, enemy.rect.top, b.damage))
                if enemy.hp <= 0:
                    enemy.explode(enemies, player, effects); enemy.kill()
                    spawn_coins(enemy.rect.centerx, enemy.rect.centery, isinstance(enemy, Boss), current_floor, coins_group)
            
            hits_crates = pygame.sprite.groupcollide(crates, bullets, False, True)
            for crate, bullet_list in hits_crates.items():
                for b in bullet_list: crate.take_damage(b.damage, items_group, effects, global_weapon_images, coins_group)
                
            hits_bags = pygame.sprite.groupcollide(sandbags, bullets, False, True)
            for bag, bullet_list in hits_bags.items():
                for b in bullet_list: bag.take_damage(b.damage, effects)
                    
            if player.invincible_timer <= 0 and player.revive_anim_timer <= 0:
                dmg_taken = sum(e.damage for e in pygame.sprite.spritecollide(player, enemies, False))
                for b in pygame.sprite.spritecollide(player, enemy_bullets, True):
                    dmg_taken += b.damage
                    if b.b_type == 2: player.poison_timer = 180
                        
                if dmg_taken > 0:
                    if player.take_damage(dmg_taken, effects): 
                        is_victory = False; game_state, death_timer = "GAMEOVER_ANIM", pygame.time.get_ticks()
                    elif getattr(player, "just_revived", False):
                        effects.add(DamageText(player.rect.centerx, player.rect.top - 35, "复活重生", custom_color=(255, 215, 0), is_text=True))
                        player.just_revived = False

            picked_coins = len(pygame.sprite.spritecollide(player, coins_group, True))
            coins += picked_coins
            total_coins += picked_coins

            for enemy in list(enemies):
                if enemy.hp <= 0 and enemy.alive():
                    enemy.explode(enemies, player, effects)
                    spawn_coins(enemy.rect.centerx, enemy.rect.centery, isinstance(enemy, Boss), current_floor, coins_group)
                    enemy.kill()
                    
            if game_state == "PLAYING" and pygame.sprite.spritecollide(player, portals, False):
                game_state = "PORTAL_CONFIRM"

        if game_state in ["PLAYING", "TRAINING", "SHOP", "TALENT", "PORTAL_CONFIRM", "GAMEOVER_ANIM", "RESULT", "PAUSED"]:
            screen.fill(BLACK)
            
            start_c = int(camera_x // TILE_SIZE) - 1
            end_c = int((camera_x + SCREEN_WIDTH) // TILE_SIZE) + 2
            start_r = int(camera_y // TILE_SIZE) - 1
            end_r = int((camera_y + SCREEN_HEIGHT) // TILE_SIZE) + 2
            
            for r in range(start_r, end_r):
                for c in range(start_c, end_c):
                    draw_x, draw_y = c*TILE_SIZE - camera_x, r*TILE_SIZE - camera_y
                    
                    if 0 <= r < MAP_ROWS and 0 <= c < MAP_COLS: 
                        val = game_map[r][c]
                        variant_idx = tile_variant_map[r][c]
                    else: 
                        val = 4 
                        variant_idx = (r * 13 + c * 7) % 100 

                    if val == 0: screen.blit(wall_imgs[variant_idx % len(wall_imgs)], (draw_x, draw_y))
                    elif val == 4: screen.blit(outer_wall_imgs[variant_idx % len(outer_wall_imgs)], (draw_x, draw_y))
                    elif val == 1: screen.blit(floor_imgs[variant_idx % len(floor_imgs)], (draw_x, draw_y))
                    elif val == 2:
                        pygame.draw.rect(screen, ORANGE, (draw_x, draw_y, TILE_SIZE, TILE_SIZE))
                        pygame.draw.rect(screen, RED, (draw_x, draw_y, TILE_SIZE, TILE_SIZE), 2)
                    elif val == 3: screen.blit(wall_inner_imgs[variant_idx % len(wall_inner_imgs)], (draw_x, draw_y))

            for s in spawners: pygame.draw.circle(screen, RED, (s.x-camera_x, s.y-camera_y), 20, 2)
            for effect in effects: 
                if isinstance(effect, BossAoeEffect): effect.draw(screen, camera_x, camera_y)

            for crate in crates:
                crate.draw(screen, camera_x, camera_y)
                
            for pedestal in pedestals:
                pedestal.draw(screen, camera_x, camera_y)

            for e in list(items_group)+list(sandbags)+list(coins_group)+list(enemies)+list(bullets)+list(enemy_bullets)+list(grenades):
                screen.blit(e.image, (e.rect.x-camera_x, e.rect.y-camera_y))
                if isinstance(e, BossStage2) and getattr(e, "stolen_weap_data", None):
                    wimg = global_weapon_images.get(e.stolen_weap_data["name"])
                    if wimg:
                        sim = pygame.transform.scale(wimg, (int(wimg.get_width()*1.2), int(wimg.get_height()*1.2)))
                        screen.blit(sim, (e.rect.x - camera_x + 55, e.rect.y - camera_y + 35 + math.sin(pygame.time.get_ticks() / 150)*4))

            
            for pt in portals: 
                pt.draw(screen, camera_x, camera_y)
                
            for e in enemies:
                if not isinstance(e, Boss): e.draw_hp(screen, camera_x, camera_y)
            for effect in effects: 
                if not isinstance(effect, BossAoeEffect): effect.draw(screen, camera_x, camera_y)
                
            for bag in sandbags:
                bag.draw_dps(screen, camera_x, camera_y)

            if game_state == "GAMEOVER_ANIM" or (game_state == "RESULT" and not is_victory): player.update(is_dead=True)
            screen.blit(player.image, (player.rect.x-camera_x, player.rect.y-camera_y))
            player.draw_weapon(screen, camera_x, camera_y, mx, my, global_weapon_images)
            
            if getattr(player, "orbit_shield_active", False):
                rot_ang = pygame.time.get_ticks() / 3
                sh1 = pygame.transform.rotate(shield_part_img, rot_ang)
                sh2 = pygame.transform.rotate(shield_part_img, rot_ang + 180)
                ox = player.rect.centerx - camera_x
                oy = player.rect.centery - camera_y
                r = 45 
                screen.blit(sh1, sh1.get_rect(center=(ox + math.cos(math.radians(rot_ang))*r, oy - math.sin(math.radians(rot_ang))*r)))
                screen.blit(sh2, sh2.get_rect(center=(ox + math.cos(math.radians(rot_ang+180))*r, oy - math.sin(math.radians(rot_ang+180))*r)))

            if debuffs["vision_reduce"] > 0:
                vision_radius = 220 
                mask = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                mask.fill((0, 0, 0, 255)) 
                hole = pygame.Surface((vision_radius*2, vision_radius*2), pygame.SRCALPHA)
                for r in range(vision_radius, 0, -2):
                    alpha = int(255 * (1 - (r / vision_radius)**2))
                    pygame.draw.circle(hole, (255, 255, 255, alpha), (vision_radius, vision_radius), r)
                mask.blit(hole, (SCREEN_WIDTH//2 - vision_radius, SCREEN_HEIGHT//2 - vision_radius), special_flags=pygame.BLEND_RGBA_SUB)
                screen.blit(mask, (0, 0))

            if game_state in ["PLAYING", "TRAINING"]:
                for st in pedestals:
                    if math.hypot(player.rect.centerx - st.rect.centerx, player.rect.centery - st.rect.centery) < 70:
                        st.draw_prompt(screen, camera_x, camera_y)
                        
                for item in items_group:
                    if math.hypot(player.rect.centerx - item.rect.centerx, player.rect.centery - item.rect.centery) < 60:
                        item.draw_prompt(screen, camera_x, camera_y)
            
            draw_hud(screen, player, skill_icon_img)
            draw_minimap(screen, player, game_mode, current_floor)
            
            if game_mode == "TUTORIAL" and current_room_index >= 0:
                tut_texts = ["WASD 移动 ， F 键拾取物品", 
                             "鼠标左键攻击，蓄力武器长按蓄力", 
                             "[TAB]：商店 ， 1/2 切换武器.", 
                             " 空格 ：技能，双持武器", 
                             "选择游戏模式，打败敌人和强力BOSS，取得游戏胜利" ]
                tut_msg = tut_texts[min(current_room_index, len(tut_texts)-1)]
                tut_surf = font_large.render(tut_msg, True, YELLOW)
                screen.blit(tut_surf, (SCREEN_WIDTH//2 - tut_surf.get_width()//2, SCREEN_HEIGHT - 130))
            
            room_info_y = 60 if boss_alive else 20
            screen.blit(font_large.render(room_info_text, True, room_info_color), (SCREEN_WIDTH//2 - font_large.size(room_info_text)[0]//2, room_info_y))
            
            for e in enemies:
                if isinstance(e, Boss): e.draw_hp(screen, camera_x, camera_y)

            bar_bg = pygame.Rect(320, SCREEN_HEIGHT - 80, SCREEN_WIDTH - 370, 60)
            pygame.draw.rect(screen, (30,30,30), bar_bg, border_radius=10)
            pygame.draw.rect(screen, GRAY, bar_bg, 2, border_radius=10)
            
            slot_width = (bar_bg.width - 40) // max(2, player.weapon_slots)
            for i in range(player.weapon_slots):
                slot_rect = pygame.Rect(bar_bg.x + 20 + i * slot_width, bar_bg.y + 10, slot_width - 10, 40)
                border_color = YELLOW if i == player.current_weapon else GRAY
                if i == player.stolen_weap_idx: border_color = RED 
                pygame.draw.rect(screen, border_color, slot_rect, 2, border_radius=5)
                
                if i < len(player.weapons):
                    w_info = player.weapons[i]
                    if i == player.stolen_weap_idx:
                        txt = font_base.render("-[封 印 ]-", True, RED)
                        screen.blit(txt, (slot_rect.x + slot_rect.w//2 - txt.get_width()//2, slot_rect.y + 10))
                    else:
                        act_dmg = w_info["damage"]
                        if w_info["type"] in ["pistol", "bow"]: act_dmg = int(act_dmg * player.bonus_ranged_mult)
                        elif w_info["type"] == "melee": act_dmg = int(act_dmg * player.bonus_melee_mult)
                        elif w_info["type"] == "grenade": act_dmg = int(act_dmg * player.bonus_explosion_mult)
                        
                        if slot_width > 50:
                            screen.blit(font_base.render(w_info["name"][:8], True, WHITE), (slot_rect.x + 5, slot_rect.y + 10))
                            screen.blit(font_base.render(f"伤害: {act_dmg}", True, WHITE), (slot_rect.x + 205, slot_rect.y + 10))

            if game_state in ["PLAYING", "TRAINING", "PORTAL_CONFIRM"]:
                pygame.draw.line(screen, WHITE, (mx-10, my), (mx+10, my), 2)
                pygame.draw.line(screen, WHITE, (mx, my-10), (mx, my+10), 2)
                
            if game_state == "PAUSED":
                overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT)); overlay.set_alpha(200); overlay.fill(BLACK); screen.blit(overlay, (0, 0))
                
                cw, ch = 800, 640
                cx, cy = SCREEN_WIDTH//2 - cw//2, SCREEN_HEIGHT//2 - ch//2
                pygame.draw.rect(screen, (30,30,40), (cx, cy, cw, ch), border_radius=10)
                pygame.draw.rect(screen, ORANGE, (cx, cy, cw, ch), 3, border_radius=10)
                
                txt = font_title.render("游 戏 暂 停", True, ORANGE)
                screen.blit(txt, (cx + cw//2 - txt.get_width()//2, cy + 30))
                
                pygame.draw.rect(screen, (50,50,60), (cx + 30, cy + 100, 240, 500), border_radius=10)
                btn_resume  = draw_button(screen, "继续游戏", cx + 50, cy + 130, 200, 50, (50,150,50), (100,200,100), mx, my)
                btn_restart = draw_button(screen, "重新开始", cx + 50, cy + 220, 200, 50, (150,100,50), (200,150,100), mx, my)
                btn_main    = draw_button(screen, "返回主菜单", cx + 50, cy + 310, 200, 50, GRAY, WHITE, mx, my)
                btn_quit_pause = draw_button(screen, "退出游戏", cx + 50, cy + 400, 200, 50, RED, (255,100,100), mx, my) 

                # （TAB）
                tab_stats_hover = draw_button(screen, "角色属性", cx + 320, cy + 100, 140, 40, DARK_GRAY if pause_tab != 0 else ORANGE, YELLOW, mx, my)
                tab_weaps_hover = draw_button(screen, "背包武器", cx + 470, cy + 100, 140, 40, DARK_GRAY if pause_tab != 1 else ORANGE, YELLOW, mx, my)
                tab_talents_hover = draw_button(screen, " 天 赋 ", cx + 620, cy + 100, 140, 40, DARK_GRAY if pause_tab != 2 else ORANGE, YELLOW, mx, my)

                pygame.draw.rect(screen, (40,40,50), (cx + 300, cy + 150, 460, 450), border_radius=10)
                
                if pause_tab == 0:
                    stat_title = "- 基 础 面 板 属 性  -"
                    screen.blit(font_large.render(stat_title, True, CYAN), (cx + 300 + 460//2 - font_large.size(stat_title)[0]//2, cy + 170))
                    
                    stat_col1 = [
                        f"当前层数： 第 {current_floor} 层 ",
                        f"持有金币: {coins} ",
                        f" 血 量 : {int(player.hp)} / {player.max_hp} ",
                        f" 护 盾 : {player.shield:.1f} / {player.max_shield}",
                        f" 移 速 : {player.speed:.1f}"
                    ]
                    stat_col2 = [
                        f"远程伤害:  +{int((player.bonus_ranged_mult-1)*100)}%",
                        f"近战伤害:  +{int((player.bonus_melee_mult-1)*100)}%",
                        f"爆炸伤害： :  +{int((player.bonus_explosion_mult-1)*100)}%",
                        f" 攻 速 ：:  -{player.bonus_cd_reduction}%",
                    ]
                    
                    for k, v1 in enumerate(stat_col1): 
                        txt = font_base.render(v1, True, WHITE)
                        screen.blit(txt, (cx+320, cy+230 + k*35))
                        
                    for k, v2 in enumerate(stat_col2): 
                        txt = font_base.render(v2, True, (200,200,255))
                        screen.blit(txt, (cx+320, cy+420 + k*30))

                elif pause_tab == 1:
                    wt = "- 背 包 武 器 数 据 - "
                    screen.blit(font_large.render(wt, True, RED), (cx + 300 + 460//2 - font_large.size(wt)[0]//2, cy + 170))
                    for k, weapon in enumerate(player.weapons):
                        aw = weapon["damage"]
                        if weapon["type"] in ["pistol", "bow"]: aw = int(aw * player.bonus_ranged_mult)
                        elif weapon["type"] == "melee": aw = int(aw * player.bonus_melee_mult)
                        elif weapon["type"] == "grenade": aw = int(aw * player.bonus_explosion_mult)
                        cd = max(10, int(weapon['cd'] * (max(0.1, 1.0 - player.bonus_cd_reduction / 100.0))))
                        weap_txt = f"{k+1} 栏位 : [{weapon['name']}] "
                        w2 = f" 伤害：{aw}  [攻速：{cd}]"
                        screen.blit(font_base.render(weap_txt, True, WHITE), (cx+320, cy+220 + k*60))
                        screen.blit(font_base.render(w2, True, ORANGE), (cx+330, cy+220 + k*60 + 25))
                        
                elif pause_tab == 2:
                    tt = "- 已 获 得 天 赋- "
                    screen.blit(font_large.render(tt, True, PURPLE), (cx + 300 + 460//2 - font_large.size(tt)[0]//2, cy + 170))
                    talents_names = [all_talents_dict[t_id] for t_id in acquired_talents] if acquired_talents else ["还未获得天赋"]

                    for k, t_n in enumerate(talents_names[:16]): 
                         t_c = k % 2 ; t_r = k // 2
                         screen.blit(font_base.render(f" {t_n}", True, GREEN), (cx+320 + t_c*200, cy+220 + t_r*40))


            if game_state == "PORTAL_CONFIRM":
                overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT)); overlay.set_alpha(150); overlay.fill(BLACK); screen.blit(overlay, (0, 0))
                cw, ch = 400, 200
                cx, cy = SCREEN_WIDTH//2 - cw//2, SCREEN_HEIGHT//2 - ch//2
                pygame.draw.rect(screen, (40,40,40), (cx, cy, cw, ch), border_radius=10)
                pygame.draw.rect(screen, PURPLE, (cx, cy, cw, ch), 3, border_radius=10)
                
                txt_main = "O而K之" if game_mode=="TUTORIAL" else "是否进入下一层"
                txt = font_large.render(txt_main, True, WHITE)
                screen.blit(txt, (cx + cw//2 - txt.get_width()//2, cy + 40))
                
                btn_confirm_yes = draw_button(screen, "下一层！", cx + 20, cy + 110, 150, 50, (50,150,50), (100,200,100), mx, my)
                btn_confirm_no  = draw_button(screen, "稍等片刻", cx + 230, cy + 110, 150, 50, (150,50,50), (200,100,100), mx, my)

            elif game_state == "SHOP":
                overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT)); overlay.set_alpha(200); overlay.fill(BLACK); screen.blit(overlay, (0, 0))
                pw, ph = 700, 500
                px, py = (SCREEN_WIDTH - pw)//2, (SCREEN_HEIGHT - ph)//2
                
                pygame.draw.rect(screen, (40,40,40), (px, py, pw, ph), border_radius=10)
                pygame.draw.rect(screen, YELLOW, (px, py, pw, ph), 3, border_radius=10)
                
                shop_t = "蜜 汁 小 商 店"
                screen.blit(font_title.render(shop_t, True, YELLOW), (px + pw//2 - font_title.size(shop_t)[0]//2, py+20))
                
                screen.blit(font_large.render(f"金币: {coins}", True, CYAN), (px+30, py+80))
                start_idx, end_idx = shop_page * 4, min((shop_page + 1) * 4, len(shop_items))
                
                shop_btns = []
                for i in range(start_idx, end_idx):
                    item = shop_items[i]
                    y = py + 140 + (i - start_idx)*70

                    pygame.draw.rect(screen, (55, 55, 70), (px + 20, y - 10, pw - 40, 60), border_radius=6)
                    
                    name_color = GRAY if item['level'] >= item['max'] else WHITE
                    desc_text = f"■ {item['name']} " + ("MAX 满级啦" if item['level'] >= item['max'] else f"Lv ：.{item['level']})")
                    screen.blit(font_large.render(desc_text, True, name_color), (px+40, y + 5))
                    
                    btn_rect = pygame.Rect(px+pw-160, y-5, 130, 50)
                    can_buy = coins >= item['cost'] and item['level'] < item['max']
                    is_hover = can_buy and btn_rect.collidepoint(mx, my)
                    
                    pygame.draw.rect(screen, (100,200,100) if is_hover else (50,150,50) if can_buy else GRAY, btn_rect, border_radius=5)
                    
                    cost_txt = font_base.render(f"$ {item['cost']}", True, BLACK if is_hover else WHITE)
                    screen.blit(cost_txt, (btn_rect.x + btn_rect.w//2 - cost_txt.get_width()//2, btn_rect.y + 15))
                    
                    shop_btns.append((btn_rect, item, can_buy))
                    
                prev_hover = draw_button(screen, "上一页", px + 40, py + ph - 70, 160, 40, GRAY, WHITE, mx, my) if shop_page > 0 else False
                next_hover = draw_button(screen, "下一页", px + pw - 250, py + ph - 70, 200, 40, GRAY, WHITE, mx, my) if end_idx < len(shop_items) else False
                screen.blit(font_base.render("TAB键关闭：)", True, GRAY), (px+145, py+ph-30))

            elif game_state == "TALENT": 
                overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT)); overlay.set_alpha(230); overlay.fill(BLACK); screen.blit(overlay, (0, 0))
                tal_tt = "天 赋 三 选 一 :"
                screen.blit(font_large.render(tal_tt, True, PURPLE), (SCREEN_WIDTH//2 - font_large.size(tal_tt)[0]//2, 100))
                talent_btns = []
                for i, t in enumerate(current_talents):
                    bx, by = SCREEN_WIDTH//2 - 250, 220 + i * 140
                    btn = draw_button(screen, f"{t['name']} - : {t['desc']}", bx, by, 500, 100, (50,50,80), (80,80,120), mx, my)
                    talent_btns.append((btn, t))
                    
            elif game_state == "GAMEOVER_ANIM" and pygame.time.get_ticks() - death_timer > 3000: game_state = "RESULT"
            elif game_state == "RESULT":
                overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT)); overlay.set_alpha(220); overlay.fill(BLACK); screen.blit(overlay, (0,0))
                res_txt = "通  关  成  功 " if is_victory else "你  死  了"
                res_col = GREEN if is_victory else RED
                screen.blit(font_title.render(res_txt, True, res_col), (SCREEN_WIDTH//2 - font_title.size(res_txt)[0]//2, 80))
                
                r2 = f"难度:{game_mode} ,第【 {current_floor} 】层"
                screen.blit(font_large.render(r2, True, WHITE), (SCREEN_WIDTH//2 - font_large.size(r2)[0]//2, 180))
                r3 = f"获取金币总量 : 【{total_coins} 】| 当前剩余金币： {coins}."
                screen.blit(font_large.render(r3, True, YELLOW), (SCREEN_WIDTH//2 - font_large.size(r3)[0]//2, 240))
                
                pygame.draw.rect(screen, GRAY, (SCREEN_WIDTH//2 - 400, 290, 800, 2))
                rt = "最终"
                screen.blit(font_large.render(rt, True, PALE_YELLOW), (SCREEN_WIDTH//2 - font_large.size(rt)[0]//2, 310))
                
                for idx, w in enumerate(player.weapons):
                    w_img = global_weapon_images.get(w["name"])
                    px_x = SCREEN_WIDTH//2 - 200 + idx*400
                    if w_img:
                        s_img = pygame.transform.scale(w_img, (int(w_img.get_width()*0.8), int(w_img.get_height()*0.8)))
                        screen.blit(s_img, (px_x, 380 - s_img.get_height()//2))
                    act_dmg = w["damage"]
                    if w["type"] in ["pistol", "bow"]: act_dmg = int(act_dmg * player.bonus_ranged_mult)
                    elif w["type"] == "melee": act_dmg = int(act_dmg * player.bonus_melee_mult)
                    elif w["type"] == "grenade": act_dmg = int(act_dmg * player.bonus_explosion_mult)
                    screen.blit(font_base.render(f"{w['name']}", True, WHITE), (px_x, 420))
                    screen.blit(font_base.render(f"面板数值 {act_dmg}", True, (255,100,100)), (px_x-50, 445))
                
                btn_restart_res = draw_button(screen, "返回主菜单", SCREEN_WIDTH//2-250, 550, 500, 50, GRAY, WHITE, mx, my)
                btn_quit_res = draw_button(screen, "退出游戏", SCREEN_WIDTH//2-300, 620, 600, 50, RED, (255,100,100), mx, my)

        pygame.display.flip(); clock.tick(FPS)

if __name__ == "__main__":
    main()