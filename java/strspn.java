/*
 * Copyright (C) 2007-2009 Nathan Fiedler
 *
 * $Id$
 */

/**
 * Finds the length of the string prefix that matches the 'accept'
 * character set.
 *
 * Cavaets: does not take character collation into account.
 * Runtime: O(n*m) ?
 *
 * @author  Nathan Fiedler
 */
public class strspn {

    public static int accept(String s, String accept) {
        boolean failed = false;
        int ii = 0;
        while (!failed && ii < s.length()) {
            int match = 0;
            for (int jj = 0; jj < accept.length(); jj++) {
                if (s.charAt(ii) == accept.charAt(jj)) {
                    match++;
                }
            }
            if (match == 0) {
                break;
            }
            ii++;
        }
        return ii;
    }

    public static void main(String[] args) {
        String tests[] = {
            "this is a string",
            "hist ",
            "string",
            "str",
            "string",
            "rts",
            "string",
            "rst",
            "gnirts",
            "rst",
        };
        for (int ii = 0; ii < tests.length; ii += 2) {
            int p = accept(tests[ii], tests[ii + 1]);
            if (p == 0) {
                System.out.println("No matches for " + tests[ii] + " and " +
                                  tests[ii + 1]);
            } else {
                String s = tests[ii].substring(0, p);
                System.out.println("'" + s + "' contains " + tests[ii + 1] +
                                  " (" + p + " characters)");
            }
        }
    }
}
