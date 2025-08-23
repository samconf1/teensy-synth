import uihandler
import math


osc1_phase = [0,0,0,0,0,0,0]
osc2_phase = [0,0,0,0,0,0,0]

osc1_inc = []
osc2_inc = []

osc1_blocks = []
osc2_blocks = []

osc1_frequency = []
osc2_frequency = []



sample_rate = 44100
table_length = 2048
block_length - 256


sine = [math.sin(2 * math.pi * i / table_length) for i in range(table_length)]

saw = [2.0 * (i / table_length) - 1.0 for i in range(table_length)]

square = [1.0 if i < table_length // 2 else -1.0 for i in range(table_length)]

triangle = []
for i in range(table_length):
    phase = i / table_length
    if phase < 0.25:               
        triangle_table.append(-1.0 + 4.0 * phase)
    elif phase < 0.75:              
        triangle_table.append(1.0 - 4.0 * (phase - 0.25))
    else:                           
        triangle_table.append(-1.0 + 4.0 * (phase - 0.75))
        
        
def calculate_cents(unison, detune):
    if unison == 1:
        return [0]
    
    offsets = []
    step = (detune * 2) / (unison - 1)   # spacing in cents
    half = (unison - 1) // 2                   # how many voices on each side

    for i in range(-half, half+1):
        offsets.append(i * step)
    return offsets
    
        
        


def precomp_osc1(table, frequency):
    global block_length, osc1_phase, osc1_inc
    global table_length
    unison = uihandler.parameters["osc1_unison"]
    detune = uihandler.parameters["osc1_detune"]
    table = uihandler.parameters["osc1_wave"]

    
    block = []
    block = [0.0] * block_length
    
    #unison
    unison_cents = calculate_cents(unison, detune)
    for i in range(unison):
        osc1_frequency[i] = frequency*(2**(unison_cents[i]/1200))
        osc1_inc[i] = osc1_frequency[i]*table_length/sample_rate
        
        for j in range(block_length):
                block[j] = block[j] + table[int(osc1_phase[i]) % table_length / unison]
                osc1_phase[i]  += osc1_inc[i]
                if osc1_phase[i] >= table_length:
                    osc1_phase[i] -= table_length
                    
    return block
                    
def precomp_osc2(frequency):
    global block_length, osc2_phase, osc2_inc
    global table_length
    unison = uihandler.parameters["osc2_unison"]
    detune = uihandler.parameters["osc2_detune"]
    table = uihandler.parameters["osc2_wave"]
    block = []
    block = [0.0] * block_length
    
    #unison
    unison_cents = calculate_cents(unison, detune)
    for i in range(unison):
        osc2_frequency[i] = frequency*(2**(unison_cents[i]/1200))
        osc2_inc[i] = osc2_frequency[i]*table_length/sample_rate
        
        for j in range(block_length):
                block[j] = block[j] + table[int(osc2_phase[i]) % table_length / unison]
                osc2_phase[i]  += osc2_inc[i]
                if osc2_phase[i] >= table_length:
                    osc2_phase[i] -= table_length
                    
    return block


def osc1_envelope():
    global sample_rate
    attack = uihandler.parameters["osc1_attack"]
    decay = uihandler.parameters["osc1_decay"]
    sustain = uihandler.parameters["osc1_sustain"]
    envelope_value = 0
    envelope = []
    
    envelope_state = attack
    attack_inc = 1000/(sample_rate*attack)
    while envelope_value < (1-attack_inc):
        envelope_value += envelope_inc
        envelope.append(envelope_value)
    envelope.append(1)
    
    envelope_state = decay
    decay_inc = 1000*(1-decay)/(sample_rate*decay)
    while envelope_value > (sustain +decay_inc):
        envelope_value -= decay_inc
        envelope.append(envelope_value)
    envelope.append(sustain)
    
    return envelope
    
    
    
    
def osc1_release():
    global sample_rate
    release = uihandler.parameters["osc1_release"]
    sustain = uihandler.parameters["osc1_sustain"]
    
    envelope_value = sustain 
    release_inc = 1000*sustain / (release*sample_rate)
    while envelope_value > release_inc:
        envelope_value -= release_inc
    
    envelope.append(0)
    return envelope
        
    
     
def note_on(midi_values):
    frequency_values = []
    for n in midi_values:
        frequency_values.append(440*2^((n-69)/12))
        
    
        
    for i in frequency_values:
        for j in range(block_length):
            precomp_osc1(i)[j]*osc1_envelope[j]
            
            
        
        
        
        

def note_off(midi_values):
    osc1_release()
    
        
        
    
    

        
        

        

        
        
        
        


        

        
    