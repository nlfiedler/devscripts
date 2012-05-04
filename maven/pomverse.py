#!/usr/bin/env python
#
# Python script that scans a directory tree looking for Maven pom files
# (named pom.xml) and displaying the versions of the artifacts both
# defined in, as well as depended on, by that pom file.
#

import os
import os.path
import sys
from xml.etree.ElementTree import ElementTree

global_props = dict()


def parse_pom(filename):
    """
    Parse the pom file looking for dependencies, and displaying them
    with any parameter references resolved, if possible.
    """
    with open(filename) as pom:
        tree = ElementTree()
        doc = tree.parse(pom)
        propsTag = doc.find("{http://maven.apache.org/POM/4.0.0}properties")
        props = dict()
        if propsTag is not None:
            for elem in propsTag.getiterator():
                idx = elem.tag.rfind('}')
                props[elem.tag[idx + 1:]] = elem.text
                if "properties" in props:
                    del props["properties"]
            global_props.update(props)

        def resolve_var(var):
            while var.startswith("${"):
                name = var[2:-1]
                if name in global_props:
                    var = global_props[name]
                else:
                    break
            return var

        def get_art_vers(elem):
            versTag = elem.find("{http://maven.apache.org/POM/4.0.0}version")
            if versTag is not None:
                version = resolve_var(versTag.text)
            else:
                version = "*"
            artTag = elem.find("{http://maven.apache.org/POM/4.0.0}artifactId")
            if artTag is None:
                print >> sys.stderr, "missing %s/artifact tag" % elem.tag
            artifact = artTag.text
            return (artifact, version)

        (pomArtifact, pomVersion) = get_art_vers(doc)
        if pomVersion == "*":
            print >> sys.stderr, "missing project/version tag"
        parentTag = doc.find("{http://maven.apache.org/POM/4.0.0}parent")
        if parentTag is not None:
            (artifact, version) = get_art_vers(parentTag)
            print "{}/{} parent is {}/{}".format(
                pomArtifact, pomVersion, artifact, version)

        def print_depends(elem):
            dps = elem.find("{http://maven.apache.org/POM/4.0.0}dependencies")
            if dps is not None:
                print_depends(dps)
                for elem in dps.findall("{http://maven.apache.org/POM/4.0.0}dependency"):
                    (artifact, version) = get_art_vers(elem)
                    print "{}/{} depends on {}, {}".format(
                        pomArtifact, pomVersion, artifact, version)

        print_depends(doc)
        dpmTag = doc.find("{http://maven.apache.org/POM/4.0.0}dependencyManagement")
        if dpmTag is not None:
            print_depends(dpmTag)


def main():
    # If argument is given, use that as top directory; otherwise use cwd.
    if len(sys.argv) > 1:
        cwd = sys.argv[1]
    else:
        cwd = os.getcwd()
    # Walk the directory tree looking for pom files that are not in
    # source control directories.
    for root, dirs, files in os.walk(cwd):
        for name in files:
            if name == "pom.xml":
                parse_pom(os.path.relpath(os.path.join(root, name)))
        if '.svn' in dirs:
            dirs.remove('.svn')
        elif '.hg' in dirs:
            dirs.remove('.hg')
        elif '.git' in dirs:
            dirs.remove('.git')

if __name__ == "__main__":
    main()
