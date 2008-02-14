#!/usr/bin/env ruby
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

# Script to recursively search a directory structure for source files that
# contain a particular expression.

require 'optparse'

# Typical source file extensions.
EXTENSIONS = %w{ .c .java .js .php .pl .pm .py .rb .sh }
# Additional "source" extensions that may be of interest.
#MORE_EXTENSIONS = %w{ .erb .haml .html .rhtml .rxml .xml }
# List of files we always exclude from our search.
EXCLUDES = %w{ . .. .svn .hg vendor }

#
# Perform a line-based grep of the named file, returning true if the
# file contains a line matching the regular expression, and false
# otherwise.
#
def grep(filename, pattern)
  match = false
  File.open(filename) do |file|
    file.each do |line|
      if line.match(pattern)
        match = true
        break
      end
    end
  end
  match
end

#
# Walk the directory tree starting at 'root', performing a grep on all
# files whose extensions are in the EXTENSIONS list.
#
def walk_tree(root, regex, reverse)
  stack = [root]
  while !stack.empty?
    dir = stack.pop
    Dir.foreach(dir) do |filename|
      next if EXCLUDES.include?(filename)
      wholepath = File.join(dir, filename)
      if File.directory?(wholepath)
        stack.push(wholepath)
      else
        ext = File.extname(filename)
        if EXTENSIONS.include?(ext)
          match = grep(wholepath, regex)
          match = reverse ? !match : match
          if match
            puts wholepath
          end
        end
      end
    end
  end
end

case_match = true
reverse = false
show_help = false

# Parse the command line arguments.
opts = OptionParser.new
opts.on('-h', '--help', "Show help for this script.") do |val|
  show_help = true
end
opts.on('-i', '--ignore-case', "Use case-insensitive comparison.") do |val|
  case_match = false
end
opts.on('-v', '--invert-match', "Show files that do _not_ match.") do |val|
  reverse = true
end
rest = opts.parse(*ARGV)

if show_help
  puts opts.to_s
  puts "\nProvide a single regular expression following the options, and this"
  puts "script will find all matching source files, using a line-based grep."
  exit
elsif rest.length != 1
  puts "Please provide exactly one regular expression."
  exit
end

# Perform the search.
regex = rest.pop
unless case_match
  # Make the regular expression case-insensitive.
  regex = /#{regex}/i
end
walk_tree('.', regex, reverse)
