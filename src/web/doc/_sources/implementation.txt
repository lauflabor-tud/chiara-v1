Implementation of Chiara
========================


File storage
------------

Each user mounts a WebDAV share to some location and puts the data onto it.
When (in the web interface) the user uploads the data into Chiara, the files
are copied to a storage that only Chiara can access.

.. note::

    This implies some tricks with the file permissions:
    
    * user *chiara* must be able to read and write to the directories that have
      been uploaded (=put on the remote webdav folder ("network drive") ).

    * no user (potentially *chiara*, but that's not necessary) will have write
      access to the newly imported file. If the 

The files will be stored under some name that contains just their *id* in some
folder. All users that subscribe to the archive will get a (hard) link to the
file in their directory.

.. note::

    Users cannot edit the file. When a user deletes the file, the original file
    persists. When a user then creates a new file of the same name, it will be
    a physically different file.

    *Chiara* will figure this out using the modification time stamp and display
    a potential difference in the web interface (and ask "want to update?").

Meta data
---------

Each *logical node* (directory) may have its own metadata, provided in the file
*info.txt* in the directory.

The text in these files will be searchable.

There are several pre-defined fields for which these *info.txt* files will be
parsed.

Backup and data security
------------------------

Data that is once stored cannot be deleted again. It can only be unlinked from
a specific repository or a personal folder. It also cannot be overwritten.

If a file is updated, it will be internally stored as "new revision" of that
file. 

.. warning::

    The physical backup has to be performed separately!

Data organization
-----------------

Ah, the central and interesting part.

The central element is a "collection", which is pretty much like a folder. It
can be accessed by its *id*.  

Collections can be accessed by
    
    * their *id*
    * a full, ordered path of collection names (not necessarily unique!)

Managing collections
--------------------

A user can manage the collection she has write access to. She can

    * add collections she has read access to (unless there is another
      collection with the same name already in this collection)
    * remove collections (with the restriction that each collection *must* 
      (a) either be a root collection or (b) still have a parent collection).
    * add files to the collection
    * update files in the collection. This is similar to adding the file.
    
In the web interface at "manage collections", a collections-tree is set up, so
that there will not be infinitely many collections on a screen.

To facilitate uploading data into a collection, on the web interface there will
be an option "create path to collection (and sub-collections [checkbox])". For
security reasons, such paths will be limited to a certain maximal depth. 

On initial uploading, the option "insert directory to collections" will be
provided, "removing" (moving to the server's private space) the original files
and replacing them with "obtained" data from the collection (which is
read-only - but can be deleted and newly written).

Each modification of a collection (id, revision) results in a new revision of
that collection.

browsing collections
''''''''''''''''''''

When a collection has multiple parent, display
parents: "p1, "p2" , "p3", ... "p3" and link to all parents.
Parents to which the user has no access may be (a) either gray or (b) not shown
at all (better).


adding / updating files
'''''''''''''''''''''''

* Idea: "add files to collection" works also for folders, but recursively!
  Collection id can directly be entered.

* Adding or updating files in a collection: The collection will get a new
  revision, so that users who subscribed to "latest" will get the update, and
  users that subscribed to a specific revision will get the old one.

Collection permissions
''''''''''''''''''''''

When uploading a new collection (directory with sub-directories), it is accessible by default 

The folder where the database is in must be writeable by www-data

Subscription
''''''''''''

There are two alternatives (which do not exclude each other!)

    (1) When a user has found an interesting collection, she can subscribe to
        it. It will appear as a folder in hers shared folder / network folder
        root directory.
    (2) There is a special folder "my collections", which is a collection to
        which the user can add the collections of choice.


Avoiding infinite recursion
'''''''''''''''''''''''''''

Todo: think if infinite recursion has to be avoided!

If it has to be avoided, every collection gets a "level" - and can only
include higher levels as sub-collection.

Alternative: When building a directory tree from a subscribed collection,
store which folder id's have already been included, and skip them in further
folder creation. (Otherwise, create a subfolder for every subcollection and so
on...)


The info.txt file
-----------------

In each directory (on uploading), a "info.txt" file can be present. It can be
structured as follows:

    First, it starts with some text, which is interpreted as "short
    information"  - something that summarized what is in the collection  until
    there is a line like this:

    ### details ###

    In the following, the lines contain a detailled description of the
    collection (e.g. how files are organized in subfolders; subject
    information; ...)

    This continues until a line which begins with

    ### tags ###

    In the remainder, all lines are parsed as follows:
    
        * Lines are split at the  ":" - sign
        * parts are trimmed (whitespaces removed)
        * all parts except the first are concatenated
        * the first part is interpreted as tag name, the second part as tag
          content. 

    Example:

    keywords: locomotion, language, database
    some thing # invalid line
      symbols in here: # ' : ; . () /

    note that in the last line, the tag name is 'symbols in here', and the tag
    content is '# ' : ; . () /'





