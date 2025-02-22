"""This module handles graph and component tables.
They are discussed in detail in :ref:`pysynphot-appendixc`.

"""
from __future__ import division, print_function

import logging
import numpy as N
from astropy.io import fits as pyfits

#Flag to control verbosity
DEBUG = False


class CompTable(object):
    """Class to handle a :ref:`component table <pysynphot-master-comp>`.

    Parameters
    ----------
    CFile : str
        Component table filename.

    Attributes
    ----------
    name
        Same as input ``CFile``.

    compnames, filenames : array_like
        Values from ``COMPNAME`` and ``FILENAME`` columns in EXT 1.

    Raises
    ------
    TypeError
        No filename given.

    """
    def __init__(self, CFile=None):
        # None is common for various errors.
        # the default value of None is not useful; pyfits.open(None) does not work.
        if CFile is None :
            raise TypeError('initializing CompTable with CFile=None; possible bad/missing CDBS')

        cp = pyfits.open(CFile)

        self.compnames = cp[1].data.field('compname')
        self.filenames = cp[1].data.field('filename')

        # Is this necessary?
        compdict = {}
        for i in range(len(self.compnames)):
            compdict[self.compnames[i]] = self.filenames[i]

        cp.close()
        self.name=CFile


class GraphTable(object):
    """Class to handle a :ref:`graph table <pysynphot-graph>`.

    Parameters
    ----------
    GFile : str
        Graph table filename.

    Attributes
    ----------
    keywords : array_like
        Values from ``KEYWORD`` column in EXT 1, converted to lowercase.

    innodes, outnodes, compnames, thcompnames : array_like
        Values from ``INNODE``, ``OUTNODE``, ``COMPNAME``, and ``THCOMPNAME`` columns in EXT 1.

    primary_area : number
        Value from ``PRIMAREA`` in EXT 0 header, if exists.

    Raises
    ------
    TypeError
        No filename given.

    """
    def __init__(self, GFile=None):
        # None is common for various errors.
        # the default value of None is not useful; pyfits.open(None) does not work.
        if GFile is None :
            raise TypeError('initializing GraphTable with GFile=None; possible bad/missing CDBS')

        gp = pyfits.open(GFile)

        if 'PRIMAREA' in gp[0].header:
            self.primary_area = gp[0].header['PRIMAREA']

        self.keywords = gp[1].data.field('keyword')
        self.innodes = gp[1].data.field('innode')
        self.outnodes = gp[1].data.field('outnode')
        self.compnames = gp[1].data.field('compname')
        self.thcompnames = gp[1].data.field('thcompname')

        # keywords must be forced to lower case (STIS keywords are
        # mixed mode %^&^(*^*^%%%@#$!!!)
        for i in range(len(self.keywords)):
            self.keywords[i] = self.keywords[i].lower()


##        for comp in self.compnames:
##            try:
##                if comp.index('nic') == 0:
##                    print comp
##            except:
##                pass

        # prints components associated with a given keyword
##        i = -1
##        for keyword in self.keywords:
##            i = i + 1
##            if keyword == 'acs':
##                print self.compnames[i]

        gp.close()

    def GetNextNode(self, modes, innode):
        """GetNextNode returns the outnode that matches an element from
        the modes list, starting at the given innode.
        This method isnt actually used, its just a helper method for
        debugging purposes.

        """
        nodes = N.where(self.innodes == innode)

        ## If there's no entry for the given innode, return -1
        if nodes[0].size == 0:
            return -1

        ## If we don't match anything in the modes list, we find the
        ## outnode corresponding the the string 'default'
        defaultindex = N.where(self.keywords[nodes] == 'default')

        if len(defaultindex[0]) != 0:
            outnode = self.outnodes[nodes[0][defaultindex[0]]]

        ## Now try and match one of the strings in the modes list with
        ## the keywords corresponding to the list of entries with the given
        ## innode
        for mode in modes:
            result = self.keywords[nodes].count(mode)
            if result != 0:
                index = N.where(self.keywords[nodes]==mode)
                outnode = self.outnodes[nodes[0][index[0]]]


        ## Return the outnode corresponding either to the matched mode,
        ## or to 'default'
        return outnode

    def GetComponentsFromGT(self, modes, innode):
        """Obtain components from graph table for the given
        observation mode keywords and starting node.

        .. note::

            This prints extra information to screen if
            ``pysynphot.tables.DEBUG`` is set to `True`.

        Parameters
        ----------
        modes : list of str
            List of individual keywords within the observation mode.

        innode : int
            Starting node, usually 1.

        Returns
        -------
        components, thcomponents : list of str
            List of optical and thermal component names.

        Raises
        ------
        KeyError
            No matches found for one of the keywords.

        ValueError
            Incomplete observation mode or unused keyword(s) detected.

        """
        components = []
        thcomponents = []
        outnode = 0
        inmodes=set(modes)
        used_modes=set()
        count = 0
        while outnode >= 0:
            if (DEBUG and (outnode < 0)):
                logging.info("outnode == %d: stop condition"%outnode)

            previous_outnode = outnode

            nodes = N.where(self.innodes == innode)

            # If there are no entries with this innode, we're done
            if nodes[0].size == 0:
                if DEBUG:
                    logging.info("no such innode %d: stop condition"%innode)
                #return (components,thcomponents)
                break

            # Find the entry corresponding to the component named
            # 'default', bacause thats the one we'll use if we don't
            # match anything in the modes list
            defaultindex = N.where(self.keywords[nodes] =='default')

            if 'default' in self.keywords[nodes]:
                dfi=N.where(self.keywords[nodes] == 'default')[0][0]
                outnode = self.outnodes[nodes[0][dfi]]
                component = self.compnames[nodes[0][dfi]]
                thcomponent = self.thcompnames[nodes[0][dfi]]
                used_default=True
            else:
                #There's no default, so fail if you don't match anything
                # in the keyword matching step.
                outnode = -2
                component = thcomponent = None

            # Now try and match something from the modes list
            for mode in modes:

                if mode in self.keywords[nodes]:
                    used_modes.add(mode)
                    index = N.where(self.keywords[nodes]==mode)
                    if len(index[0])>1:
                        raise KeyError('%d matches found for %s'%(len(index[0]),mode))
                    idx=index[0][0]
                    component = self.compnames[nodes[0][idx]]
                    thcomponent = self.thcompnames[nodes[0][idx]]
                    outnode = self.outnodes[nodes[0][idx]]
                    used_default=False

            if DEBUG:
                logging.info("Innode %d  Outnode %d  Compname %s"%(innode, outnode, component))
            components.append(component)
            thcomponents.append(thcomponent)


            innode = outnode

            if outnode == previous_outnode:
                if DEBUG:
                    logging.info("Innode: %d  Outnode:%d  Used default: %s"%(innode, outnode,used_default))
                count += 1
                if count > 3:
                    if DEBUG:
                        logging.info("same outnode %d > 3 times: stop condition"%outnode)
                    break

        if (outnode < 0):
            if DEBUG:
                logging.info("outnode == %d: stop condition"%outnode)
            raise ValueError("Incomplete obsmode %s"%str(modes))


        #Check for unused modes
        if inmodes != used_modes:
            unused=str(inmodes.difference(used_modes))
            raise ValueError("Warning: unused keywords %s"%unused)

        return (components,thcomponents)
