import rotaryio
import board
import traceback
import json
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text import label
from adafruit_display_shapes.arc import Arc
from adafruit_display_shapes.line import Line
import shared_resources
from audio_driver import stop_audio, start_audio


#default scene and patch
patches = []
active_scene = "p0"
current_patch = "p0"
last_scene = "p0"

#initialise encoders
top_left = rotaryio.IncrementalEncoder(board.D33, board.D34)
top_right = rotaryio.IncrementalEncoder(board.D35, board.D36)
bottom_left = rotaryio.IncrementalEncoder(board.D37, board.D38)
bottom_right = rotaryio.IncrementalEncoder(board.D39, board.D40)

#load fonts
helvb12 = bitmap_font.load_font("/helvB12.bdf")
helvb14 = bitmap_font.load_font("/helvB14.bdf")
helvb24 = bitmap_font.load_font("/helvB24.bdf")
helvr08 = bitmap_font.load_font("/helvR08.bdf")

def dir_from_start(start_deg, sweep_deg): #calculation for direction for arcs
    return int((start_deg - (sweep_deg / 2.0)) % 360)

#initialise all display elements
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



#all in order of topright, bottomleft, bottomright
encoder_names = [top_right, bottom_left, bottom_right]
encoder_lastpos = [0,0,0]

top_left_lastpos = top_left.position
for i in range(3): #fill encoder lastpos 
    encoder_lastpos[i] = encoder_names[i].position

#functions to draw graph visualisations for waveforms 
def draw_sine():
    shared_resources.layer3.append(Arc(x=54, y=108, radius=32,angle=180, direction=90, segments=40, outline=0xFF0000, arc_width=1.3, fill=0xFF0000))
    shared_resources.layer3.append(Arc(x=116, y=108, radius=32, angle=180, direction=270, segments=40, outline=0xFF0000, arc_width=1.3, fill=0xFF0000))
    shared_resources.layer3.append(Line(10,108,146,108, color=0xffffff)) #x axis
    shared_resources.layer3.append(Line(22,45,22,170, color=0xffffff)) #y axis
    
def draw_saw():
    shared_resources.layer3.append(Line(22,108,44,50, color=0xff0000))
    shared_resources.layer3.append(Line(44,50,44,170, color=0xff0000))
    shared_resources.layer3.append(Line(44,170,86,50, color=0xff0000))
    shared_resources.layer3.append(Line(86,50,86,170, color=0xff0000))
    shared_resources.layer3.append(Line(86,170,128,50, color=0xff0000))
    shared_resources.layer3.append(Line(128,50,128,170, color=0xff0000))
    shared_resources.layer3.append(Line(128,170,148,108, color=0xff0000))
    shared_resources.layer3.append(Line(10,108,146,108, color=0xffffff)) #x axis
    shared_resources.layer3.append(Line(22,45,22,170, color=0xffffff)) #y axis
    
def draw_triangle():
    shared_resources.layer3.append(Line(22,108,38,65, color=0xff0000))
    shared_resources.layer3.append(Line(38,65,70,152, color=0xff0000))
    shared_resources.layer3.append(Line(70,152,102,65, color=0xff0000))
    shared_resources.layer3.append(Line(102,65,134,152, color=0xff0000))
    shared_resources.layer3.append(Line(134,152,148,108, color=0xff0000))
    shared_resources.layer3.append(Line(134,152,148,108, color=0xff0000))
    shared_resources.layer3.append(Line(10,108,146,108, color=0xffffff)) #x axis
    shared_resources.layer3.append(Line(22,45,22,170, color=0xffffff)) #y axis
    
def draw_square():
    shared_resources.layer3.append(Line(22,58,53,58, color=0xff0000))
    shared_resources.layer3.append(Line(53,58,53,158, color=0xff0000))
    shared_resources.layer3.append(Line(53,158,84,158, color=0xff0000))
    shared_resources.layer3.append(Line(84,158,84,58, color=0xff0000))
    shared_resources.layer3.append(Line(84,58,115,58, color=0xff0000))
    shared_resources.layer3.append(Line(115,58,115,158, color=0xff0000))
    shared_resources.layer3.append(Line(115,158,146,158, color=0xff0000))
    shared_resources.layer3.append(Line(146,158,146,108, color=0xff0000))
    shared_resources.layer3.append(Line(10,108,146,108, color=0xffffff)) #x axis
    shared_resources.layer3.append(Line(22,45,22,170, color=0xffffff)) #y axis
    

def draw_env(a,d,s,r): #dynamically draw envelope visualisation based on parameters. 
    attack_px = int((max(0, min(1, a/2000)))**0.4 * 40)
    decay_px = int((max(0, min(1, d/5000)))**0.5 * 42)
    sustain_level = int(100*(1-s))
    release_px = int((max(0, min(1, r/5000)))**0.5 * 42)

    shared_resources.layer3.append(Line(22,160,22 + attack_px,60, color=0xff0000))
    shared_resources.layer3.append(Line(22+attack_px, 60, 22+attack_px+decay_px, 60 + sustain_level, color=0xffff00))
    shared_resources.layer3.append(Line(22+attack_px+decay_px, 60 + sustain_level, 22+attack_px+decay_px+release_px, 160, color=0xff0000))
    
    shared_resources.layer3.append(Line(10,108,146,108, color=0xffffff)) #x axis
    shared_resources.layer3.append(Line(22,45,22,170, color=0xffffff)) #y axis
    
def draw_filter(cutoff, resonance): #dynamically draw filter visualiation based on parameters
    cutoff_px = int((max(0, min(1, cutoff/20000)))**0.4 * 90)
    resonance_px = int((max(0, min(1, resonance/4.5)))**0.5 * 30)

    shared_resources.layer3.append(Line(22,90,22+cutoff_px,90, color=0xff0000))
    shared_resources.layer3.append(Line(22+cutoff_px,90,37+cutoff_px,90-resonance_px, color=0xff0000))
    shared_resources.layer3.append(Line(37+cutoff_px,90-resonance_px, 57+cutoff_px, 160, color=0xff0000))
    
    shared_resources.layer3.append(Line(10,108,146,108, color=0xffffff)) #x axis
    shared_resources.layer3.append(Line(22,45,22,170, color=0xffffff)) #y axis
    
def clear_layer3():
    shared_resources.layer3
    while len(shared_resources.layer3):
        shared_resources.layer3.pop()

#global parameters dictionary
parameters = {
    "osc1_wave": "saw",
    "osc1_level" : 1.0,
    "osc1_unison" : 7,
    "osc1_detune" : 24.0,
    
    "osc2_wave": "triangle",
    "osc2_level" : 1.0,
    "osc2_unison" : 7,
    "osc2_detune" : 24.0,
    
    "env1_attack" : 2000,
    "env1_decay" : 5000,
    "env1_sustain" : 1.0,
    "env1_release" : 5000,
    
    "env2_attack" : 2000,
    "env2_decay" : 5000,
    "env2_sustain" :1.0,
    "env2_release" : 5000,
    
    "filter_cutoff" : 2000,
    "filter_resonance" : 1,
    
    "dirty" : False
    }

#global metadata dictionary 
parameter_metadata = {
    "osc1_wave": 	{"type": "string", "choices": ["sine", "triangle", "saw", "square"]},
    "osc1_level":    {"type": "float", "min": 0.0, "max": 1.0,   "step": 0.05},
    "osc1_unison":   {"type": "int",   "min": 1,   "max": 7,     "step": 2}, #min 1 to prevent divison by zero in unison clipping calcs
    "osc1_detune":   {"type": "float", "min": 0.0, "max": 24,  "step": 0.4},

    "osc2_wave": {"type": "string", "choices": ["sine", "triangle", "saw", "square"]},
    "osc2_level":    {"type": "float", "min": 0.0, "max": 1.0,   "step": 0.05},
    "osc2_unison":   {"type": "int",   "min": 1,   "max": 7,     "step": 2},
    "osc2_detune":   {"type": "float", "min": 0.0, "max": 24,  "step": 0.4},

    "env1_attack":   {"type": "int",   "min": 1,   "max": 2000,  "step": 25},
    "env1_decay":    {"type": "int",   "min": 1,   "max": 5000,  "step": 100}, #here is where i had to edit the step size 
    "env1_sustain":  {"type": "float", "min": 0.0, "max": 1.0,   "step": 0.05},
    "env1_release":  {"type": "int",   "min": 1,   "max": 5000,  "step": 100},

    "env2_attack":   {"type": "int",   "min": 1,   "max": 2000,  "step": 25}, #minimum 1 to prevent division by zero in envelope calcs
    "env2_decay":    {"type": "int",   "min": 1,   "max": 5000,  "step": 100}, #same edit here
    "env2_sustain":  {"type": "float", "min": 0.0, "max": 1.0,   "step": 0.05},
    "env2_release":  {"type": "int",   "min": 1,   "max": 5000,  "step": 100},

    "filter_cutoff":        {"type": "float", "min": 200, "max": 20000.0, "step": 200}, #edited step size here as well 
    "filter_resonance":     {"type": "float", "min": 0.5,  "max": 5,    "step": 0.4}
}

#scenes reference dictionary for init. 
scenes = {
    "Synth1_Settings" :
                {"edges" : ["octaveUp"],
                "nodes" : ["Synth1_Envelope"],
                "encoders" : ["osc1_wave", "osc1_level", "osc1_unison", "osc1_detune"]},
    
    "Synth1_Envelope" : {
                    "edges" : ["octaveUp"],
                    "nodes" : ["Synth2_Settings"],
                    "encoders" : ["env1_attack", "env1_decay", "env1_sustain", "env1_release"]},
    
    "Synth2_Settings" : {
                "edges" : ["octaveUp"],
                "nodes" : ["Synth2_Envelope"],
                "encoders" : ["osc2_wave", "osc2_level", "osc2_unison", "osc2_detune"]},
    
    "Synth2_Envelope" : {
                    "edges" : ["octaveUp"],
                    "nodes": ["_Filter"],
                    "encoders" : ["env2_attack", "env2_decay", "env2_sustain", "env2_release"]},
    
    "_Filter" : {
                    "edges" : ["octaveUp"],
                   "nodes" : ["Synth1_Settings"],
                   "encoders" : ["filter_cutoff", "filter_resonance"]
                   }
    
}
   
class Scene(): #parent class for all scenes for expandability - no use right now 
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

        
        
    def handle_encoders(self): #handle encoders
        global top_left_lastpos
        encoder_changes = [0,0,0]
        encoder_new_values = [0,0,0]
        text_objects = ["pot2_text1", "pot3_text1", "pot4_text1"]
        arc_objects = [top_right_arc, bottom_left_arc, bottom_right_arc] 
        
        #first, top left encoder needs to be handled seperately because it has wave parameter which is a string. 
        if top_left_lastpos != top_left.position:
            top_left_change = top_left.position - top_left_lastpos
            top_left_lastpos = top_left.position
            
            #handle wave parameter
            if self.encoders[0] == "osc1_wave" or self.encoders[0] == "osc2_wave": 
                current_wave = parameters[self.encoders[0]]
                current_osc = self.encoders[0]
                #update parameter
                parameters[self.encoders[0]] = parameter_metadata[current_osc]["choices"][(parameter_metadata[current_osc]["choices"].index(current_wave) + top_left_change) % 4]
                pot1_text1.text = parameters[self.encoders[0]] #update text
                
                
                if self.encoders[0] == "osc1_wave": #update visuals 
                    clear_layer3()
                    globals()["draw_" + parameters["osc1_wave"]]()
                    wave_numerator = parameter_metadata["osc1_wave"]["choices"].index(parameters["osc1_wave"])
                    top_left_arc.angle = int((wave_numerator/4)*360) #update arc 
                
                elif self.encoders[0] == "osc2_wave": #update visuals
                    clear_layer3()
                    globals()["draw_" + parameters["osc2_wave"]]()
                    wave_numerator = parameter_metadata["osc2_wave"]["choices"].index(parameters["osc2_wave"])
                    top_left_arc.angle = int((wave_numerator/4)*360) #update arc
                
                #update arc
                top_left_arc.direction = dir_from_start(270, top_left_arc.angle)
                
                            
            else: #handle top left encoder for all other parameters. 
                tl_new_value = parameters[self.encoders[0]] + top_left_change*parameter_metadata[self.encoders[0]]["step"] #calculate new value 
                if tl_new_value <= parameter_metadata[self.encoders[0]]["max"] and tl_new_value >= parameter_metadata[self.encoders[0]]["min"]: #bounds checking
                    if type(parameters[self.encoders[0]]) != "<class 'int'>":
                        parameters[self.encoders[0]] = round(tl_new_value, 2) #round to 2 dp if float or double to prevent floating point error
                    else:
                        parameters[self.encoders[0]] = tl_new_value #if int then no need for rounding. 
                    pot1_text1.text = str(parameters[self.encoders[0]]) #update text
                    #update encoder visuals
                    top_left_arc.angle = (parameters[self.encoders[0]] - parameter_metadata[self.encoders[0]]["min"])/(parameter_metadata[self.encoders[0]]["max"] - parameter_metadata[self.encoders[0]]["min"])*360 #update ui arc
                    top_left_arc.direction = dir_from_start(270, top_left_arc.angle)
                    
                    clear_layer3() #update graph visuals 
                    if self.encoders[0] == "env1_attack":
                        draw_env(parameters["env1_attack"], parameters["env1_decay"], parameters["env1_sustain"], parameters["env1_release"])
                    elif self.encoders[0] == "env2_attack":
                        draw_env(parameters["env2_attack"], parameters["env2_decay"], parameters["env2_sustain"], parameters["env2_release"])
                    elif self.encoders[0] == "filter_cutoff":
                        draw_filter(parameters["filter_cutoff"], parameters["filter_resonance"])
                        
            parameters["dirty"] = True #set parameters dirty to true! Tells main loop to reupdate C parameters
                    
            
        for i in range(1, min(len(self.encoders), len(self.encoders))): #for all other encoders
            try:
                if encoder_lastpos[i-1] != encoder_names[i-1].position:
                    encoder_changes[i-1] = encoder_names[i-1].position - encoder_lastpos[i-1]
                    encoder_new_values[i-1] = parameters[self.encoders[i]] + encoder_changes[i-1]*parameter_metadata[self.encoders[i]]["step"]
                    
                    if encoder_new_values[i-1] <= parameter_metadata[self.encoders[i]]["max"] and encoder_new_values[i-1] >= parameter_metadata[self.encoders[i]]["min"]:
                        if type(parameters[self.encoders[i]]) != "<class 'int'>":
                            parameters[self.encoders[i]] = round(encoder_new_values[i-1], 3)
                        else:
                            parameters[self.encoders[i]] = encoder_new_values[i-1]
                        globals()[text_objects[i-1]].text = str(parameters[self.encoders[i]])
                        arc_objects[i-1].angle = (parameters[self.encoders[i]] - parameter_metadata[self.encoders[i]]["min"])/(parameter_metadata[self.encoders[i]]["max"] - parameter_metadata[self.encoders[i]]["min"])*360
                        arc_objects[i-1].direction = dir_from_start(270, arc_objects[i-1].angle)
                        
                        if self.encoders[0] == "env1_attack":
                            clear_layer3()
                            draw_env(parameters["env1_attack"], parameters["env1_decay"], parameters["env1_sustain"], parameters["env1_release"])
                        elif self.encoders[0] == "env2_attack":
                            clear_layer3()
                            draw_env(parameters["env2_attack"], parameters["env2_decay"], parameters["env2_sustain"], parameters["env2_release"])
                        elif self.encoders[0] == "filter_cutoff":
                            clear_layer3()
                            draw_filter(parameters["filter_cutoff"], parameters["filter_resonance"])
                    
                    parameters["dirty"] = True
                encoder_lastpos[i-1] = encoder_names[i-1].position
            
            except Exception as e: #exception in case of index error
                print("Exception occurred:")
                print("Python: Stopping Audio")
                stop_audio()
                traceback.print_exception(e)
                break
                
                
class patch(Scene): # child class for patch scenes
    def __init__(self, patch_name, patch_data): #initialise all needed info 
        Scene.__init__(self)
        self.patch_name = patch_name
        self.patch_data = patch_data
        self.edges = []
        self.nodes = []
        self.encoders = []
        self.edges.append("octaveUp")
        self.nodes.append("Synth1_Settings")
        patches.append(patch_name)
        self.patch_index = patches.index(patch_name)
        if self.patch_index != 0: #if it isnt the first patch
            self.edges.append("ccw") # add edge to this node pointing to previous node
            self.nodes.append("p" + str(self.patch_index - 1))
            globals()[patches[self.patch_index - 1]].edges.append("cw") #add edge to last node, pointing to this node 
            globals()[patches[self.patch_index - 1]].nodes.append("p" + str(self.patch_index))

            
            
def update_settings_display(): #IF GOING TO A SETTINGS SCENE
    encoders = scenes[active_scene]["encoders"]
    
    #If coming FROM a patch scene, remove patch UI elements
    if last_scene[0] == "p":
        shared_resources.layer2.remove(patch_text)
        shared_resources.layer2.remove(left)
        shared_resources.layer2.remove(right)
        shared_resources.layer2.remove(left_text)
        shared_resources.layer2.remove(right_text)
        
        #Add settings ui elements
        shared_resources.layer1.append(top_left_bg)
        shared_resources.layer1.append(top_right_bg)
        shared_resources.layer1.append(bottom_left_bg)
        shared_resources.layer1.append(bottom_right_bg)
        shared_resources.layer2.append(top_left_arc)
        shared_resources.layer2.append(top_right_arc)
        shared_resources.layer2.append(bottom_left_arc)
        shared_resources.layer2.append(bottom_right_arc)
        shared_resources.layer2.append(pot1_text1)
        shared_resources.layer2.append(pot1_text2)
        shared_resources.layer2.append(pot2_text1)
        shared_resources.layer2.append(pot2_text2)
        shared_resources.layer2.append(pot3_text1)
        shared_resources.layer2.append(pot3_text2)
        shared_resources.layer2.append(pot4_text1)
        shared_resources.layer2.append(pot4_text2)
    
    #always update title 
    title1_text.text = active_scene.split("_")[0]
    title2_text.text = active_scene.split("_")[1]
    
    #always update encoder arcs
    if active_scene == "Synth1_Settings":
        wave_numerator = parameter_metadata["osc1_wave"]["choices"].index(parameters["osc1_wave"])
        top_left_arc.angle = int((wave_numerator/4)*360)
        
    elif active_scene == "Synth2_Settings":
        wave_numerator = parameter_metadata["osc2_wave"]["choices"].index(parameters["osc2_wave"])
        top_left_arc.angle = int((wave_numerator/4)*360)
    else:
        top_left_arc.angle = (parameters[encoders[0]] - parameter_metadata[encoders[0]]["min"])/(parameter_metadata[encoders[0]]["max"] - parameter_metadata[encoders[0]]["min"])*360
        
    top_left_arc.direction = dir_from_start(270, top_left_arc.angle)
    pot1_text1.text = str(parameters[encoders[0]])
    pot1_text2.text = str(encoders[0].split("_")[1]).upper()
    
    top_right_arc.angle = (parameters[encoders[1]] - parameter_metadata[encoders[1]]["min"])/(parameter_metadata[encoders[1]]["max"] - parameter_metadata[encoders[1]]["min"])*360
    top_right_arc.direction = dir_from_start(270, top_right_arc.angle)
    pot2_text1.text = str(parameters[encoders[1]])
    pot2_text2.text = str(encoders[1].split("_")[1]).upper()
    
    if len(encoders) > 2: #avoid index error - filter only has 2 encoders.
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
    
    #always draw graphs
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


def update_patch_display(): #IF GOING TO A PATCH SCENE
    global last_scene
    if last_scene[0] == "p": #if coming from a patch scene, just update the patch number. 
        patch_text.text = current_patch.upper()
    
    else:
        #if coming from a settings scene, remove all settings ui elements
        shared_resources.layer1.remove(top_left_bg)
        shared_resources.layer1.remove(top_right_bg)
        shared_resources.layer1.remove(bottom_left_bg)
        shared_resources.layer1.remove(bottom_right_bg)
        shared_resources.layer2.remove(top_left_arc)
        shared_resources.layer2.remove(top_right_arc)
        shared_resources.layer2.remove(bottom_left_arc)
        shared_resources.layer2.remove(bottom_right_arc)
        shared_resources.layer2.remove(pot1_text1)
        shared_resources.layer2.remove(pot1_text2)
        shared_resources.layer2.remove(pot2_text1)
        shared_resources.layer2.remove(pot2_text2)
        shared_resources.layer2.remove(pot3_text1)
        shared_resources.layer2.remove(pot3_text2)
        shared_resources.layer2.remove(pot4_text1)
        shared_resources.layer2.remove(pot4_text2)
        title2_text.text = ""
        clear_layer3()
        
        #if coming from a settings scene, add all patch scene ui elements
        title1_text.text = "Patch Menu"
        patch_text.text = active_scene.upper()
        left.text = "<"
        right.text = ">"
        left_text.text = "(Knob 5 \n left)"
        right_text.text = "(Knob 5 \n right)"
        shared_resources.layer2.append(patch_text)
        shared_resources.layer2.append(left)
        shared_resources.layer2.append(right)
        shared_resources.layer2.append(left_text)
        shared_resources.layer2.append(right_text)
        
        
        
        
def reset_encoder_positions(): #reset encoder positions so any delta from a previous scene in carried over 
    global top_left_lastpos
    top_left_lastpos = top_left.position

    for i in range(len(encoder_lastpos)):
        encoder_lastpos[i] = encoder_names[i].position        
            
        
def scene_change(action): #scene changed, called by check buttons in main loop. #action is which button was pressed 
    global active_scene, last_scene
    local_active_scene = globals()[active_scene] #so local active scene is the last active scene 
    for i in range(len(local_active_scene.edges)): #look for matching node 
        if local_active_scene.edges[i] == action:
            last_scene = active_scene #set last scene to this scene 
            active_scene = local_active_scene.nodes[i] #set active scene to next scene
            reset_encoder_positions()
            update_settings_display() #update display 
            return
        
    if action == "octaveDown" and active_scene[0] != "p": #if octave down pressed from anywhere, go back to patch menu. 
        last_scene = active_scene
        active_scene = current_patch
        reset_encoder_positions()
        update_patch_display()
        
    

def patch_change(action):
    global active_scene, last_scene
    global current_patch
    local_active_scene = globals()[active_scene]
    if active_scene[0] == "p": #if active scene is a patch (so making sure we are in patch menu)
        for i in range(len(local_active_scene.edges)): #look for matching node
            if local_active_scene.edges[i] == action: #if matching node, set new last scene and active scene
                last_scene = active_scene
                active_scene = local_active_scene.nodes[i]
                current_patch = active_scene #update current patch
                reset_encoder_positions()
                update_patch_display() #update display 
                
                
        #update parameters
        for key, value in globals()[current_patch].patch_data.items():
            if key in parameters: #only if patch has an entry for the parameter
                parameters[key] = value
            parameters["dirty"] = True #so C updates its local parameters

    
def save_patch(): 
    stop_audio() #First stop audio, this is about a second or 2, we don't want a dma request to interrupt the saving
    print("saving patch")
    new_patch_index = len(patches)
    new_patch_name = "p" + str(new_patch_index)
    patch_data_copy = parameters.copy() #copy current parameters
    globals()[new_patch_name] = patch(new_patch_name, patch_data_copy) #add new patch to patches
    all_patches = {}
    
    for p in patches: #iterate through patches, append each patch data to all_patches
        patch_obj = globals()[p]       
        all_patches[p] = patch_obj.patch_data

    with open("/patches.json", "w", encoding="utf-8") as file:
        json.dump(all_patches, file) #create and dump new json file 
    
    print("patch_saved")
    start_audio() #restart audio
    
    
    
def handle_scenes(): #called in main loop
    scene_obj = globals()[active_scene]
    if getattr(scene_obj, "encoders", []): #only handle encoders on settings. this condition checks whether the scene has an encoders attribute. 
        scene_obj.handle_encoders()
        
        

def init_uihandler(): #initialisations
    try: #handle missing or invalid json file 
        with open("/patches.json", "r", encoding="utf-8") as file:
            json_data = json.load(file)
    except OSError:
        print("patches.json not found, using defaults")
        json_data = {"p0": parameters.copy()}
    except ValueError:
        print("patches.json invalid format, using defaults")
        json_data = {"p0": parameters.copy()}

    #go through json or defaults and build patches list. 
    for patch_name in sorted(json_data.keys(), key=lambda x: int(x[1:])): #makes sure the patches are loaded in order. I had an issue where they would be loaded randomly 
        patch_data = json_data[patch_name]
        globals()[patch_name] = patch(patch_name, patch_data)
        print(f"patch {patch_name} created")
    

    for obj, value in scenes.items(): # creates settings objects from reference dictionary
        globals()[obj] = settings(value["edges"], value["nodes"], value["encoders"])
    

    for key, value in p0.patch_data.items(): #siterate through patch data, set parameters to p0 data, only if the current parameter exists in the patch 
        if key in parameters:     
            parameters[key] = value
            
    
    #display element initialisations
    title1_text.text = "Patch Menu"
    patch_text.text = active_scene.upper()
    left.text = "<"
    right.text = ">"
    left_text.text = "(Knob 5 \n left)"
    right_text.text = "(Knob 5 \n right)"
    shared_resources.layer2.append(patch_text)
    shared_resources.layer2.append(left)
    shared_resources.layer2.append(right)
    shared_resources.layer2.append(left_text)
    shared_resources.layer2.append(right_text)
    shared_resources.layer2.append(title1_text)
    shared_resources.layer2.append(title2_text)
            
