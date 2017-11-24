#!/usr/bin/python2.7

import re, os, stat, sys
import codecs
import types
from anytree import Node, RenderTree

INIT_REGEX = r'^\/etc\/(init\.d\/|sysinit\.d\/|rc[\w\d]*\.d\/|rc[\w\d]*\.(sh|local)+)+[a-z]*'
PATH = ['/bin', '/sbin', '/usr/bin', '/usr/sbin', '/usr/local/bin', '/usr/local/sbin']
PROGRAMS = {}

_TEXT_BOMS = (
    codecs.BOM_UTF16_BE,
    codecs.BOM_UTF16_LE,
    codecs.BOM_UTF32_BE,
    codecs.BOM_UTF32_LE,
    codecs.BOM_UTF8,
)


def list_programs():
    global PROGRAMS
    for path in PATH:
        PROGRAMS[path] = os.listdir(path)


def is_binary_file(source_path):
    with open(source_path, 'rb') as source_file:
        initial_bytes = source_file.read(8192)
    return not any(initial_bytes.startswith(bom) for bom in _TEXT_BOMS) and b'\0' in initial_bytes

def list_startup_scripts(path):
    ret = []
    for root, dirs, files in os.walk(path):
        for file in files:
            f = os.path.join(root, file)
            if re.search(INIT_REGEX, f):
                if os.path.islink(f):
                    ret.append(os.path.realpath(f))
                else:
                    ret.append(f)
    return list(set(ret))

def is_executable(path):
    if not os.path.isfile(path): return False
    if os.path.islink(path):
        return os.stat(os.path.realpath(path))[stat.ST_MODE] & (stat.S_IXUSR|stat.S_IXGRP|stat.S_IXOTH)
    return os.stat(path)[stat.ST_MODE] & (stat.S_IXUSR|stat.S_IXGRP|stat.S_IXOTH)

def is_command(command):
    if command == '[': return None
    for path in PROGRAMS:
        for program in PROGRAMS[path]:
            if program == command:
                return '%s/%s' % (path,program)
    return None

def is_duplicate(node, name):
    for child in node.children:
        if child.name == name: return True
    return False

def parse_script(path, parent=None):
    #executables = []
    root_node = Node(path, parent=parent)
    if (not parent and not is_binary_file(path)) or (parent and not path == parent.name and not is_binary_file(path)):
        path_regex = re.compile(r'[\/]+[\/\w\d\.]+$')
        assign_regex = re.compile(r'[=]+[\w\d\_]+$')
        content = open(path, 'r').read()
        for line in content.splitlines():
            if not line.strip().startswith('#'):
                for p in path_regex.findall(line):
                    if is_executable(p) and not is_duplicate(root_node, p):
                        #executables.append(p)
                        #node = Node(p, parent=root_node)
                        parse_script(p, root_node)
                for p in assign_regex.findall(line):
                    command = is_command(p.replace('=', ''))
                    if command and not is_duplicate(root_node, command):
                        parse_script(command, root_node)
                words = line.split(' ')
                for word in words:
                    command = is_command(word)
                    if command and not is_duplicate(root_node, command):
                        #executables.append(command)
                        #node = Node(command, parent=root_node)
                        parse_script(command, root_node)
        #executables = list(set(executables))
        #for child in root_node.children:
        #    if (not parent and not is_binary_file(child.name)) or (parent and not is_binary_file(child.name) and not child.name == parent.name):
        #        if not is_duplicate(root_node, child.name):
        #            parse_script(child.name, root_node)

        #for executable in executables:
        #    if type(executable) is list: executable = executable[0]
        #    if not is_binary_file(executable) and not executable == parent:

        #        executables.append(parse_script(executable, path))
        #return executables
    return root_node





def build_tree(path):
    nodes = []
    list_programs()
    startup_scripts = list_startup_scripts(path)
    for script in startup_scripts:
        nodes.append(parse_script(script))
    return nodes


def main():
    if len(sys.argv) != 2:
        print 'Usage: sfind.py <PATH>'
        exit()
    path = sys.argv[1]
    os.chroot(path)
    nodes = build_tree(path)
    for node in nodes:
        for pre, fill, node in RenderTree(node):
            print("%s%s" % (pre, node.name))

if __name__ == "__main__":
    main()
