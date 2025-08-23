import rotaryio
import board
import json
import displayio, busio
from adafruit_bitmap_font import bitmap_font
import adafruit_ili9341
from adafruit_display_text import label
try:
    from fourwire import FourWire
except ImportError:
    from displayio import FourWire
from adafruit_display_shapes.arc import Arc
from adafruit_display_shapes.line import Line


patches = []
#control_pot = rotaryio.IncrementalEncoder(board.D10, board.D9)
active_scene = "p0"
current_patch = "p0"
last_scene = "p0"

top_left = rotaryio.IncrementalEncoder(board.D10, board.D9)
top_right = rotaryio.IncrementalEncoder(board.D10, board.D9)
bottom_left = rotaryio.IncrementalEncoder(board.D10, board.D9)
bottom_right = rotaryio.IncrementalEncoder(board.D10, board.D9)

#display init
displayio.release_displays()
spi = busio.SPI(clock=board.D13, MISO=board.D12, MOSI=board.D11)
cs = board.D10
dc = board.D9
reset = board.D8

display_bus = FourWire(spi, command=dc, chip_select=cs, reset=reset)
display = adafruit_ili9341.ILI9341(display_bus, width=320, height=240)

splash = displayio.Group()
display.root_group = splash

layer0 = displayio.Group()  # background colour
layer1 = displayio.Group()  # arc backgrounds
layer2 = displayio.Group()
layer3 = displayio.Group()

splash.append(layer0)  # index 0
splash.append(layer1)  # index 1
splash.append(layer2)
splash.append(layer3)

bg = displayio.TileGrid(
    displayio.Bitmap(display.width, display.height, 1),
    pixel_shader=displayio.Palette(1)
)
bg.pixel_shader[0] = 0x09082B
layer0.append(bg)

helvb12 = bitmap_font.load_font("/helvb12.bdf")
helvb14 = bitmap_font.load_font("/helvb14.bdf")
helvb24 = bitmap_font.load_font("/helvb24.bdf")
helvr08 = bitmap_font.load_font("/helvr08.bdf")

def dir_from_start(start_deg, sweep_deg):
    return int((start_deg - (sweep_deg / 2.0)) % 360)

def draw_sine():
    global layer3
    layer3.append(Arc(x=54, y=108, radius=32,angle=180, direction=90, segments=40, outline=0xFF0000, arc_width=1.3, fill=0xFF0000))
    layer3.append(Arc(x=116, y=108, radius=32, angle=180, direction=270, segments=40, outline=0xFF0000, arc_width=1.3, fill=0xFF0000))
    layer3.append(Line(10,108,146,108, color=0xffffff)) #x axis
    layer3.append(Line(22,45,22,170, color=0xffffff)) #y axis
    
def draw_saw():
    global layer3
    layer3.append(Line(22,108,44,50, color=0xff0000))
    layer3.append(Line(44,50,44,170, color=0xff0000))
    layer3.append(Line(44,170,86,50, color=0xff0000))
    layer3.append(Line(86,50,86,170, color=0xff0000))
    layer3.append(Line(86,170,128,50, color=0xff0000))
    layer3.append(Line(128,50,128,170, color=0xff0000))
    layer3.append(Line(128,170,148,108, color=0xff0000))
    layer3.append(Line(10,108,146,108, color=0xffffff)) #x axis
    layer3.append(Line(22,45,22,170, color=0xffffff)) #y axis
    
def draw_triangle():
    global layer3
    layer3.append(Line(22,108,38,65, color=0xff0000))
    layer3.append(Line(38,65,70,152, color=0xff0000))
    layer3.append(Line(70,152,102,65, color=0xff0000))
    layer3.append(Line(102,65,134,152, color=0xff0000))
    layer3.append(Line(134,152,148,108, color=0xff0000))
    layer3.append(Line(134,152,148,108, color=0xff0000))
    layer3.append(Line(10,108,146,108, color=0xffffff)) #x axis
    layer3.append(Line(22,45,22,170, color=0xffffff)) #y axis
    
def draw_square():
    global layer3
    layer3.append(Line(22,58,53,58, color=0xff0000))
    layer3.append(Line(53,58,53,158, color=0xff0000))
    layer3.append(Line(53,158,84,158, color=0xff0000))
    layer3.append(Line(84,158,84,58, color=0xff0000))
    layer3.append(Line(84,58,115,58, color=0xff0000))
    layer3.append(Line(115,58,115,158, color=0xff0000))
    layer3.append(Line(115,158,146,158, color=0xff0000))
    layer3.append(Line(146,158,146,108, color=0xff0000))
    layer3.append(Line(10,108,146,108, color=0xffffff)) #x axis
    layer3.append(Line(22,45,22,170, color=0xffffff)) #y axis
    
def draw_env(a,d,s,r):
    global layer3
    attack_px = int((max(0, min(1, a/2000)))**0.4 * 40)
    decay_px = int((max(0, min(1, d/5000)))**0.5 * 42)
    sustain_level = int(100*(1-s))
    release_px = int((max(0, min(1, r/5000)))**0.5 * 42)

    layer3.append(Line(22,160,22 + attack_px,60, color=0xff0000))
    layer3.append(Line(22+attack_px, 60, 22+attack_px+decay_px, 60 + sustain_level, color=0xffff00))
    layer3.append(Line(22+attack_px+decay_px, 60 + sustain_level, 22+attack_px+decay_px+release_px, 160, color=0xff0000))
    
def draw_filter(cutoff, resonance):
    global layer3
    cutoff_px = int((max(0, min(1, cutoff/20000)))**0.4 * 90)
    resonance_px = int((max(0, min(1, resonance/4.5)))**0.5 * 30)

    layer3.append(Line(22,90,22+cutoff_px,90, color=0xff0000))
    layer3.append(Line(22+cutoff_px,90,37+cutoff_px,90-resonance_px, color=0xff0000))
    layer3.append(Line(37+cutoff_px,90-resonance_px, 57+cutoff_px, 160, color=0xff0000))
    
def clear_layer3():
    global layer3
    layer3 = displayio.Group()
    splash[3] = layer3
    
    
    

top_left_arc = Arc(x=200, y=40, radius=25, angle=120, direction=dir_from_start(270, 120), segments=50, outline=0xff0000, arc_width=2, fill=0xff0000)
top_right_arc = Arc(x=280, y=40, radius=25, angle=320, direction=dir_from_start(270, 320), segments=50, outline=0xff0000, arc_width=2, fill=0xff0000)
bottom_left_arc = Arc(x=200, y=115, radius=25, angle=260, direction=dir_from_start(270, 260), segments=50, outline=0xff0000, arc_width=2, fill=0xff0000)
bottom_right_arc = Arc(x=280, y=115, radius=25, angle=42, direction=dir_from_start(270, 42), segments=50, outline=0xff0000, arc_width=2, fill=0xff0000)
top_left_bg = Arc(x=200, y=40, radius=25, angle=360, direction=180, segments=100, outline=0x454545, arc_width=1.5, fill=0x575756)
top_right_bg = Arc(x=280, y=40, radius=25, angle=360, direction=180, segments=100, outline=0x454545, arc_width=1.5, fill=0x575756)
bottom_left_bg = Arc(x=200, y=115, radius=25, angle=360, direction=180, segments=100, outline=0x454545, arc_width=1.5, fill=0x575756)
bottom_right_bg = Arc(x=280, y=115, radius=25, angle=360, direction=180, segments=100, outline=0x454545, arc_width=1.5, fill=0x575756)
title1_text = label.Label(font = helvb12, text="", color=0xFFFFFF, anchored_position=(17,25), anchor_point=(0.0,1.0), scale=1)
title2_text = label.Label(font = helvb14, text="", color=0xFF0000, anchored_position=(95,26), anchor_point=(0.0,1.0), scale=1)
pot1_text1 = label.Label(font = helvr08, text="", color=0x575756, anchored_position=(202,40), anchor_point=(0.5,0.5), scale=1)
pot1_text2 = label.Label(font = helvr08, text="", color=0xffffff, anchored_position=(202,77), anchor_point=(0.5,0.5), scale=1)
pot2_text1 = label.Label(font = helvr08, text="", color=0x575756, anchored_position=(282,40), anchor_point=(0.5,0.5), scale=1)
pot2_text2 = label.Label(font = helvr08, text="", color=0xffffff, anchored_position=(282,77), anchor_point=(0.5,0.5), scale=1)
pot3_text1 = label.Label(font = helvr08, text="", color=0x575756, anchored_position=(202,115), anchor_point=(0.5,0.5), scale=1)
pot3_text2 = label.Label(font = helvr08, text="", color=0xffffff, anchored_position=(202,155), anchor_point=(0.5,0.5), scale=1)
pot4_text1 = label.Label(font = helvr08, text="", color=0x575756, anchored_position=(282,115), anchor_point=(0.5,0.5), scale=1)
pot4_text2 = label.Label(font = helvr08, text="", color=0xffffff, anchored_position=(282,155), anchor_point=(0.5,0.5), scale=1)
x_axis = Line(10,160,145,160, color=0xffffff)
y_axis = Line(22,45,22,170, color=0xffffff)
line1 = Line(22,160,50,50, color=0xff0000)
line2 = Line(50,50,70,100, color=0xff0000)
line3 = Line(70,100,120,100, color=0xff0000)
line4 = Line(120,100,145,160, color=0xff0000)
patch_text = label.Label(font = helvb24, text="", color=0xFFFFFF, anchored_position=(160,95), anchor_point=(0.5,0.5), scale=1)
left = label.Label(font = helvb24, text="", color=0xFFFFFF, anchored_position=(40,95), anchor_point=(0.5,0.5), scale=1)
right = label.Label(font = helvb24, text="", color=0xFFFFFF, anchored_position=(280,95), anchor_point=(0.5,0.5), scale=1)
left_text = label.Label(font = helvr08, text="", color=0x575756, anchored_position=(40,120), anchor_point=(0.5,0.5), scale=1, line_spacing=0.7)
right_text = label.Label(font = helvr08, text="", color=0x575756, anchored_position=(280,120), anchor_point=(0.5,0.5), scale=1, line_spacing=0.7)



#all in order of topright, bottomleft, bottomright - 
encoder_names = [top_right, bottom_left, bottom_right]
encoder_lastpos = [0,0,0]

top_left_lastpos = top_left.position
for i in range(3):
    encoder_lastpos[i] = encoder_names[i].position



parameters = {
    "osc1_wave": "sine",
    "osc1_level" : 0,
    "osc1_unison" : 0,
    "osc1_detune" : 0,
    
    "osc2_wave": "sine",
    "osc2_level" : 0,
    "osc2_unison" : 0,
    "osc2_detune" : 0,
    
    "env1_attack" : 0,
    "env1_decay" : 0,
    "env1_sustain" : 0,
    "env1_release" : 0,
    
    "env2_attack" : 0,
    "env2_decay" : 0,
    "env2_sustain" : 0,
    "env2_release" : 0,
    
    "filter_cutoff" : 0,
    "filter_resonance" : 0
    }


parameter_metadata = {
    "osc1_wave": {"type": "string", "choices": ["sine", "triangle", "saw", "square"]},
    "osc1_level":    {"type": "float", "min": 0.0, "max": 1.0,   "step": 0.02},
    "osc1_unison":   {"type": "int",   "min": 1,   "max": 7,     "step": 2},
    "osc1_detune":   {"type": "float", "min": 0.0, "max": 24,  "step": 0.4},

    "osc2_wave": {"type": "string", "choices": ["sine", "triangle", "saw", "square"]},
    "osc2_level":    {"type": "float", "min": 0.0, "max": 1.0,   "step": 0.02},
    "osc2_unison":   {"type": "int",   "min": 1,   "max": 7,     "step": 2},
    "osc2_detune":   {"type": "float", "min": 0.0, "max": 24,  "step": 0.4},

    "env1_attack":   {"type": "int",   "min": 0,   "max": 2000,  "step": 5},
    "env1_decay":    {"type": "int",   "min": 0,   "max": 5000,  "step": 5},
    "env1_sustain":  {"type": "float", "min": 0.0, "max": 1.0,   "step": 0.01},
    "env1_release":  {"type": "int",   "min": 0,   "max": 5000,  "step": 1},

    "env2_attack":   {"type": "int",   "min": 0,   "max": 2000,  "step": 5},
    "env2_decay":    {"type": "int",   "min": 0,   "max": 5000,  "step": 5},
    "env2_sustain":  {"type": "float", "min": 0.0, "max": 1.0,   "step": 0.02},
    "env2_release":  {"type": "int",   "min": 0,   "max": 5000,  "step": 5},

    "filter_cutoff":        {"type": "float", "min": 200, "max": 20000.0, "step": 50},
    "filter_resonance":     {"type": "float", "min": 0.5,  "max": 5,    "step": 0.1}
}

scenes = {
    "Synth1_Settings" : {"edges" : ["octaveUp"],
                "nodes" : ["Synth1_Envelope"],
                "encoders" : ["osc1_wave", "osc1_level", "osc1_unison", "osc1_detune"]},
    
    "Synth1_Envelope" : {"edges" : ["octaveUp"],
                    "nodes" : ["Synth2_Settings"],
                    "encoders" : ["env1_attack", "env1_decay", "env1_sustain", "env1_release"]},
    
    "Synth2_Settings" : {"edges" : ["octaveUp"],
                "nodes" : ["Synth2_Envelope"],
                "encoders" : ["osc2_wave", "osc2_level", "osc2_unison", "osc2_detune"]},
    
    "Synth2_Envelope" : {"edges" : ["octaveUp"],
                    "nodes": ["_Filter"],
                    "encoders" : ["env2_attack", "env2_decay", "env2_sustain", "env2_release"]},
    
    "_Filter" : {"edges" : ["octaveUp"],
                   "nodes" : ["Synth1_Settings"],
                   "encoders" : ["filter_cutoff", "filter_resonance"]
                   }
    
}
   




    
class Scene(): #parent class for all scenes
    def __init__(self):
        print("Initialised")
        
class settings(Scene): #child class for settings scenes
    def __init__(self, edges, nodes, encoders):
        Scene.__init__(self)
        self.edges = edges
        self.nodes = nodes
        self.encoders = encoders

        
        global top_left_lastpos
        top_left_lastpos = top_left.position
        for p in range(3):
            encoder_lastpos[p] = encoder_names[p].position

        
        
            
            
    def handle_encoders(self):
        global top_left_lastpos
        encoder_changes = [0,0,0]
        encoder_new_values = [0,0,0]
        text_objects = ["pot2_text1", "pot3_text1", "pot4_text1"]
        
        if top_left_lastpos != top_left.position:
            top_left_change = top_left.position - top_left_lastpos
            if self.encoders[0] == "osc1_wave" or self.encoders[0] == "osc2_wave": #for osc types
                current_wave = parameters[self.encoders[0]]
                current_osc = self.encoders[0]
                try:
                    parameters[self.encoders[0]] = parameter_metadata[current_osc]["choices"][parameter_metadata[current_osc]["choices"].index(current_wave) + top_left_change]
                    pot1_text1.text = parameters[self.encoders[0]]
                    if self.encoders[0] == "osc1_wave":
                        globals()["draw_" + parameters["osc1_wave"]]()
                    elif self.encoders[0] == "osc2_wave":
                        globals()["draw_" + parameters["osc2_wave"]]()
                    
                except:
                    pass                
            else:
                tl_new_value = parameters[self.encoders[0]] + top_left_change*parameter_metadata[self.encoders[0]]["step"]
                if tl_new_value <= parameter_metadata[self.encoders[0]]["max"] and tl_new_value >= parameter_metadata[self.encoders[0]]["min"]:
                    parameters[self.encoders[0]] = tl_new_value
                    pot1_text1.text = str(parameters[self.encoders[0]])
                    if self.encoders[0] == "env1_attack":
                        draw_env(parameters["env1_attack"], parameters["env1_decay"], parameters["env1_sustain"], parameters["env1_release"])
                    elif encoders[0] == "env2_attack":
                        self.draw_env(parameters["env2_attack"], parameters["env2_decay"], parameters["env2_sustain"], parameters["env2_release"])
                    elif encoders[0] == "filter_cutoff":
                        self.draw_filter(parameters["filter_cutoff"], parameters["filter_resonance"])
                    
            
            top_left_lastpos = top_left.position
            
        for i in range(len(self.encoders)): #for all other parameters
            try:
                if encoder_lastpos[i] != encoder_names[i].position:
                    encoder_changes[i] = encoder_names[i].position - encoder_lastpos[i]
                    encoder_new_values[i] = parameters[self.encoders[i+1]] + encoder_changes[i]*parameter_metadata[self.encoders[i+1]]["step"]
                    if encoder_new_values[i] <= parameter_metadata[self.encoders[i+1]]["max"] and encoder_new_values[i] >= parameter_metadata[self.encoders[i+1]]["min"]:
                        parameters[self.encoders[i+1]] = encoder_new_values[i]
                        globals()[text_objects[i]].text = str(parameters[self.encoders[i+1]])
                        if self.encoders[0] == "env1_attack":
                            draw_env(parameters["env1_attack"], parameters["env1_decay"], parameters["env1_sustain"], parameters["env1_release"])
                        elif encoders[0] == "env2_attack":
                            self.draw_env(parameters["env2_attack"], parameters["env2_decay"], parameters["env2_sustain"], parameters["env2_release"])
                        elif encoders[0] == "filter_cutoff":
                            self.draw_filter(parameters["filter_cutoff"], parameters["filter_resonance"])
            
                encoder_lastpos[i] = encoder_names[i].position
            
            except:
                break
        
                
                
            
                
    
class patch(Scene): # child class for patch scenes
    def __init__(self, patch_name, patch_data):
        Scene.__init__(self)
        self.patch_name = patch_name
        self.patch_data = patch_data
        self.edges = []
        self.nodes = []
        self.encoders = []
        self.edges.append("octaveUp")
        self.nodes.append("Synth1_Envelope")
        patches.append(patch_name)
        self.patch_index = patches.index(patch_name)
        if self.patch_index != 0:
            self.edges.append("ccw")
            self.nodes.append("p" + str(self.patch_index - 1))
            globals()[patches[self.patch_index - 1]].edges.append("cw")
            globals()[patches[self.patch_index - 1]].nodes.append("p" + str(self.patch_index))

            
            
def update_settings_display():
    encoders = scenes[active_scene]["encoders"]
    if last_scene[0] != "p":
        title2_text.text = active_scene.split("_")[1]
        
        top_left_arc.angle = (parameters[encoders[0]] - parameter_metadata[encoders[0]]["min"])/(parameter_metadata[encoders[0]]["max"] - parameter_metadata[encoders[0]]["min"])*360
        top_left_arc.direction = dir_from_start(270, top_left_arc.angle)
        pot1_text1.text = str(parameters[encoders[0]])
        pot1_text2.text = str(encoders[0].split("_")[1]).upper()
        
        top_right_arc.angle = (parameters[encoders[1]] - parameter_metadata[encoders[1]]["min"])/(parameter_metadata[encoders[1]]["max"] - parameter_metadata[encoders[1]]["min"])*360
        top_right_arc.direction = dir_from_start(270, top_right_arc.angle)
        pot2_text1.text = str(parameters[encoders[1]])
        pot2_text2.text = str(encoders[1].split("_")[1]).upper()
        
        if len(encoders) > 2:
            bottom_left_arc.angle = (parameters[encoders[2]] - parameter_metadata[encoders[2]]["min"])/(parameter_metadata[encoders[2]]["max"] - parameter_metadata[encoders[2]]["min"])*360
            bottom_left_arc.direction = dir_from_start(270, bottom_left_arc.angle)
            pot3_text1.text = str(parameters[encoders[2]])
            pot3_text2.text = str(encoders[2].split("_")[1]).upper()
            
            bottom_right_arc.angle = (parameters[encoders[3]] - parameter_metadata[encoders[3]]["min"])/(parameter_metadata[encoders[3]]["max"] - parameter_metadata[encoders[3]]["min"])*360
            bottom_right_arc.direction = dir_from_start(270, bottom_right_arc.angle)
            pot4_text1.text = str(parameters[encoders[3]])
            pot4_text2.text = str(encoders[3].split("_")[1]).upper()
        
        else:
            bottom_left_arc.angle = 0
            bottom_right_arc.angle = 0
            pot3_text1.text = ""
            pot4_text1.text = ""
            pot3_text2.text = ""
            pot4_text2.text = ""
            
        if encoders[0] == "osc1_wave":
            clear_layer3()
            globals()["draw_" + parameters["osc1_wave"]]()
        elif encoders[0] == "osc2_wave":
            clear_layer3()
            globals()["draw_" + parameters["osc2_wave"]]()
        elif encoders[0] == "env1_attack":
            clear_layer3()
            draw_env(parameters["env1_attack"], parameters["env1_decay"], parameters["env1_sustain"], parameters["env1_release"])
        elif encoders[0] == "env2_attack":
            clear_layer3()
            draw_env(parameters["env2_attack"], parameters["env2_decay"], parameters["env2_sustain"], parameters["env2_release"])
        elif encoders[0] == "filter_cutoff":
            clear_layer3()
            draw_filter(parameters["filter_cutoff"], parameters["filter_resonance"])
            
            
        
        
        
            
        
            
            
            
    else:
        #redraw everything
    
    
    
                 
        
def reset_encoder_positions():
    global top_left_lastpos
    top_left_lastpos = top_left.position

    for i in range(len(encoder_lastpos)):
        encoder_lastpos[i] = encoder_names[i].position        
            
        
def scene_change(action):
    global active_scene, last_scene
    try:
        for i in range(len(globals()[active_scene].edges)):
            if globals()[active_scene].edges[i] == action:
                last_scene = active_scene
                active_scene = globals()[active_scene].nodes[i]
                reset_encoder_positions()
                
    #draw new UI
                break
            
    
    except:
        if action == "octaveDown" and active_scene not in patches:
            last_scene = active_scene
            active_scene = current_patch
            reset_encoder_positions()
    
    
            
    #display changes
    
def patch_change(action):
    global active_scene, last_scene
    global current_patch
    if active_scene[0] == "p":
        for i in range(len(globals()[active_scene].edges)):
            if globals()[active_scene].edges[i] == action:
                last_scene = active_scene
                active_scene = globals()[active_scene].nodes[i]
                reset_encoder_positions()
                current_patch = active_scene
                
        
    for key, value in globals()[current_patch].patch_data.items():
        if key in parameters:     
            parameters[key] = value
    
    
    
def save_patch():
    new_patch_index = len(patches)
    new_patch_name = "p" + str(new_patch_index)
    patch_data_copy = parameters.copy()
    globals()[new_patch_name] = patch(new_patch_name, patch_data_copy)
    all_patches = {}
    for p in patches:
        patch_obj = globals()[p]       
        all_patches[p] = patch_obj.patch_data
    with open("/patches.json", "w", encoding="utf-8") as file:
        json.dump(all_patches, file)
    
    
    
    
    
def handle_scenes():
    scene_obj = globals()[active_scene]
    if getattr(scene_obj, "encoders", []): #only handle encoders on settings
        scene_obj.handle_encoders()
        
        
    

#initialisations

def init_uihandler():
    with open("/patches.json", "r", encoding="utf-8") as file:
        json_data = json.load(file)

    for patch_name, patch_data in json_data.items():
        globals()[patch_name] = patch(patch_name, patch_data)
    

    for obj, value in scenes.items(): # creates settings objects from dictionary
        globals()[obj] = settings(value["edges"], value["nodes"], value["encoders"])
    

    for key, value in p0.patch_data.items():
        if key in parameters:     
            parameters[key] = value
            
            
    title1_text.text = "Patch Menu"
    patch_text.text = "P1"
    left.text = "<"
    right.text = ">"
    left_text.text = "(Knob 5 \n left)"
    right_text.text = "(Knob 5 \n right)"
    layer2.append(patch_text)
    layer2.append(left)
    layer2.append(right)
    layer2.append(left_text)
    layer2.append(right_text)
    layer2.append(title1_text)
    layer2.append(title2_text)
            
            
    
            
            
    
            
            
    
    
    
    



               




    
        

    
        
        