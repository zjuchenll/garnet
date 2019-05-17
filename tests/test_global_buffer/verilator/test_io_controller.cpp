/*==============================================================================
** Module: test_addrgen_bank_interconnect.cpp
** Description: Test driver for io controller
** Author: Taeyoung Kong
** Change history: 05/11/2019 - Implement first version 
** NOTE:    Word size is 16bit.
**          Address should be word-aligned.
**          This does not support unaligned access.
**============================================================================*/

#include "Vio_controller.h"
#include "verilated.h"
#include "testbench.h"
#include "time.h"
#include <verilated_vcd_c.h>
#include <vector>
#include <random>
#include <string.h>

// Address is byte addressable
uint16_t NUM_BANKS = 32;
uint16_t NUM_IO = 8;
uint16_t BANK_ADDR_WIDTH = 17;
uint16_t BANK_DATA_WIDTH = 64;
uint16_t CGRA_DATA_WIDTH = 16;
uint16_t CONFIG_FEATURE_WIDTH = 8;
uint16_t CONFIG_REG_WIDTH = 8;

using namespace std;

uint16_t** glb;

typedef enum MODE
{
    IDLE        = 0,
    INSTREAM    = 1,
    OUTSTREAM   = 2,
    SRAM        = 3
} MODE;

typedef enum REG_ID
{
    ID_MODE            = 0,
    ID_START_ADDR      = 1,
    ID_NUM_WORDS       = 2,
    ID_START_PULSE_EN  = 3,
    ID_DONE_PULSE_EN   = 4,
    ID_SWITCH_SEL      = 5
} REG_ID;

struct Addr_gen
{
    uint16_t id;
    MODE mode;
    uint32_t start_addr;
    uint32_t int_addr;
    uint32_t num_words;
    uint32_t int_cnt;
    uint32_t num_banks;
};

class IO_CTRL {
public:
    IO_CTRL(uint16_t num_io) {
        addr_gens = new Addr_gen[num_io];
        this->num_io = num_io;
        for (uint16_t i=0; i<num_io; i++) {
            addr_gens[i].id = i;
            addr_gens[i].mode = IDLE;
            addr_gens[i].start_addr = 0;
            addr_gens[i].int_addr = 0;
            addr_gens[i].num_words = 0;
            addr_gens[i].num_banks = 0;
        }
    }
    ~IO_CTRL(void) {
        delete[] addr_gens; 
    }

    uint16_t get_num_io() {
        return this->num_io;
    }
    MODE get_mode(uint16_t num_io) {
        return addr_gens[num_io].mode;
    }
    uint32_t get_start_addr(uint16_t num_io) {
        return addr_gens[num_io].start_addr;
    }
    uint32_t get_int_addr(uint16_t num_io) {
        return addr_gens[num_io].int_addr;
    }
    uint32_t get_num_words(uint16_t num_io) {
        return addr_gens[num_io].num_words;
    }
    uint32_t get_int_cnt(uint16_t num_io) {
        return addr_gens[num_io].int_cnt;
    }
    uint32_t get_num_banks(uint16_t num_io) {
        return addr_gens[num_io].num_banks;
    }
    Addr_gen& get_addr_gen(uint16_t num_io) {
        return addr_gens[num_io];
    }

    void set_mode(uint16_t num_io, MODE mode) {
        addr_gens[num_io].mode = mode;
    }
    void set_start_addr(uint16_t num_io, uint32_t start_addr) {
        if (start_addr % 2 != 0) {
            std::cerr << std::endl;  // end the current line
            std::cerr << "Address is not word aligned" << std::endl;
            exit(EXIT_FAILURE);
        }
        addr_gens[num_io].start_addr = start_addr;
    }

    void set_int_addr(uint16_t num_io, uint32_t int_addr) {
        if (int_addr % 2 != 0) {
            std::cerr << std::endl;  // end the current line
            std::cerr << "Address is not word aligned" << std::endl;
            exit(EXIT_FAILURE);
        }
        addr_gens[num_io].int_addr = int_addr;
    }

    void set_num_words(uint16_t num_io, uint32_t num_words) {
        addr_gens[num_io].num_words = num_words;
    }

    void set_int_cnt(uint16_t num_io, uint32_t int_cnt) {
        addr_gens[num_io].int_cnt = int_cnt;
    }

    void set_num_banks(uint16_t num_io, uint32_t num_banks) {
        if (num_banks > NUM_BANKS - (num_io * (NUM_BANKS/NUM_IO)) ) {
            std::cerr << std::endl;  // end the current line
            std::cerr << "IO controller " << num_io << "cannot access to " << num_banks << "number of banks." << std::endl;
            exit(EXIT_FAILURE);
        }
        addr_gens[num_io].num_banks = num_banks;
    }
private:
    Addr_gen *addr_gens;
    uint16_t num_io;
};

class IO_CTRL_TB : public TESTBENCH<Vio_controller> {
public:
    uint8_t *io_to_bank_rd_en_d1;
    uint32_t *io_to_bank_rd_addr_d1;

    IO_CTRL_TB(void) {
        io_to_bank_rd_en_d1 = new uint8_t[NUM_BANKS];
        io_to_bank_rd_addr_d1 = new uint32_t[NUM_BANKS];
        m_dut->glc_to_io_stall = 0;
        reset();
    }

    ~IO_CTRL_TB(void) {}

    void tick() {
        m_tickcount++;

        // All combinational logic should be settled
        // before we tick the clock
        eval();
        if(m_trace) m_trace->dump(10*m_tickcount-4);

        // Toggle the clock
        // Rising edge
        m_dut->clk = 1;
        glb_update();
        m_dut->eval();

        if(m_trace) m_trace->dump(10*m_tickcount);

        // Falling edge
        m_dut->clk = 0;
        m_dut->eval();
        if(m_trace) {
            m_trace->dump(10*m_tickcount+5);
            m_trace->flush();
        }
    }

    void config_wr(Addr_gen &addr_gen) {
        uint16_t num_id = addr_gen.id;
        config_wr(num_id, ID_MODE, addr_gen.mode);
        config_wr(num_id, ID_START_ADDR, addr_gen.start_addr);
        config_wr(num_id, ID_NUM_WORDS, addr_gen.num_words);
        config_switch_sel(num_id, addr_gen.num_banks);
    }

    void config_wr(uint16_t num_ctrl, REG_ID reg_id, uint32_t data) {
        printf("Configuration for %d\n", num_ctrl);
        if (num_ctrl > NUM_IO ) {
            std::cerr << std::endl;  // end the current line
            std::cerr << "Wrong number of io controller" << std::endl;
            m_trace->close();
            exit(EXIT_FAILURE);
        }
        uint32_t feature_id = num_ctrl;
        uint32_t config_addr = (reg_id << CONFIG_FEATURE_WIDTH) + feature_id;
        uint32_t config_data = data;
        m_dut->config_en = 1;
        m_dut->config_wr = 1;
        m_dut->config_addr = config_addr;
        m_dut->config_wr_data = config_data;
        tick();
        m_dut->config_en = 0;
        m_dut->config_wr = 0;
    }

    void config_switch_sel(uint16_t num_ctrl, uint16_t num_banks) {
        if (num_banks == 0) {
            config_wr(num_ctrl, ID_SWITCH_SEL, 0);
        }
        else if (num_banks == 1) {
            config_wr(num_ctrl, ID_SWITCH_SEL, 0b1000);
        }
        else if (num_banks == 2) {
            config_wr(num_ctrl, ID_SWITCH_SEL, 0b1100);
        }
        else if (num_banks == 3) {
            config_wr(num_ctrl, ID_SWITCH_SEL, 0b1110);
        }
        else if (num_banks == 4) {
            config_wr(num_ctrl, ID_SWITCH_SEL, 0b1111);
        }
        else {
            config_wr(num_ctrl, ID_SWITCH_SEL, 0b1111);
            for (uint16_t i=num_ctrl+1; i < NUM_IO; i++) {
                config_wr(i, ID_SWITCH_SEL, 0);
            }
        }
    }
    
    void config_rd(uint16_t num_ctrl, REG_ID reg_id, uint32_t data) {
        uint32_t feature_id = num_ctrl;
        uint32_t config_addr = (reg_id << CONFIG_FEATURE_WIDTH) + feature_id;
        uint32_t config_data = data;
        m_dut->config_en = 1;
        m_dut->config_rd = 1;
        m_dut->config_addr = config_addr;
        m_dut->config_wr_data = config_data;
        tick();
        m_dut->config_en = 0;
        m_dut->config_rd = 0;
    }

    void io_ctrl_setup(IO_CTRL* io_ctrl) {
        for(uint16_t i=0; i < io_ctrl->get_num_io(); i++) {
            if (io_ctrl->get_mode(i) == OUTSTREAM) {
                printf("Address generator %d : OUTSTREAM\n", i);
                io_ctrl->set_int_addr(i, io_ctrl->get_start_addr(i));
                io_ctrl->set_int_cnt(i, io_ctrl->get_num_words(i));
            }
            else if (io_ctrl->get_mode(i) == INSTREAM) {
                printf("Address generator %d : INSTREAM\n", i);
                io_ctrl->set_int_addr(i, io_ctrl->get_start_addr(i));
                io_ctrl->set_int_cnt(i, io_ctrl->get_num_words(i));
            }
            else if (io_ctrl->get_mode(i) == SRAM)
                printf("Address generator %d : SRAM\n", i);
            else
                printf("Address generator %d : IDLE\n", i);
        }
    }
    
    void test(IO_CTRL* io_ctrl, uint32_t latency=100) {
        // glb setting
        for(uint16_t i=0; i<io_ctrl->get_num_io(); i++) {
            config_wr(io_ctrl->get_addr_gen(i)); 
        }

        // why hurry?
        for (uint32_t t=0; t<100; t++) {
            tick();
        }

        uint32_t max_num_words = 0;
        for(uint16_t i=0; i < io_ctrl->get_num_io(); i++) {
            if (io_ctrl->get_mode(i) != IDLE) {
                max_num_words = std::max(io_ctrl->get_num_words(i), max_num_words);
            }
        }
        uint16_t* wr_data_array = new uint16_t[max_num_words];

        for (uint32_t i=0; i<max_num_words; i++)
            //wr_data_array[i] = (uint16_t)rand(); 
            wr_data_array[i] = (uint16_t) (500 + i); 

        // toggle cgra_start_pulse
        m_dut->cgra_start_pulse = 1;
        tick();
        m_dut->cgra_start_pulse = 0;

        // internal counter and address set to num_words and start_address
        io_ctrl_setup(io_ctrl);

        // latency of read
        tick();

        // latency of application
        for (uint32_t t=0; t<latency; t++) {
            tick();
            instream(io_ctrl);
        }

        for(uint16_t i=0; i < io_ctrl->get_num_io(); i++) {
            if (io_ctrl->get_mode(i) == OUTSTREAM) {
                m_dut->cgra_to_io_wr_en[i] = 1;
                m_dut->cgra_to_io_wr_data[i] = wr_data_array[0];
            }
        }

        printf("IO Controller starts\n");

        uint32_t num_cnt = 0;
        while (m_dut->cgra_done_pulse != 1) {
            tick();
            instream(io_ctrl);
            outstream(io_ctrl, wr_data_array, num_cnt);
        }

        printf("End feeding data\n");
        
        // why hurry?
        for (uint32_t t=0; t<100; t++) {
            tick();
        }
    }

private:

    void instream(IO_CTRL* io_ctrl) {
        for(uint16_t i=0; i < io_ctrl->get_num_io(); i++) {
            if (io_ctrl->get_mode(i) == INSTREAM) {
                uint32_t int_cnt = io_ctrl->get_int_cnt(i);
                uint32_t int_addr = io_ctrl->get_int_addr(i);
                if (int_cnt > 0) {
                    printf("Address generator number %d is streaming data to CGRA.\n", i);
                    printf("\tData: 0x%04x / Addr: 0x%08x / Valid: %01d\n", m_dut->io_to_cgra_rd_data[i], int_addr, m_dut->io_to_cgra_rd_data_valid[i]);
                    my_assert(m_dut->io_to_cgra_rd_data[i], glb[(uint16_t)(int_addr >> BANK_ADDR_WIDTH)][(int_addr & ((1<<BANK_ADDR_WIDTH)-1))>>1], "io_to_cgra_rd_data");
                    my_assert(m_dut->io_to_cgra_rd_data_valid[i], 1, "io_to_cgra_rd_data_valid");
                    io_ctrl->set_int_addr(i, int_addr + 2);
                    io_ctrl->set_int_cnt(i, int_cnt - 1);
                }
            }
        }
    }

    void outstream(IO_CTRL* io_ctrl, uint16_t *data_array, uint32_t &num_cnt) {
        uint16_t next_wr_en = rand() % 2;
        for(uint16_t i=0; i < io_ctrl->get_num_io(); i++) {
            if (io_ctrl->get_mode(i) == OUTSTREAM) {
                uint32_t int_addr = io_ctrl->get_int_addr(i);
                uint32_t int_cnt = io_ctrl->get_int_cnt(i);
                printf("CGRA is writing data to IO controller.\n");
                printf("\tData: 0x%04x / Addr: 0x%08x / Valid: %01d\n", m_dut->cgra_to_io_wr_data[i], int_addr, m_dut->cgra_to_io_wr_en[i]);
                if (m_dut->cgra_to_io_wr_en[i] == 1) {
                    io_ctrl->set_int_addr(i, int_addr + 2);
                    io_ctrl->set_int_cnt(i, int_cnt - 1);
                    m_dut->cgra_to_io_wr_data[i] = data_array[++num_cnt];
                }
                if (io_ctrl->get_int_cnt(i) == 0)
                    m_dut->cgra_to_io_wr_en[i] = 0;
                else
                    m_dut->cgra_to_io_wr_en[i] = next_wr_en;
            }
        }
    }

    void glb_update() {
        glb_write();
        glb_read();
    }

    void glb_read() {
        for (uint16_t i=0; i<NUM_BANKS; i++) {
            if (io_to_bank_rd_en_d1[i] == 1) {
                m_dut->bank_to_io_rd_data[i] = ((uint64_t) glb[i][(io_to_bank_rd_addr_d1[i]>>1)+3] << 48)
                                             + ((uint64_t) glb[i][(io_to_bank_rd_addr_d1[i]>>1)+2] << 32)
                                             + ((uint64_t) glb[i][(io_to_bank_rd_addr_d1[i]>>1)+1] << 16)
                                             + ((uint64_t) glb[i][(io_to_bank_rd_addr_d1[i]>>1)+0]);

                printf("Read data from bank %d\n", i);
                printf("\tData: 0x%016lx / Addr: 0x%08x\n", m_dut->bank_to_io_rd_data[i], io_to_bank_rd_addr_d1[i]);
            }
            // bank_to_io_rd_data is from glb stub with one cycle latency
            io_to_bank_rd_en_d1[i] = m_dut->io_to_bank_rd_en[i];
            io_to_bank_rd_addr_d1[i] = m_dut->io_to_bank_rd_addr[i];
        }
    }

    void glb_write() {
        for (uint16_t i=0; i<NUM_BANKS; i++) {
            if (m_dut->io_to_bank_wr_en[i] == 1) {
                glb[i][((m_dut->io_to_bank_wr_addr[i]>>3)<<2)+0] = (uint16_t) ((m_dut->io_to_bank_wr_data[i] & 0x000000000000FFFF) & (m_dut->io_to_bank_wr_data_bit_sel[i] & 0x000000000000FFFF));
                glb[i][((m_dut->io_to_bank_wr_addr[i]>>3)<<2)+1] = (uint16_t) (((m_dut->io_to_bank_wr_data[i] & 0x00000000FFFF0000) & (m_dut->io_to_bank_wr_data_bit_sel[i] & 0x00000000FFFF0000)) >> 16);
                glb[i][((m_dut->io_to_bank_wr_addr[i]>>3)<<2)+2] = (uint16_t) (((m_dut->io_to_bank_wr_data[i] & 0x0000FFFF00000000) & (m_dut->io_to_bank_wr_data_bit_sel[i] & 0x0000FFFF00000000)) >> 32);
                glb[i][((m_dut->io_to_bank_wr_addr[i]>>3)<<2)+3] = (uint16_t) (((m_dut->io_to_bank_wr_data[i] & 0xFFFF000000000000) & (m_dut->io_to_bank_wr_data_bit_sel[i] & 0xFFFF000000000000)) >> 48);
                printf("Write data to bank %d\n", i);
                printf("\tData: 0x%016lx / Bit_sel: 0x%016lx, Addr: 0x%08x\n", m_dut->io_to_bank_wr_data[i], m_dut->io_to_bank_wr_data_bit_sel[i], m_dut->io_to_bank_wr_addr[i]);
            }
        }
    }
};

int main(int argc, char **argv) {
    int rcode = EXIT_SUCCESS;
    if (argc % 2 == 0) {
        printf("\nParameter wrong!\n");
        return 0;
    }
    size_t pos;
    for (int i = 1; i < argc; i=i+2) {
        string argv_tmp = argv[i];
        if (argv_tmp == "BANK_ADDR_WIDTH") {
            BANK_ADDR_WIDTH = stoi(argv[i+1], &pos);
        }
        else if (argv_tmp == "BANK_DATA_WIDTH") {
            BANK_DATA_WIDTH = stoi(argv[i+1], &pos);
        }
        else if (argv_tmp == "CGRA_DATA_WIDTH") {
            CGRA_DATA_WIDTH = stoi(argv[i+1], &pos);
        }
        else if (argv_tmp == "CONFIG_FEATURE_WIDTH") {
            CONFIG_FEATURE_WIDTH = stoi(argv[i+1], &pos);
        }
        else if (argv_tmp == "CONFIG_REG_WIDTH") {
            CONFIG_REG_WIDTH = stoi(argv[i+1], &pos);
        }
        else {
            printf("\nParameter wrong!\n");
            return 0;
        }
    }

    srand (time(NULL));
    // Instantiate address generator testbench
    IO_CTRL_TB *io_ctrl_tb = new IO_CTRL_TB();
    io_ctrl_tb->opentrace("trace_io_ctrl.vcd");
    io_ctrl_tb->reset();

    // Create global buffer stub using array
    glb = new uint16_t*[NUM_BANKS];

    // initialize glb with random 16bit number 
    for (uint16_t i=0; i<NUM_BANKS; i++) {
        glb[i] = new uint16_t[(1<<(BANK_ADDR_WIDTH-1))];
        for (uint32_t j=0; j<(1<<(BANK_ADDR_WIDTH-1)); j++) {
                //glb[i][j]= (uint16_t)rand();
                glb[i][j]= j;
        }
    }

    //============================================================================//
    // configuration test
    //============================================================================//

    //============================================================================//
    // IO controller instantiation
    //============================================================================//
    IO_CTRL *io_ctrl = new IO_CTRL(NUM_IO);
    // Set io_ctrl[0]
    io_ctrl->set_mode(0, INSTREAM);
    io_ctrl->set_start_addr(0, (5<<BANK_ADDR_WIDTH) + (1<<(BANK_ADDR_WIDTH-2))+100);
    io_ctrl->set_num_words(0, 1000);
    io_ctrl->set_num_banks(0, 6);

    // Set io_ctrl[0]
    io_ctrl->set_mode(1, INSTREAM);
    io_ctrl->set_start_addr(1, (6<<BANK_ADDR_WIDTH)+100);
    io_ctrl->set_num_words(1, 1000);
    io_ctrl->set_num_banks(1, 2);

    // Set io_ctrl[4]
    io_ctrl->set_mode(4, OUTSTREAM);
    io_ctrl->set_start_addr(4, (16<<BANK_ADDR_WIDTH)+100);
    io_ctrl->set_num_words(4, 1000);
    io_ctrl->set_num_banks(4, 16);

    //============================================================================//
    // IO controller test
    //============================================================================//
    printf("\n");
    printf("/////////////////////////////////////////////\n");
    printf("Start IO controller test\n");
    printf("/////////////////////////////////////////////\n");
    io_ctrl_tb->test(io_ctrl);
    printf("/////////////////////////////////////////////\n");
    printf("IO controller test is successful\n");
    printf("/////////////////////////////////////////////\n");
    printf("\n");

    printf("\nAll simulations are passed!\n");
    for (uint16_t i=0; i<NUM_BANKS; i++) {
        delete[] glb[i];
    }
    delete[] glb;
    exit(rcode);
}

