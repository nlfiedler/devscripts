#!/usr/bin/env python
#
# Python script to clean up old shelved Perforce changes owned by the current
# user. Use -h to display usage information. This script requires the P4Python
# library to be installed. See http://www.perforce.com/product/components/apis
#

import argparse
from datetime import datetime, timedelta
import sys
import P4


def delete_changes(p4, args, user):
    """Delete the shelved changes owned by the current user.

    Keyword arguments:
    p4    -- Perforce API
    args  -- command line arguments
    user  -- Perforce user object
    """
    for change in p4.iterate_changes('-u', user['User'], '-s', 'shelved'):
        try:
            date = datetime.strptime(change['Date'], '%Y/%m/%d %H:%M:%S')
        except ValueError:
            sys.stderr.write('failed to parse date {} in change {}'.
                format(change['Date'], change['Change']))
        week_ago = datetime.now() - timedelta(7)
        if date <= week_ago or args.all:
            if args.delete:
                p4.delete_shelve(change['Change'])
                print "Deleted change {}".format(change['Change'])
            else:
                print "p4 shelve -dc {}".format(change['Change'])
        else:
            print "Ignoring recent change {}".format(change['Change'])


def main():
    """Parse command line arguments and do the work.
    """
    desc = '''Removes old shelved changes owned by the current user.
    By default, nothing is removed unless -y is passed (a la obliterate).
    Any changes made in the last week will be retained, unless -a is given.
    '''
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument("-a", "--all", action="store_true",
                        help="remove all shelved changes, even recent ones")
    parser.add_argument("-y", "--delete", action="store_true",
                        help="perform the deletion")
    args = parser.parse_args()

    try:
        p4 = P4.P4()
        p4.connect()
        user = p4.fetch_user()
        if user:
            delete_changes(p4, args, user)
            if not args.delete:
                print("This was report mode. Use -y to remove changes.")
        else:
            sys.stderr.write("Cannot retrieve current Perforce user\n")
    except P4.P4Exception, e:
        sys.stderr.write("error: p4 action failed: {}\n".format(e))


if __name__ == '__main__':
    main()
