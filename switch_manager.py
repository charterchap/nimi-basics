#!/usr/bin/env python3
"""
author Jeff Charter Chapman
"""
import sys
import numpy as np
import pandas as pd
import niswitch

import logging
log = logging.getLogger(__name__)


class SwitchManager:
    """
    wrapper around national instruments nimi-python niswitch to simplify use of 
    a PXI switch matrix.
    """

    def __init__(self, device="PXI1Slot8", topo="2531/1-Wire 8x64 Matrix"):
        self.device=device
        self.topology=topo
        self.cols, self.rows = self.getChannels()


    def getChannels(self):
        """
        returns 2 lists of all valid (columns, rows)
        returns 'r1', 'c1' style names
        """
        with niswitch.Session(self.device,
                              topology=self.topology) as session_matrix:
            channel_names = []
            for i in range(1, 99999):
                try:
                    channel_names.append(session_matrix.get_channel_name(i))
                except niswitch.errors.Error as e:
                    break
            columns = [col for col in channel_names if col.startswith('c')]
            rows = [row for row in channel_names if row.startswith('r')]

            return (columns, rows)


    def getConnections(self, row_slice=(0, None), col_slice=(0, None)):
        """
        returns a pandas DataFrame (it's a matrix w/ names) of the current
        status of all possible connections. Matrix is populate with
        niswitch.PathCapability.value
        so one can do a comparison like: 
            niswitch.PathCapability.PATH_EXISTS.value == getConnections()['c1']['r1']

        to search through only a subset one can use row_slice and col_slice
        it's a bit tricky to get right. on my 8x64 matrix
        getConnections(row_slice=(2,3)) will yield 
                c0  c1  c2  c3  c4  c5  c6  c7  c8  c9 ... c60  c61  c62  c63
            r2   1   1   1   1   1   1   1   1   2   1 ... 1    1    1    1   

        where as getConnections(row_slice=(2,3),col_slice=(60,None)) yields
                c60  c61  c62  c63
            r2    1    1    1    1

        of course you can always just get the whole thing and slice after:

        # print(getConnections()[:'r0'])
          >>>     c0  c1  c2  c3  c4  c5  c6  c7  c8  c9 ... c60  c61  c62  c63
              r0   1   1   1   1   2   1   1   1   1   1 ...   1    1    1    1
        for c in sm.getConnections()[:'r0'].iteritems():
            print(c)

        # print(getConnections()['c62'])
        """

        # create an empty numpy matrix with the expected size
        mat = np.zeros( 
            shape = (
                len(self.rows[row_slice[0]:row_slice[1]]),
                len(self.cols[col_slice[0]:col_slice[1]]) ), 
            dtype='int32' )

        # convert it to a pandas DataFrame
        connections = pd.DataFrame(mat,
                                   columns=self.cols[col_slice[0]:col_slice[1]],
                                   index=self.rows[row_slice[0]:row_slice[1]],dtype=object)

        # get the current state of everything requested
        with niswitch.Session(self.device,
                              topology=self.topology) as session_matrix:
            for r in self.rows[row_slice[0]:row_slice[1]]:
                for c in self.cols[col_slice[0]:col_slice[1]]:
                    state = session_matrix.can_connect(r, c)
                    connections[c][r] = state.value

        return connections


    def clearRow(self, row):
        """
        clear all connections on row. example input for row is 'r1'
        """
        # e.g. 'r1' -> 1, 'r11' -> 11
        row_as_val = int(''.join(filter(str.isdigit, row)))

        row_connections = self.getConnections(row_slice=(row_as_val, row_as_val+1))
        for col in self.cols:
            if niswitch.PathCapability.PATH_EXISTS.value == row_connections[col][row]:
                with niswitch.Session(self.device,
                                      topology=self.topology) as session_matrix:
                    log.debug("disconnecting %s->%s" % (row, col))
                    session_matrix.disconnect(channel1=row, channel2=col)


    def clearCol(self,col):
        """
        clear all connections on col. example input for col is 'c60'
        """
        # e.g. 'c1' -> 1
        col_as_val = int(''.join(filter(str.isdigit, col)))

        col_connections = self.getConnections(
            col_slice=(col_as_val, col_as_val+1))
        for row in self.rows:
            if niswitch.PathCapability.PATH_EXISTS.value == col_connections[col][row]:
                with niswitch.Session(self.device,
                                      topology=self.topology) as session_matrix:
                    log.debug("disconnecting %s->%s" % (row, col))
                    session_matrix.disconnect(channel1=row, channel2=col)


    def connect(self,row,col):
        """
        if connection already there leave, otherwise make it.
        """
        with niswitch.Session(self.device, topology=self.topology) as session_matrix:
            if( not session_matrix.can_connect(channel1=row, channel2=col)
                    == niswitch.PathCapability.PATH_EXISTS ):
                log.debug("connecting %s->%s" % (row, col))
                session_matrix.connect(channel1=row, channel2=col)

    def disconnect(self, row, col):
        """
        analagous to connect()
        if connection not there leave, otherwise disconnect.
        """
        with niswitch.Session(self.device, topology=self.topology) as session_matrix:
            if( session_matrix.can_connect(channel1=row, channel2=col)
                   == niswitch.PathCapability.PATH_EXISTS ):
                log.debug("disconnecting %s->%s" % (row, col))
                session_matrix.disconnect(channel1=row, channel2=col)

    def reset(self):
        # reset switch matrix
        with niswitch.Session(self.device, topology=self.topology, reset_device=True) as session_matrix:
            log.debug("resetting niswitch")

    def disconnect_all(self):
        with niswitch.Session(self.device, topology=self.topology) as session_matrix:
            log.debug("disconnecting all")
            session_matrix.disconnect_all()


if __name__ == "__main__":
    # misc example code
    sm = SwitchManager()
    cols, rows = sm.getChannels()
    print(cols)
    print(rows)
    print(sm.getConnections(row_slice=(2, 3), col_slice=(60, None)))
    print("----")
    # sm.clearRow('r7')
    sm.clearCol('c62')

    # connect 'r7'->'c38'...'r7'->'c63'
    for col in cols[38:]:
        sm.connect('r7',col)

    sm.clearRow('r7')

    print(sm.getConnections())
