<!DOCTYPE HTML>
<html>

<head>
    <?php require "functions.php"; ?>
    <meta charset="utf-8">
    <title>CHIARA data management</title>
    <link rel="stylesheet" type="text/css" href="css/main.css">
    <link rel="icon" type="image/ico" href="favicon.ico">

</head>

<body bgcolor="#efefff">
    
    <table align="center" cellpadding=0 class="main">

    <!--<table align="center" cellspacing=1 border=0 cellpadding=0 
    style="border:0px;">-->
        <!-- chiara logo -->
        <tr>
            <td colspan=2 bgcolor="#afcfff">
                <img src="img/chiara-logo.png" width=900 height=120>
            </td>
        </tr>
        
        <!-- table headlines -->
        <tr>
            <td colspan=2 class="bright_bg">
                
                <!-- view my shared folder -->
                <a href='index.php?action=view'
                <?php     
                    if (array_key_exists('action', $_GET)) 
                        {$action = $_GET['action'];}
                    elseif (array_key_exists('subcommand', $_POST)) 
                        {$action = $_POST['action'];} 
                    else {$action = '';}

                    if ($action == 'view')
                        { echo ' class="my_a"'; } 
                    else {echo ' class="my_b"';} 
                ?>
                >view my shared folder</a>
                &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp;
                
                <!-- retrieve new collections -->
                <a href='index.php?action=retrieve' 
                <?php
                    if ($action == 'retrieve')
                        { echo ' class="my_a"'; } 
                    else {echo ' class="my_b"';} 
                ?>
                >retrieve new collections</a>
                &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp;
                
                <!-- manage my collections -->
                <a href='index.php?action=manage'
                <?php
                    if ($action == 'manage')
                        { echo ' class="my_a"'; } 
                    else {echo ' class="my_b"';} 
                ?>
                >manage my collections</a>
                &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp;
                &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp;

                <!-- documentation -->
                <span align="right"><a class="my_doc" href="doc/index.html" target="_blank"
                >Documentation</a></span>
            </td>
        </tr>
        
        <!-- manage all actions -->
        <tr>
            <td colspan=2>
                <?php
                 /* This is just a stub-php - it merely invokes python :)
                  * This is because several things might be necessary (file movement on 
                  * disk, ... where php might just not be perfectly appropriate.
                  */
                         
                    switch ($action)
                    {
                    case 'view':
                        view_dir();
                        break;
                    case 'manage':
                        manage_collections();
                        break;
                    case 'retrieve':
                        retrieve_collections();
                        break;
                    case 'preferences':
                        manage_preferences();
                    default:
                        break;
                    }
                    echo "<BR><BR>";
                ?>
            </td>
        </tr>
       
        <!-- shows logged in user --> 
        <tr>
            <td colspan=1 class="bright_bg">
                <a href='index.php?action=preferences'
                <?php
                    if ($action == 'preferences')
                        { echo ' class="my_a"'; } 
                    else {echo ' class="my_doc"';} 
                ?>
                >Preferences</a>
            </td>    
            <td colspan=1 align="right" class="bright_bg">
                <span align="right" class="add_info">
                <?php 
                    if ($_SERVER['PHP_AUTH_USER'] != "")
                    { echo "Login: ";
                      echo $_SERVER['PHP_AUTH_USER'];
                    } else
                    { echo "not logged in"; }
                ?>
                </span>
            </td>
        </tr>
    </table>
</body>

</html>
