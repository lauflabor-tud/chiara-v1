#!/usr/bin/python
"""
:module: chiara.py
:moduleauthor: Moritz Maus <mmaus@sport.tu-darmstadt.de>
:synopsis: The Python part of Chiara Data management

This module provides the data management tool "Chiara".

.. warning::

    THIS MODULE USES INSECURE STRING CONCATENATION FROM PARAMETERS!
    CHANGE THIS ACCORDING TO THE CURSOR.EXECUTE BUILD-IN SECURE METHOD!

TODO: 
    * add metadata in upload process

"""

import os
import sys
import socket
import argparse
import sqlite3
import re
import subprocess
import datetime
import time
import hashlib
from ConfigParser import SafeConfigParser

# Configuration parser
cfg_parser = SafeConfigParser()
cfg_parser.read('../config.ini')
# Set config parameters
chiara_root = cfg_parser.get('server','chiara_root')
port = int(cfg_parser.get('server','port')) # for the chiara "file server"

__version__ = '0.1.1'


class ChiaraError(Exception):
    """
    This is the general exception class when something goes wrong within a
    chiara call - stop the function, close the db connection after rollback,
    and quit.
    """
    def __init__(self, value=''):
        """
        Returns an ChiaraError object which is used to stop inner-level
        functions and tell outer-level functions to clean up (e.g. rollback the
        db and exit). An optional 'value' parameter is the error message that
        might be printed.
        """
        self.value = value
        self.message = value
    def __str__(self):
        return repr(self.value)

def shellquote(s):
    """ escapes a string to be copied into a shell, e.g. as filename"""
    return "'" + s.replace("'", "'\\''") + "'"

def initdb(args):
    """
    initialize the db if not existing
    """
    print 'initializing db'
    if os.path.exists(chiara_root + 'py/chiara.db'):
        print "\nError - chiara.db already exists!"
        print "Remove file manually before continuing"
        return
    db = sqlite3.connect(chiara_root + 'py/chiara.db')
    cur = db.cursor()
    ctbls = []
    ctbls.append("""CREATE TABLE groups (id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT);""")
    ctbls.append("""CREATE TABLE in_group (id INTEGER PRIMARY KEY
    AUTOINCREMENT,
    group_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL);""")
    ctbls.append("""CREATE TABLE users (id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT, admin INTEGER);""")
    ctbls.append("""CREATE TABLE group_access (id INTEGER PRIMARY KEY
    AUTOINCREMENT,
    group_id INTEGER NOT NULL, collection_id INTEGER NOT NULL, modify
    INTEGER);""")
    ctbls.append("""CREATE TABLE user_access (id INTEGER PRIMARY KEY
    AUTOINCREMENT,
    user_id INTEGER NOT NULL, collection_id INTEGER NOT NULL, modify INTEGER);
    """)
    ctbls.append("""CREATE TABLE subscription (id INTEGER PRIMARY KEY
    AUTOINCREMENT, user_id
    INTEGER NOT NULL, collection_id INTEGER NOT NULL, collection_rev INTEGER
    NOT NULL);""")
    ctbls.append("""CREATE TABLE collection (id INTEGER NOT NULL, 
    revision INTEGER NOT NULL,
    name TEXT,
    shortinfo TEXT,
    longinfo TEXT,
    comment TEXT,
    size INTEGER,
    modified DATE,
    hash TEXT,
    PRIMARY KEY(id, revision));""")
    ctbls.append("""CREATE TABLE is_sub (id INTEGER PRIMARY KEY AUTOINCREMENT,
    parent_id INTEGER NOT NULL,
    parent_rev INTEGER NOT NULL,
    child_id INTEGER NOT NULL,
    child_rev INTEGER NOT NULL);""")
    ctbls.append("""CREATE TABLE metadata (id INTEGER PRIMARY KEY
    AUTOINCREMENT,
    collection_id INTEGER NOT NULL,
    collection_rev INTEGER NOT NULL,
    tagname TEXT NOT NULL,
    tagcontent TEXT); """)
    ctbls.append("""CREATE TABLE has_files (id INTEGER PRIMARY KEY
    AUTOINCREMENT,
    file_id INTEGER NOT NULL,
    file_rev INTEGER NOT NULL,
    collection_id INTEGER NOT NULL,
    collection_rev INTEGER NOT NULL);""")
    ctbls.append("""CREATE TABLE files (id INTEGER NOT NULL,
    revision INTEGER NOT NULL,
    name TEXT,
    size INTEGER,
    modified DATE,
    hash TEXT,
    PRIMARY KEY(id, revision));""")

    print "# of tables:", len(ctbls)
    try:
        for cmd in ctbls:
            cur.execute(cmd)
    except sqlite3.OperationalError as err:
        print "error:\n", err.message
        print "\nCommand was: ", cmd
        print "ERRORS OCCURRED - tables not created"
        db.rollback()

    db.commit() 

    
def db_fcn(fn):
    """
    This is a decorator that does all the nice db connecting and cleaning up
    stuff.

    To use it, the function's first argument must be "cur"

    e.g.
    @db_fcn
    def my_fun(cur, args)

    then, you can access this function like this:
    my_fun('x')

    """
    def wrapped(*args, **kwargs):
        if not os.path.exists(chiara_root + 'py/chiara.db'):
            raise ChiaraError, "Chiara DB not initialized!"

        try:
            db = sqlite3.connect(chiara_root + 'py/chiara.db')
            cur = db.cursor()
            fn(cur, *args, **kwargs) # has no return!
            db.commit()
        except sqlite3.OperationalError as err:
            print "SQL error:\n", err.message
            db.rollback()
        except (ValueError, ChiaraError) as err:
            print "Error in program: ", err.message
            db.rollback()
        finally:
            db.close()
    
    # copy docstring of the original function
    doc = ''.join(["<DECORATED WITH db_fcn DECORATOR!>\n", fn.__doc__])
    wrapped.__doc__ = doc
    return wrapped


def userhome(args):
    """
    returns the user's home directory, parsed from the supplied args

    :args:
        args (object-type) : must contain the "user" variable

    :returns:
        homedir (str): a string, delimited with "/", that points to the user's
        home directory
    """

    return ''.join(['../data/', args.user,'/'])

def q_dir(path):
    """
    formats the given path name, that is, remove leading "/" and give trailing
    "/"
    """
    p = path.strip()[:]
    if p.startswith('/'):
        p = p[1:]
    if not p.endswith('/'):
        p += '/'
    return p

def path_to_name(path):
    """
    cutting-out the file or collection name of a 
    given path

    :args:
        path (str): the path of the collection

    :returns:
        name: the name of the collection
    """

    name = path
    
    # remove last /
    if(name.endswith('/')):
        name = name[:len(name)-1]
    # cutting-out from next to last
    if(name.rfind('/') != -1):
        name = name[name.rfind('/')+1:] 
    
    return name 

def get_folder_id(cur, user, folder_list):
    """
    returns the folder ID of the last folder in the list "folder_list"
    
    :args:
        cur (cursor): a SQL database cursor
        user (str): a (valid) username
        folder_list (str): a list of folders to which the user is subscribed.

    :returns:
        id, rev (int) or None, None
    """


    cmd0 = """SELECT collection.id, collection.revision FROM collection JOIN
    subscription ON subscription.collection_id = collection.id AND
    subscription.collection_rev = collection.revision JOIN users ON users.id =
    subscription.user_id WHERE """


    cmd0 += ('collection.name="' + folder_list[0] + '" and users.name="' + user
            + '";')
    #print cmd0
    res = cur.execute(cmd0).fetchone()
    if res is not None:
    #    recursively walk trough the collections in the db
        cid, crev = res
        for subfolder in folder_list[1:]:
            cmd = """SELECT collection.id, collection.revision FROM collection
            JOIN is_sub ON is_sub.child_id = collection.id and is_sub.child_rev
            = collection.revision WHERE """
            cmd += ( ' is_sub.parent_id=' + str(cid) + ' AND' +
                    ' is_sub.parent_rev=' + str(crev) )
            cmd += ' AND collection.name="' + subfolder + '";'
            #print cmd
            res = cur.execute(cmd).fetchone()
            if res is not None:
                cid, crev = res
            else:
                # failure: path not found in collections!
                return None, None
        return cid, crev
    else:
        return None, None


def add_file_to_storage(fpath, fid, frev):
    """
    add file to local storage - but let the file manager do this, it runs under
    another user!

    :args:
        fpath (str): the full path of the file
        fid (int): the file id
        frev (int): the file revision

    """

    try:
        s = socket.socket()
        s.connect(('127.0.0.1', port))
    except socket.error:
        print "failure!"
        print "could not connect to file manager - is server running?"
        raise ChiaraError('could not connect to file manager - is' + 
                'server running?')
    msg = ':'.join(['chiara', 'store', fpath,
        str(fid), str(frev)]) # password - command - file - file_id - file-rev
    MSGLEN = len(msg)
    totalsent = 0
    while totalsent < MSGLEN:
        sent = s.send(msg[totalsent:])
        if sent == 0:
            raise ChiaraError("socket connection broken")
        totalsent = totalsent + sent

    dat = s.recv(1024) # wait for server response
    if dat == '0':
        # server command successful
        pass
    else:
        print "failure!\ncould not store data on server"
        s.shutdown(socket.SHUT_RDWR)
        s.close()
        return
    s.shutdown(socket.SHUT_RDWR)
    s.close()


def load_file_from_storage(fpath, fid, frev):
    """
    load file from local storage - but let the file manager do this, it runs under
    another user!

    :args:
        fpath (str): the full target path of the file
        fid (int): the file id
        frev (int): the file revision

    """

    # connect to the data server
    try:
        s = socket.socket()
        s.connect(('127.0.0.1', port))
    except socket.error:
        print "failure!"
        print "could not connect to file manager - is server running?"
        raise ChiaraError('could not connect to file manager - is' + 
                ' server running?')

    # this is how to send the command
    msg = ':'.join(['chiara', 'get', fpath, str(fid), str(frev)])
    # password - command - file - file_id - file-rev
    MSGLEN = len(msg)
    debug = False #switch: do not actually download data
    if not debug:
        totalsent = 0
        while totalsent < MSGLEN:
            sent = s.send(msg[totalsent:])
            if sent == 0:
                raise ChiaraError("socket connection broken")
            totalsent = totalsent + sent

        dat = s.recv(1024) # wait for server response
        if dat == '0':
            # server command successful
            pass
        else:
            print "result:", dat
            print "failure!\n could  not get data from file server"
            s.shutdown(socket.SHUT_RDWR)
            s.close()
            return False

    s.shutdown(socket.SHUT_RDWR)
    s.close()

def get_hash_list(uname, cname):
    """
    create a list with md5 hashes of all files and directories of the given collection

    :args:
        uname (str): the user name
        cname (str): the collection name
    
    :returns:
        dict: {path : hash}     (e.g. {test/a.txt : ADEF35F23...E3 , test/b.svg : 4F5D398...84})
    """
    hash_list = {}

    # go into the users webfolder
    os.chdir('../data/' + uname)

    # get all file hashes of the respective collection
    file_hashes = {}
    sep = ":sep:"
    for line in os.popen("md5deep -lr " + shellquote(cname) + " | awk '{print $1 " + '"' + sep  + '"' + " substr($0,length($1)+1);}'").read().splitlines():
        sline = line.split(sep)
        file_hashes[sline[1].strip()] = sline[0]

    # actualize hash list
    hash_list.update(file_hashes)

    # get all directory hashes of the respective collection
    dir_names = os.popen("find " + shellquote(cname) + " -type d").read().splitlines()
    for dir in dir_names:
        regex = re.compile(dir)
        fileindir_hashes = []
        for file_name in file_hashes.keys():
            if(regex.match(file_name)):
                fileindir_hashes.append(file_hashes[file_name]) 
        fileindir_hashes.sort() 
        dir_struct_hash = os.popen("du -a " + shellquote(dir) + " | sort -k2 | md5sum | awk {'print $1'}").read()
        fileindir_hashes.append(dir_struct_hash)
        dir_hash = {q_dir(dir) : hashlib.md5(''.join(fileindir_hashes)).hexdigest()}
        # actualize hash list
        hash_list.update(dir_hash)

    # go out of the users webfolder
    os.chdir('../../py')

    # return hash list
    return hash_list

@db_fcn
def useradd(cur, args):
    """
    modifies the user
    """
    cur.execute('SELECT COUNT(*) from users where name="' + args.user + '";')
    res = cur.fetchone()[0]
    if res > 0:
        raise ChiaraError, "User " + args.user + " already exists!"

    cur.execute('SELECT MAX(id) FROM users;')
    res = cur.fetchone()[0]
    if res is None:
        newid = 1
    else:
        newid = res + 1
    if args.admin:
        print "adding user <", args.user, "> with id", newid, " as admin"
    else:
        print "adding user <", args.user, "> with id", newid, " as no admin"
    
    cur.execute('INSERT INTO users (id, name, admin) VALUES (' + str(newid) + ', "' +
            args.user + '", ' + args.admin + ');')


@db_fcn
def userrm(cur, args):
    """
    modifies the user
    """

    res = cur.execute('select id from users where name="' + args.user + '";')
    uid = res.fetchone()
    if uid == None:
        raise ChiaraError, "User " + args.user + " does not exist!"
    else:
        uid = uid[0]

    cur.execute("DELETE FROM subscription WHERE user_id=" + str(uid) + ";")
    cur.execute("DELETE FROM user_access WHERE user_id=" + str(uid) + ";")
    cur.execute("DELETE FROM in_group WHERE user_id=" + str(uid) + ";")
    cur.execute("DELETE FROM users WHERE id=" + str(uid) + ";")

    print 'user ' + args.user + ' deleted'


@db_fcn
def groupadd(cur, args):
    """
    adds a group
    """

    cur.execute('SELECT COUNT(*) from groups where name="' + args.group + '";')
    res = cur.fetchone()[0]
    if res > 0:
        raise ChiaraError, "Group " + args.group + " already exists!"

    cur.execute('SELECT MAX(id) FROM groups;')
    res = cur.fetchone()[0]
    if res is None:
        newid = 1
    else:
        newid = res + 1
    print "adding group <", args.group , "> with id", newid
    cur.execute('INSERT INTO groups (id, name) VALUES (' + str(newid) + ', "' +
            args.group + '");')


@db_fcn
def group_add_user(cur, args):
    """
    adds a user to a group
    """
    
    res = cur.execute('Select count(*) from users where name="' + args.user +
    '";');
    if res.fetchone()[0] == 0:
        raise ChiaraError, "user " + args.user + " unknown"

    res = cur.execute('Select count(*) from groups where name="' + args.group +
    '";');
    if res.fetchone()[0] == 0:
        raise ChiaraError, "group " + args.group + " unknown"

    query =  """ Select count(*) from in_group AS ig JOIN users AS US ON
    ig.user_id = US.id JOIN groups AS GS on GS.id = ig.group_id where GS.name="""
    query += '"' + args.group + '" and US.name = "' + args.user + '";'
    res = cur.execute(query)
    if res.fetchone()[0] > 0:
        raise ChiaraError, ("user " + args.user + " already in group " +
            args.group)

    query =( "INSERT INTO in_group (user_id, group_id) SELECT " + 
        ' users.id, groups.id from users JOIN groups where users.name="' + 
        args.user + '" and groups.name="' + args.group + '" Limit 1;')

    cur.execute(query)

    print "added user " + args.user + ' to group ' + args.group


@db_fcn
def group_rm_user(cur, args):
    """
    removes a user from a group
    """

    # check if user is in group
    query = ("SELECT count(*) FROM in_group WHERE user_id IN (SELECT id FROM" +
            ' users where name="' + args.user +'") AND group_id IN (' +
            ' SELECT id FROM groups where name="' + args.group + '");')
    res = cur.execute(query).fetchone()[0]
    if res == 0:
        raise ChiaraError, "user not in group"
    
    query = ("DELETE FROM in_group WHERE user_id IN (SELECT id FROM" +
            ' users where name="' + args.user +'") AND group_id IN (' +
            ' SELECT id FROM groups where name="' + args.group + '");')

    cur.execute(query)

    print "removed user " + args.user + ' from group ' + args.group


@db_fcn
def list_all_groups(cur, args):
    """
    list all groups
    """

    print 'listing all groups:'
    for row in cur.execute('SELECT id, name from groups ORDER BY id;'):
        print str(row[0]) + '\t' + str(row[1])

@db_fcn
def list_all_users(cur, args):
    """
    lists all users"
    """

    print 'listing all users:'
    for row in cur.execute('SELECT id, name, admin from users ORDER BY id;'):
        print str(row[0]) + '\t' + str(row[1] + '\t' + str(row[2]))

@db_fcn
def list_group(cur, args):
    """
    lists all users in the group
    """
    
    print 'listing all users of group ' + args.group
    
    for row in cur.execute('SELECT users.id, users.name from users JOIN ' + 
            'in_group ON in_group.user_id = users.id JOIN groups ON ' +
            'groups.id = in_group.group_id WHERE groups.name = "' + args.group
            + '";'):
        print str(row[0]) + '\t' + str(row[1])


@db_fcn
def list_user(cur, args):
    """
    lists all groups the user is in
    """
    
    print "listing all groups of user " + args.user

    for row in cur.execute('SELECT groups.id, groups.name from users JOIN ' + 
            'in_group ON in_group.user_id = users.id JOIN groups ON ' +
            'groups.id = in_group.group_id WHERE users.name = "' + args.user
            + '";'):
        print str(row[0]) + '\t' + str(row[1])

@db_fcn
def grouprm(cur, args):
    """
    deletes a group
    """

    res = cur.execute('select id from groups where name="' + args.group + '";')
    uid = res.fetchone()
    if uid == None:
        raise ChiaraError, "group " + args.group + " does not exist!"
    else:
        uid = uid[0]
        cur.execute("DELETE FROM group_access WHERE group_id=" + str(uid) + ";")
        cur.execute("DELETE FROM in_group WHERE group_id=" + str(uid) + ";")
        cur.execute("DELETE FROM groups WHERE id=" + str(uid) + ";")

    print 'group ' + args.group + ' deleted'

@db_fcn
def add_dir_to_collection(cur, args, allowInvalidInfo=False):
    """
    adds a directory to the collection

    :args:
        args (object): the arguments, parsed by the argument parser. Any object
        with an 'add' element (str, representing the directory to be added) is
        valid.

        allowInvalidInfo (bool): If true, no valid info.txt-file in the
        directory is required. This is important for recursive uploads.

    :returns:
        (None)

    """
    uname = args.user
    cupath = args.add   
    cname = path_to_name(cupath)

    directory = userhome(args) + q_dir(cupath)
    if not os.path.exists(directory + 'info.txt'):
        print "failure!\nNo info.txt found"
        return

    si, li, tags, success = parse_info(directory + 'info.txt')
    if not success:
        print "failure!\ninfo.txt is invalid"
        raise ChiaraError, "invalid info.txt"

    # get current time
    cur_time = int(time.time())

    # get hash list of the collection
    hash_list = get_hash_list(uname, cname)
    # walk through the directory
    IsTopFolder=True
    for cpath, dirs, files in os.walk(directory):
    # walks guarantees a top-down approach (required for here!)
        # each directory should end with "/"
        try:
            si, li, tags, info_success = parse_info(q_dir(cpath) + 'info.txt')
        except IOError:
            info_success = False

        curpath = cpath[:]
        if curpath[-1] != '/':
            curpath += '/'
        upath = curpath[len(userhome(args)):]
        parents = upath.split('/')[:-2] # last is an empty string!
        cname = upath.split('/')[-2]
        chash = hash_list[q_dir(cpath[len(userhome(args)):])]
        #print 'folder: ' + curpath
        print 'data path: ' + upath + ' (as "' + cname + '")'
    #        print 'collection name: ' + cname
        #print ('parents: ' + '|'.join(parents) + ' (' + str(len(parents)) 
        #        + ' total)')
        if len(parents) > 0:
            parent_id, parent_rev = get_folder_id(cur, uname, parents)
            if parent_id == None:
                print "failure!\ncannot get parent folder id"
                continue
        #print '\n\t', '\n\t'.join(files)
        #print '\n'
        
        maxreps = 100 # 100 repetitions if a collection id cannot be obtained.
        reps = 0
        cid = None
        crev = 1
        # get size of the current directory
        shell_cmd = "du -bs " + shellquote(curpath) + " | awk '{print $1}'"
        csize = os.popen(shell_cmd).read()
        ## get last modified date of the current directory
        #shell_cmd = "stat -c %Y " + curpath
        #cdate = os.popen(shell_cmd).read()

        while reps < maxreps and cid == None:
            reps += 1
            cid = get_blank_cid(cur, uname, cname, csize, cur_time, chash, subscribe=info_success)
        if cid == None:
            print "failure!\ncannot get empty collection id"
            raise ChiaraError("Problem with databse - cannot get"+
                " empty collection id")
        # cid is ID of current collection!
        if info_success:
            print "(subscription added)"
            IsTopFolder = False
        # add metadata to database 
        if info_success:
            cur.execute("""UPDATE collection SET shortinfo=?, longinfo=?
            WHERE id=? AND revision=1;""", (si, li, cid))
            cur.executemany("""INSERT INTO metadata (collection_id,
            collection_rev, tagname, tagcontent) VALUES (?,?,?,?) """, [[cid,
                1] + tag for tag in tags]) 


        #si, li, tags, success = parse_info(directory + 'info.txt')

        if len(parents) > 0:
            cur.execute('INSERT INTO is_sub (parent_id, parent_rev, child_id,'
                    + ' child_rev) VALUES ' + '(?,?,?,?);', (parent_id,
                        parent_rev, cid, 1))

        # now: add files!

        for locfile in files:
            fullname = curpath + locfile # escaping is not required here!
              
            # get size of the current file
            shell_cmd = "du -b " + shellquote(fullname) + " | awk '{print $1}'"
            fsize = os.popen(shell_cmd).read()
            ## get last modified date of the current file
            #shell_cmd = "stat -c %Y " + fullname
            #fdate = os.popen(shell_cmd).read()

            # get hash of the file
            fhash = hash_list[upath + locfile]
            
            fid = get_blank_fid(cur, locfile, cid, crev, fsize, cur_time, fhash)

            # add file to local storage
            add_file_to_storage(fullname, fid, 1)

    print "\nsuccess"

def get_blank_fid(cur, name, cid, crev, fsize, fdate, fhash):
    """
    returns a file id that is linked to collection cid, revision crev

    :args:
        cur (cursor): a SQL database cursor
        name (str): name of the file
        cid (int): collection id
        crev (int): revision of the collection

    :returns:
        fid (int) or None if unsuccessful
    """

    max_id = cur.execute('SELECT MAX(id) FROM files;').fetchone()[0]
    if max_id == None:
        max_id = 1
    else:
        max_id += 1
    try:
        cur.execute('INSERT into files (id, revision, name, size, modified, hash) VALUES' +
                '(?,?,?,?,?,?)', (max_id, 1, name, fsize, fdate, fhash))
        cur.execute('INSERT into has_files (file_id, file_rev, collection_id,' + 
        'collection_rev) VALUES (?,?,?,?);', (max_id, 1, cid, crev));
        return max_id
    except sqlite3.IntegrityError:
        return None

def get_blank_cid(cur, user, name, csize, cdate, chash, subscribe=False):
    """
    returns an empty collection that belongs to "user"

    :args:
        cur (cursor): a SQL database cursor
        user: the username
        name: name of the collection
    """

    uid = cur.execute('SELECT id FROM users WHERE name="' + user +
        '" LIMIT 1;').fetchone()[0]
    max_id = cur.execute('SELECT MAX(id) FROM collection;').fetchone()[0]
    if max_id == None:
        max_id = 1
    else:
        max_id += 1
    try:
        cur.execute('INSERT into collection (id, revision, name, comment, size, modified, hash) VALUES' +
                '(?,?,?,?,?,?,?)', (max_id, 1, name, 'Add collection to the repository.', csize, cdate, chash))
        if subscribe:
            cur.execute('INSERT into subscription (user_id, collection_id,' + 
            'collection_rev) VALUES (?,?,?);', (uid, max_id, 1));
        cur.execute('INSERT INTO user_access (user_id, collection_id, modify)'
                + ' VALUES (?,?, 1);', (uid, max_id))
    except sqlite3.IntegrityError:
        return None

    return max_id

def parse_info(filename):
    """
    tries to parse the information file.
    
    :args:
        filename (str): the name of the file to parse, including the directory.

    :returns:
        (shortinfo (str), longinfo(str), tags(list), success)
    """
    shortinfo = []
    longinfo = []
    tags = []
    stage = 0 # stages: 0: shortinfo, 1 : longinfo 2: tags
    with open(filename, 'r') as f:
        for line in f:
            if stage == 0:
    # add all data to shortinfo
                if line.lower().strip().startswith('### details ###'):
                    stage = 1;
                else:
                    shortinfo.append(line)
            elif stage==1:
    # add all data to longinfo
                if line.lower().strip().startswith('### tags ###'):
                    stage = 2;
                else:
                    longinfo.append(line)
            elif stage==2:
    # parse tags
                parts = line.split(':')
                if len(parts) > 1:  # only if line is in format "tag: value"
                    tagname = parts[0].strip()
                    if len(tagname) > 0:
                        fulltagcontent = ':'.join(parts[1:]).strip()
                        for tagcontent in fulltagcontent.split(','):
                            tags.append([tagname, tagcontent.strip()])
            else:
    # should not be possible to reach
                raise NotImplementedError, "Internal error in program"

    if stage==2:
        shortinfo = ''.join(shortinfo)
        longinfo = ''.join(longinfo)
        return (shortinfo, longinfo, tags, True)
    else:
        return (None, None, None, False)

@db_fcn
def unsubscribe_by_folder(cur, args):
    """
    This function removes the collection, identified by folder name, from the
    subject's collections.

    :args:
        args (object): parsed argument, must contain .user and .unsubscribe
    """
    # permissions are not altered!
    qdir = q_dir(args.unsubscribe)
    folders = qdir.split('/')[:-1]
    if len(folders) == 0:
        print "failure!\ncannot unsubscribe base folder"
        return

    cid, crev = get_folder_id(cur, args.user, folders)
    if cid == None:
        print ("failure!\nFolder " + qdir + " not in " + args.user + "'s" + 
            "collections.")
        return
    cmd = ("DELETE FROM subscription WHERE collection_id=" + str(cid) + 
            " AND collection_rev=" + str(crev) + " AND user_id IN (SELECT " +
            'id FROM users WHERE name="' + args.user + '");')
    cur.execute(cmd)
    print "success!\nunsubscribed from collection '" + qdir + "'<br />\n"

@db_fcn
def unsubscribe_by_id(cur, args):
    """
    This function removes the collection, identified by ID and revision, from the
    subject's collections.

    :args:
        args (object): parsed argument, must contain .user and .unsubscribe_id
    """
    # permissions are not altered!
#    if not '-' in args.unsubscribe_id:
#        print "failure!"
#        print "The collection to unsubscribe from must be given in 'id-rev' ",
#        print "format"
#        raise ChiaraError('parameter format failure')
#
#    cid, crev = args.unsubscribe_id.split('-')
#    if not (cid.isdigit() and crev.isdigit()):
#        print "failure!"
#        print """The collection to unsubscribe from must be given in 'id-rev' 
#            format"""
#        raise ChiaraError('parameter format failure')

    user, cid, crev = parse_UCR(args, 'unsubscribe_id')

    cmd = ("DELETE FROM subscription WHERE collection_id=" + str(cid) + 
            " AND collection_rev=" + str(crev) + " AND user_id IN (SELECT " +
            'id FROM users WHERE name="' + args.user + '");')
    cur.execute(cmd)
    print ("success!\nunsubscribed from collection #" + str(cid) + " rev. " +
        str(crev) + "<br />\n")

@db_fcn
def user_view_collection(cur, args, MaxInfoLen=200):
    """
    This function returns a list of the collections the user has subscribed to.
    This list is separated by blank lines.
    Each line is separated by tabs into three fields:
    Infotag - id - revision - collection name - shortinfo
    
    Line breaks are changed into "<BR />"

    Infotags can be:
        * m : user can manage collection
        * r : user can read collection

    :args:
        args (object): parsed argument, must contain .user and .unsubscribe
        MaxInfoLen (int): cut the "short info" of a collection to at most this
            length in bytes

    """

    # in words: (1) look all subscribed collection id's.
    # create a view where all (user_id, collection_id, access) - pairs are collected for
    # that user, looking both in group access and person access
    # join both tables
#    sqlquery = """
#        SELECT MAX(ua.write), s.collection_id, s.collection_rev,
#               c.name, c.shortinfo
#          FROM subscription AS s 
#          JOIN users AS u
#            ON u.id = s.user_id
#          JOIN (SELECT CASE WHEN ua.modify THEN 1 ELSE 0 END AS write,
#                  ua.collection_id, ua.user_id FROM user_access as ua UNION
#                  SELECT CASE WHEN ga.modify THEN 1 ELSE 0 END AS write,
#                    ga.collection_id, ga.group_id FROM group_access as ga 
#                      JOIN in_group ON ga.group_id=in_group.group_id
#                      JOIN users ON in_group.user_id = users.id) AS ua
#            ON ua.user_id = s.user_id 
#          JOIN collection AS c ON c.id=s.collection_id AND 
#              c.revision=s.collection_rev
#          WHERE u.name=?
#          GROUP BY s.collection_id, s.collection_rev; """
#    cur.execute(sqlquery, (args.user,))
    
    SQLQuery = """ 
        SELECT s.collection_id, s.collection_rev, c.name, c.shortinfo 
        FROM subscription AS s 
          JOIN users AS u ON u.id = s.user_id
          JOIN collection AS c ON c.id = s.collection_id AND c.revision =
              s.collection_rev
        WHERE u.name=:user 
        GROUP BY s.collection_id, s.collection_rev; """

    for res in cur.execute(SQLQuery, {'user' : args.user}).fetchall():
        parts = []
        if has_access(cur, args.user, res[0]) == 2:
            parts.append('m')
        else:
            parts.append('r')
        parts.extend([str(x) for x in res[:3]])
        parts.append(str(res[3])[:MaxInfoLen].replace('\r\n','\n').replace('\n','<br />'))
        print '\t'.join(parts)

#    for res in cur:
#        parts = []
#        if bool(res[0]):
#            print 'positive: |', res[0] , '|'
#            parts.append('m')
#        else:
#            parts.append('r')
#        parts.extend([str(x) for x in res[1:4]])
#        parts.append(str(res[4])[:MaxInfoLen].replace('\r\n','\n').replace('\n','<br />'))
#        print '\t'.join(parts)

@db_fcn
def search_collections(cur, args):
    """
    Searches for collections that are accessible to the user and match the
    specified search criteria.

    Note: *only* collections that contain metadata will be searched!
    """
    # first: parse args
    user = args.user
    # strip at least the most dangerous SQL insertion characters
    desc = args.search[0].strip().replace(';','').replace('#','')
    desc = desc.replace('(','').replace(')','')
    tags = args.search[1]
    #parse tags: format is either tagname: tag value; tagname: tag value; ...
    # value could also be a comma-separated list
    formattype = 1
    if ';' in tags or ':' in tags:
        all_tags = []
        taglist = tags.split(';')
        for elem in taglist:
            res = elem.split(':')
            if len(res) > 1:
                tagname = res[0].strip()
                rawtagvalue = ''.join(res[1:])
                tagvalues = [x.strip() for x in rawtagvalue.split(',') if
                        len(x.strip()) > 0]
                for tagvalue in tagvalues:
                    all_tags.append([tagname, tagvalue])
    else:
    # or: tagvalue, tagvalue, tagvalue...
        formattype = 2
        taglist = [x.strip() for x in tags.split(',') if len(x.strip()) > 0]

    if False: # debug
        if formattype==1:
            print "format type:1<br>\n"
            print '<br />\n'.join([x1 + x2 for x1,x2 in all_tags]) + "<br />\n"
        else:
            print "format type:2<br>\n"
            print '<br />\n'.join(taglist) + "<br />\n"

        print "description: " + desc + "<BR>\n"
        print "\n\n<BR><BR>TODO: put this all in proper sql statements!"
    
    # check stackoverflow: multiple queries or a single query with many joins?
    # or: select count() and check # count with # requirements?
    
    # "inner sql cmd": metadata
    sqlcmd0 = ("SELECT collection_id AS cid, collection_rev AS crev "
        + " from metadata WHERE ")
    InnerQuery = False # use inner query at all?
    ncount = 0
    if formattype == 1:
        for tagname, tagvalue in all_tags:
            sqlcmd0 += (' (tagname LIKE "%' + tagname.strip() + 
            '%" AND tagcontent LIKE "%' + tagvalue.strip() + '%") OR ' )
            InnerQuery = True
            ncount += 1
    elif formattype == 2:
        for tagval in taglist:
            sqlcmd0 += (' tagcontent LIKE "%' + tagval.strip() + '%" OR ')
            InnerQuery = True
            ncount += 1
    sqlcmd0 += ' 0' # just for syntax: the last condition is 
    # "<something> OR 0", so this is always the last condition
    sqlcmd0 += ' GROUP BY cid, crev HAVING ' 
    sqlcmd0 += ' COUNT(DISTINCT tagcontent) = ' + str(ncount) + ' '
    sqlcmd0 += ' AND COUNT(*) = ' + str(ncount) + ' '
    sqlcmd0 += ' AND COUNT(DISTINCT tagcontent) = ' + str(ncount) + ' '

    if False:
        print "<BR>\n"
        print "inner query: ", InnerQuery
        print "<BR>\n"
        print sqlcmd0

    # ONLY TAKE THE COLLECTIONS WITH HIGHEST REVISION
    MaxRevisions =  """ SELECT a.id, a.revision, a.name, a.shortinfo FROM collection AS a
                  JOIN (SELECT id, MAX(revision) max_revision
                  FROM collection Group by id) AS b
                  ON a.id = b.id AND a.revision = b.max_revision
                  order by a.id """

    SQLCmd = "SELECT c.id, c.revision, c.name, c.shortinfo FROM (" + MaxRevisions + ") AS c "
    if InnerQuery:
        SQLCmd += "JOIN ( " + sqlcmd0 + " ) as meta ON meta.cid = c.id AND "
        SQLCmd += "meta.crev = c.revision "

    SQLCmd += ' WHERE c.shortinfo LIKE "%' + desc + '%" ' 
    # DONT'T FORGET TO ADD THE JOIN ON THE PERMISSION TABLE!
    AccessQuery =  """  AND c.id IN (
            SELECT g.collection_id as G_CID FROM  group_access AS g
                WHERE group_id IN
                    (SELECT group_id from in_group JOIN users AS u ON u.id =
                    in_group.user_id AND u.name=""" 
    AccessQuery += '"' + user + '") UNION '
    AccessQuery += """ SELECT ua.collection_id as U_CID FROM user_access AS ua
                    JOIN users AS u ON u.id = ua.user_id WHERE u.name="""
    AccessQuery += '"' + user + '") '
    # ALSO REMOVE EVERY COLLECTION THE USER IS ALREADY SUBSCRIBED TO!
    OwnQuery = " AND c.id NOT IN (SELECT s.collection_id FROM subscription AS s"
    OwnQuery += ' JOIN users AS u ON s.user_id = u.id WHERE u.name="'
    OwnQuery += user + '") LIMIT 50;'
     
    SQLCmd += AccessQuery + OwnQuery

    res = cur.execute(SQLCmd)
    for line in res:
        print '\t'.join(
            [str(x).replace('\t','').replace('\r\n','\n').replace(
                '\n','<BR>')[:200] for x in line])

@db_fcn
def subscribe_by_id(cur, args):
    """
    adds the collection to the user's subscriptions.
    """

    user, cid, crev = parse_UCR(args, 'subscribe')
#    user = args.user
#    if not '-' in args.subscribe:
#        raise ChiaraError(
#            'collection must be given in "id-rev" format, e.g. 26-1')
#    pts = args.subscribe.split('-')
#    cid = pts[0]
#    if len(pts) == 3 and ''.join(pts[1:]) == '1':
#        crev = '-1'
#    else:
#        crev = pts[1]
#    if not (cid.isdigit() and crev.isdigit()):
#        raise ChiaraError(
#            'collection must be given in "id-rev" format, e.g. 26-1')

    # fist: check if user has access
    query = "SELECT " + cid + """ IN (
             SELECT g.collection_id as G_CID FROM  group_access AS g
               WHERE group_id IN (
                 SELECT group_id FROM in_group 
                   JOIN users AS u 
                     ON u.id = in_group.user_id 
                        AND u.name=""" 
    query += '"' + user + '") UNION '
    query += """ SELECT ua.collection_id AS U_CID 
                         FROM user_access AS ua
                            JOIN users AS u 
                              ON u.id = ua.user_id 
                        WHERE u.name="""
    query += '"' + user + '") '
    res = bool(cur.execute(query).fetchone()[0])
    if res:
        # tidy up database - remove all previous (identical) subscriptions
        query = """ DELETE FROM subscription  
                        WHERE collection_id=""" + cid 
        query += ' AND collection_rev=' + crev
        query += ' AND user_id IN (SELECT id FROM users WHERE name="'
        query +=  user + '");'
       # print query
        cur.execute(query)
        # now, insert data
        query = """ INSERT INTO subscription (user_id, collection_id,
            collection_rev) SELECT u.id, """
        query += cid + ", " + crev + ' FROM users u WHERE u.name="'
        query += user + '";'
#        print query
        cur.execute(query)
        print "success!\nAdded collection to " + user + "'s collections."

    else:
        print ("failure!\nAccess to collection " + cid + " forbidden for " +
            user + "!") 
        raise ChiaraError('Access to collection forbidden for user!')

@db_fcn
def download_collection(cur, args):
    """
    loads the data from the collection to the user's home directory.
    """

    user, cid, crev = parse_UCR(args, 'download')
    
    # check if collection exists and user has access to it
    res = has_access(cur, user, cid)
    #print "access:", res
    if not has_access(cur, user, cid):
        raise ChiaraError('User has no access to collection!')

   # first: prepare direcotry structure!
    # get collection's name
    cmd = """SELECT name FROM collection WHERE id=? AND revision=?;"""
    res = cur.execute(cmd,(cid, crev)).fetchone()
    if res is None:
        raise ChiaraError, "(data consistency error) collection not known..."

    name = res[0]
    curr_dir = userhome(args) + name + '/'


    # delete everything that was there before
    shellcmd='rm -rf ' + shellquote(curr_dir)
    res = os.system(shellcmd)
    if os.system(shellcmd):
        print shellcmd
        print "failure!\ncould not purge folder " + curr_dir
        raise ChiaraError('could not purge folder ' + curr_dir)

    # recursively walk through all (sub-)collections
    if download_dir(cur, cid, crev, curr_dir, 0):
        print "success!"
        print "collecetion successfully inserted into local directory"
        print "NOTE: potential previous files have been removed!"
    else:
        print "failure!"
        print "There was an error retrieving the collection."
        print "(If this error persists, please contact the admin.)"

    #shellcmd='mkdir -p ' + shellquote(curr_dir)
    #print "cmd: ", shellcmd
    #res = os.system(shellcmd)
    #print "result:", res
    #curr_cid, curr_crev = cid, crev

def download_dir(cur, cid, crev, topdir, depth, maxdepth=10):
    """
    downloads the content of collection cid-crev into a correspondingly named
    subfolder in "topdir". 
    This function operates recursively, including all subcollections.

    :args:
        cur (cursor): a SQL database cursor
        cid (str or int): collection id to download
        crev (str or int): collection revision
        topdir (str): path relative to chiara's file server working directory
            to store the data into (including the collection name)
        depth (int): do not include subdirectories if depth > maxdepth.
        maxdepth (int): (see above) This is to avoid possible infinite
            recursions.

    :returns:
        True if everything was successful, False otherwise
    """
    
    allOK = True
    if depth > maxdepth:
        print "failure!\nmaximum depth reached"
        return False

    CollNameQuery = """SELECT name FROM collection 
        WHERE id=:cid AND revision=:crev LIMIT 1;"""
    CollName = cur.execute(CollNameQuery, {'cid' : cid, 'crev' :
        crev}).fetchone()[0]
    query = """SELECT s.child_id, s.child_rev, c.name FROM is_sub AS s
                 JOIN collection AS c 
                   ON s.child_id=c.id AND s.child_rev=c.revision
                 WHERE s.parent_id=:cid AND s.parent_rev=:crev;"""
    # NOTE: here, fetchall is mandatory because cur will be passed recursively
    # to all sub-calls!
    
    # first: create all subdirs and work on subdirs :)
    res=cur.execute(query, {'cid' : int(cid), 'crev' : int(crev) }).fetchall()
    for SubC in res:
        #print topdir + SubC[2]
        allOK = allOK and download_dir(cur, SubC[0], SubC[1], topdir +  SubC[2]
                + '/', depth+1)
        res = os.system('mkdir -p ' + shellquote(topdir + SubC[2] + '/'))
        cmd =  'chmod 777 ' + shellquote(topdir + SubC[2] + '/')
        os.system(cmd) 

         #    res = os.system('whoami')
         #    print "res of create dir", res
        cmd ='/bin/chgrp chiara ' + shellquote('/var/www/chiara/' + topdir[3:] + SubC[2] )
         #    print cmd
        res = os.system(cmd)
         #    #res2 = subprocess.call(cmd, shell=True, stderr=subprocess.STDOUT)
         #    p = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE,
         #            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, close_fds=True)
         #    res2 = p.stdout.read()
         #    print "res of chown dir", res
         #    print "res of subprocess:", res2

         #    p = subprocess.Popen('whoami', shell=True, stdin=subprocess.PIPE,
         #            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, close_fds=True)
         #    res3 = p.stdout.read()
         #    print "res of whoami:", res3
        #print "chmod cmd:", cmd
        #if res != 0:
        #    os.chown( shellquote(topdir + SubC[2] ), 33, 1002)
        #           raise ChiaraError('could not set it right')
        #print 'result creating directory: ', res

    # second: retrieve files
    #print "\n--- retrieving files for ", topdir, str(cid) + '|' + str(crev)
    syscmd = 'mkdir -p ' + shellquote(topdir)
    res = os.system(syscmd)
    #print 'result of', syscmd, ':', res
    os.system('chmod 777 ' + shellquote(topdir)) 
    #TODO: set modes and ownership (groups) properly! 
    #TODO: on chiara server, set permissions properly on files when
    # uploading! (read-only)

    FQuery = """SELECT f.name, f.id, f.revision FROM files AS f 
                    JOIN has_files AS h 
                        ON f.id = h.file_id AND f.revision = h.file_rev
                    WHERE h.collection_id=? 
                      AND h.collection_rev=?;"""
    res = cur.execute(FQuery, (cid, crev))

    for elem in res:
        # communicate with server to put links in the directory
        #print "file: ", elem[0], ' -> ', elem[1], '-', elem[2]
        fullname = shellquote(topdir + elem[0] )
        load_file_from_storage(fullname, elem[1], elem[2])

    return allOK


def parse_UCR(args, selection, AllowNoRev=False):
    """
    parses the argument

    :args:
        args (object): the (argparse) object to parse
        selection (str): the selected option to parse. (IN FUTURE VERSION THIS
            MIGHT BE OPTIONAL)
        AllowNoRev (bool, optional): If True, no error is raised if only a
            collection id and no collection revision is provided

    :returns:
        (user, collection_id, collection_revision) if valid format is given

    :raises:
        ChiaraError if invalid parameters are passed

    """
    user = args.user
    if re.match('^[A-Za-z0-9_]+$', user) is None:
        raise ChiaraError('invalid username given')
    
    if not hasattr(args, selection):
        raise ValueError, "Invalid parser request"

    pts = getattr(args, selection).split('-')
    cid = pts[0]
    if len(pts) == 3 and ''.join(pts[1:]) == '1':
        crev = '-1'
    else:
        if len(pts) > 1:
            crev = pts[1]
        elif AllowNoRev:
            crev = None
        else:
            raise ChiaraError(
                'collection must be in "id-rev" format, e.g. 26-1 or 3--1')
    if not cid.isdigit():
        raise ChiaraError(
            'collection must be in "id-rev" format, e.g. 26-1 or 3--1')
    if crev != None:
        if not (crev.isdigit() or crev == '-1'):
            raise ChiaraError(
                'collection must be in "id-rev" format, e.g. 26-1 or 3--1')
    return user, cid, crev




def has_access(cur, user, cid): 
    """
    returns whether the user has (read) access to the collection cid

    :args:
        cur (cursor) : the cursor of the database
        user (str): the username
        cid (str): the collection id to check
    
    :returns:
        access (0,1,2) : 0: no access, 1: read, 2: write access
    """

    # first: check if there is read-access
    access = False
    query1 = """SELECT DISTINCT ua.modify FROM user_access AS ua
                 JOIN users AS u ON u.id = ua.user_id
                 WHERE ua.collection_id=:cid AND u.name=:user;"""

    query2 = """SELECT ga.modify FROM group_access AS ga
                 JOIN in_group AS ig ON ig.group_id = ga.group_id
                 JOIN users AS u ON ig.user_id = u.id
               WHERE ga.collection_id=:cid AND u.name=:user;"""
    for nr, query in enumerate([query1, query2]):
        for row in cur.execute(query, {'cid' : cid, 'user' : user}):
            # any result means: at leat read access!
            access = True
            if AnyTo01(row[0]):
                # highest access level "write" found -> return
                return 2
    if access:
        return 1
    return 0

def AnyTo01(string):
    """
    returns 0 or 1, depending what is in the given object "string"
    If it starts with "TRUE" (case insensitive) or is any integer != 0, 
    it will return 1, otherwise 0

    :args:
        string (str or anything convertable to str): the thing to parse
    
    :returns:
        tval (int): 0 or 1

    """
    tostr = str(string)
    try:
        ival = int(tostr)
    except ValueError:
        if tostr.lower().strip().startswith('true'):
            ival = 1
        else:
            ival = 0

    if ival != 0:
        return 1
    else:
        return 0

@db_fcn
def user_view_permissions(cur, args):
    """
    returns a tab-separated table that shows the permissions on a given id
    """

    user, cid, crev = parse_UCR(args, 'view_rights', AllowNoRev=True)
    if not has_access(cur, user, cid):
        raise ChiaraError, 'Error: user has no read access to collection'

    SQLQuery = """ SELECT u.name, u.id, ua.modify 
                    FROM user_access AS ua
                    JOIN users AS u ON ua.user_id = u.id
                  WHERE ua.collection_id=?
                  ORDER BY u.name;"""
    
    res = cur.execute(SQLQuery, (cid,))
    print 'User access (name - id - modify):'
    for elem in res:
        print '\t'.join([str(elem[0]), str(elem[1]), str(AnyTo01(elem[2]))])

    SQLQuery = """SELECT g.name, g.id, ga.modify 
                    FROM group_access AS ga
                    JOIN groups AS g ON ga.group_id = g.id
                  WHERE ga.collection_id=?
                  ORDER BY g.name;"""
    res = cur.execute(SQLQuery, (cid,))
    print 'Group access (name - id - modify):'
    for elem in res:
        print '\t'.join([str(elem[0]), str(elem[1]), str(AnyTo01(elem[2]))])

@db_fcn
def user_grant_group(cur, args):
    """
    grants or removes access rights to a group
    """

    user = args.user
    if re.match('^[A-Za-z0-9_]+$', user) is None:
        raise ChiaraError('invalid username given')
    
    cid, gid, mode = args.grant_group
    if has_access(cur, user, cid) < 2:
        raise ChiaraError(
            'user is not allowed to alter permissions on this collection!')
    
    mode = mode.lower()
    if not (cid.isdigit() and mode in ['rw','ro','none']):
        raise ChiaraError('invalid argument given - ' + 
                'use IDs and "rw" or "ro" for mode')
    SQLQuery = """DELETE FROM group_access 
                    WHERE group_id = :gid
                      AND collection_id = :cid; """
    cur.execute(SQLQuery, {'gid' : gid, 'cid' : cid })
    if mode != 'none':
        modify = 0
        if mode == 'rw':
            modify = 1
        SQLQuery = """INSERT INTO group_access (group_id, collection_id, modify)
                      VALUES (:gid, :cid, :modify);"""
        cur.execute(SQLQuery, {'gid' :  gid, 'cid' : cid, 'modify' : modify})
    print "success!\nrights altered"

    # permissions are *ONLY* given for the "searchable" directories. You only
    # need access to a master collection and you can download all
    # subcollections...
    #print "TODO: alter permissions recursively?"

@db_fcn
def user_grant_user(cur, args):
    """
    grants or removes access rights to a user
    """

    user = args.user
    if re.match('^[A-Za-z0-9_]+$', user) is None:
        raise ChiaraError('invalid username given')
 
    cid, uid, mode = args.grant_user
    if has_access(cur, user, cid) < 2:
        raise ChiaraError(
            'user is not allowed to alter permissions on this collection!')

    mode = mode.lower()
    if not (cid.isdigit() and mode in ['rw','ro','none']):
        raise ChiaraError('invalid argument given - ' + 
                'use IDs and "rw" or "ro" for mode')
    SQLQuery = """DELETE FROM user_access 
                    WHERE user_id = :uid
                      AND collection_id = :cid; """
    cur.execute(SQLQuery, {'uid' : uid, 'cid' : cid })
    if mode != 'none':
        modify = 0
        if mode == 'rw':
            modify = 1
        SQLQuery = """INSERT INTO user_access (user_id, collection_id, modify)
                      VALUES (:uid, :cid, :modify);"""
        cur.execute(SQLQuery, {'uid' :  uid, 'cid' : cid, 'modify' : modify})
    print "success!\nrights altered"

    # permissions are *ONLY* given for the "searchable" directories. You only
    # need access to a master collection and you can download all
    # subcollections...
    #print "TODO: alter permissions recursively?"


@db_fcn
def push_revision(cur, args):
    """
    push the local changes in the user's webfolder with a
    new collection revision to the repository
    """

    # parse user name/id, directory and comment
    uname = args.user
    SQL_uid = """SELECT id FROM users WHERE name=:uname;"""
    uid = int(cur.execute(SQL_uid, {'uname' : uname}).fetchone()[0])
    elements = args.push_revision
    cname = path_to_name(elements[0])
    cpath = userhome(args) + q_dir(cname)   
    comment = elements[1]
      
    # check and parse info.txt
    if not os.path.exists(cpath + 'info.txt'):
        print "failure!\nNo info.txt found"
        return
    si, li, tags, success = parse_info(cpath + 'info.txt')
    if not success:
        print "failure!\ninfo.txt is invalid"
        raise ChiaraError, "invalid info.txt"
    try:
        csi, cli, ctags, info_success = parse_info(q_dir(cpath) + 'info.txt')
    except IOError:
        info_success = False

    # get current time
    cur_time = int(time.time())

    # get collection name, id, revision, size and modified date
    SQL_cid_crev = """SELECT collection.id,collection.revision 
        FROM collection JOIN subscription 
        WHERE collection.id=subscription.collection_id AND collection.revision=subscription.collection_rev
            AND collection.name=:cname AND subscription.user_id=:uid;"""
    cid_crev = cur.execute(SQL_cid_crev, {'cname' : cname , 'uid' : uid}).fetchone()
    cid = int(cid_crev[0])
    crev = int(cid_crev[1])
    shell_csize = "du -bs " + shellquote(cpath) + " | awk '{print $1}'"
    csize = int(os.popen(shell_csize).read())
    #shell_cmd = "stat -c %Y " + cpath
    #cdate = os.popen(shell_cmd).read()   

    # check if collection is at newest revision
    SQL_crev_max = """SELECT MAX(revision) FROM collection WHERE name=:cname;"""
    crev_max = cur.execute(SQL_crev_max, {'cname' : cname}).fetchone()[0]
    if crev != crev_max:
        print "failure!\nyou have to update to newest version!"
        return

    # get hash list of the collection
    hash_list = get_hash_list(uname, cname)
    chash = hash_list[q_dir(cname)]

    # collection is modified     
    if is_collection_modified(cur, cid, crev, chash):
        # update database: collection, metadata and supscription table
        SQL_add = """INSERT INTO collection VALUES(:id, :rev, :name, :shortinfo, 
            :longinfo, :comment, :size, :date, :hash);"""
        cur.execute(SQL_add, {'id' : cid, 'rev' : crev+1, 'name' : cname, 'shortinfo' : csi, 
            'longinfo' : cli , 'comment' : comment, 'size' : csize, 'date' : cur_time, 'hash' : chash})
        cur.executemany("""INSERT INTO metadata (collection_id, collection_rev, tagname, tagcontent) 
            VALUES (?,?,?,?) """, [[cid, crev+1] + tag for tag in tags]) 
        cur.execute("""UPDATE subscription SET collection_rev=:crev WHERE user_id=:uid AND collection_id=:cid;""", 
            {'crev' : crev+1, 'uid' : uid, 'cid' : cid})
        # check directories and files in webfolder
        for fname in os.listdir(cpath):
            fpath = cpath + fname
            # recursively update all subcollections
            if os.path.isdir(fpath):
                user = dict(name=uname, id=uid)
                cparent = dict(name=cname, id=cid, rev=crev, path=cpath)
                cchild = dict(name=fname)
                push_recursive(cur, user, cparent, cchild, cur_time, hash_list)
            # update all files
            if os.path.isfile(fpath):
                push_files(cur, fpath, fname, cid, crev, cur_time, hash_list)
        
        print "success!"
        
    # collection is not modified
    else:
        print "The respective collection in your webfolder has not been modified."
    

def push_recursive(cur, user, cparent, cchild, cur_time, hash_list):
    
    # get user information
    uname = user.get('name')
    uid = int(user.get('id'))
    # get parent collection information
    cpname = cparent.get('name')
    cpid = int(cparent.get('id'))
    cprev = int(cparent.get('rev'))
    cppath = cparent.get('path')
    # get current collection information
    cname = cchild.get('name')
    cpath = q_dir(q_dir(cppath) + cname)
    chash = hash_list[cpath[len(userhome(args)):]]
    shell_csize = "du -bs " + shellquote(cpath) + " | awk '{print $1}'"
    csize = int(os.popen(shell_csize).read())
    #shell_cmd = "stat -c %Y " + cpath
    #cdate = int(os.popen(shell_cmd).read())
    if is_collection_new(cur, cname, cpid, cprev):
        cid_max = int(cur.execute("""SELECT MAX(id) FROM collection""").fetchone()[0])
        cid = cid_max + 1
        crev = 0
    else:
        SQL_cid_crev = """SELECT child_id, child_rev FROM collection JOIN is_sub 
            WHERE collection.id=is_sub.child_id AND parent_id=:cpid AND parent_rev=:cprev AND name=:cname;"""
        cid_crev = cur.execute(SQL_cid_crev, {'cpid' : cpid , 'cprev' : cprev , 'cname' : cname}).fetchone()
        cid = int(cid_crev[0])
        crev = int(cid_crev[1])
        
    # collection is new
    if is_collection_new(cur, cname, cpid, cprev):
        # update database: collection, metadata and supscription table
        cur.execute("""INSERT INTO collection (id, revision, name, size, modified, hash) VALUES (?,?,?,?,?,?);""",
            [cid, crev+1, cname, csize, cur_time, chash])
        cur.execute("""INSERT INTO is_sub (parent_id, parent_rev, child_id, child_rev) VALUES (?,?,?,?);""",
            [cpid, cprev+1, cid, crev+1])
        # check directories and files in webfolder
        for fname in os.listdir(cpath):
            fpath = cpath + fname
            # recursively update all subcollections
            if os.path.isdir(fpath):
                user = dict(name=uname, id=uid)
                cparent = dict(name=cname, id=cid, rev=crev, path=cpath)
                cchild = dict(name=fname)
                push_recursive(cur, user, cparent, cchild, cur_time, hash_list)          
            # update all files
            if os.path.isfile(fpath):
                push_files(cur, fpath, fname, cid, crev, cur_time, hash_list)    

    # collection is modified
    elif is_collection_modified(cur, cid, crev, chash):
        # update database: collection and is_sub table
        cur.execute("""INSERT INTO collection (id, revision, name, size, modified, hash) VALUES (?,?,?,?,?,?);""",
            [cid, crev+1, cname, csize, cur_time, chash])
        cur.execute("""INSERT INTO is_sub (parent_id, parent_rev, child_id, child_rev) VALUES (?,?,?,?);""",
            [cpid, cprev+1, cid, crev+1])
        # check directories and files in webfolder
        for fname in os.listdir(cpath):
            fpath = cpath + fname
            # recursively update all subcollections
            if os.path.isdir(fpath):
                user = dict(name=uname, id=uid)
                cparent = dict(name=cname, id=cid, rev=crev, path=cpath)
                cchild = dict(name=fname)
                push_recursive(cur, user, cparent, cchild, cur_time, hash_list)       
            # update all files
            if os.path.isfile(fpath):
                push_files(cur, fpath, fname, cid, crev, cur_time, hash_list)    

    # collection is not modified
    else:
        cur.execute("""INSERT INTO is_sub (parent_id, parent_rev, child_id, child_rev) VALUES (?,?,?,?);""",
            [cpid, cprev+1, cid, crev])
    

def push_files(cur, fpath, fname, cid, crev, cur_time, hash_list):
    
    # get file information
    shell_fsize = "du -bs " + shellquote(fpath) + " | awk '{print $1}'"
    fsize = int(os.popen(shell_fsize).read())
    fhash = hash_list[fpath[len(userhome(args)):]]
    #shell_cmd = "stat -c %Y " + fpath
    #fdate = int(os.popen(shell_cmd).read())
    if is_file_new(cur, fname, cid, crev):
        fid_max = int(cur.execute("""SELECT MAX(id) FROM files""").fetchone()[0])
        fid = fid_max + 1
        frev = 0
    else:
        SQL_fid_frev = """SELECT files.id, files.revision FROM files JOIN has_files 
            WHERE files.id=has_files.file_id AND files.revision=has_files.file_rev 
            AND collection_id=:cid AND collection_rev=:crev AND files.name=:fname;"""
        fid_frev = cur.execute(SQL_fid_frev, {'cid' : cid, 'crev' : crev, 'fname' : fname}).fetchone()
        fid = int(fid_frev[0])
        frev = int(fid_frev[1])

    # file is new
    if is_file_new(cur, fname, cid, crev):
        print "add " + fpath[len(userhome(args)):]
        # update database: files and has_files table
        cur.execute("""INSERT INTO files VALUES(:id, :rev, :name, :size, :date, :hash);""", 
            {'id' : fid, 'rev' : frev+1, 'name' : fname, 'size' : fsize, 'date' : cur_time, 'hash' : fhash})
        cur.execute("""INSERT INTO has_files (file_id, file_rev, collection_id, collection_rev) VALUES                          (?,?,?,?);""", [fid, frev+1, cid, crev+1])
        # add file to local storage 
        add_file_to_storage(fpath, fid, frev+1)

    # file is modified
    elif is_file_modified(cur, fid, frev, fhash):
        print "update " + fpath[len(userhome(args)):]
        cur.execute("""INSERT INTO files VALUES(:id, :rev, :name, :size, :date, :hash);""", 
            {'id' : fid, 'rev' : frev+1, 'name' : fname, 'size' : fsize, 'date' : cur_time, 'hash' : fhash})
        cur.execute("""INSERT INTO has_files (file_id, file_rev, collection_id, collection_rev) VALUES                          (?,?,?,?);""", [fid, frev+1, cid, crev+1])
        # add file to local storage 
        add_file_to_storage(fpath, fid, frev+1)

    # file is not modified
    else:
        cur.execute("""INSERT INTO has_files (file_id, file_rev, collection_id, collection_rev) VALUES                          (?,?,?,?);""", [fid, frev, cid, crev+1])


def is_collection_modified(cur, cid, crev, chash_new):
 
    # get collection hash from database
    SQL_chash = """SELECT hash FROM collection WHERE id=:id AND revision=:rev;"""
    chash = cur.execute(SQL_chash, {'id' : cid, 'rev' : crev}).fetchone()[0]
    
    return chash_new != chash
   
#    # get collection size of newest revision in database
#    SQL_csize = """SELECT size FROM collection WHERE id=:id AND revision=:rev;"""
#    csize = int(cur.execute(SQL_csize, {'id' : cid, 'rev' : crev}).fetchone()[0])
#    
#    return csize_new != csize

def is_collection_new(cur, cname, cpid, cprev):

    # check if parent collection new   
    if cprev==0:
        return True
 
    # get a list of all subcollections of the given parent collection 
    SQL_cnames = """SELECT name FROM is_sub JOIN collection WHERE is_sub.child_id=collection.id AND parent_id=:cpid AND parent_rev=:cprev;"""
    cnames = [names[0] for names in cur.execute(SQL_cnames, {'cpid' : cpid, 'cprev' : cprev}).fetchall()]

    return cname not in cnames

def is_file_modified(cur, fid, frev, fhash_new):
    
    # get file hash from database
    SQL_fhash = """SELECT hash FROM files WHERE id=:id AND revision=:rev"""
    fhash = cur.execute(SQL_fhash, {'id' : fid, 'rev' : frev}).fetchone()[0]

    return fhash_new != fhash

#    # get old file size in database
#    SQL_fsize = """SELECT size FROM files WHERE id=:id AND revision=:rev"""
#    fsize = int(cur.execute(SQL_fsize, {'id' : fid, 'rev' : frev}).fetchone()[0])
#   
#    return fsize_new != fsize

def is_file_new(cur, fname, cid, crev):
    
    # check if collection is new
    if crev==0:
        return True

    # get a list of all files of the given collection
    SQL_fnames = """SELECT files.name FROM has_files JOIN files WHERE has_files.file_id=files.id AND has_files.file_rev=files.revision AND collection_id=:cid AND collection_rev=:crev;"""
    fnames = [names[0] for names in cur.execute(SQL_fnames, {'cid' : cid, 'crev' : crev}).fetchall()]

    return fname not in fnames


@db_fcn
def pull_revision(cur, args):
    """
    update to a desired revision of the collection
    """
    # parse user name/id and collection name
    uname = args.user
    SQL_uid = """SELECT id FROM users WHERE name=:uname;"""
    uid = int(cur.execute(SQL_uid, {'uname' : uname}).fetchone()[0])
    elements = args.pull_revision
    cname = elements[0]
    cpath = userhome(args) + q_dir(cname)   
    crev = int(elements[1])
    
    # get collection name, id, revision, size and modified date
    SQL_cid_crevcur = """SELECT collection.id,collection.revision 
        FROM collection JOIN subscription 
        WHERE collection.id=subscription.collection_id AND collection.revision=subscription.collection_rev
            AND collection.name=:cname AND subscription.user_id=:uid;"""
    cid_crevcur = cur.execute(SQL_cid_crevcur, {'cname' : cname , 'uid' : uid}).fetchone()
    cid = int(cid_crevcur[0])
    crev_current = int(cid_crevcur[1])
    
    # check if collection is already in the chosen revision
    # change != to ==
    if crev == crev_current:
        print "failure!\nthe collection is already in the chosen revision!"
        return
 
    # delete everything that was there before
    shellcmd = 'rm -rf ' + shellquote(cpath)
    removed = os.system(shellcmd)
    if removed:
        print shellcmd
        print "failure!\ncould not purge folder " + shellquote(cpath)
        raise ChiaraError('could not purge folder ' + shellquote(cpath))
    
    # recursively pull the collection
    cparent = dict(name=None, id=None, rev=None, path=None)
    cchild = dict(name=cname, id=cid, rev=crev, path=cpath)
    allOK = pull_recursive(cur, cparent, cchild, 0)

    # update database: subscription
    cur.execute("""UPDATE subscription SET collection_rev=:new_crev WHERE user_id=:uid AND collection_id=:cid;""",
        {'new_crev' : crev , 'uid' : uid , 'cid' : cid})
    
    # check if collection was successfully pulled
    if allOK:
        print "success!"
        print "collecetion successfully inserted into local directory"
        print "NOTE: potential previous files have been removed!"
    else:
        print "failure!"
        print "There was an error retrieving the collection."
        print "(If this error persists, please contact the admin.)"
    

def pull_recursive(cur, cparent, cchild, depth, maxdepth=10):
    
    allOK = True
    if depth > maxdepth:
        print "failure!\nmaximum depth reached"
        return False

    # get parent collection name
    cpname = cparent.get('name')
    # is top directory
    if cpname is None:
        # get current collection information
        cname = cchild.get('name')
        cid = cchild.get('id')
        crev = cchild.get('rev')
        cpath = cchild.get('path')
    else:
        # get parent collection information
        cpid = cparent.get('id')
        cprev = cparent.get('rev')
        cppath = cparent.get('path') 
        # get current collection information
        cname = cchild.get('name')
        SQL_cid_crev = """SELECT child_id, child_rev FROM collection JOIN is_sub 
            WHERE collection.id=is_sub.child_id AND parent_id=:cpid AND parent_rev=:cprev AND name=:cname;"""
        cid_crev = cur.execute(SQL_cid_crev, {'cpid' : cpid , 'cprev' : cprev , 'cname' : cname}).fetchone()
        cid = int(cid_crev[0])
        crev = int(cid_crev[1])
        cpath = q_dir(q_dir(cppath) + cname)

     # create collection folder
    res = os.system('mkdir -p ' + shellquote(cpath))
    res = os.system('chmod 777 ' + shellquote(cpath))
    res = os.system('/bin/chgrp chiara ' + shellquote(cpath))

    # recursively pull the collection
    SQL_subcnames = """SELECT name FROM is_sub JOIN collection 
        WHERE is_sub.child_id=collection.id AND is_sub.child_rev=collection.revision 
        AND is_sub.parent_id=:cid AND is_sub.parent_rev=:crev;"""
    subcnames = [names[0] for names in cur.execute(SQL_subcnames, {'cid' : cid, 'crev' : crev}).fetchall()]
    for subcname in subcnames:
        cparent = dict(name=cname, id=cid, rev=crev, path=cpath)
        cchild = dict(name=subcname)
        # pull recursive
        allOK = allOK and pull_recursive(cur, cparent, cchild, depth+1)    

    # pull the files of the collection
    SQL_fid_frev_fnames = """SELECT files.id,files.revision,files.name FROM has_files JOIN files 
        WHERE has_files.file_id=files.id AND has_files.file_rev=files.revision 
        AND collection_id=:cid AND collection_rev=:crev;"""
    fid_frev_fnames = cur.execute(SQL_fid_frev_fnames, {'cid' : cid, 'crev' : crev}).fetchall()
    for fid_frev_fname in fid_frev_fnames:
        fid = int(fid_frev_fname[0])
        frev = int(fid_frev_fname[1])
        fname = fid_frev_fname[2]
        fpath = cpath + fname
        # copy all files in top collection folder
        print "load file " + fpath
        load_file_from_storage(shellquote(fpath), fid, frev)

    return allOK



@db_fcn
def list_revisions(cur, args):
    """
    list all revisions with their comment and modified date
    """
   
    # get user name, id and collection name 
    uname = args.user
    uid = int(cur.execute("""SELECT id FROM users WHERE name=:uname;""", {'uname' : uname}).fetchone()[0])
    cname = args.list_revisions
    
    # get all revisions of the collection with comment and modified date
    SQL_cinfos = """SELECT revision, comment, modified FROM collection JOIN subscription 
        WHERE collection.id=subscription.collection_id AND name=:cname AND user_id=:uid;"""
    cinfos = cur.execute(SQL_cinfos, {'cname' : cname, 'uid' : uid}).fetchall()
    
    # list all revisions with infos
    for line in cinfos:
        modified = datetime.datetime.fromtimestamp(int(line[2])).strftime('%d.%m.%Y, %H:%M:%S') 
        print str(line[0]) + "\t" + line[1] + "\t" + modified

@db_fcn
def is_admin(cur, args):
    """
    return 1 if the user is an admin, otherwise 0
    """
    
    print cur.execute("""SELECT admin FROM users WHERE name=:uname;""", {'uname' : args.user}).fetchone()[0]


def user_fn(args):
    """ 
    is called when subparser "usercmd" is active
    """

    if args.list:
        # list the contents of a specified directory in user's home folder
        listdir(args)
    elif args.subscribe:
        # subscribe to a collection
        subscribe_by_id(args)
    elif args.unsubscribe:
        # unsubscribe from a collection where the name is given
        # (collection must be present in user's home folder)
        unsubscribe_by_folder(args)
    elif args.unsubscribe_id:
        # unsubscribe from a collection which is given by id and revision
        unsubscribe_by_id(args)
    elif args.download:
        # download a collection to user's home directory
        download_collection(args)
    elif args.add:
        # add a collection from user's home to the archive
        add_dir_to_collection(args)
    elif args.view_collection:
        # views all collections the user is subscribed to, including meta- and
        # access information
        user_view_collection(args)
    elif args.view_rights:
        # views the permission on a given collection id
        user_view_permissions(args)
    elif args.search:
        # search the library for collections that match the search and are
        # available to the user
        search_collections(args)
    elif args.grant_group:
        # grant or revoke access rights to a group
        user_grant_group(args)
    elif args.grant_user:
        # grant or revoke access rights to a user
        user_grant_user(args)
    elif args.push_revision:
        # push local changes to a new collection revision
        push_revision(args)
    elif args.pull_revision:
        # update the local directory to the desired revision
        pull_revision(args)
    elif args.list_revisions:
        # list all revisions with their comment and modified date
        list_revisions(args)
    elif args.is_admin:
        # return 1 if the user is an admin, otherwise 0
        is_admin(args)
    else:
        print "failure!"
        print "I don't know what to do!"

    return

@db_fcn
def listdir(cur, args):
    """
    returns a commented list of a directory

    Args:
        args (str): the parameter list given by the command line. Required
        entries: user, directory (has to start with /)
    Returns:
        (None)

    Output: 
        Lines of the following form:
        <type>\t<name>\t<revision>\t<in_collection>\t<modified>

    """
   
    #    qdir is the modified directory name: does not start with /, ends with /
    qdir = q_dir(args.list)

    refdir = userhome(args) + qdir
    #nremove = len('../data/' + args.user)

    print "listing content of " + qdir #refdir[nremove:]
    allNodes = os.listdir(refdir)
    allDirs = []
    allFiles = []
    allOther = []
    for nd in allNodes:
        qname = os.path.join(refdir, nd)
        if os.path.isdir(qname):
            allDirs.append(qname[len(refdir):])
        elif os.path.isfile(qname):
            allFiles.append(qname[len(refdir):])
        else:
            allOther.append(qname[len(refdir):])

    # sort lists
    allDirs.sort(key=lambda s: s.lower())
    allFiles.sort(key=lambda s: s.lower())
    allOther.sort(key=lambda s: s.lower())


    #print 'refdir', refdir
    #rdir = refdir
    #while rdir.endswith('//'):
    #    rdir = rdir[:-1]
    #print 'rdir', rdir

    if len(qdir) > 1:
        RawFolderList = qdir.split('/')[:-1]
    else:
        RawFolderList = []

    for fn in allDirs:
        # find if dir is in collection!
        print '|'.join(RawFolderList)
        cid, crev = get_folder_id(cur, args.user, RawFolderList + [fn,])
        if (cid, crev) == (None, None):
            print 'd\t' + fn  + '\t-1'
        else:
            AccessLevel = has_access(cur, args.user, cid)
            if AccessLevel==0:
                print 'Dx\t' + fn  + '\t-1'
            elif AccessLevel==1:
                print 'Dr\t' + fn  + '\t' + str(crev)
            elif AccessLevel==2:
                print 'Dw\t'+ fn  + '\t' + str(crev)
            else:
                # actually, this cannot happen
                raise ChiaraError('invalid value encountered from has_access')

    for fn in allFiles:
        print 'f\t' + fn  + '\t-1'

    for fn in allOther:
    # e.g. special files. actually, they should not exist.
        print 'x' + fn + "test"



#remember: cwd is the directory of the calling (php) file!
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="The chiara client program",
            epilog='use --help <subcmd> to get more detailled help on subcommands' )
    subparsers = parser.add_subparsers()

    uparser = subparsers.add_parser('user', help='user commands')
    uparser.add_argument('-u','--user', help='the user to perform the action for',
            required=True)
    uparser.set_defaults(func=user_fn)
    ucmd = uparser.add_mutually_exclusive_group()
    ucmd.add_argument('-l', '--list', metavar='directory',
        help='list the content of the directory LIST')
    ucmd.add_argument('-a', '--add', metavar='directory',
            help='add folder <directory> as new collection')
    ucmd.add_argument('-s', '--subscribe', metavar='collection_id', 
            help='subsribe to a collection given in "id-rev" format')
    ucmd.add_argument('-x', '--unsubscribe', metavar='collection',
            help='unsubsribe from a collection')
    ucmd.add_argument('-y', '--unsubscribe_id', metavar='collection_id',
            help='unsubscribe from a collection given by "id-rev" format')
    ucmd.add_argument('-d', '--download', metavar='collection_id',
            help='download collection, given by "id-rev", to home folder.\n' + 
            'NOTE: this will overwrite any content in that directory!')
    ucmd.add_argument('--view_collection', help="""view the collections the
        user has subscribed to""", action='store_true')
    ucmd.add_argument('--view_rights', metavar='collectionID',
        help="""view the permissions on a collection """ )
    ucmd.add_argument('--search', help="search in available collections",
            nargs=2, metavar=('DESCRIPTION','TAGS'))
    ucmd.add_argument('--grant_group', 
        help="grant access ('ro', 'rw', 'none') to a group", nargs=3,
        metavar=('collection_id', 'group_id', 'mode'));
    ucmd.add_argument('--grant_user', 
        help="grant or revoke access ('ro','rw','none') to a user", nargs=3,
        metavar=('collection_id', 'group_id', 'mode')); 
    ucmd.add_argument('--push_revision', 
        help="push the local changes in the user's webfolder with a " +
            "new collection revision to the repository", nargs=2, 
        metavar=('directory', 'comment'));
    ucmd.add_argument('--pull_revision', 
        help="update to a desired revision of the collection", nargs=2, 
        metavar=('collection', 'collection_revision'));
    ucmd.add_argument('--list_revisions', 
        help="list all revisions with their comment and modified date", metavar='collection')
    ucmd.add_argument('--is_admin', 
        help="return 1 if the user is an admin, otherwise 0", nargs=1, metavar='user');

     # hint for future work on parsers: use "dest" instead of metavar ;)


    parser_s = subparsers.add_parser('sys', help='system commands')

    sspars = parser_s.add_subparsers(help='available commands')
    idb_parse = sspars.add_parser('init_db', help='initialize the database')
    idb_parse.set_defaults(func=initdb)

    sysadduser_parse = sspars.add_parser('adduser', help='add a user')
    sysadduser_parse.add_argument('user', help='the username')
    sysadduser_parse.add_argument('admin', help='boolean if admin')
    sysadduser_parse.set_defaults(func=useradd)

    sysrmuser_parse = sspars.add_parser('rmuser', help='remove a user')
    sysrmuser_parse.add_argument('user', help='the username')
    sysrmuser_parse.set_defaults(func=userrm)

    sysaddgroup_parse = sspars.add_parser('addgroup', help='add group')
    sysaddgroup_parse.add_argument('group', help='the groupname')
    sysaddgroup_parse.set_defaults(func=groupadd)

    sysrmgroup_parse = sspars.add_parser('rmgroup', help='remove a group')
    sysrmgroup_parse.add_argument('group', help='the groupname')
    sysrmgroup_parse.set_defaults(func=grouprm)

    sysrmfromgroup_parse = sspars.add_parser('rmfromgroup',
            help='remove user from a group')
    sysrmfromgroup_parse.add_argument('user', help='the username')
    sysrmfromgroup_parse.add_argument('group', help='the groupname')
    sysrmfromgroup_parse.set_defaults(func=group_rm_user)

    sysaddtogroup_parse = sspars.add_parser('addtogroup',
            help='add a user to a group')
    sysaddtogroup_parse.add_argument('user', help='the username')
    sysaddtogroup_parse.add_argument('group', help='the groupname')
    sysaddtogroup_parse.set_defaults(func=group_add_user)

    syslistgroups_parse = sspars.add_parser('listgroups', help='lists all groups')
    syslistgroups_parse.set_defaults(func=list_all_groups)

    syslistusers_parse = sspars.add_parser('listusers', help='lists all users')
    syslistusers_parse.set_defaults(func=list_all_users)

    syslistgroup_parse = sspars.add_parser('listgroup', 
            help='list all users of a group')
    syslistgroup_parse.add_argument('group', help='the groupname')
    syslistgroup_parse.set_defaults(func=list_group)

    syslistgroup_parse = sspars.add_parser('listuser', 
            help='list all groups of a user')
    syslistgroup_parse.add_argument('user', help='the username')
    syslistgroup_parse.set_defaults(func=list_user)

    args = parser.parse_args()
    args.func(args)

# required functionality:
# 1.) compare present files with database backend
# 2.) introduce files to database





