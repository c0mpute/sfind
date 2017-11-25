#!/usr/bin/python2.7

import re, os, stat, sys
import codecs
import types
import getopt
from termcolor import colored
import argparse
from anytree import Node, RenderTree, AsciiStyle, Walker

INIT_REGEX = r'etc\/(init\.d\/|sysinit\.d\/|rc[\w\d]*\.d\/|rc[\w\d]*\.(sh|local)+)+[a-z\.\_]*'
PATH = ['/bin', '/sbin', '/usr/bin', '/usr/sbin', '/usr/local/bin', '/usr/local/sbin']
PROGRAMS = {}
TREE = []
w = Walker()

_TEXT_BOMS = (
    codecs.BOM_UTF16_BE,
    codecs.BOM_UTF16_LE,
    codecs.BOM_UTF32_BE,
    codecs.BOM_UTF32_LE,
    codecs.BOM_UTF8,
)

def print_node(node):
    for pre, fill, node in RenderTree(node, style=AsciiStyle()):
            print("%s%s" % (pre, node.name))

def highlight_node(name, node, color='red'):
    for pre, fill, node in RenderTree(node, style=AsciiStyle()):
        if name in node.name:
            start = node.name.find(name)
            end = start + len(name)
            print pre + node.name[:start] + colored(node.name[start:end], color) + node.name[end:]
        else:
            print("%s%s" % (pre, node.name))

def highlight_node_path(name, node_path, color='red'):
    root = None
    for node in node_path:
        root = Node(node.name, parent=root)
    highlight_node(name, root.root, color)


def list_programs():
    global PROGRAMS
    for path in PATH:
        if os.path.isdir(path):
            PROGRAMS[path] = os.listdir(path)

def is_binary_file(source_path):
    with open(source_path, 'rb') as source_file:
        initial_bytes = source_file.read(8192)
    return not any(initial_bytes.startswith(bom) for bom in _TEXT_BOMS) and b'\0' in initial_bytes

def list_startup_scripts(path):
    ret = []
    for root, dirs, files in os.walk(path):
        for file in files:
            f = os.path.join(root, file).replace('.','',1)
            if re.search(INIT_REGEX, f):
                if os.path.islink(f):
                    ret.append(os.path.realpath(f).replace('.','',1))
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
    root_node = Node(path, parent=parent)
    if (not parent and not is_binary_file(path)) or (parent and not path == parent.name and not is_binary_file(path)):
        path_regex = re.compile(r'[\/]+[\/\w\d\.]+$')
        assign_regex = re.compile(r'[=]+[\w\d\_]+$')
        content = open(path, 'r').read()
        for line in content.splitlines():
            line = line.strip()
            if not line.startswith('#'):
                for p in path_regex.findall(line):
                    if is_executable(p) and not is_duplicate(root_node, p) and not p == root_node.name:
                        parse_script(p, root_node)
                for p in assign_regex.findall(line):
                    command = is_command(p.replace('=', ''))
                    if command and not is_duplicate(root_node, command) and not command == root_node.name:
                        parse_script(command, root_node)
                words = line.split(' ')
                for word in words:
                    command = is_command(word)
                    if command and not is_duplicate(root_node, command) and not command == root_node.name:
                        parse_script(command, root_node)
    return root_node

def build_tree(path):
    nodes = []
    list_programs()
    startup_scripts = list_startup_scripts(path)
    for script in startup_scripts:
        nodes.append(parse_script(script))
    return nodes

def search_node(name, node):
    for child in node.children:
        if name in child.name:
            for node_list in w.walk(child, child.root)[0]:
                if name in node_list.name:
                    highlight_node_path(name, node_list.path)
        else:
            search_node(name, child)

def search(name, tree):
    for node in tree:
        if name in node.name:
            highlight_node(name, node)
        else:
            search_node(name, node)




def main():
    global TREE
    parser = argparse.ArgumentParser(description="An argparse example")
    parser.add_argument('-s','--search', help='Search', required=False)
    parser.add_argument('arg', nargs='+')
    parsed = parser.parse_args()
    path = vars(parsed)['arg'][0]

    os.chdir(path)
    os.chroot(path)

    TREE = build_tree('.')
    if vars(parsed)['search']:
        search(vars(parsed)['search'], TREE)
        exit()

    for node in TREE:
        print_node(node)


if __name__ == "__main__":
    main()
