import random
import tkinter as tk
import time
import os # 彻底关闭程序，终止进程
import math

root = tk.Tk() # 创建游戏主窗口
root.protocol("WM_DELETE_WINDOW", root.destroy) # 窗口安全设置，点击右上角x时可正常关闭，不会卡死
root.title("game") 
main_frame = tk.Frame(root) # 框架容器
main_frame.pack() # 把框架放在窗口上
m1 = root.winfo_screenwidth()//2 - 450 # 获取电脑屏幕宽度，取一半，减去窗口的一般
m2 = root.winfo_screenheight()//2 - 410 # 同上，上面是水平居中，这个是垂直居中
root.geometry(f'{900}x{750}+{m1}+{m2}') # 宽度x高度+X坐标+Y坐标

control_frame = tk.Frame(main_frame) # 创建顶部控制栏框架
control_frame.pack(side=tk.TOP, fill=tk.X) # 放在顶部，横向填满

close_button = tk.Button(control_frame, text="不玩了 закончится", command=lambda: os._exit(0), 
                         bg="black", fg="white", width=18) # 关闭按钮
close_button.pack(side=tk.RIGHT, padx=5, pady=2) # 位置，放在右侧，上下留白5像素，左右留白2像素

# 顶部说明标签 Предметы: ① Синий: усиление пуль ② Фиолетовый: увеличение скорости движения ③ Голубой: левый Shift телепортация
score_label = tk.Label(control_frame, text=f"道具： ①蓝色：子弹强化 ②紫色：移速增加 ③青色：左shift 瞬移", font=("Arial", 12))
score_label.pack(side=tk.LEFT, padx=5) # 同上上

# Canvas是 tkinter 绘图专用组件
a = tk.Canvas(main_frame, width=900, height=700, bg='black') # 创建游戏画布
a.pack()

# !!! 1. 玩家改为直径20的浅绿色圆形（原矩形）
B = a.create_oval(440, 490, 460, 510, fill='#90EE90')  # 直径20：440-460(x)，490-510(y)
a_time = 0 # 备用计时变量，当前代码未使用
# !!! 敌人列表更新：[容器ID(球形碰撞体), 血条背景ID, 血条进度ID, 最大血量, 当前血量, 半径, 生成方向]
e = []          
# !!! 子弹列表更新：[子弹ID, dx, dy]（存储移动方向）
b = []          
z = []          # 增益1蓝
z2 = []         # 增益2紫
z3 = []         # 增益3青
score = 0
high_score = 0   #历史最高分
speed_user = 5  # 角色移动速度
hurt = 15        # 子弹伤害

# !!! 新增：持续射击控制变量
shooting = False  # 标记是否按住鼠标左键
shoot_interval = 0.1  # 持续射击间隔（秒），控制射速
last_shoot_time = 0  # 上一次射击时间

# 菜单，当前未使用
def menu():
    menu_canvas = tk.Canvas(root, width=600, height=450, bg="black")
    menu_canvas.pack()
    menu_canvas.create_text(300, 100, text="shoot game", fill="white", font=("Arial", 30))
    start_button = tk.Button(menu_canvas, text="start", command=start_game)
    start_button.place(x=250, y=200)

def start_game():
    pass

# !!! 2. 生成有血条的球形敌人（碰撞体积为红球，血条仅视觉）
def create_enemy(x, y, radius, max_hp):
    # !!! 透明容器替换为红色球形碰撞体（实际碰撞体积）以x，y为中心画圆，红色，无边框
    container = a.create_oval(x-radius, y-radius, x+radius, y+radius, fill='red', outline='')
    # !!! 血条背景（仅视觉，无碰撞），位置在球形敌人上方
    hp_bg = a.create_rectangle(x-radius, y-radius-8, x+radius, y-radius-3, fill='black', outline='red')
    # !!! 红色血条（仅视觉）
    hp_bar = a.create_rectangle(x-radius, y-radius-8, x+radius, y-radius-3, fill='red', outline='')
    # 返回完整结构：[球形碰撞体ID, 血条背景ID, 血条进度ID, 最大血量, 当前血量, 半径]
    return [container, hp_bg, hp_bar, max_hp, max_hp, radius]    # !!! 修改返回结构

# !!! 3. 更新血条显示（适配球形敌人位置）
def update_enemy_hp(enemy):
    try:
        container, hp_bg, hp_bar, max_hp, current_hp, radius = enemy  # !!! 适配新结构 解包敌人数据
        x1, y1 = a.coords(container)[0], a.coords(container)[1]       # 获取球形敌人左上角坐标
        hp_ratio = max(0, current_hp / max_hp)                        # 血量比例（避免负数）
        new_hp_width = 2 * radius * hp_ratio                          # 剩余血条宽度（敌人直径 × 血量比例）
        # !!! 血条位置跟随球形敌人，始终在上方
        a.coords(hp_bar, x1, y1-8, x1 + new_hp_width, y1-3)    #重新设置血条长度，始终显示在敌人头顶   
    except:
        pass

# 重新开始
def restart():
    popup.destroy() # 关闭游戏结束弹窗
    # 声明所有全局变量：函数内要修改的外部变量必须声明
    global e, b, z, z2, z3, score, speed_user, B, pause_bg, pause_text, Score, High_score
    global zengyi_1_text, zengyi_2_text, shunyi_number, zengyi_3_text, zengyi_3_text_2, zengyi_3_text_3
    global zengyi_1_active, zengyi_1_time_left, zengyi_2_active, zengyi_2_time_left, shooting, last_shoot_time
    e = []  
    b = []   
    z = [] 
    z2 = []
    z3 = []
    score = 0
    shunyi_number = 0
    speed_user = 5
    zengyi_1_active = False
    zengyi_1_time_left = 0
    zengyi_2_active = False
    zengyi_2_time_left = 0
    shooting = False
    last_shoot_time = 0      # 重置所有游戏数据，恢复初始状态
    
    a.delete("all") # 清空所有画布元素
    # !!! 重新创建球形玩家
    B = a.create_oval(440, 490, 460, 510, fill='#90EE90')
    # 重置暂停提示：按 P 开始
    pause_bg = a.create_rectangle(350, 250, 550, 350, fill='pink', stipple='gray50', outline='') 
    pause_text = a.create_text(445, 300, text="按P开始游戏", fill="white", font=("Arial", 20))
    # 重置所有分数、道具提示文字
    Score = a.create_text(850, 20, text="", font=("Arial", 12), fill="yellow")
    High_score = a.create_text(150, 20, text="", font=("Arial", 12), fill="red")
    zengyi_1_text = a.create_text(450, 20, text="", font=("Arial", 12), fill="yellow")
    zengyi_2_text = a.create_text(450, 40, text="", font=("Arial", 12), fill="yellow")
    zengyi_3_text = a.create_text(70, 80, text="", font=("Arial", 12), fill="yellow")
    zengyi_3_text_2 = a.create_text(120, 100, text="", font=("Arial", 12), fill="yellow")
    zengyi_3_text_3 = a.create_text(80, 120, text="", font=("Arial", 12), fill="yellow")
    # 重新创建鼠标准星
    global crosshair
    crosshair = a.create_text(0, 0, text="+", fill="white", font=("Arial", 12))

# 暂停设置，方向键按下设置
paused = False
left_1 = False
up_1 = False 
right_1 = False
down_1 = False

# 绑定WASD方向键
root.bind("<KeyPress-a>", lambda e: globals().update(left_1=True))
root.bind("<KeyRelease-a>", lambda e: globals().update(left_1=False))
root.bind("<KeyPress-d>", lambda e: globals().update(right_1=True))
root.bind("<KeyRelease-d>", lambda e: globals().update(right_1=False))
root.bind("<KeyPress-w>", lambda e: globals().update(up_1=True))
root.bind("<KeyRelease-w>", lambda e: globals().update(up_1=False))
root.bind("<KeyPress-s>", lambda e: globals().update(down_1=True))
root.bind("<KeyRelease-s>", lambda e: globals().update(down_1=False))

# 切换暂停 / 开始
def key_press():
    global paused, pause_text, pause_bg, pause_text_1, pause_bg_1, pause_text_2, pause_bg_2
    paused = not paused
    # 暂停时显示粉色半透明遮罩，取消暂停时删除遮罩
    if paused:
        pause_bg = a.create_rectangle(350, 250, 550, 350, fill='pink', stipple='gray50', outline='') 
        pause_text = a.create_text(445, 300, text="游戏暂停", fill="white", font=("Arial", 20))
    else:
        if pause_bg:
            a.delete(pause_bg)
            pause_bg = None
        if pause_text:    
            a.delete(pause_text)
            pause_text = None
        if pause_bg_1:
            a.delete(pause_bg_1)
            pause_bg_1 = None
        if pause_text_1:    
            a.delete(pause_text_1)
            pause_text_1 = None
        if pause_bg_2:
            a.delete(pause_bg_2)
            pause_bg_2 = None
        if pause_text_2:    
            a.delete(pause_text_2)
            pause_text_2 = None    

# !!! 4. 获取玩家中心坐标（适配球形玩家）
def get_player_center():
    # 获取球形玩家的中心坐标，左上角+右下角除以二
    coords = a.coords(B)
    center_x = (coords[0] + coords[2]) / 2
    center_y = (coords[1] + coords[3]) / 2
    return (center_x, center_y)

# !!! 5. 计算射击方向向量（鼠标瞄准）
def get_shoot_direction(pcx, pcy, mx, my, speed=8):
    dx = mx - pcx
    dy = my - pcy   # 鼠标-玩家的坐标差
    dist = math.hypot(dx, dy) # 勾股定理算直线距离
    if dist < 1:
        return 0, -speed
    return dx/dist * speed, dy/dist * speed  # 单位向量 × 速度 = 标准移动方向

# !!! 6. 鼠标瞄准射击（持续射击版，移除event依赖）
def shoot():
    if paused:  # 暂停时不射击
        return
    colors = ['#FFB6C1','#87CEEB','#98FB98','#DDA0DD',
              '#FFD700','#F0E68C','#E6E6FA',"#8FDCE6"] # 强化子弹的随机颜色库
    # 获取玩家中心和鼠标位置
    px, py = get_player_center()
    
    # !!! 关键修复：只取画布内鼠标坐标
    mx = a.winfo_pointerx() - a.winfo_rootx()
    my = a.winfo_pointery() - a.winfo_rooty()

    dx, dy = get_shoot_direction(px, py, mx, my, 8) # 计算子弹方向

    # 子弹
    bid = a.create_rectangle(px-2, py-2, px+2, py+2, fill="white") # 创建白色小方块子弹
    b.append([bid, dx, dy]) # 存入子弹列表：[子弹 ID, 方向 X, 方向 Y]
    # 子弹强化：生成额外子弹（偏移角度）
    if zengyi_1_active :
        cor = random.choice(colors)
        # 额外子弹1：向左偏移15度
        angle_offset = math.radians(15)
        dx1 = dx * math.cos(angle_offset) - dy * math.sin(angle_offset)
        dy1 = dx * math.sin(angle_offset) + dy * math.cos(angle_offset)
        bullet1 = a.create_rectangle(
            player_center[0]-2, player_center[1]-2,
            player_center[0]+2, player_center[1]+2,
            fill=cor
        )
        b.append([bullet1, dx1, dy1]) # 三角函数实现角度偏移
        
        # 额外子弹2：向右偏移15度
        angle_offset = math.radians(-15)
        dx2 = dx * math.cos(angle_offset) - dy * math.sin(angle_offset)
        dy2 = dx * math.sin(angle_offset) + dy * math.cos(angle_offset)
        bullet2 = a.create_rectangle(
            player_center[0]-2, player_center[1]-2,
            player_center[0]+2, player_center[1]+2,
            fill=cor
        )
        b.append([bullet2, dx2, dy2])

# !!! 7. 持续射击控制函数
def start_shooting(event):
    global shooting
    shooting = True

def stop_shooting(event):
    global shooting
    shooting = False

# !!! 8. 计算敌人追踪玩家的移动向量 敌人永远朝向玩家移动，单位向量保证移动速度恒定
def get_enemy_move_vector(enemy_center, player_center, speed):
    dx = player_center[0] - enemy_center[0]
    dy = player_center[1] - enemy_center[1]
    distance = math.hypot(dx, dy)
    if distance == 0:
        return (0, 0)
    dx = (dx / distance) * speed
    dy = (dy / distance) * speed
    return (dx, dy)

# 增益时间
# ① 子弹强化持续 15 秒，显示倒计时
zengyi_1_active = False
zengyi_1_time_left = 0
zengyi_1_text = a.create_text(450, 20, text="", font=("Arial", 12), fill="yellow")

def time_1(seconds_left): 
    if seconds_left > 0 :    
        a.itemconfig(zengyi_1_text, text=f"强化子弹：{seconds_left}秒")
    else:
        a.itemconfig(zengyi_1_text, text="") 

# ② 移速强化从 5 → 8，持续 10 秒
zengyi_2_active = False
zengyi_2_time_left = 0
zengyi_2_text = a.create_text(450, 40, text="", font=("Arial", 12), fill="yellow")

def time_2(seconds_left): 
    global speed_user
    if seconds_left > 0 :
        speed_user = 8    
        a.itemconfig(zengyi_2_text, text=f"强化移速：{seconds_left}秒")
    else:
        speed_user = 5
        a.itemconfig(zengyi_2_text, text="") 

# ③ 瞬移找到最下方敌人，玩家瞬移到敌人下方 80 像素，无敌人时 + 5 分
zengyi_3_active = False
shunyi_number = 0
zengyi_3_text = a.create_text(70, 80, text="", font=("Arial", 12), fill="yellow")
zengyi_3_text_2 = a.create_text(120, 100, text="", font=("Arial", 12), fill="yellow")
zengyi_3_text_3 = a.create_text(80, 120, text="", font=("Arial", 12), fill="yellow")
zengyi_3_time_left_1 = 0
zengyi_3_time_left_2 = 3

# 找到最下方敌人，玩家瞬移到敌人下方 80 像素，无敌人时 + 5 分
def shunyi():
    global shunyi_number, score, zengyi_3_time_left_1, zengyi_3_time_left_2
    if shunyi_number > 0:
        if len(e) > 0 :
            # 找到最下方的敌人（适配球形敌人）
            lowest_enemy = max(e, key=lambda en: a.coords(en[0])[3])
            enemy_coords = a.coords(lowest_enemy[0])
            enemy_center_y = (enemy_coords[1] + enemy_coords[3]) / 2
            enemy_center_x = (enemy_coords[0] + enemy_coords[2]) / 2
            # 瞬移到敌人下方（适配球形玩家）
            new_center_x = enemy_center_x
            new_center_y = enemy_center_y + 80
            # 确保玩家不超出画布边界（直径20）
            new_center_x = max(10, min(new_center_x, 890))
            new_center_y = max(10, min(new_center_y, 690))
            # 移动球形玩家
            a.coords(B, 
                     new_center_x-10, new_center_y-10,
                     new_center_x+10, new_center_y+10)
        else:
            score += 5
            a.itemconfig(Score, text=f'分数： {score}')
            zengyi_3_time_left_2 = 3
            a.itemconfig(zengyi_3_text_3, state='normal', text="战场无敌人,获得5分")        
    else:
        zengyi_3_time_left_1 = 3
        a.itemconfig(zengyi_3_text_2, state='normal', text=f"剩余瞬移次数: {shunyi_number}次,还未获得瞬移")      

    shunyi_number -= 1
    shunyi_number = max(0, shunyi_number)  # 确保次数不为负
    a.itemconfig(zengyi_3_text, text=f"剩余瞬移次数: {shunyi_number}次")

# !!! 9. 按键绑定（移除空格射击，保留瞬移和暂停）
def move(event):       
    global paused, pause_text, pause_bg
    if event.keysym == 'p':
        key_press()          
    if not paused:
        if event.keysym == "Shift_L":
            shunyi()        
    else:
        pass             # P 键：暂停 / 开始，左 Shift：瞬移                                     

# 绑定所有按键
root.bind('<Key>', move)

# !!! 10. 鼠标事件绑定（持续射击）
# 鼠标左键按下开始射击，释放停止射击
a.bind("<ButtonPress-1>", start_shooting)
a.bind("<ButtonRelease-1>", stop_shooting)
# 鼠标准星跟随
crosshair = a.create_text(0, 0, text="+", fill="white", font=("Arial", 12))
a.bind("<Motion>", lambda e: a.coords(crosshair, a.canvasx(e.x), a.canvasy(e.y)))

pause_bg = None
pause_text = None
pause_bg_1 = None
pause_text_1 = None
pause_bg_2 = None
pause_text_2 = None

# 创建分数显示
Score = a.create_text(800, 20, text="", font=("Arial", 12), fill="yellow")
High_score = a.create_text(150, 20, text="", font=("Arial", 12), fill="red")

# !!! 11. 初始游戏说明更新（空格射击改为鼠标左键）
paused = True
pause_bg_1 = a.create_rectangle(25, 70, 165, 110, fill='pink', stipple='gray50', outline='') 
pause_text_1 = a.create_text(100, 90, text="游戏规则：", fill="white", font=("Arial", 20))

pause_bg = a.create_rectangle(190, 100, 430, 220, fill='pink', stipple='gray50', outline='') 
pause_text = a.create_text(310, 160, text=f" 1.↑↓←→ 控制移动 \n 2.‘P’暂停,开始 \n 3.鼠标左键持续射击",  # !!! 修改射击说明
                            fill="white", font=("Arial", 20))

pause_bg_2 = a.create_rectangle(50, 270, 700, 430, fill='pink', stipple='gray50', outline='')
pause_text_2 = a.create_text(375, 350, text=f" 1. 蓝色：强化子弹，持续15秒\n" 
                    " 2. 紫色：增强移速，持续十秒 \n "
                    "3. 青色：拾取后左shift，瞬移到最下方敌人的下面\n     如果地图中无敌人，消耗一次传送增加5分",
                            fill="white", font=("Arial", 20))

# 主循环
frame_count = 0
while True:    
    if not paused: # 暂停时不运行游戏逻辑
        # 复制列表避免遍历时修改原列表
        e2 = e[:]
        n = b[:]
        Z1 = z[:]
        Z2 = z2[:]
        Z3 = z3[:]

        # 角色移动控制（适配球形玩家）
        coords = a.coords(B)
        if left_1 and coords[0] > 0: 
            a.move(B, -speed_user, 0) # 按 A 左移，不超出左边界
        if up_1 and coords[1] > 0: 
            a.move(B, 0, -speed_user)
        if right_1 and coords[2] < 900: 
            a.move(B, speed_user, 0)
        if down_1 and coords[3] < 700: 
            a.move(B, 0, speed_user)

        # !!! 12. 持续射击逻辑（核心新增），按住鼠标 + 时间到 0.1 秒 → 射击一次
        current_time = time.time()
        if shooting and (current_time - last_shoot_time) >= shoot_interval:
            shoot()  # 调用射击函数
            last_shoot_time = current_time

        # !!! 13. 生成四面八方的球形敌人（大小/血量挂钩）
        if random.random() < 0.008:         # 每帧有 0.8% 概率生成敌人               
            up = random.randint(5, 40)
            enemy_radius = up // 2  # !!! 敌人半径和血量挂钩（半径=数值//2）
            enemy_max_hp = up * 2   # 敌人最大血量（和尺寸挂钩）
           
            # !!! 随机选择生成方向：上(0)/下(1)/左(2)/右(3)
            spawn_side = random.randint(0, 3)
            canvas_width = 900
            canvas_height = 700
            spawn_offset = 50  # 生成在画布外50像素
            
            if spawn_side == 0:
                # 上方生成
                enemy_x = random.randint(enemy_radius, canvas_width - enemy_radius)
                enemy_y = -spawn_offset
            elif spawn_side == 1:
                # 下方生成
                enemy_x = random.randint(enemy_radius, canvas_width - enemy_radius)
                enemy_y = canvas_height + spawn_offset
            elif spawn_side == 2:
                # 左方生成
                enemy_x = -spawn_offset
                enemy_y = random.randint(enemy_radius, canvas_height - enemy_radius)
            else:
                # 右方生成
                enemy_x = canvas_width + spawn_offset
                enemy_y = random.randint(enemy_radius, canvas_height - enemy_radius)
            
            # !!! 创建球形敌人
            new_enemy = create_enemy(enemy_x, enemy_y, enemy_radius, enemy_max_hp)
            e.append(new_enemy)
               
        # !!! 14. 敌人移动（四面八方朝玩家追踪）
        speed = 0.5 + score * 0.04     
        game_over = False
        player_center = get_player_center()  # 获取玩家中心
        # 敌人 + 血条一起向玩家移动
        for enemy in e2:
            try:
                container, hp_bg, hp_bar, max_hp, current_hp, radius = enemy
                # 获取敌人中心坐标
                enemy_coords = a.coords(container)
                enemy_center_x = (enemy_coords[0] + enemy_coords[2]) / 2
                enemy_center_y = (enemy_coords[1] + enemy_coords[3]) / 2
                # 计算朝向玩家的移动向量
                dx, dy = get_enemy_move_vector((enemy_center_x, enemy_center_y), player_center, speed)
                
                # 移动球形敌人 + 血条（同步移动）
                a.move(container, dx, dy)
                a.move(hp_bg, dx, dy)
                a.move(hp_bar, dx, dy)
                
                # !!! 游戏结束条件：球形敌人触碰到玩家→ 游戏结束
                if (enemy_coords[0] < coords[2] and enemy_coords[2] > coords[0] and
                    enemy_coords[1] < coords[3] and enemy_coords[3] > coords[1]):
                    # 删除敌人所有元素 
                    a.delete(container)
                    a.delete(hp_bg)
                    a.delete(hp_bar)
                    if enemy in e:
                        e.remove(enemy)
                    # 更新最高分
                    if score > high_score : 
                        high_score = score
                    paused = True
                    game_over = True
                    break
            except:
                if enemy in e:
                    e.remove(enemy)
                continue
        
        # 游戏结束弹窗
        if game_over:
            popup = tk.Toplevel(root)
            popup_width = 400
            popup_height = 300
            p1 = (root.winfo_screenwidth() - popup_width) // 2 - 50
            p2 = (root.winfo_screenheight() - popup_height) // 2 - 100
            popup.geometry(f'{popup_width}x{popup_height}+{p1}+{p2}')
            popup.configure(bg="pink")
            
            label_high = tk.Label(popup, text=f"最高分： {high_score}", bg="pink",
                    fg='black', font=("Arial", 15, "bold"))
            label_high.place(relx=0.075, rely=0.06)

            label_score = tk.Label(popup, text=f"你的得分是： {score}", bg="pink",
                    fg='black', font=("Arial", 25, "bold"))
            label_score.place(relx=0.075, rely=0.15)

            label = tk.Label(popup, text="可惜，你还得练！", bg="pink",
                    fg='black', font=("Arial", 30, "bold"))
            label.place(relx=0.075, rely=0.35)

            button_close = tk.Button(popup, text="关闭", command=lambda: os._exit(0), width=15, bg="white"
                , fg="black", font=("Arial", 10))   
            button_close.place(relx=0.59, rely=0.7)
            
            button_restart = tk.Button(popup, text="再来一次", command=restart, width=15, bg="white"
                , fg="black", font=("Arial", 10))   
            button_restart.place(relx=0.19, rely=0.7)
            continue

        # !!! 15. 子弹移动（按鼠标方向向量）
        for bullet in n:
            try:
                bullet_id, dx, dy = bullet  # !!! 取出子弹ID和移动方向
                a.move(bullet_id, dx, dy) # 出界自动删除
                # 子弹超出画布边界删除
                bullet_coords = a.coords(bullet_id)
                if (bullet_coords[0] < 0 or bullet_coords[2] > 900 or
                    bullet_coords[1] < 0 or bullet_coords[3] > 700):
                    a.delete(bullet_id)
                    if bullet in b:
                        b.remove(bullet)
            except:
                if bullet in b:
                    b.remove(bullet)
                continue

    # 增益1：子弹强化
        if random.random() < 0.003:                      
            zengyi1 = random.randint(1, 870)
            z.append(a.create_rectangle(zengyi1, 0, zengyi1+20, 30, fill='blue')) 

        # 增益1移动
        for z1 in Z1:
            try:
                a.move(z1, 0, 0.9)
                if a.coords(z1)[1] > 700:
                    a.delete(z1)
                    if z1 in z:
                        z.remove(z1)
            except:
                if z1 in z:
                    z.remove(z1)
                continue
        frame_count += 0.7 

        # 拾取增益1（适配球形玩家）
        player_coords = a.coords(B)
        for z11 in Z1:        
            try:    
                if (a.coords(z11)[0] < player_coords[2] and
                    a.coords(z11)[2] > player_coords[0] and
                    a.coords(z11)[1] < player_coords[3] and
                    a.coords(z11)[3] > player_coords[1] ):
                    a.delete(z11)
                    if z11 in z:
                        z.remove(z11)
                    zengyi_1_active = True
                    zengyi_1_time_left = 15            
            except:
                if z11 in z:
                    z.remove(z11)
                continue 

    # 增益2：移速增加（修复原代码bug）
        if random.random() < 0.0015:   
            zengyi_2_x= random.randint(1,870)
            zengyi_2_math = random.uniform(0, 2 * math.pi)  # !!! 改为浮点数角度
            # !!! 存储增益2的完整信息（ID、初始角度、当前角度、初始x）
            z2.append([
                a.create_oval(zengyi_2_x, 0, zengyi_2_x+20, 30, fill="#9A45C1"),
                zengyi_2_math,
                0.0,
                zengyi_2_x
            ])
 
        # 增益2移动（修复轨迹bug）
        to_remove_z2 = []
        for idx, z2_item in enumerate(Z2):                                         
            try:
                z22, angle_seed, current_angle, init_x = z2_item
                current_angle += 0.04
                current_angle = current_angle % (2 * math.pi)
                zengyi_2_move = 2.5 * math.sin(angle_seed + current_angle)
                
                current_x = a.coords(z22)[0] + zengyi_2_move
                if current_x < 0:
                    zengyi_2_move = -current_x
                elif current_x + 20 > 900:
                    zengyi_2_move = 900 - (current_x + 20)
                
                a.move(z22, zengyi_2_move, 2)
                z2[idx][2] = current_angle  # 更新当前角度
                
                if a.coords(z22)[1] > 700:
                    a.delete(z22)
                    to_remove_z2.append(z2_item)
            except Exception as e:
                to_remove_z2.append(z2_item)
                continue
        # 批量删除超出边界的增益2
        for item in to_remove_z2:
            if item in z2:
                z2.remove(item)

        # 拾取增益2（适配球形玩家）
        to_remove_pick_z2 = []
        for z2_item in Z2:                                         
            try:    
                z222 = z2_item[0]
                z2_coords = a.coords(z222)
                if (z2_coords[0] < player_coords[2] and z2_coords[2] > player_coords[0] and
                    z2_coords[1] < player_coords[3] and z2_coords[3] > player_coords[1]):
                    a.delete(z222)
                    to_remove_pick_z2.append(z2_item)
                    zengyi_2_active = True
                    zengyi_2_time_left = 10             
            except:
                to_remove_pick_z2.append(z2_item)
                continue 
        # 批量删除拾取的增益2
        for item in to_remove_pick_z2:
            if item in z2:
                z2.remove(item)

    # 增益3：瞬移
        if random.random() < 0.001 + score * 0.00008:                             
            zengyi_3 = random.randint(1, 870)
            z3.append(a.create_oval(zengyi_3, 0, zengyi_3+20, 25, fill='#2B9BA9'))        

        # 增益3移动
        for z33 in Z3:                                     
            try:
                a.move(z33, 0, 0.9)
                if a.coords(z33)[1] > 900:
                    a.delete(z33)
                    if z33 in z3:
                        z3.remove(z33)
            except:
                if z33 in z3:
                    z3.remove(z33)
                continue

        # 拾取增益3（适配球形玩家）
        to_remove_pick_z3 = []
        for z33 in Z3:                                         
            try:    
                z3_coords = a.coords(z33)
                if (z3_coords[0] < player_coords[2] and z3_coords[2] > player_coords[0] and
                    z3_coords[1] < player_coords[3] and z3_coords[3] > player_coords[1]):
                    a.delete(z33)
                    to_remove_pick_z3.append(z33)
                    shunyi_number += 1
                    a.itemconfig(zengyi_3_text, text=f"剩余瞬移次数: {shunyi_number}次")
            except:
                to_remove_pick_z3.append(z33)
                continue 
        # 批量删除拾取的增益3
        for item in to_remove_pick_z3:
            if item in z3:
                z3.remove(item)
        
    # 增益时间计数
        if frame_count >= 50:
            frame_count = 0
            if zengyi_1_time_left > 0 :
                zengyi_1_time_left -= 1
                time_1(zengyi_1_time_left)
                if zengyi_1_time_left <= 0 :
                    zengyi_1_active = False
            if zengyi_2_time_left > 0 :
                zengyi_2_time_left -= 1
                time_2(zengyi_2_time_left)
                if zengyi_2_time_left <= 0 :
                    zengyi_2_active = False 
            if zengyi_3_time_left_1 > 0 :
                zengyi_3_time_left_1 -= 1
                if zengyi_3_time_left_1 <= 0 :
                    a.itemconfig(zengyi_3_text_2, state='hidden')
            if zengyi_3_time_left_2 > 0 :
                zengyi_3_time_left_2 -= 1
                if zengyi_3_time_left_2 <= 0 :     
                    a.itemconfig(zengyi_3_text_3, state='hidden')             

        # 子弹击中敌人的掉血效果（适配球形敌人）
        remove_enemy = []
        for zidan in n:                  # 遍历每一颗子弹
            hit_flag = False             # 标记是否击中敌人
            for enemy2 in e2:            # 遍历每一个敌人
                if hit_flag:
                    continue
                try:                                  
                    container, hp_bg, hp_bar, max_hp, current_hp, radius = enemy2
                    # 碰撞检测：子弹和球形敌人碰撞
                    bullet_coords = a.coords(zidan[0])  # !!! 适配新子弹结构
                    enemy_coords = a.coords(container)
                    if (bullet_coords[0] < enemy_coords[2] and
                        bullet_coords[2] > enemy_coords[0] and
                        bullet_coords[1] < enemy_coords[3] and
                        bullet_coords[3] > enemy_coords[1]):
                        a.delete(zidan[0])
                        if zidan in b:    
                            b.remove(zidan)
                        # 敌人掉血
                        enemy2[4] -= hurt
                        # 更新血条
                        update_enemy_hp(enemy2)
                        if enemy2[4] <= 0:
                            a.delete(container)
                            a.delete(hp_bg)
                            a.delete(hp_bar)
                            remove_enemy.append(enemy2)    
                        hit_flag = True  # 一颗子弹只击中一个敌人
                except:
                    continue
        
        # 删除被击败的敌人 更新分数
        for em in remove_enemy:
            if em in e:
                e.remove(em)
                score += 1
                a.itemconfig(Score, text=f'分数： {score}')
                a.itemconfig(High_score, text=f'最高分数： {high_score}') 
        remove_enemy.clear()                           

    root.update() # 刷新窗口
    time.sleep(0.008) # 每帧延迟 8 毫秒，控制游戏帧率