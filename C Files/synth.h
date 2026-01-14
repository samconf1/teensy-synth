#ifndef AUDIO_DRIVER_SYNTH_H
#define AUDIO_DRIVER_SYNTH_H

#define MAX_UNISON 7
#define TABLE_LENGTH 2048
#define SAMPLE_RATE 44100

typedef struct note_node note_node_t;

void synth_init(void);
void synth_note_on(uint8_t* midi_values, uint8_t* velocity_values, uint8_t len);
void synth_note_off(uint8_t* midi_values, uint8_t len);
void generate_block(void);
int count_notes(note_node_t *list_head);
void send_to_buffer(float *block);
void apply_filter(float *block);
void print_sp(void);
bool synth_is_note_on(void);


typedef struct note_node { 
    uint8_t midi_value;
    float frequency;                
    uint8_t unison;   
    float detune;       
    float phase[MAX_UNISON];   
    float inc[MAX_UNISON];          
    float *wavetable;          
    float *envelope;
    bool envelope_end;  
    uint32_t block_number;
    uint16_t envelope_length;
    
    // linked list pointer
    struct note_node *next;         // points to next note, or null if last
} note_node_t;

extern note_node_t *active_notes1;
extern note_node_t *active_notes2;
extern note_node_t *release_notes1;
extern note_node_t *release_notes2; 

typedef struct {
    //osc1
    uint8_t osc1_wave;             //0 = sine, 1 = saw, 2 = square, 3 = triangle
    float osc1_level;          
    uint8_t osc1_unison;   
    float osc1_detune;              
    
    // osc2
    uint8_t osc2_wave;
    float osc2_level;
    uint8_t osc2_unison;
    float osc2_detune;
    
    // env1
    uint16_t env1_attack;         
    uint16_t env1_decay;          
    float env1_sustain;         
    uint16_t env1_release;        
    
    // env2
    uint16_t env2_attack;
    uint16_t env2_decay;
    float env2_sustain;
    uint16_t env2_release;
    
    // filter
    float filter_cutoff;    
    float filter_resonance; 
    
    float total_level;
    int dirty; //0 = clean, 1 = dirty
} synth_params_t;

extern synth_params_t current_params;

#endif