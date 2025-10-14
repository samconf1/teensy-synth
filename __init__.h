#ifndef AUDIO_DRIVER_INIT_H
#define AUDIO_DRIVER_INIT_H

#include "py/obj.h"
#include <stdint.h>
#include <stdbool.h>


extern uint16_t block_length;
extern uint16_t buffer_size;
extern volatile uint32_t buffer_ptrs;
extern int16_t* ring_buffer;
extern uint16_t sample_rate;



// functions exposed to python
mp_obj_t audio_driver_start_audio(void);
mp_obj_t audio_driver_set_buffer_length(mp_obj_t py_block_length, mp_obj_t py_buffer_multiplier, mp_obj_t py_sample_rate);
mp_obj_t audio_driver_send_filter_values(mp_obj_t py_cutoff, mp_obj_t py_resonance);
mp_obj_t audio_driver_buffer_has_space(void);
mp_obj_t audio_driver_send_to_buffer(mp_obj_t py_block);
mp_obj_t audio_driver_py_get_pointers(void);
mp_obj_t audio_driver_get_callback_count(void);


void calculate_coefficients(void);
void set_read_ptr(uint16_t read);
void set_write_ptr(uint16_t write);
void get_buffer_ptrs(uint16_t *read_ptr, uint16_t *write_ptr);

#endif 
