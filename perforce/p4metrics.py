#!/usr/bin/env python3.3
"""Report jobs resolved, change count, customer issues fixed."""

import argparse
from collections import defaultdict
import re
import sys

import P4

# Permit loose pattern matching -- case insensitive, optional space before
# ':' '^Jobs:' '^jobs:'  '^Jobs :' '^jobs :' '^JOBS :'
JOB_REX = re.compile(r'^[jJ][oO][bB][sS] ?:')


class P4Changelist:

    """A changelist, as reported by p4 changes."""

    def __init__(self):
        """Construct instance of P4Changelist."""
        self.change = None
        self.description = None
        self.user = None
        self.time = None

    @staticmethod
    def create_using_changes(vardict):
        """Create a P4Changelist from the output of p4 changes."""
        cl = P4Changelist()
        cl.change = int(vardict["change"])
        cl.description = vardict["desc"]
        cl.user = vardict["user"]
        cl.time = int(vardict["time"])
        return cl


class ChangesHandler(P4.OutputHandler):

    """OutputHandler for p4 changes, passes changelists to callback function."""

    def __init__(self, callback):
        """Construct instance of ChangesHandler."""
        P4.OutputHandler.__init__(self)
        self.callback = callback

    def outputStat(self, h):
        """Grab clientFile from fstat output."""
        change = P4Changelist.create_using_changes(h)
        self.callback(change)
        return P4.OutputHandler.HANDLED


def extract_jobs(desc):
    """Scan the commit description looking for fixed jobs.

    :return: list, or None if no jobs found

    """
    if not desc:
        return None
    lines = desc.splitlines()
    for i in range(0, len(lines)):
        line = lines[i].strip()
        m = JOB_REX.match(line)
        if m:
            jobs = []
            line = line[m.span()[1]:]
            if line:
                jobs.append(line.strip())
            for i in range(i + 1, len(lines)):
                line = lines[i].strip()
                if not line or ' ' in line or ':' in line:
                    # reached the end of the job identifiers
                    break
                # whatever is left of the line is a job identifier
                jobs.append(line)
            return jobs
    return None


def first_dict(result_list):
    """Return the first dict from a p4 result list."""
    for e in result_list:
        if isinstance(e, dict):
            return e
    return None


def process_changes(p4, username, after_change):
    """Collect metrics from the changes."""
    change_count = 0
    all_jobs = list()

    def callback(changelist):
        """Process the given list."""
        nonlocal change_count
        change_count += 1
        jobs = extract_jobs(changelist.description)
        if jobs:
            all_jobs.extend(jobs)

    cmd = ["changes", "-l", "-u", username]
    if after_change:
        cmd.append("-e")
        cmd.append(after_change)
    handler = ChangesHandler(callback)
    with p4.using_handler(handler):
        p4.run(cmd)

    job_counts = defaultdict(int)
    customer_issues = 0
    for job in all_jobs:
        r = p4.run(['job', '-o', job])
        if isinstance(r, list):
            job_spec = first_dict(r)
            if 'CallNumbers' in job_spec or 'Customers' in job_spec:
                customer_issues += 1
            job_type = job_spec['Type']
            job_counts[job_type] += 1

    print("Changes: {}".format(change_count))
    for job_type, count in job_counts.items():
        print("{}(s): {}".format(job_type, count))
    print("Customer issues: {}".format(customer_issues))


def main():
    """Run P4 commands to collect metrics."""
    desc = """Examine p4 changes and jobs to report metrics."""
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument('--after', type=int,
                        help="select changes after (and including) the given change")
    args = parser.parse_args()
    p4 = P4.P4()
    p4.connect()
    user = p4.fetch_user()
    if user:
        process_changes(p4, user["User"], args.after)
    else:
        sys.stderr.write("Cannot retrieve current Perforce user\n")


if __name__ == "__main__":
    main()
