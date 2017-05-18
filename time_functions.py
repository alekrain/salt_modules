# =============================================================================
# SaltStack Execution Module
#
# NAME: _modules/time_functions.py
# VERSION: 0.1
# DATE  : 2016.08.03
#
# PURPOSE: Some basic time functions
#
# CHANGE LOG:
#
# NOTES:
#

import time
import datetime


def get_local_time():
    '''
    Get the time and display it in localized form using YYYY-MM-DD hh:mm:ss.ssssss format.

    .. code-block:: bash

        salt '*' time_functions.get_local_time
    '''
    return str(datetime.datetime.now())


def get_utc_time():
    '''
    Get the time and display it in UTC form using YYYY-MM-DD hh:mm:ss.ssssss format.

    .. code-block:: bash

        salt '*' time_functions.get_utc_time
    '''
    return str(datetime.datetime.utcnow())


def get_local_epoch_time():
    '''
    Get the time and display it in localized seconds since epoch.

    .. code-block:: bash

        salt '*' time_functions.get_epoch_time
    '''
    d = datetime.datetime.now()
    return int(time.mktime(d.timetuple()))


def get_utc_epoch_time():
    '''
    Get the time and display it in UTC seconds since epoch.

    .. code-block:: bash

        salt '*' time_functions.get_epoch_time
    '''
    d = datetime.datetime.utcnow()
    return int(time.mktime(d.timetuple()))
