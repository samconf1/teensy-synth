#ifndef AUDIO_DRIVER_H
#define AUDIO_DRIVER_H

#include "fsl_edma.h"
#include <stdint.h>
#include <stdbool.h>
#include "py/obj.h"

extern volatile uint32_t dma_callback_count;
extern volatile uint32_t underrun_count;


extern void set_read_ptr(uint16_t read_ptr);

void enable_system_clocks(void);
void sai_init(void);
void dma_init(void);

void DMA4_DMA20_IRQHandler(void);
void dma_callback(edma_handle_t *handle, void *param, bool transferDone, uint32_t tcds);

mp_obj_t audio_driver_get_underrun_count(void);


#endif
