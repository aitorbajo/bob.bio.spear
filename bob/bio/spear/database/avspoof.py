#!/usr/bin/env python
# vim: set fileencoding=utf-8 :
# Pavel Korshunov <pavel.korshunov@idiap.ch>
# Wed 18 May 16:43:22 CEST 2016

"""
  AVspoof database implementation of bob.bio.db.BioDatabase interface.
  It is an extension of an SQL-based database interface, which directly talks to AVspoof database, for
  verification experiments (good to use in bob.bio.base framework).
"""

from bob.bio.base.database import BioDatabase
from bob.bio.spear.database import AudioBioFile


class AVspoofBioFile(AudioBioFile):
    def __init__(self, f):
        """
        Initializes this File object with an File equivalent from the underlying SQl-based interface for
        AVspoof database.
        """
        super(AVspoofBioFile, self).__init__(client_id=f.client_id, path=f.path, file_id=f.id)

        self.__f = f


class AVspoofBioDatabase(BioDatabase):
    """
    Implements verification API for querying AVspoof database.
    """

    def __init__(self, **kwargs):
        # call base class constructors to open a session to the database
        super(AVspoofBioDatabase, self).__init__(name='avspoof', **kwargs)

        from bob.db.avspoof.query import Database as LowLevelDatabase
        self.__db = LowLevelDatabase()

        self.low_level_group_names = ('train', 'devel', 'test')
        self.high_level_group_names = ('world', 'dev', 'eval')

    def model_ids_with_protocol(self, groups=None, protocol=None, gender=None):
        groups = self.convert_names_to_lowlevel(groups, self.low_level_group_names, self.high_level_group_names)

        return [client.id for client in self.__db.clients(groups=groups, gender=gender)]

    def objects(self, protocol=None, purposes=None, model_ids=None, groups=None, **kwargs):

        # convert group names from the conventional in verification experiments to the internal database names
        matched_groups = self.convert_names_to_lowlevel(groups, self.low_level_group_names, self.high_level_group_names)

        # this conversion of the protocol with appended '-licit' or '-spoof' is a hack for verification experiments.
        # To adapt spoofing databases to the verification experiments, we need to be able to split a given protocol
        # into two parts: when data for licit (only real/genuine data is used) and data for spoof (attacks are used instead
        # of real data) is used in the experiment. Hence, we use this trick with appending '-licit' or '-spoof' to the
        # protocol name, so we can distinguish these two scenarios.
        # By default, if nothing is appended, we assume licit protocol.
        # The distinction between licit and spoof is expressed via purposes parameters
        # this is the difference in terminology.

        # lets check if we have an appendix to the protocol name
        appendix = None
        if protocol:
            appendix = protocol.split('-')[-1]

        # if protocol was empty or there was no correct appendix, we just assume the 'licit' option
        if not (appendix == 'licit' or appendix == 'spoof'):
            appendix = 'licit'
        else:
            # put back everything except the appendix into the protocol
            protocol = '-'.join(protocol.split('-')[:-1])

        # if protocol was empty, we set it to the grandtest, which is the whole data
        if not protocol:
            protocol = 'grandtest'

        correct_purposes = purposes
        # licit protocol is for real access data only
        if appendix == 'licit':
            # by default we assume all real data
            if purposes is None:
                correct_purposes = ('enroll', 'probe')

        # spoof protocol uses real data for enrollment and spoofed data for probe
        # so, probe set is the same as attack set
        if appendix == 'spoof':
            # by default we return all data (enroll:realdata + probe:attackdata)
            if purposes is None:
                correct_purposes = ('enroll', 'attack')
            # otherwise replace 'probe' with 'attack'
            elif isinstance(purposes, (tuple, list)):
                correct_purposes = []
                for purpose in purposes:
                    if purpose == 'probe':
                        correct_purposes += ['attack']
                    else:
                        correct_purposes += [purpose]
            elif purposes == 'probe':
                correct_purposes = ('attack',)

        # now, query the actual AVspoof database
        objects = self.__db.objects(protocol=protocol, groups=matched_groups, cls=correct_purposes,
                                    clients=model_ids, **kwargs)
        # make sure to return BioFile representation of a file, not the database one
        return [AVspoofBioFile(f) for f in objects]
