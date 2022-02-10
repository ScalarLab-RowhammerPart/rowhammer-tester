#!/usr/bin/env python3

import random
import argparse
import itertools

from rowhammer_tester.scripts.utils import *
from rowhammer_tester.scripts.read_level import read_level, Settings, sdram_cmd, cdly_inc
from rowhammer_tester.scripts.read_level import read_level_hardcoded, write_level_hardcoded

# Perform a memory test using a random data pattern and linear addressing
def memtest(wb, length, *, generator, base=None, verbose=None, burst=255):
    sdram_hardware_control(wb)
    if base is None:
        base = wb.mems.main_ram.base

    refdata = [next(generator) for _ in range(length)]
    memwrite(wb, refdata, base=base, burst=burst)

    data = memread(wb, length, base=base, burst=burst)
    assert len(refdata) == len(data)

    errors = 0
    for val, ref in zip(data, refdata):
        if val != ref:
            errors += 1
            if verbose is not None:
                compare(val, ref, fmt=verbose, nbytes=4)

    return errors

# ###########################################################################

def eye_opening(wb):
    print("Starting CA training phase")
    print("==========================")
    # F0RC0C register starts
    f0rc0c = 0x0C0 | 0x0

    sdram_cmd(wb, f0rc0c, 7, dfii_command_ras|dfii_command_cas|dfii_command_we|dfii_command_cs)

    wb.regs.ddrphy_eye_opening_en.write(1)
    for _ in range(32):
        print(f"start: {wb.regs.ddrphy_eye_opening_start.read()} - end: {wb.regs.ddrphy_eye_opening_end.read()} - eye_opening_en: {wb.regs.ddrphy_eye_opening_en.read()}")
        cdly_inc(wb)

    wb.regs.ddrphy_eye_opening_en.write(0)
    rcd_reset = 0x060 | 0x0 # F0RC06: command space control; 0: reset RCD
    sdram_cmd(wb, rcd_reset, 7, dfii_command_ras|dfii_command_cas|dfii_command_we|dfii_command_cs)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--srv', action='store_true', help='Start litex server')
    parser.add_argument('--no-init', action='store_true', help='Do not perform initialization sequence')
    parser.add_argument('--size', default='0x2000', help='Memtest size')
    parser.add_argument('--memspeed', action='store_true', help='Run memroy speed test')
    parser.add_argument('--max-delays', type=int, default=32, help='Avoid testing too many delays to save time')
    parser.add_argument('--read-level-hardcoded', action='store_true', help='Use predefined read leveling values')
    args = parser.parse_args()

    if args.srv:
        litex_server()

    wb = RemoteClient()
    wb.open()

    if not args.no_init:
        print('SDRAM initialization:')
        sdram_software_control(wb)
        # Reset the PHY
        wb.regs.ddrphy_rst.write(1)
        time.sleep(0.2)
        wb.regs.ddrphy_rst.write(0)
        time.sleep(0.2)

        # Perform the init sequence
        sdram_init(wb)

        eye_opening(wb)

        if hasattr(wb.regs, 'ddrphy_rdly_dq_bitslip'):
            print('\nRead leveling:')
            settings = Settings.load()

            # Make it faster by testing less delays
            delays_step = 1
            while settings.delays / delays_step > args.max_delays:
                delays_step *= 2

            if args.read_level_hardcoded:
                assert get_generated_defs()['TARGET'] == 'zcu104'
                read_level_hardcoded(wb, config=[
                    (2, 184),
                    (2, 184),
                    (2, 136),
                    (2, 136),
                    (3, 368),
                    (3, 360),
                    (3, 328),
                    (3, 296),
                ])
            else:
                read_level(wb, Settings.load(), delays_step=delays_step)

    memtest_size = int(args.size, 0)

    def run_memtest(name, generator, **kwargs):
        print('\nMemtest ({})'.format(name))
        errors = memtest(wb, length=memtest_size, generator=generator, **kwargs)
        print('OK' if errors == 0 else 'FAIL: errors = {}'.format(errors))

    def rand_generator(seed):
        rng = random.Random(seed)
        while True:
            yield rng.randint(0, 2**32 - 1)

    run_memtest('basic', itertools.cycle([0xaaaaaaaa, 0x55555555]))
    run_memtest('random', rand_generator(42))

    if args.memspeed:
        for n in [0x1000//4, 0x10000//4, 0x100000//4]:
            print('Size = 0x{:08x}'.format(n*4))
            memspeed(wb, n)
        # Example results:
        #  Size = 0x00001000
        #   Write speed:  48.14 KB/s (0.0 sec)
        #   Read  speed:   2.08 KB/s (0.1 sec)
        #  Size = 0x00010000
        #   Write speed:  82.45 KB/s (0.0 sec)
        #   Read  speed:   3.09 KB/s (1.3 sec)
        #  Size = 0x00100000
        #   Write speed: 123.88 KB/s (0.5 sec)
        #   Read  speed:   3.04 KB/s (21.6 sec)
        #  Size = 0x01000000
        #   Write speed:  47.24 KB/s (22.2 sec)
        # So reading 1MB takes ~21.6 seconds.
        # We have 256MB DRAM on board, so it should take ~1.5 hour to read.
        # Writing is an order of magnitude faster.

    wb.close()
