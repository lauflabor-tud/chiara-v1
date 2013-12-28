How to use Chiara
=================

.. sidebar:: Questions?
    :subtitle: Please contact us at:
  
    mmaus@sport.tu-darmstadt.de
    dominik.reis@stud.tu-darmstadt.de

.. contents::


Mount your webfolder to your local disk
---------------------------------------
The following steps will show you how to connect your local disk with your webfolder. You have to choose the manual depending on your operating system.

Linux
'''''
**Mount**

1. Install the package *davfs*. If you use a distribution based on *Debian* you can install it as follows::

    sudo apt-get install davfs2

#. Create an empty directory in which the data will be mapped. For the example */home/user/mnt* you have to type::

    mkdir /home/user/mnt

#. Mount your webfolder into this directory. You can do this with the following command. But you have to replace *<chiara-user>* into your chiara-username. ::

    sudo mount -t davfs -o uid=1000 http://130.83.212.83/<chiara-user> /home/user/mnt

#. Now you can find the content of your webfolder in */home/user/mnt*.

**Unmount**

    If you want to unmount */home/user/mnt* for example you have to type::
    
        sudo umount /home/user/mnt

Mac Os X
''''''''
**Mount**

1. Open **Finder**, click **Go** and then click **Connect to Server...**.
#. Insert *http://130.83.212.83/<chiara-username>* in the **Server Address** box. But you have to replace *<chiara-username>* into your chiara-username.
#. If you want to add this server address to **Favorite Servers** click the **+** button.
#. Click **Connect**.
#. Enter your chiara-username and password and click **Connect**. 
#. Open **Finder**.
#. You can launch your webfolder by clicking it under **SHARED** in the sidebar.

**Unmount**

1. Open **Finder**.
#. Find your webfolder under **SHARED** in the sidebar and click the eject symbol next to its name.

Windows
'''''''
**Mount**

1. Click the **Start** button and then right-click **Computer**.
#. Click **Map network drive**...
#. In the **Drive** list, choose a drive letter.
#. Type *\\\\130.83.212.83\\<chiara-username>* in the **Folder** box. But you have to replace *<chiara-username>* into your chiara-username.
#. To connect every time you log on to your computer, select the **Reconnect at logon** check box.
#. Click **Finish**.
#. When the *Windows Security* window has been opened, enter your chiara-username and password and click **OK**. 
#. Open Computer by clicking the **Start** button, and the clicking **Computer**.
#. You can launch your webfolder by open the drive letter you have chosen above.

**Unmount**

1. Open Computer by clicking the **Start** button, and the clicking **Computer**.
#. Right-click on your webfolder.
#. Click **Disconnect**.


Put data into the repository
----------------------------
The following steps will show you how to put data into the repository to share these with your partners.

1. Copy the new directory to your webfolder.
#. Be sure that the new dirctory or one of its parent directories contains an `info.txt`_ file.
#. Launch Chiara's website.
#. Choose the tab `view my shared folder`_ and add the respective directory to collections.
#. Choose the tab `manage my collections`_ and customize the permissions.


Get data into your webfolder
----------------------------
The following steps will show you how to get shared data of your partners into your webfolder.

1. Launch Chiara's website.
#. Choose the tab `retrieve new collections`_ and search new collections by dint of description and tags.
#. Subscribe the respective directory.
#. Choose `manage my collections`_ and download the directory.
#. Take a look into your webfolder.


Interface description
---------------------
The Chiara web page comes with four tabs. In the following you can find the description of each one (exclusive the documentation tab).

View my shared folder
'''''''''''''''''''''
This tab shows the content of your mounted webfolder. You can apply different options to the directories in it.

**add to collections** 
    Adds the respective directory to the repository to share it with your partners. For permission handling see `Manage my collections`_. The directory or one of its parent directories must be contain an `info.txt`_ file.

**unsubscribe**
    Unsubscribes an ordered directory. But this will not remove the directory from the repository.

**push local revision**
    Pushs the local changes of the respective collection to the repository with a new revision number. You have to comment your actual changes.

    *Note:* You need writing permissions for the update option.

**update to revision**
    Updates the respective collection in your webfolder in the chosen revision. 

    *Note:* Your local changes will be overwritten. 
    


Retrieve new collections
''''''''''''''''''''''''
Enables a searching of collections in the repository.

You can search for description or tags (like author, keywords, ...) to filter your query. The description and tags are defined in the `info.txt`_. If you do not insert anything, all permitted collections will be found.

*Note:* You can only find collections for which you have reading permissions.


Manage my collections
'''''''''''''''''''''
This tab shows all added or subscribed collections. You can apply different options to the collections.

**download**
    Downloads the respective collection in the newest revision into your webfolder.

**permissions**
    You can give users and groups read/write access to the respective collection.
 
    +---------------------------+-----------+-----------+----------------+
    |                           | no access | read only | read and write |
    +===========================+===========+===========+================+
    | **update to revision**    |    no     |    yes    |       yes      |
    +---------------------------+-----------+-----------+----------------+
    | **push local revision**   |    no     |    no     |       yes      |
    +---------------------------+-----------+-----------+----------------+
    | **find in search**        |    no     |    yes    |       yes      |
    +---------------------------+-----------+-----------+----------------+
    | **download option**       |    no     |    yes    |       yes      |
    +---------------------------+-----------+-----------+----------------+
    | **permissions option**    |    no     |    no     |       yes      |
    +---------------------------+-----------+-----------+----------------+

**unsubscribe**
    Unsubscribes ordered collection. But this will not remove the collection from the repository.


Additional Information
----------------------

info.txt
''''''''
Each directory or one of its parent directories must be contain an *info.txt*  before you can add it to the repository.
It contains the information of the respective directory. You can define a description, some details and search tags. This also helps to retrieve the directory easier.

It can be structured as follows::

    First, it starts with a summary of the collection. 
    
    This ends at a line which begins with:

    ### details ###

    In the following, the lines contain a detailed description of the collection 
    (e.g. how files are organized in subfolders; subject information; ...)
    
    This continues until a line which begins with:

    ### tags ###
    
    In this section you can add some tags like:
        * keyword: example, test
        * year: 2013

    All lines are parsed as follows:
        * Lines are split at the first  ":" - sign
        * parts are trimmed (whitespaces removed)
        * all parts except the first are concatenated
        * the first part is interpreted as tag name, the second part as tag
          content

Download an example: :download:`info.txt <resources/info.txt>`

