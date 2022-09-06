from migen import *

from litex.soc.interconnect.csr import CSRStatus, CSRStorage, AutoCSR
from litex.soc.integration.doc import AutoDoc, ModuleDoc

class RowHammerDMA(Module, AutoCSR, AutoDoc, ModuleDoc):
    """
    Row Hammer DMA attacker

    This module allows to perform a Row Hammer attack by configuring it with
    two addresses that map to different rows of a single bank. When enabled,
    it will perform alternating DMA reads from the given locations, which will
    result in the DRAM controller having to repeatedly open/close rows at each
    read access.
    """
    def __init__(self, dma):
        address_width = len(dma.sink.address)

        self.enabled  = CSRStorage(description="Used to start/stop the operation of the module")
        self.address1 = CSRStorage(address_width, description="First far-attacked address")
        self.address2 = CSRStorage(address_width, description="Second far-attacked address")
        self.address3 = CSRStorage(address_width, description="First near-attacked address")
        self.address4 = CSRStorage(address_width, description="Second near-attacked address")
        self.dilution = CSRStorage(32, description="Half-Double dilution parameter")
        self.count    = CSRStatus(32, description="""This is the number of DMA accesses performed.
                                  When the module is enabled, the value can be freely read. When
                                  the module is disabled, the register is clear-on-write and has
                                  to be read before the next attack.""")

        counter1 = Signal.like(self.count.status)
        counter2 = Signal.like(self.count.status)
        self.comb += self.count.status.eq(counter1)
        self.sync += \
            If(self.enabled.storage,
                If(dma.sink.valid & dma.sink.ready,
                    counter1.eq(counter1 + 1),
                    counter2.eq(counter2 + 1)
                )
            ).Elif(self.count.we,  # clear on read when not enabled
                counter1.eq(0),
                counter2.eq(0)
            )

        address = Signal(address_width)
        self.comb += If(counter2 == self.dilution,
            address.eq(self.address3.storage)
        ).Elif(counter2 == self.dilution + 1,
            address.eq(self.address4.storage),
            self.counter2.eq(0)
        ).Else(
            Case(counter1[0], {
                0: address.eq(self.address1.storage),
                1: address.eq(self.address2.storage),
            })
        )

        self.comb += [
            dma.sink.address.eq(address),
            dma.sink.valid.eq(self.enabled.storage),
            dma.source.ready.eq(1),
        ]
