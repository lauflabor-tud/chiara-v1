Setting up Chiara
=================

.. sidebar:: Questions?
    :subtitle: Please contact us at:

    mmaus@sport.tu-darmstadt.de
    dominik.reis@stud.tu-darmstadt.de

.. contents::


Compatibility
-------------
*Chiara* is only compatible with *Linux*. So you have to set up a Linux server.

Setup per remote access
-----------------------
The following steps will show you what you need to do to configure Chiara on a server from somewhere else.

Linux/Mac Os X 
''''''''''''''
1. Open *Terminal* and access to the server with *SSH* by typing::

    ssh <user>@<server-address>

#. Answer at the security warning with **yes**.
#. Insert your password.
#. Now you are logged on to the server.

     
Windows
'''''''
1. Dowload *PuTTY* at http://www.putty.org/.
#. Run *putty.exe*.
#. Fill-out the fields **Host name (or IP address)** and **Port**.
#. Choose at connection type **SSH**.
#. *Optional:* If you want to save this configuration, you have to insert in the **Saved Sessions** field an arbitrary name and click **Save**.
#. Click **Open**.
#. When the *PuTTY Security Alert* Window opens, click **Yes**.
#. Enter your username and password.
#. Now you are logged on to the server.


Install/Configure Apache
------------------------
The following description is for distributions based on *Debian*. You have to execute all commands with **sudo**. 

1. Install *Apache*. ::
   
    apt-get install apache2
 
#. Install *PHP*. ::
   
    apt-get install php5 libapache2-mod-php5
   
    /etc/init.d/apache2 restart

#. Install additional PHP packages. ::
    
    apt-get install php5-mysql php5-curl php5-gd php5-idn php-pear php5-imagick php5-imap php5-mcrypt php5-memcache php5-ming php5-ps php5-pspell php5-recode php5-snmp php5-sqlite php5-tidy php5-xmlrpc php5-xsl

    /etc/init.d/apache2 restart

#. *Optional:* If you Search further PHP packages, you can list all available as follows::
    
    apt-cache search php5
   
#. Enable necessary modules. ::
    
    a2enmod dav dav_fs auth_digest

#. *Optional:* Install *Python* package. ::

    apt-get install libapache2-mod-wsgi

    a2enmod wsgi

.. _chiara configuration file:

7. Navigate to */etc/apache2/sites-available* and create a chiara configuration file like this: :download:`chiara <resources/chiara>`

#. Link this file to *sites-enabled* and use *a2ensite <sitename>* to enable the website. ::
    
    ln -s /etc/apache2/sites-available/chiara /etc/apache2/sites-enabled/chiara
    
    a2ensite chiara
    
    /etc/init.d/apache2 restart

#. Link Chiara to Apache. *<path/to/chiara>* means the path where Chiara is located (e.g. */qnap/chiara*). ::

    ln -s <path/to/chiara> /var/www/chiara

#. Set Chiara configuration parameters in the file *config.ini*.

#. Add user and group *chiara* and set permissions. ::
    
    addgroup chiara
    
    adduser chiara --ingroup chiara

    usermod -aG chiara chiara
    
    usermod -aG chiara www-data

    chown -cR www-data:chiara <path/to/chiara>

    find <path/to/chiara> -exec chmod 775 {} +

    chmod 644 <path/to/password-file>/passwd.dav

#. Add the following lines into the file */etc/rc.local* to start the Chiara server at system start. :: 

    # start chiara
    su chiara -c '<path/to/chiara>/py/chiaraSRV2.py &'

#. Start Chiara server manually with the following command or restart the system. ::

    su chiara -c '<path/to/chiara>/py/chiaraSRV2.py &'

#. Open your browser and insert your server adress configured in the `chiara configuration file`_ to check if it works (e.g. *http://130.83.212.83/chiara*). 


Configure Chiara
----------------
The configuration of Chiara is set via *<path/to/chiara>/py/chiara.py*. Best move to *<path/to/chiara>* for executing the commands in this chapter. You can call the help as follows::
    
    ./chiara.py sys -h

Initialize database
'''''''''''''''''''
Before you are able to manage users and groups, you have to initialize a database. ::    
    
    ./chiara.py sys init_db

Manage users
''''''''''''
**Add user**

1. Add user in the `chiara configuration file`_ in Apache.
#. Add password of the user to the password file with *htdigest*. This file is located at the chiara trunk, but you can move this to somewhere else. <realm> should be kept fixed (e.g. Chiara@LL). Please note your configuration in *conifg.ini* under section *password*. ::

    htdigest <file> <realm> <user>

#. Add the user home directory to Chiara with proper access rights. ::

    mkdir <path/to/chiara>/data/<user>
    
    chown -c www-data:www-data <path/to/chiara>/data/<user>

    chmod 775 <path/to/chiara>/data/<user>

#. Add user to chiara system. ::

    ./chiara.py sys adduser <user>

**Remove user**

1. Remove user from chiara system. ::
    
    ./chiara.py sys rmuser <user>

#. Remove the user home directory. ::

    rm -r <path/to/chiara>/data/<user>

#. Remove user in the `chiara configuration file`_ in Apache.

**List all users** ::

    ./chiara.py sys listusers

**List all groups of user** ::

    ./chiara.py sys listuser <user>

Manage groups
'''''''''''''
**Add group** ::

    ./chiara.py sys addgroup <group>

**Remove group** ::

    ./chiara.py sys rmgroup <group>

**Add users to group** ::

    ./chiara.py sys addtogroup <user> <group>

**Remove users from group** ::

    ./chiara.py sys rmfromgroup <user> <group>

**List all groups** ::

    ./chiara.py sys listgroups

**List all users of a group** ::

    ./chiara.py sys listgroup <group>


Overview: Parts of Chiara
-------------------------
Chiara consists of the following four parts.

Python
''''''
The Python part is located in the directory *<path/to/chiara>/py*. It contains the following modules.

**chiara.py**
    This module provides the data management tool of Chiara (add users, groups, etc. to the database). See `Configure Chiara`_.

**chiaraSRV2.py**
    A tiny server that should be run under the user *chiara* to allow certain actions to be done under the username *chiara*.


SQLite
''''''
The SQLite database is located in *<path/to/chiara>/py* and is called *chiara.db*. It will be initialized and configured by *chiara.py*. See `Configure Chiara`_.

Database structure
``````````````````

.. image:: resources/tables-2.svg
    :height: 550px
    :width: 940px
    :align: center

Restore data
````````````
A collection can never be written, if no user have write access to it. It can also be totally lost, if no user have read and write access to it. In these cases you can manually give a user write access to the respective collection to restore it.

**Install SQLite3 and connect to the database.**

1. Install sqlite3. ::

    sudo apt-get install sqlite3

#. Connect to chiara.db. ::

    sqlite3 <path/to/chiara>/py/chiara.db

**Find all collections, to which no one has write but at least one user has read access.** ::
    
    SELECT Collection.name, Collection.id
    FROM Collection 
    LEFT JOIN user_access 
    ON (Collection.id = user_access.collection_id) 
    WHERE user_access.collection_id IS NULL;

**Give a user write access to a collection, to which no user has write but at least one user has read access.**

1. Find the collection ID of the lost collection. ::

    SELECT id FROM Collection WHERE name=<collection-name>;

#. Find the user ID of the user who will get the access. ::

    SELECT id FROM users WHERE name=<user-name>;

#. Find the maximum ID of all user_access entries. ::

    SELECT MAX(id) FROM user_access;

#. Insert a new entry in the user_access database with the found collection ID, user ID and increased maximum entry ID. ::

    INSERT INTO user_access VALUES (<MAX-ID + 1>, <user-ID>, <collection-ID>, 1);

**Find all collections, to which no user has read and write access.** ::

    SELECT Collection.name, Collection.id 
    FROM Collection
    JOIN (
        SELECT DISTINCT read.collection_id 
        FROM (SELECT * FROM user_access WHERE modify=0) AS read 
        LEFT JOIN (SELECT * FROM user_access WHERE modify=1) AS write 
        ON read.collection_id=write.collection_id 
        WHERE write.collection_id IS NULL
    ) AS onlyread 
    ON Collection.id=onlyread.collection_id;

**Give a user write access to a collection, to which no user has read and write access.**

1. Find the collection ID of the lost collection. ::

    SELECT id FROM Collection WHERE name=<collection-name>;

#. Find the user ID of the user who will get the write access. ::

    SELECT id FROM users WHERE name=<user-name>;
  
#. Change read access to write access with the found collection and user ID. ::

    UPDATE user_access SET modify=1 WHERE collection_id=<collection-ID> AND user_id=<user-ID>;

PHP
'''

The PHP part is located in the directory *<path/to/chiara>/web*. It contains the following modules.

**index.php** 
    This module will be called from Apache. It builds the main frame (logo, tabbar and footbar) of the web page.

**functions.php**
    This module manages the functionality of the chiara web page by calling *chiara.py* using the command line (e.g. view my shared folder, add to collections, etc.).
 

reStructeredText
''''''''''''''''
The chiara html documentation is located in *<path/to/chiara>/doc* and is linked to *<path/to/chiara>/web/doc*. It will be built with *reStructeredText* and compiled with *Sphinx*. If you want to install Sphinx, you can do this as follows::

    sudo apt-get install sphinx-common sphinxbase-utils sphinx-doc sphinxsearch

The *index.rst* is the main file and combine all documentation parts like *use-of-chiara.rst*, *setup-chiara.rst*, etc. 


