#!/usr/bin/env python3

"""
Author Jeff Charter Chapman
Except Subset Sum implementation modified from saltycrane

A Resistance Manager instance can manage 1 channel on the NI PXI 2722 card
There are 16 possible channels
"""
import sys
import niswitch
import logging
log = logging.getLogger(__name__)

class ResistanceManager:
    """
    ResistanceManager can manage 1 channel per instance
    """
    def __init__(self, device="PXI1Slot7", channel=0, topo="2722/Independent"):
        self.device=device
        self.topology=topo
        self.channel=channel
        self.connections=[]
        self.bank_a, self.bank_b = self.getChannels()

    def __del__(self):
        self.clearWholeChannel()


    def getChannels(self):
        """
        returns 2 lists of all valid bank names for the given channel
        returns 'b0r1', 'b0engage' style names
        """
        prefix_bank_A="b"+str(self.channel*2)
        prefix_bank_B="b"+str((self.channel*2)+1)

        with niswitch.Session(self.device,
                              topology=self.topology) as session_matrix:
            channel_names = []
            for i in range(1, 99999):
                try:
                    channel_names.append(session_matrix.get_channel_name(i))
                except niswitch.errors.Error as e:
                    break

            b0 = [col for col in channel_names if col.startswith(prefix_bank_A)]
            b1 = [row for row in channel_names if row.startswith(prefix_bank_B)]

            log.debug(b0)
            log.debug(b1)

            return (b0, b1)

    def setResistance(self, resistance_ohms):
        """
        Set the resistance
        """
        self.clearWholeChannel()

        with niswitch.Session(self.device, topology=self.topology) as ni_session:
            for a, b in self.get_banks_to_close_by_name(resistance_ohms):
                log.debug('closing %s %s' % (a, b))
                ni_session.connect( a, b )


    def get_banks_to_close_by_name(self, resistance):
        """ returns array of pairs to close to get the resistance
            these pairs can be fed to an ni_session for an niswitch, connect() func
        """
        retConnections = []
        if resistance >= 0 and resistance <= 16000:

            resistance = round(resistance*4)/4 # round to nearest .25

            """ See NI specs
                These are the available resistance values in ohms. 
                some combination of these values can be used to create the 
                desired resistance value. Say one wants 67 ohms, this can be made 
                with sum of 1,2,64
            """

            even_bank = [.25,.5,1,2,4,8,16,32]
            odd_bank  = [64,128,256,512,1024,2048,4096,8192]

            sum, values = SubsetSum.get_banks_to_leave_open(even_bank+odd_bank, resistance);

            bank0_close = set(even_bank) - set( values )
            bank1_close = set(odd_bank)  - set( values )

            prefix_bank_A=self.bank_a[0] # e.g. 'b0', sure hope the order is always the same
            prefix_bank_B=self.bank_b[0] # e.g. 'b1'

            a_engage=self.bank_a[1] # e.g. 'b0engage'
            b_engage=self.bank_b[1]

            bank0_dict = {}
            bank0_dict[.25] = self.bank_a[2]
            bank0_dict[.5 ] = self.bank_a[3]
            bank0_dict[1]   = self.bank_a[4]
            bank0_dict[2]   = self.bank_a[5]
            bank0_dict[4]   = self.bank_a[6]
            bank0_dict[8]   = self.bank_a[7]
            bank0_dict[16]  = self.bank_a[8]
            bank0_dict[32]  = self.bank_a[9]

            bank1_dict = {}
            bank1_dict[64  ] = self.bank_b[2]
            bank1_dict[128 ] = self.bank_b[3]
            bank1_dict[256 ] = self.bank_b[4]
            bank1_dict[512 ] = self.bank_b[5]
            bank1_dict[1024] = self.bank_b[6]
            bank1_dict[2048] = self.bank_b[7]
            bank1_dict[4096] = self.bank_b[8]
            bank1_dict[8192] = self.bank_b[9]

            connections = self.connections
            connections.clear()

            connections.append( (prefix_bank_A, a_engage) )
            connections.append( (prefix_bank_B, b_engage) )
            connections.append( (prefix_bank_A, prefix_bank_B) ) # connect the 2 banks
            for bank in bank0_close:
                connections.append( (prefix_bank_A, bank0_dict[bank]) )

            for bank in bank1_close:
                connections.append( (prefix_bank_B, bank1_dict[bank]) )

            retConnections.extend(connections)
        else:
            # Failure case (resistance out of range).
            log.debug("'resistance' parameter (%.2f) is out of range."%resistance)
            log.debug("The acceptable range is 0 <= resistance <= 16000")

        return retConnections


    def clearWholeChannel(self):
        """
        check all possible connections and disconnect if needed
        """
        with niswitch.Session(self.device, topology=self.topology) as ni_session:
            def checkAndDisconnect(a,b):
                state = ni_session.can_connect(a, b)
                if niswitch.PathCapability.PATH_EXISTS.value == state.value:
                    log.debug('disconnecting: %s %s' % (a, b))
                    ni_session.disconnect( a, b )

            for n in self.bank_a[1:]:
                checkAndDisconnect(self.bank_a[0], n)

            for n in self.bank_b[1:]:
                checkAndDisconnect(self.bank_b[0], n)

            checkAndDisconnect(self.bank_a[0], self.bank_b[0])


class SubsetSum:
    """ 
        Provides support for resistance manager

        subset sum algorithm used to calculate relays to close in the PXI-2722
        resistance module card. RTFM for PXI-2722.

        return a tuple (target_sum, list of values that make up the target sum)  
            `target_sum -- if a subset was found, else 0`

        This class uses recursive function calls and 'memoization' to solve a 
        0-1 Knapsack problem.  Given a set v, and a target value S, these 
        methods will return a subset of values from within v which sums to S, 
        if such a subset exists.

        See: https://github.com/saltycrane/subset-sum/tree/master/subsetsum
    """
    @staticmethod
    def get_banks_to_leave_open(x_list, target):
        memo = dict()
        result, _ = SubsetSum.g(x_list, x_list, target, memo)
        return (sum(result), result)

    @staticmethod
    def g(v_list, w_list, target_Sum, memo):
        subset = []
        id_subset = []
        for i, (x, y) in enumerate(zip(v_list, w_list)):
            # Check if there is still a solution if we include v_list[i]
            if SubsetSum.f(v_list, i + 1, target_Sum - x, memo) > 0:
                subset.append(x)
                id_subset.append(y)
                target_Sum -= x
        return subset, id_subset

    @staticmethod
    def f(v_list, i, target_Sum, memo):
        if i >= len(v_list):
            return 1 if target_Sum == 0 else 0
        if (i, target_Sum) not in memo:    # <-- Check if value has not been calculated.
            count = SubsetSum.f(v_list, i + 1, target_Sum, memo)
            count += SubsetSum.f(v_list, i + 1, target_Sum - v_list[i], memo)
            memo[(i, target_Sum)] = count  # <-- Memoize calculated result.
        return memo[(i, target_Sum)]       # <-- Return memoized value.
