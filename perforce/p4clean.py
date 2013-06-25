#!/usr/bin/env python3
#
# Python script to clean up old shelved and/or pending Perforce changes owned
# by the current user. Use -h to display usage information. This script
# requires the P4Python library to be installed. See
# http://www.perforce.com/product/components/apis
#

import argparse
from datetime import datetime, timedelta
import sys
import P4


def delete_changes(p4, args, user, status='shelved'):
    """Delete the shelved or pending changes owned by the current user.

    Keyword arguments:
    p4 -- Perforce API
    args -- command line arguments
    user -- Perforce user object
    status -- the change status to query for (e.g. 'shelved', 'pending')
    """
    week_ago = datetime.now() - timedelta(7)
    for change in p4.iterate_changes('-u', user['User'], '-s', status):
        try:
            date = datetime.strptime(change['Date'], '%Y/%m/%d %H:%M:%S')
        except ValueError:
            sys.stderr.write('failed to parse date {} in change {}'.format(
                change['Date'], change['Change']))
        if date <= week_ago or args.all:
            if args.delete:
                try:
                    if status == 'shelved':
                        p4.delete_shelve(change['Change'])
                    elif status == 'pending':
                        p4.delete_change(change['Change'])
                    print("Deleted change {}".format(change['Change']))
                except P4.P4Exception as e:
                    print("Error removing {}: {}".format(change['Change'], e))
            else:
                print("p4 shelve -dc {}".format(change['Change']))
        else:
            print("Ignoring recent change {}".format(change['Change']))


def main():
    """Parse command line arguments and do the work.
    """
    desc = '''Removes old shelved or pending changes owned by the current user.
    By default, nothing is removed unless -y is passed (a la obliterate).
    Any changes made in the last week will be retained, unless -a is given.
    '''
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument("-a", "--all", action="store_true",
                        help="remove all shelved changes, even recent ones")
    parser.add_argument("-p", "--pending", action="store_true",
                        help="select for pending changes (vs. shelved)")
    parser.add_argument("-y", "--delete", action="store_true",
                        help="perform the deletion")
    parser.add_argument("-c", "--client", metavar="CLIENT",
                        help="perform the deletion")
    args = parser.parse_args()

    try:
        p4 = P4.P4()
        if args.client:
            p4.client = args.client
        p4.connect()
        user = p4.fetch_user()
        if user:
            if args.pending:
                delete_changes(p4, args, user, 'pending')
            else:
                delete_changes(p4, args, user)
            if not args.delete:
                print("This was report mode. Use -y to remove changes.")
        else:
            sys.stderr.write("Cannot retrieve current Perforce user\n")
    except P4.P4Exception as e:
        sys.stderr.write("error: p4 action failed: {}\n".format(e))


if __name__ == '__main__':
    main()
