#include "shared-module/audio_driver/audio_driver.h"
#include "shared-bindings/audio_driver/__init__.h"
#include <stdlib.h>
#include "fsl_edma.h"
#include "fsl_dmamux.h"

//sai includes
#include "fsl_sai.h"
#include "fsl_clock.h"
#include "fsl_iomuxc.h"
#include "fsl_gpio.h"

static int16_t* zero_block = NULL; //empty block, if buffer underrun


void sai_init(void) {
    
    zero_block = (int16_t*) calloc(block_length, sizeof(int16_t));

    SAI_Init(SAI1); 

    IOMUXC_SetPinMux(IOMUXC_GPIO_B1_14_SAI1_TX_BCLK, 3,0,0,0,0); //alt 3
    IOMUXC_SetPinMux(IOMUXC_GPIO_B1_15_SAI1_TX_SYNC, 3,0,0,0,0); //alt 3
    IOMUXC_SetPinMux(IOMUXC_GPIO_B1_01_SAI1_TX_DATA0, 3,0,0,0,0); //pin 7 alt 3
    

    //electrical settings
    //IOMUXC_SetPinConfig(IOMUXC_GPIO_B0_10_SAI1_TX_BCLK, 0xF080);
    //IOMUXC_SetPinConfig(IOMUXC_GPIO_B0_11_SAI1_TX_SYNC, 0xF080);
    //IOMUXC_SetPinConfig(IOMUXC_GPIO_B1_00_SAI1_TX_DATA0, 0xF080);

    sai_master_clock_t masterclock_config;
    masterclock_config.mclkHz = 24576000; //target mclk - and for divider calc
    masterclock_config.mclkSourceClkHz = CLOCK_GetFreq(kCLOCK_AudioPllClk); // the mclk source
    masterclock_config.mclkOutputEnable = false; //mclk output not sent to pin because the uda1334a generates its own mclk using lrclk and bclk speeds.
    masterclock_config.mclkSource = kSAI_MclkSourceSysclk;


    sai_bit_clock_t bitclock_config;
    bitclock_config.bclkSource = kSAI_BclkSourceMclkDiv; //bclk from mclk divider
    bitclock_config.bclkPolarity = kSAI_BclkPolarityActiveHigh; //polarity - for uda1334a its high


    sai_config_t config;
    config.bclkSource = kSAI_BclkSourceMclkDiv; //config and bclk config both have a bclkSource value for some reason - assign it here as well
    config.protocol = kSAI_BusI2S;
    config.syncMode = kSAI_ModeAsync;
    config.masterSlave = kSAI_Master;

    config.mclkOutputEnable = true;
    config.mclkSource = kSAI_MclkSourceSysclk;
  
    
    sai_transfer_format_t format_config;
    format_config.bitWidth = 16;                 // 16-bit samples            
    format_config.sampleRate_Hz = sample_rate;         // standard audio rate
    format_config.stereo = kSAI_Stereo;   
    format_config.masterClockHz = 24576000; /*!< Master clock frequency in Hz */                   /* FSL_FEATURE_SAI_HAS_MCLKDIV_REGISTER */
    format_config.watermark = kSAI_Fifo0Word; /*!< Watermark value */   
    format_config.channel = 0;
    format_config.endChannel = 1;
    format_config.channelNums = 2;
    format_config.channelMask = kSAI_Channel0Mask | kSAI_Channel1Mask;

    SAI_TxInit(SAI1, &config);

    SAI_SetMasterClockConfig(SAI1, &masterclock_config);
    SAI_TxSetBitclockConfig(SAI1, config.masterSlave, &bitclock_config);

    SAI_TxSetFormat(SAI1, &format_config, CLOCK_GetFreq(kCLOCK_AudioPllClk), CLOCK_GetFreq(kCLOCK_AudioPllClk));
    SAI_TxEnableDMA(SAI1, kSAI_FIFORequestDMAEnable, true);
    SAI_TxSetWatermark(SAI1, kSAI_Fifo6Word); //fifo watermark

    SAI_TxEnable(SAI1, true);
}


//static volatile bool dma_running = false;

//DMA initialisation

static edma_handle_t dma_handle;
edma_transfer_config_t transfer_config;

#define dma_channel 20

void dma_init(void) {
    // enable dma mux
    DMAMUX_Init(DMAMUX);
    DMAMUX_SetSource(DMAMUX, dma_channel, kDmaRequestMuxSai1Tx); // I2S1 TX
    DMAMUX_EnableChannel(DMAMUX, dma_channel);
    CLOCK_EnableClock(kCLOCK_Dma0);

    // enable dma
    edma_config_t edmaConfig;
    EDMA_GetDefaultConfig(&edmaConfig); // get default config
    EDMA_Init(DMA0, &edmaConfig); //initialize dma
    EDMA_CreateHandle(&dma_handle, DMA0, dma_channel); //create handle
    EDMA_SetCallback(&dma_handle, dma_callback, NULL); // register callback
    NVIC_SetPriority(DMA0_IRQn, 2); 
    NVIC_EnableIRQ(DMA0_IRQn);

    // transfer config
    EDMA_PrepareTransfer(&transfer_config,
                         ring_buffer,               // source
                         sizeof(int16_t),           // size of source
                         (void*)&SAI1->TDR[0],         // address of destination
                         sizeof(int16_t),           // size of destination
                         sizeof(int16_t),           // minor loop - size of each sample
                         block_length * sizeof(int16_t), // major loop - size of block
                         kEDMA_MemoryToPeripheral); //direction of transfer

    EDMA_SetModulo(DMA0, dma_channel, kEDMA_ModuloDisable, kEDMA_ModuloDisable);

    EDMA_SubmitTransfer(&dma_handle, &transfer_config, kEDMA_EnableInterruptMask);

    EDMA_StartTransfer(&dma_handle); //start dma
    
    }


void DMA0_IRQHandler(void) {
    EDMA_HandleIRQ(&dma_handle);
}

//dma callback
void dma_callback(edma_handle_t *handle, void *param, bool transferDone, uint32_t tcds) {
    uint32_t ptrs = buffer_ptrs;
    uint16_t read_ptr = ptrs >> 16;
    uint16_t write_ptr = ptrs & 0xFFFF;
    edma_transfer_config_t next_transfer_config;

    if (transferDone) {
        int16_t *src_ptr;
        
        int16_t available = 0;
        if (write_ptr >= read_ptr) {
            available = write_ptr - read_ptr;
        } else {
            available = buffer_size - read_ptr + write_ptr;
        }

        if (available >= block_length) {
            src_ptr = &ring_buffer[read_ptr];
            read_ptr = (read_ptr + block_length) % buffer_size;
        } else {
            src_ptr = zero_block; // underrun → silence
        }

        set_read_ptr(read_ptr); // update read pointer

        // Prepare the next transfer
        EDMA_PrepareTransfer(&next_transfer_config,
                             src_ptr,                  // new source block
                             sizeof(int16_t),
                             (void *)&SAI1->TDR[0],   // destination (SAI FIFO)
                             sizeof(int16_t),
                             sizeof(int16_t),          // minor loop = 1 sample
                             block_length * sizeof(int16_t), // major loop = block
                             kEDMA_MemoryToPeripheral);

        // Submit it again
        EDMA_SubmitTransfer(handle, &next_transfer_config, kEDMA_EnableInterruptMask);
    }
}
