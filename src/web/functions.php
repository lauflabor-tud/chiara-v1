<?php 

# Configuration parser
$cfg_parser = parse_ini_file("../config.ini", True);
# Set config parameters
$server_ip = $cfg_parser["server"]["server_ip"];
$apache_conf = $cfg_parser["server"]["apache_conf"];
$chiara_root = $cfg_parser["server"]["chiara_root"];
$users_webfolder = $cfg_parser["server"]["users_webfolder"];
$password_file = $cfg_parser["password"]["password_root"];
$realm = $cfg_parser["password"]["realm"];


function direscape($dir)
{
    /* escapes a directory with trailing and leading "'". */
    return "'" . str_replace("'", "\'", $dir) . "'";
}

function path_to_name($dir)
{
    /* cutting-out the file or collection name of a 
    given path */

    $name = $dir;
    # remove last /
    if(strlen($name)-1 == strrpos($name, "/"))
    {
        $name = substr($name, 0, strlen($name)-1);
    }
    # cutting-out from next to last
    if(strpos($name, "/") !== false)
    {
        $name = substr($name, strrpos($name, "/")+1); 
    } 
    return $name; 
}

function markup_success_failure($string)
{
    /* prints a formatted output of a string.
     * allowed formats are: 
     * - a line starts with "failure" -> red
     * - a line starts with "success" -> green
     * - any other string -> dark grey text
     * each line is separated by <br />
     * */
    $output = str_replace("\n\r", "\n", $string);
    $allLines = explode("\n", $output);
    /* Note: if the output starts with "failure", the return is 0, which is 
        * evaluated as "false". Hence, also compare the datatype (=== or !== in php) 
        * */
    if (stripos($allLines[0], "failure") !== false)
    {
        echo '<span class="failure">' . $allLines[0]. '<BR>' . $allLines[1] . "<BR>\n</span>\n";

    }
    else
    {
        foreach ($allLines as $line)
        {
            if (strpos($line,"success") === 0)
            {
                echo '<span class="success">' . $line . "</span><BR>\n";
            }
            else
            {
                echo '<span class="add_info">' . $line . "</span><BR>\n";
            }
        }
    }
}

function view_dir()
{
    /* This function is a general "meta-function" in the sense that it is the 
     * primary function of the collection management (user-level). It invokes 
     * other functions for the details.
     * */
    
    if (array_key_exists('subcommand', $_GET)) {$subcommand = $_GET['subcommand'];}
    else {$subcommand = ''; }
    switch ($subcommand)
    {
        case '':
            /* initial click on "view" -> view webfolder*/
            view_my_directory();
            break;
        case 'unsubscribefolder':
            unsubscribe_folder();
            break;
        case 'addcollection':
            add_collection();
            break;
        case 'pushrevisionform':
            view_push_revision_form();
            break;
        case 'pushrevision':
            push_revision();
            break;
        case 'pullrevisionform':
            view_pull_revision_form();
            break;
        case 'pullrevision':
            pull_revision();
            break;
        default:
            echo '<span class="failure">failure!<br />invalid subcommand given</span>';
            echo 'invalid command was: |'. $subcommand . "|\n";
            break;
    }
}

function get_file_size($path)
{
    $fullpath = "../data/" . $_SERVER['PHP_AUTH_USER'] . $path;

    $size = shell_exec("du -bs " . direscape($fullpath) . " | awk '{print $1}'");
    
    if ($size >= pow(10,12)){
        return round($size / pow(10,12), 2) . " TB";
    } elseif ($size >= pow(10,9)){
        return round($size / pow(10,9), 2) . " GB";
    } elseif ($size >= pow(10,6)){
        return round($size / pow(10,6), 2) . " MB";
    } elseif ($size >= pow(10,3)){
        return round($size / pow(10,3), 2) . " KB";
    } else {
        return trim($size) . " B";
    }
}

function view_my_directory()
{
    if (isset($_GET['dir']))
    {
        $dir = $_GET['dir'];
        if (empty($dir))
        {
            $dir = "/";
        }
    }
    else
    {
        $dir = '/';
    }

    echo "<BR>";
    echo '<Table border=0 cellspacing=2 cellpadding=1 width=900>';
    echo "<TR>\n";
    echo '<TD colspan=3><span class="curr_dir">' . $dir . "</span></TD></TR>\n";

    echo "<TR><TD colspan=3>\n";
    /* possibly add .. to go upwards */
    if ($dir != '/')
    {
        if (substr($dir,1,1) == "/")
        {
         $dir = substr($dir,1);
        }
        $subdirs = explode("/", $dir);
        array_pop($subdirs);
        array_pop($subdirs);
        $higherdir = implode("/", $subdirs);
        echo '<a class="dir" href="index.php?action=view&dir=' . urlencode($higherdir . "/" ) . '">..</a><BR>' . "\n";
    }

    echo "</TD></TR>\n";
    
    /* echo "dir: " . $dir; */
    $cmd = "../py/chiara.py user -u " . $_SERVER['PHP_AUTH_USER'] . " -l " . direscape($dir);
    /*    echo $cmd; */
    $output = shell_exec($cmd);
    $output = str_replace("\n\r", "\n", $output);
    $allLines = explode("\n", $output);

    /* start at 1 - omit first line! */
    for ($i = 1; $i < count($allLines); ++$i)
    {
        echo "<TR>";
        $fileinfo = explode("\t", $allLines[$i]);
 
        /* directory which is not a collection */
        if ($fileinfo[0] == "d" or $fileinfo[0] == "Dx")
        {
            echo '<TD width="25%"><a class="dir" href="index.php?action=view&dir=' . urlencode($dir . $fileinfo[1]) . '/">';
            echo $fileinfo[1] . "</a></TD>";
            echo '<TD width="25%" class="shortinfo">' . 'size: ' . get_file_size($dir . $fileinfo[1]) . "</TD>\n";
            echo '<TD width="50%" align="right"> &nbsp;';
            /* only allow top-level folders to be added to the collections! */
            if ($dir == '/')
            {
            echo '<a href="index.php?action=view&subcommand=addcollection&folder=';
            echo urlencode($dir . $fileinfo[1] . '/');
            echo '" class="addcollection">'. "add to collections" . "</a>";
            }
            echo "</TD>\n";
        }
        /* directory which is already a collection */
        elseif ($fileinfo[0]=="Dr" or $fileinfo[0]=="Dw")
        {
            /* only allow top-level folders to be added to the collections! */
            if ($dir == '/')
            {
                echo '<TD width="25%"><a class="dir" href="index.php?action=view&dir=' . urlencode($dir . $fileinfo[1]) . '/">' . $fileinfo[1] . "</a></TD>";
                echo '<TD width="25%" class="shortinfo">' . 'size: ' . get_file_size($dir . $fileinfo[1]) . '&nbsp&nbsp|&nbsp&nbsp' . 'rev.: ' . $fileinfo[2] . "</TD>\n";
                echo '<TD width="50%" align="right"> &nbsp;';
                if ($fileinfo[0] == "Dw")
                {
                    // push local revision
                    echo '<a href="index.php?action=view&subcommand=pushrevisionform&folder=';
                    echo urlencode($dir . $fileinfo[1] . '/');
                    echo '&comment=';
                    echo '&wrongcomment=false';
                    echo '" class="updatecollection">'. "push local revision" . "</a>";
                }
            
                // update to version
                echo "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;";
                echo '<a href="index.php?action=view&subcommand=pullrevisionform&folder=';
                echo urlencode($dir . $fileinfo[1] . '/');
                echo '" class="updatecollection">'. "update to revision" . "</a>";
                
                // unsubsrcibe folder
                echo "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;";
                echo '<a href="index.php?action=view&subcommand=unsubscribefolder&folder=';
                echo urlencode($dir . $fileinfo[1] . '/');
                echo '" class="unsubscribecollection">'. "unsubscribe" . "</a>";
            }
            else
            {
                echo '<TD width="25%"><a class="dir" href="index.php?action=view&dir=' . urlencode($dir . $fileinfo[1]) . '/">';
                echo $fileinfo[1] . "</a></TD>";
                echo '<TD width="25%" class="shortinfo">' . 'size: ' . get_file_size($dir . $fileinfo[1]) . "</TD>\n";
                echo '<TD width="50%" align="right"> &nbsp;';
            }
            echo "</TD>\n";
        }
        elseif ($fileinfo[0] == "f")
        {
            echo '<TD width="25%"><a class="file" href="download-file.php?filepath=' . urlencode($dir . $fileinfo[1]) . '">' . $fileinfo[1] . "</a></TD>";
            echo '<TD width="25%" class="shortinfo"">' . "size: " . get_file_size($dir . $fileinfo[1]) . "</TD>\n";
            echo '<TD width="50%">&nbsp;</TD>' . "\n";
        }
        echo "</TR>\n";
    }
    echo "</table>\n";
}


function unsubscribe_folder()
{
    /* unsubscribe by folder name */
    $cmd = "../py/chiara.py user -u " . $_SERVER['PHP_AUTH_USER'] . ' --unsubscribe ' . 
        direscape($_GET['folder']);
    $output = shell_exec($cmd);
    markup_success_failure($output);
}

function add_collection()
{
    echo '<span class="add_info">adding ' . $_GET['folder'] . "' to ";
    echo $_SERVER['PHP_AUTH_USER'] . "'s collections</span><BR><BR>\n";

    $cmd = "../py/chiara.py user -u " . $_SERVER['PHP_AUTH_USER'] . ' --add ' . direscape($_GET['folder']);
    #echo "shell command:<BR>" . $cmd . "<BR>\n";
    $output = shell_exec($cmd);
    #echo "output: |" . $output ."|";
    markup_success_failure($output);
}


function view_push_revision_form()
{
    $cname = path_to_name($_GET['folder']);

    /* displays the 'push revision' formular for metadata */
    echo '<form name="pushrevision" action="index.php">';
    echo '<input type="hidden" name="action" value="view">' . "\n";
    echo '<input type="hidden" name="subcommand" value="pushrevision">' . "\n";
    echo '<input type="hidden" name="folder" value=' . $_GET['folder'] . '>' . "\n"; 
    echo '<table border=0 cellspacing=2 cellpadding=2>';
        echo "<TR>\n";
        echo '<TD class="smallTitle" colspan=3>Collection</TD>' . "\n";
        echo "</TR>\n";
        echo "<TR>\n";
        echo '<TD class="collectionName" width=200>' . $cname . "</TD>" . "\n"; 
        echo "</TR>\n";
        echo "<TR>\n";
        echo '<TD class="smallTitle">Comment</TD>' . "\n";
        echo "</TR>\n";
    echo '</table>'; 
    
    echo '<table border=0 style="margin-left:18px" cellspacing=2 cellpadding=2>';
        if($_GET['wrongcomment'] === 'noinput'){
            echo "<TR>\n";
            echo '<TD><span class="failure">Please comment your local changes!</span></TD>' . "\n";
            echo "</TR>\n";
        }
        if($_GET['wrongcomment'] === 'doublequotes'){
            echo "<TR>\n";
            echo '<TD><span class="failure">Please use ' . "'single qutoes'" . ' instead of "double quotes"!</span></TD>' . "\n";
            echo "</TR>\n";
        }
        echo "<TR>\n";
        echo '<TD><TEXTAREA rows="4" cols="50" id="comment" name="comment">' . $_GET['comment'] . '</TEXTAREA></TD>' . "\n";
        echo "</TR>\n";   
        echo "<TR>\n";
        echo '<TD><INPUT type="submit" value="push" name="push"></TD>' . "\n";
        echo "</TR>\n";
    echo '</table>';
    echo '</form>';

}

function push_revision()
{
    # only push if comment box is filled
    if(preg_match('/[a-zA-Z0-9]+/', $_GET['comment']) == false)
    {
        $push_form_link = "index.php?action=view&subcommand=pushrevisionform&folder=" . $_GET['folder'] . "&comment=" . "&wrongcomment=noinput";
        header("Location: " . $push_form_link);
        view_push_revision_form();
    } 
    elseif(preg_match('/\"/', $_GET['comment']))
    {
        $push_form_link = "index.php?action=view&subcommand=pushrevisionform&folder=" . $_GET['folder'] . "&comment=" . $_GET['comment'] . "&wrongcomment=doublequotes";
        header("Location: " . $push_form_link);
        view_push_revision_form();
    }
    else
    {
        $cmd = "../py/chiara.py user -u " . $_SERVER['PHP_AUTH_USER'] . ' --push_revision ' . direscape($_GET['folder']) . ' "' . $_GET['comment'] . '"';
        $output = shell_exec($cmd);
        markup_success_failure($output);
    }
}


function view_pull_revision_form()
{   
    $cname = path_to_name($_GET['folder']);
    $cmd = "../py/chiara.py user -u " . $_SERVER['PHP_AUTH_USER'] . ' --list_revisions ' . $cname;
    # output = list of "collection_name | revision | comment | modified"
    $output = shell_exec($cmd);
    $allLines = explode("\n",$output);
    
    /* display the 'pull revision' formular for metadata */
    echo '<form name="pullrevision" action="index.php">';
    echo '<input type="hidden" name="action" value="view">' . "\n";
    echo '<input type="hidden" name="subcommand" value="pullrevision">' . "\n";
    echo '<input type="hidden" name="collection" value=' . $cname . '>' . "\n"; 

    echo '<table border=0 cellspacing=2 cellpadding=2>';
        echo "<TR>\n";
        echo '<TD class="smallTitle" colspan=3>Collection</TD>' . "\n";
        echo "</TR>\n";
        
        echo "<TR>\n";
        echo '<TD class="collectionName" width=200 colspan=3>' . $cname . "</TD>" . "\n"; 
        echo "</TR>\n";
    echo '</table>';   
    
    echo '<table border=0 cellspacing=2 cellpadding=2>';
        echo "<TR>\n";
        echo '<TD class="smallTitle" colspan=3>Revision</TD>' . "\n";
        echo "</TR>\n";
    echo '</table>';   
    
    echo '<table border=0 style="margin-left:18px" cellspacing=2 cellpadding=2>';
        echo "<TR>\n";
        echo '<TD colspan=1>';
        echo '<select name="revision"' . "\n";
        echo '<option value="unknown">' . "--select revision--</option>\n";
        foreach ($allLines as $line)
        {
            $elements = explode("\t", $line);
            if (count($elements) == 3)
            {
                echo '<option selected value="' . $elements[0] . '">' . $elements[0] . "</option>\n";
            }
        }
        echo "</select>\n";
        echo '</TD>';
        echo '<TD colspan=1><input type="submit" onclick="' . "return confirm('Note, that all your local changes will be overwritten.');" . '" value="pull" name="pull"></TD>' . "\n";
        echo "</TR>\n";
    echo '</table>';   
    
    echo '<table border=0 cellspacing=2 cellpadding=2>';
        echo "<TR>\n";
        echo '<TD class="smallTitle" colspan=3>Compendium</TD>' . "\n";
        echo "</TR>\n";
    echo '</table>';
   
    echo '<table class="listdetails">';
        echo "<THEAD\n";
        echo "<TR>\n";
        echo '<TH class="listdetails" colspan=1>Revision</TD>' . "\n";
        echo '<TH class="listdetails" colspan=1>Comment</TD>' . "\n";
        echo '<TH class="listdetails" colspan=1>Modified</TD>' . "\n";
        echo "</TR>\n";
        echo "</THEAD\n";
        
        echo "<BODY\n";
        foreach ($allLines as $line)
        {
            echo "<TR>\n";
            $elements = explode("\t", $line);
            if (count($elements) == 3)
            {
                echo '<TD class="listdetails" colspan=1>' . $elements[0] . '</TD>' . "\n";
                echo '<TD class="listdetails" colspan=1>' . $elements[1] . '</TD>' . "\n";
                echo '<TD class="listdetails" colspan=1>' . $elements[2] . '</TD>' . "\n";
            }
            echo "</TR>\n";
        }
        echo "</BODY\n";
    echo '</table>';
 
    echo '<table border=0 cellspacing=2 cellpadding=2></table>';

    echo '</form>';
}

function pull_revision()
{
    $cmd = "../py/chiara.py user -u " . $_SERVER['PHP_AUTH_USER'] . ' --pull_revision ' . $_GET['collection'] . ' ' . $_GET['revision'];
    $output = shell_exec($cmd);
    markup_success_failure($output);
}


function add_collection_by_id()
{
    echo '<span class="add_info">adding ' . $_GET['cid'] . " revision ".$_GET['crev']." to ";
    echo $_SERVER['PHP_AUTH_USER'] . "'s collections</span><BR><BR>\n";

    $cmd = "../py/chiara.py user -u " . $_SERVER['PHP_AUTH_USER'] . " --subscribe '" . $_GET['cid'] . '-' .
        $_GET['crev'] . "' ";
   # echo "shell command:<BR>" . $cmd . "<BR>\n";
    $output = shell_exec($cmd);
    #echo "output: |" . $output ."|";
    markup_success_failure($output);
    #echo "sorry - not yet implemented!";
    
}


function retrieve_collections()
{
    /* This function is a general "meta-function" in the sense that it is the 
     * primary function for obtaining new collections.It invokes * other 
     * functions for the details.
     * */
    
    if (array_key_exists('subcommand', $_GET)) {$subcommand = $_GET['subcommand'];}
    else {$subcommand = ''; }
    switch ($subcommand)
    {
        case '':
            /* initial click on "retieve" -> show search formular */
            show_search_formular();
            break;
        case 'EvaluateSearch':
            evaluate_search();
            break;
        case 'subscribe':
            add_collection_by_id();
            break;
        default:
            echo '<span class="failure">failure!<br />invalid subcommand given</span>';
            break;
    }
}

function evaluate_search()
{
    /* displays the search results */
    $cmd = "../py/chiara.py user -u " . $_SERVER['PHP_AUTH_USER'] . ' --search ' . 
        direscape($_GET['description']) . ' ' . direscape($_GET['tags']);
    $output = shell_exec($cmd);
    $allLines = explode("\n", $output);
    echo '<table border=0 cellspacing=2 cellpadding=2>' . "\n";
    foreach ($allLines as $line)
    {
        $elements = explode("\t", $line);
        if (count($elements) == 4)
        {
            echo "<TR>\n";
            echo '<TD class="collection" width=200>';
            echo $elements[2];
            echo "</TD>\n";
            echo '<TD class="shortinfo">' . $elements[3] . "</TD>\n";
            echo "<TD>&nbsp;&nbsp;&nbsp;&nbsp;";
            echo '<a href="index.php?action=retrieve&subcommand=subscribe&cid=' . $elements[0];
            echo '&crev=' . $elements[1] .'" class="addcollection">subscribe</a>' . "\n";
            echo "</TD>\n";
            echo "</TR>\n";
        }
    }
    echo '</table>' . "\n";
}


function show_search_formular()
{
    /* displays the search formular for metadata */
    ?> <form name="search" action="index.php">
    <input type="hidden" name="action" value="retrieve">
    <input type="hidden" name="subcommand" value="EvaluateSearch">
    <?
    echo '<table border=0 cellspacing=2 cellpadding=2>
        <tr>
            <td class="shortinfo">Description:</td>
            <td class="shortinfo"><input type="text" name="description" size=80 ></td>
        </tr>
        <tr>
            <td class="shortinfo">Tags:</td>
            <td class="shortinfo"><input type="text" name="tags" size=80 /></td>
        </tr>
        <tr>
            <td class="shortinfo">&nbsp;</td>
            <td class="shortinfo">example: "author: moritz; keywords: locomotion,
            running"<br /> if you just enter values, all tags will be searched.<br />
            example: "locomotion, running, moritz"<br />
            <b>Note:</b> use comma to separate values!
            </td>
        </tr>
        <tr>
            <td>&nbsp;</td>
            <td><input type="submit" value="search" name="search"></td>
        </table></form>';
}

function manage_collections()
{
    /* This function is a general "meta-function" in the sense that it is the 
     * primary function of the collection management (user-level). It invokes 
     * other functions for the details.
     * */
    
    if (array_key_exists('subcommand', $_GET)) {$subcommand = $_GET['subcommand'];}
    else {$subcommand = ''; }
    switch ($subcommand)
    {
        case '':
            /* initial click on "manage" -> view collections */
            view_my_collections();
            break;
        case 'unsubscribe':
            unsubscribe_by_id();
            break;
        case 'download':
            download_by_id();
            break;
        case 'manageRights':
            manage_rights_view();
            break;
        case 'revokeWrite':
            manage_revoke_write();
            manage_rights_view();
            break;
        case 'grantWrite':
            manage_grant_write();
            manage_rights_view();
            break;
        case 'revoke':
            manage_revoke();
            manage_rights_view();
            break;
        case 'grantNewGroup':
            manage_grant_new_group();
            manage_rights_view();
            break;
        case 'grantNewUser':
            manage_grant_new_user();
            manage_rights_view();
            break;
        default:
            echo '<span class="failure">failure!<br />invalid subcommand given</span>';
            echo 'invalid command was: |'. $subcommand . "|\n";
            break;
    }
}

function manage_grant_new_group()
    { 
        /* grants a new group access rule */
        $cmd = "../py/chiara.py user -u " . $_SERVER['PHP_AUTH_USER'] . ' --grant_group ' . 
        $_GET['id'] .' ' . $_GET['group'] . ' ' . $_GET['access_type'];
        $output = shell_exec($cmd);
        markup_success_failure($output);

    }

function manage_grant_new_user()
    { 
        /* grants a new group access rule */
        $cmd = "../py/chiara.py user -u " . $_SERVER['PHP_AUTH_USER'] . ' --grant_user ' . 
        $_GET['id'] .' ' . $_GET['user'] . ' ' . $_GET['access_type'];
        #echo $cmd;
        $output = shell_exec($cmd);
        markup_success_failure($output);
    }

function manage_grant_write()
{
    /* grants a new group writing rule */
    if ($_GET['atype'] == 'group'){$granttype = ' --grant_group ';}
    if ($_GET['atype'] == 'user'){$granttype = ' --grant_user ';}
    $cmd = "../py/chiara.py user -u " . $_SERVER['PHP_AUTH_USER'] . $granttype . 
    $_GET['id'] .' ' . $_GET['aid'] . ' rw';
    #echo $cmd;
    $output = shell_exec($cmd);
    markup_success_failure($output);
#        echo '<span class="failure"> granting write access - NOT YET IMPLEMENTED!</span>';
}

function manage_revoke_write()
{
     /* revokes writing rights */
    if ($_GET['atype'] == 'group'){$granttype = ' --grant_group ';}
    if ($_GET['atype'] == 'user'){$granttype = ' --grant_user ';}
    $cmd = "../py/chiara.py user -u " . $_SERVER['PHP_AUTH_USER'] . $granttype . 
    $_GET['id'] .' ' . $_GET['aid'] . ' ro';
    #echo $cmd;
    $output = shell_exec($cmd);
    markup_success_failure($output);
 #   echo '<span class="failure"> revoking write access - NOT YET IMPLEMENTED!</span>';
}

function manage_revoke()
{
     /* revokes complete access to collection */
    if ($_GET['atype'] == 'group'){$granttype = ' --grant_group ';}
    if ($_GET['atype'] == 'user'){$granttype = ' --grant_user ';}
    $cmd = "../py/chiara.py user -u " . $_SERVER['PHP_AUTH_USER'] . $granttype . 
    $_GET['id'] .' ' . $_GET['aid'] . ' none';
    #echo $cmd;
    $output = shell_exec($cmd);
    markup_success_failure($output);
}

function manage_rights_view()
{
    /* This function shows a form that allows to grant or revoke rights */
    $cmd = "../py/chiara.py user -u " . $_SERVER['PHP_AUTH_USER'] .
            ' --view_rights "' . $_GET['id'] . '"'; 
    #echo "shell command:<BR>" . $cmd . "<BR>\n";
    $output = shell_exec($cmd); #, $output);
    $allLines = explode("\n", $output);
    echo '<table border=0 cellspacing=2 cellpadding=2 width=690>' . "\n";
    $accessType='None';
    $n_in_list = 0;
    
    echo "<TR>\n";
    echo '<TD class="smallTitle" colspan=3>Collection</TD>';
    echo "</TR>\n";
    echo "<TR>\n";
    echo '<TD class="collectionName" width=200>' . $_GET['cname'] . "</TD>";
    echo "</TR>\n";

    foreach ($allLines as $line)
    {
        $elements = explode("\t", $line);
        if (count($elements) == 3)
        {
            echo "<TR>\n";
            echo '<TD class="userName" width=200>';
            echo $elements[0];
            echo "</TD>\n";
            echo '<TD class="permissionInfo">';
            if ($elements[2] == '1') { echo "read / write"; }
            else { echo "read only"; }
            echo "</TD>\n";
            echo '<TD class="permissionActions">'. "\n";
            if ($elements[2] == '1') { 
                echo '<a href="index.php?action=manage&subcommand=revokeWrite&id='.
                    $_GET['id'] . '&aid=' . $elements[1] . '&atype=' . $accessType . '&cname=' . $_GET['cname'] .
                    '" class="permissions">revoke write access</a>'. "\n"; 
            }
            else { 
                echo '<a href="index.php?action=manage&subcommand=grantWrite&id='.
                    $_GET['id'] . '&aid=' . $elements[1] . '&atype=' . $accessType . '&cname=' . $_GET['cname'] .
                    '" class="permissions">grant write access</a>'. "\n"; 
            }
            echo "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;";
            echo '<a href="index.php?action=manage&subcommand=revoke&id=' .
                 $_GET['id'] . '&aid=' . $elements[1] . '&atype=' . $accessType . '&cname=' . $_GET['cname'] .
                    '" class="permissions">remove</a>' . "\n";
            echo "</TD>\n";
            echo "</TR>\n";
            $n_in_list += 1;
        }
        else
        {
            if (stripos($line, "user") !== false)
            {
                echo "<TR>\n";
                echo '<TD class="smallTitle" colspan=3>Users</TD>';
                echo "</TR>\n";
                echo "<TR>\n";
                echo '<TD class="shortinfo" colspan=3><b>NOTE:</b> '.
                    'Users not listed here can still have access through group membership!</TD>';
                echo "</TR>\n";
                $accessType='user';
            }

            elseif (stripos($line, "group") !== false)
            {
                if ($n_in_list == 0) {
                    /* no users found 
                     * NOTE: this can happen only if the current user is 
                     * excluded from the list (e.g. in the python part of the 
                     * code)
                     * */

                        echo "<TR>\n";
                        echo '<TD class="shortinfo" colspan=3>(no users found)</TD>';
                        echo "</TR>\n";
                }
                echo "<TR>\n";
                echo '<TD class="smallTitle" colspan=3>Groups</TD>';
                echo "</TR>\n";
                $accessType='group';
                $n_in_list = 0;
            }
        }
    }
    if ($n_in_list == 0) {
        /* no groups found */
            echo "<TR>\n";
            echo '<TD class="shortinfo" colspan=3>(no groups found)</TD>';
            echo "</TR>\n";
    }

    # add "add user access rule"
    echo "<TR>\n";
    echo '<form action="index.php">';
    echo '<input type="hidden" name="action" value="manage">' . "\n";
    echo '<input type="hidden" name="subcommand" value="grantNewUser">' . "\n";
    echo '<input type="hidden" name="id" value="' . $_GET['id'] . '">' . "\n";
    echo '<input type="hidden" name="cname" value="' . $_GET['cname'] . '">' . "\n";
    echo '<TD class="smallTitle" colspan=3>add user access rule</TD>';
    echo "</TR>\n";
    echo '<TD>';
    echo '<select name="user">' . "\n";
    echo '<option value="unknown">' . "--select user--</option>\n";
    $output = shell_exec('../py/chiara.py sys listusers');
    echo $output;
    $allLines = explode("\n",$output);
    foreach ($allLines as $line)
    {
        $elements = explode("\t", $line);
        if (count($elements) == 3)
        {
            echo '<option value="' . $elements[0] . '">' . $elements[1] . "</option>\n";
        }
    }
    echo "</select>\n";
    echo '</TD>';
    echo '<TD><select name="access_type">' . "\n";
    echo '<option value="unknown">' . "--select access type--</option>\n";
    echo '<option value="ro">' . "read only</option>\n";
    echo '<option value="rw">' . "read and write</option>\n";
    echo '</select></TD>';
    echo '<TD align="right"><input type="submit" value="grant"></TD>';
    echo "\n</form>\n";
    echo "</TR>\n";
   
    # add "add group access rule"
    echo "<TR>\n";
    echo '<form action="index.php">';
    echo '<input type="hidden" name="action" value="manage">' . "\n";
    echo '<input type="hidden" name="subcommand" value="grantNewGroup">' . "\n";
    echo '<input type="hidden" name="id" value="' . $_GET['id'] . '">' . "\n";
    echo '<input type="hidden" name="cname" value="' . $_GET['cname'] . '">' . "\n";
    echo '<TD class="smallTitle" colspan=3>add group access rule</TD>';
    echo "</TR>\n";
    echo '<TD>';
    echo '<select name="group">' . "\n";
    echo '<option value="unknown">' . "--select group--</option>\n";
    $output = shell_exec('../py/chiara.py sys listgroups');
    echo $output;
    $allLines = explode("\n",$output);
    foreach ($allLines as $line)
    {
        $elements = explode("\t", $line);
        if (count($elements) == 2)
        {
            echo '<option value="' . $elements[0] . '">' . $elements[1] . "</option>\n";
        }
    }
    echo "</select>\n";
    echo '</TD>';
    echo '<TD><select name="access_type">' . "\n";
    echo '<option value="unknown">' . "--select access type--</option>\n";
    echo '<option value="ro">' . "read only</option>\n";
    echo '<option value="rw">' . "read and write</option>\n";
    echo '</select></TD>';
    echo '<TD align="right"><input type="submit" value="grant"></TD>';
    echo "\n</form>\n";
    echo "</TR>\n";

    echo '</table>' . "\n";

}



function download_by_id()
{
    echo '<span class="add_info">downloading collection ... for ';
    echo $_SERVER['PHP_AUTH_USER'] . "</span><BR><BR>\n";
    $cmd = "../py/chiara.py user -u " . $_SERVER['PHP_AUTH_USER'] .
            ' --d "' . $_GET['id'] . '"'; 
    #echo "shell command:<BR>" . $cmd . "<BR>\n";
    $output = shell_exec($cmd); #, $output);
    #echo "output: |" . $output ."|";
    markup_success_failure($output);
}

function view_my_collections()
{
/* This function creates a list of all collections the user is subscibed to and 
 * has modify access to */
    if (array_key_exists('folder', $_GET)) { $folder=direscape($_GET['folder']); }
    else {$folder='';}
    $cmd = "../py/chiara.py user -u " . $_SERVER['PHP_AUTH_USER'] . ' --view_collection ' . 
        $folder;
    # echo $cmd;
    $output = shell_exec($cmd);
    $allLines = explode("\n", $output);
    echo "<table border=0 cellspacing=2>";
    foreach ($allLines as $line)
    {
        $elements = explode("\t", $line);
        if (count($elements) == 5)
        {
        echo '<tr><td width=240 class="collection">' . $elements[3] . "</td>\n";
        echo '<td width=400 class="shortinfo">' . $elements[4] . "</td>\n";
        echo '<td align="right">';
        if ($elements[0]=='m')
        {
        echo '&nbsp;<a href="index.php?action=manage&subcommand=manageRights&id=' . trim($elements[1]) . '&cname=' . $elements[3] . 
            '" class="permissions">permissions</a>';
        }
        echo '&nbsp;<a href="index.php?action=manage&subcommand=unsubscribe&id=' . trim($elements[1]) . 
            '-'. trim($elements[2]) . '" class="unsubscribecollection">unsubscribe</a>';
        echo '&nbsp;<a href="index.php?action=manage&subcommand=download&id=' . trim($elements[1]) . 
            '-'. trim($elements[2]) . '" class="downloadcollection">download</a>';
        echo "</td>\n";
        echo "</tr>\n";
        }
    }
    echo "</table>";
}

function unsubscribe_by_id()
{
    /* remove the collection ID - REV from user's subscriptions */
    $cmd = "../py/chiara.py user -u " . $_SERVER['PHP_AUTH_USER'] . ' --unsubscribe_id ' .
        $_GET['id'];
    $output = shell_exec($cmd);
    markup_success_failure($output);
}

function manage_preferences()
{
    /* This function is a general "meta-function" in the sense that it is the 
     * primary function of the collection management (user-level). It invokes 
     * other functions for the details.
     * */
    if (array_key_exists('subcommand', $_GET)) {$subcommand = $_GET['subcommand'];}
    elseif (array_key_exists('subcommand', $_POST)) {$subcommand = $_POST['subcommand'];}
    else {$subcommand = ''; }
    switch ($subcommand)
    {
        case '':
            /* initial click on "Preferences" -> list all preferences */
            list_preferences();
            break;
        case 'changepasswordform':
            view_change_password_form();
            break;
        case 'changepassword':
            change_password();
            break;
        case 'adduserform':
            add_user_form();
            break;
        case 'adduser':
            add_user();
            break;
        case 'removeuserform':
            remove_user_form();
            break;
        case 'removeuser':
            remove_user();
            break;
        case 'listallusers':
            list_all_users();
            break;
        case 'addgroupform':
            add_group_form();
            break;
        case 'addgroup':
            add_group();
            break;
        case 'removegroupform':
            remove_group_form();
            break;
        case 'removegroup':
            remove_group();
            break;
        case 'adduserstogroupform':
            add_users_to_group_form();
            break;
        case 'adduserstogroup':
            add_users_to_group();
            break;
        case 'removeusersfromgroupform':
            remove_users_from_group_form();
            break;
        case 'removeusersfromgroup':
            remove_users_from_group();
            break;
        case 'listallgroups':
            list_all_groups();
            break;
        default:
            echo '<span class="failure">failure!<br />invalid subcommand given</span>';
            echo 'invalid command was: |'. $subcommand . "|\n";
            break;
    }
}

function list_preferences()
{
    /* display a list of all user preferences */
    echo 
    '<table border=0 cellspacing=2 cellpadding=2><tr>
        <td colspan="1" valign="top" width="250">
        <table border=0 cellspacing=2 cellpadding=2>
            <tr><td class="smallTitle">User Preferences</td></tr>
            <tr><td> 
                <a href="index.php?action=preferences&subcommand=changepasswordform" class="preference">
                change password</a>
            </td></tr>
        </table></td>';

    // check if user is an admin 
    $cmd = "../py/chiara.py user -u " . $_SERVER['PHP_AUTH_USER'] . ' --is_admin ' .
        $_SERVER['PHP_AUTH_USER'];
    $output = shell_exec($cmd);
    if(intval($output) == 1){
    /* display a list of all admin preferences */
    echo
        '<td colspan="1" valign="top" width="250">
        <table border=0 cellspacing=2 cellpadding=2>
            <tr><td class="smallTitle">Admin Preferences</td></tr>
            <tr><td class="subTitle">Manage users</td></tr>
            <tr><td>
                <a href="index.php?action=preferences&subcommand=adduserform" class="preference">Add user</a>
            </td></tr>
            <tr><td>
                <a href="index.php?action=preferences&subcommand=removeuserform" class="preference">Remove user</a>
            </td></tr>
            <tr><td>
                <a href="index.php?action=preferences&subcommand=listallusers" class="preference">List all users</a>
            </td></tr>

            <tr><td class="subTitle">Manage groups</td></tr>
            <tr><td>
                <a href="index.php?action=preferences&subcommand=addgroupform&nrgroups=1&more=false&add=false" class="preference">Add groups</a>
            </td></tr>
            <tr><td>
                <a href="index.php?action=preferences&subcommand=removegroupform&nrgroups=1&more=false&remove=false" class="preference">Remove groups</a>
            </td></tr>
            <tr><td>
                <a href="index.php?action=preferences&subcommand=adduserstogroupform&nrusers=1&more=false&add=false" class="preference">Add users to group</a>
            </td></tr>
            <tr><td>
                <a href="index.php?action=preferences&subcommand=removeusersfromgroupform&nrusers=1&more=false&remove=false" class="preference">Remove users from group</a>
            </td></tr>
            <tr><td>
                <a href="index.php?action=preferences&subcommand=listallgroups" class="preference">List all groups</a>
            </td></tr>
        </table></td>';
    }
    echo '</tr></table>';
}

function view_change_password_form()
{
    /* displays the 'change password' formular for metadata */
    echo '<form method="post" name="changepassword" action="index.php">';
    echo '<input type="hidden" name="action" value="preferences">' . "\n";
    echo '<input type="hidden" name="subcommand" value="changepassword">' . "\n";
    echo '<table border=0 cellspacing=2 cellpadding=2>' . "\n";

    echo '<tr>
            <td colspan=2 class="shortinfo">Please enter your current and new password in the following text fields.<br />You have to use at least 5 characters for your new password.</td>
        </tr>';
        // if current password is wrong
        if(array_key_exists('pwfailed', $_GET) && $_GET['pwfailed'] === 'currentpw'){
            echo "<TR>\n";
            echo '<TD colspan=2><span class="failure">Your current password is not correct!</span></TD>' . "\n";
            echo "</TR>\n";
        }
        // if the new passwords do not match
        elseif(array_key_exists('pwfailed', $_GET) && $_GET['pwfailed'] === 'newpw_nomatch'){
            echo "<TR>\n";
            echo '<TD colspan=2><span class="failure">The new passwords do not match!</span></TD>' . "\n";
            echo "</TR>\n";
        }
        // if the new password is too short
        elseif(array_key_exists('pwfailed', $_GET) && $_GET['pwfailed'] === 'newpw_tooshort'){
            echo "<TR>\n";
            echo '<TD colspan=2><span class="failure">Your new password is too short. Please use at least 5 characters!</span></TD>' . "\n";
            echo "</TR>\n";
        }
    echo '<tr>
            <td class="shortinfo">Current password:</td>
            <td class="shortinfo"><input type="password" autocomplete="off" name="currentpw" size=15 ></td>
        </tr>
        <tr>
            <td class="shortinfo">New password:</td>
            <td class="shortinfo"><input type="password" autocomplete="off" name="newpw" size=15 /></td>
        </tr>
        <tr>
            <td class="shortinfo">Confirm new password:</td>
            <td class="shortinfo"><input type="password" autocomplete="off" name="confirmedpw" size=15 /></td>
        </tr>
        <tr>
            <td>&nbsp;</td>
            <td><input type="submit" value="change password" name="changepassword_button"></td>
        </tr>
        </table></form>';
}


function change_password()
{
    // create the current line of the user in the password "dav"-file
    $encr_current_pw = trim(shell_exec("echo -n " . $_SERVER['PHP_AUTH_USER'] . ":" . $GLOBALS["realm"] . ":" . $_POST['currentpw'] . " | md5sum | awk '{print $1}'"));
    $current_davline = $_SERVER['PHP_AUTH_USER'] . ":" . $GLOBALS["realm"] . ":" . $encr_current_pw;
    
    // if current password is wrong
    if(intval(shell_exec("grep -c " . $current_davline . " " . $GLOBALS["password_file"])) === 0)
    {
        $change_password_form_link = "index.php?action=preferences&subcommand=changepasswordform&pwfailed=currentpw";
        header("Location: " . $change_password_form_link);
        view_change_password_form();
    } 
    // if the new passwords do not match
    elseif(strlen($_POST['newpw']) < 5)
    {
        $change_password_form_link = "index.php?action=preferences&subcommand=changepasswordform&pwfailed=newpw_tooshort";
        header("Location: " . $change_password_form_link);
        view_change_password_form();
    }
    // if the new password is too short
    elseif($_POST['newpw'] !== $_POST['confirmedpw'])
    {
        $change_password_form_link = "index.php?action=preferences&subcommand=changepasswordform&pwfailed=newpw_nomatch";
        header("Location: " . $change_password_form_link);
        view_change_password_form();
    }
    else
    {
        // create the new line of the user in the password "dav"-file
        $encr_new_pw = trim(shell_exec("echo -n " . $_SERVER['PHP_AUTH_USER'] . ":" . $GLOBALS["realm"] . ":" . $_POST['newpw'] . " | md5sum | awk '{print $1}'"));
        $new_davline = $_SERVER['PHP_AUTH_USER'] . ":" . $GLOBALS["realm"] . ":" . $encr_new_pw;
        // replace the current line with the new line in the password "dav"-file
        shell_exec("sed 's/" . $current_davline . "/" . $new_davline . "/' -i " . $GLOBALS["password_file"]);
        
        // print output
        $output = "Your password has been changed!\nsuccess"; 
        markup_success_failure($output);
    }
}

function add_user_form(){
    $server_connection = true;
    $server_access = true;

    if(empty($_POST)){
        $nr_users = 1;
        $add = false;
        $more = false;
    }else{
        $nr_users = $_POST['nrusers'];
        $add = $_POST['add'];
        $more = $_POST['more'];
    }
    
    if($add=="add"){
        error_reporting(0);
        
        $connection = ssh2_connect($GLOBALS["server_ip"]);
        if($connection){
            if(ssh2_auth_password($connection, $_POST["sshuser"], $_POST["sshpw"])){
                // get current users
                $list_users = shell_exec("../py/chiara.py sys listusers");
                $allLines = explode("\n", $list_users);
                $current_users[] = array();
                foreach ($allLines as $line){
                    $elements = explode("\t", $line);
                    if(!empty($elements[1])){
                        $current_users[] = $elements[1];
                    }
                }
                // add users
                $users="";
                for($i=1; $i<=$nr_users; $i++){
                    if(!empty($_POST['user' . $i])){
                        if(!strcmp($_POST['admin' . $i], "yes")){
                            $admin = 1;
                        }else{
                            $admin = 0;
                        }
                        // user do not exist
                        if(!in_array($_POST['user' . $i], $current_users)){      
                            // call bash script
                            $cmd_adduser = "echo '" . $_POST["sshpw"] . "' | sudo -S " . getcwd() . "/../bash/adduser " . $_POST['user' . $i] . " " . $admin . " " . $_POST['password' . $i] . " " . $GLOBALS["password_file"] . " " . $GLOBALS["apache_conf"] . " " . $GLOBALS["chiara_root"] . " " . $GLOBALS["users_webfolder"] . " " . $GLOBALS["realm"] . " " . $GLOBALS["server_ip"];
                            $cmd_restart_apache = "echo '" . $_POST["sshpw"] . "' | sudo -S /etc/init.d/apache2 restart";
                            $stream = ssh2_exec($connection, $cmd_adduser);
                            $stream = ssh2_exec($connection, $cmd_restart_apache);

                            if(empty($users)){
                                $users="&users=" . $_POST['user' . $i] . "," . $admin . ",0";
                            }else{
                                $users = $users . ";" . $_POST['user' . $i] . "," . $admin . ",0";
                            }
                        }else{
                            if(empty($users)){
                                $users="&users=" . $_POST['user' . $i] . "," . $admin . ",1";
                            }else{
                                $users = $users . ";" . $_POST['user' . $i] . "," . $admin . ",1";
                            }
                        }
                    }
                }
                header("Location: " . "index.php?action=preferences&subcommand=adduser" . $users);
            }else{
                $server_access = false;
            }
            error_reporting(E_ALL ^ E_NOTICE);
        }else{
            $server_connection = false;
        }
    }
    
    if($more=='more'){
       $nr_users = $nr_users + 1; 
    }

    echo '<table border=0 cellspacing=3 cellpadding=2>';
        echo "<TR>\n";
        echo '<TD class="smallTitle" colspan=4>Add users</TD>' . "\n";
        echo "</TR>\n";
    echo '</table>';

    /* displays the 'add user' formular for metadata */
    echo '<form method="post" name="adduser" action="index.php">';
    echo '<input type="hidden" name="action" value="preferences">' . "\n";
    echo '<input type="hidden" name="subcommand" value="adduserform">' . "\n";
    echo '<input type="hidden" name="nrusers" value=' . $nr_users . '>' . "\n";
    echo '<input type="hidden" name="add" value=false>' . "\n";
    echo '<input type="hidden" name="more" value=false>' . "\n";
      

    echo '<table border=0 cellspacing=2 cellpadding=2>';
   
    echo '<tr>
                <td colspan=1>&nbsp;</td>
                <td class="shortinfo" colspan=1 style="padding-left: 10px;">Name</td>
                <td class="shortinfo" colspan=1 style="padding-left: 10px;">Password</td>
                <td class="shortinfo" colspan=1 style="padding-left: 10px;">Admin</td>
            </tr>';

    for($i=1; $i<=$nr_users; $i++){
        $name_value = "";
        $admin_value = "";
        $password_value = "";
        if(!empty($_POST['user' . $i])){
            $name_value = $_POST['user' . $i];
        }
        if(!empty($_POST['admin' . $i])){
            $admin_value = $_POST['admin' . $i];
        }
        if(!empty($_POST['password' . $i])){
            $password_value = $_POST['password' . $i];
        }

        echo '<tr>
                <td class="shortinfo" colspan=1>User ' . $i . ':</td>
                <td class="shortinfo" colspan=1><input type="text" name="user' . $i . '" value="' . $name_value . '" size=20 ></td>
                <td class="shortinfo" colspan=1><input type="text" autocomplete="off" name="password' . $i . '" value="' . $password_value . '" size=20 ></td>';

        echo '<td class="shortinfo" colspan=1><select name="admin' . $i . '">';
        if(!strcmp("yes",$_POST["admin" . $i])){
            echo '<option selected value="yes">yes</option>"';
            echo '<option value="no">no</option>"';
        }else{
            echo '<option selected value="no">no</option>"';
            echo '<option value="yes">yes</option>"';
        }
        echo '</select></td></tr>';
    }

    echo '<tr>
            <td colspan=1>&nbsp;</td>
            <td align="left"><input type="submit" value="more" name="more"></td>
        </tr>';

    echo '<tr><td colspan=3>&nbsp;</td></tr>
          <tr><td class="shortinfo" colspan=3>You have to access to the surver with ssh for adding a user. <br/>Please enter your server username and password!</td></tr>';

    if(!$server_connection){
        echo '<tr><td colspan=3><span class="failure">Chiara cannot connect to the server!</span></td></tr>';
    }
    if(!$server_access){
        echo '<tr><td colspan=3><span class="failure">Your username or password is incorrect!</span></td></tr>';
    }

    echo '<tr>
            <td class="shortinfo">User name:</td>
            <td class="shortinfo"><input type="text" name="sshuser" size=20 ></td>
        </tr>
        <tr>
            <td class="shortinfo">Password:</td>
            <td class="shortinfo"><input type="password" autocomplete="off" name="sshpw" size=20/></td>
        </tr>';
 
    echo '<tr>
            <td colspan=1>&nbsp;</td>
            <td align="left"><input type="submit" value="add" name="add"></td>
        </tr>

        </table>
    </form>';
    
}

function add_user(){
    // list added users
    $output = "";
    $users =  explode(";",$_GET["users"]);
    foreach($users as $user) {
        if(!empty($user)){
            $elements = explode(",",$user);
            if($elements[2]==0){
                if($elements[1]==1){
                    $output = $output . "Add user '" . $elements[0] . "' as admin\n";
                }else{
                    $output = $output . "Add user '" . $elements[0] . "' as no admin\n";
                }
            }else{
                $output = $output . "User '" . $elements[0] . "' already exist!\n";
            }
        }
    }
    $output = $output . "success";
    markup_success_failure($output);
}
 


function remove_user_form(){
    $server_connection = true;
    $server_access = true;

    if(empty($_POST)){
        $nr_users = 1;
        $remove = false;
        $more = false;
    }else{
        $nr_users = $_POST['nrusers'];
        $remove = $_POST['remove'];
        $more = $_POST['more'];
    }
    
    if($remove=="remove"){
        error_reporting(0);
        
        $connection = ssh2_connect($GLOBALS["server_ip"]);
        if($connection){
            if(ssh2_auth_password($connection, $_POST["sshuser"], $_POST["sshpw"])){
                // get current users
                $list_users = shell_exec("../py/chiara.py sys listusers");
                $allLines = explode("\n", $list_users);
                $current_users[] = array();
                foreach ($allLines as $line){
                    $elements = explode("\t", $line);
                    if(!empty($elements[1])){
                        $current_users[] = $elements[1];
                    }
                }
                // remove users
                $users="";
                for($i=1; $i<=$nr_users; $i++){
                    if(!empty($_POST['user' . $i])){
                        // user exist
                        if(in_array($_POST['user' . $i], $current_users)){      
                            // call bash script
                            $cmd_removeuser = "echo '" . $_POST["sshpw"] . "' | sudo -S " . getcwd() . "/../bash/removeuser " . $_POST['user' . $i] . " " . $GLOBALS["password_file"] . " " . $GLOBALS["apache_conf"] . " " . $GLOBALS["chiara_root"] . " " . $GLOBALS["realm"];
                            $stream = ssh2_exec($connection, $cmd_removeuser);

                            if(empty($users)){
                                $users="&users=" . $_POST['user' . $i] . ",0";
                            }else{
                                $users = $users . ";" . $_POST['user' . $i] . ",0";
                            }
                        }else{
                            if(empty($users)){
                                $users="&users=" . $_POST['user' . $i] . ",1";
                            }else{
                                $users = $users . ";" . $_POST['user' . $i] . ",1";
                            }
                        }
                    }
                }
                header("Location: " . "index.php?action=preferences&subcommand=removeuser" . $users);
            }else{
                $server_access = false;
            }
            error_reporting(E_ALL ^ E_NOTICE);
        }else{
            $server_connection = false;
        }
    }
    
    if($more=='more'){
       $nr_users = $nr_users + 1; 
    }

    echo '<table border=0 cellspacing=3 cellpadding=2>';
        echo "<TR>\n";
        echo '<TD class="smallTitle" colspan=2>Remove users</TD>' . "\n";
        echo "</TR>\n";
    echo '</table>';

    /* displays the 'remove user' formular for metadata */
    echo '<form method="post" name="removeuser" action="index.php">';
    echo '<input type="hidden" name="action" value="preferences">' . "\n";
    echo '<input type="hidden" name="subcommand" value="removeuserform">' . "\n";
    echo '<input type="hidden" name="nrusers" value=' . $nr_users . '>' . "\n";
    echo '<input type="hidden" name="remove" value=false>' . "\n";
    echo '<input type="hidden" name="more" value=false>' . "\n";
      

    echo '<table border=0 cellspacing=2 cellpadding=2>';
   
    $list_users = shell_exec("../py/chiara.py sys listusers");
    $allLines = explode("\n", $list_users);
    for($i=1; $i<=$nr_users; $i++){
        echo '<tr>
                <td class="shortinfo" colspan=1>User ' . $i . ':</td>
                <td class="shortinfo" colspan=1><select name="user' . $i . '">';
        foreach ($allLines as $line){
            $elements = explode("\t", $line);
            if(!empty($elements[1])){
                if(!strcmp($elements[1],$_POST["user" . $i])){
                    echo '<option selected value="' . $elements[1] . '">' . $elements[1] . "</option>";
                }else{
                    echo '<option value="' . $elements[1] . '">' . $elements[1] . "</option>";
                }
            }
        }
        echo '</select></td></tr>';
    }

    echo '<tr>
            <td colspan=1>&nbsp;</td>
            <td align="left"><input type="submit" value="more" name="more"></td>
        </tr>';

    echo '<tr><td colspan=3>&nbsp;</td></tr>
          <tr><td class="shortinfo" colspan=2>You have to access to the surver with ssh for removing a user. <br/>Please enter your server username and password!</td></tr>';

    if(!$server_connection){
        echo '<tr><td colspan=3><span class="failure">Chiara cannot connect to the server!</span></td></tr>';
    }
    if(!$server_access){
        echo '<tr><td colspan=3><span class="failure">Your username or password is incorrect!</span></td></tr>';
    }

    echo '<tr>
            <td class="shortinfo">User name:</td>
            <td class="shortinfo"><input type="text" name="sshuser" size=20 ></td>
        </tr>
        <tr>
            <td class="shortinfo">Password:</td>
            <td class="shortinfo"><input type="password" autocomplete="off" name="sshpw" size=20/></td>
        </tr>';
 
    echo '<tr>
            <td colspan=1>&nbsp;</td>
            <td align="left"><input type="submit" value="remove" name="remove"></td>
        </tr>

        </table>
    </form>';
    
}

function remove_user(){
    // list removed users
    $output = "";
    $users =  explode(";",$_GET["users"]);
    foreach($users as $user) {
        if(!empty($user)){
            $elements = explode(",",$user);
            if($elements[1]==0){
                $output = $output . "Remove user '" . $elements[0] . "'\n";
            }else{
                $output = $output . "User '" . $elements[0] . "' do not exist!\n";
            }
        }
    }
    $output = $output . "success";
    markup_success_failure($output);
}


function list_all_users(){

    echo '<table border=0 cellspacing=2 cellpadding=2>';
        echo "<TR>\n";
        echo '<TD class="smallTitle" colspan=4>List all users</TD>' . "\n";
        echo "</TR>\n";
    echo '</table>';

    echo '<table class="listdetails">';
        echo "<THEAD\n";
        echo "<TR>\n";
        echo '<TH class="listdetails" colspan=1>ID</TD>' . "\n";
        echo '<TH class="listdetails" colspan=1>User</TD>' . "\n";
        echo '<TH class="listdetails" colspan=1>Admin</TD>' . "\n";
        echo '<TH class="listdetails" colspan=1>Groups</TD>' . "\n";
        echo "</TR>\n";
        echo "</THEAD\n";
        
        echo "<BODY\n";

    $list_users = shell_exec("../py/chiara.py sys listusers");
    $lines_users = explode("\n",$list_users);
    
        foreach (array_slice($lines_users,1,-1) as $line_users)
        {
            echo "<TR>\n";
            $elements_users = explode("\t", $line_users);
            echo '<TD class="listdetails" colspan=1>' . $elements_users[0] . '</TD>' . "\n";
            echo '<TD class="listdetails" colspan=1>' . $elements_users[1] . '</TD>' . "\n";
            if($elements_users[2]){
                $admin = "yes";
            }else{
                $admin = "no";
            }
            echo '<TD class="listdetails" colspan=1>' . $admin . '</TD>' . "\n";
            $list_groups = shell_exec("../py/chiara.py sys listuser " . $elements_users[1]);
            $lines_groups = explode("\n",$list_groups);
            $groups = "";
            foreach (array_slice($lines_groups,1,-1) as $line_groups){
                $elements_groups = explode("\t", $line_groups);
                if(empty($groups)){
                    $groups = $groups . $elements_groups[1];
                }else{
                    $groups = $groups . ", " . $elements_groups[1];
                }
            }
            echo '<TD class="listdetails" colspan=1>' . $groups . '</TD>' . "\n";
            echo "</TR>\n";
        }
        echo "</BODY\n";
    echo '</table>';
 
    echo '<table border=0 cellspacing=2 cellpadding=2></table>';
}

function add_group_form(){

    $nr_groups = $_GET['nrgroups'];
    
    if($_GET['add']=="add"){
        $groups="";
        for($i=1; $i<=$nr_groups; $i++){
            if(empty($groups)){
               $groups="&groups=" . $_GET['group' . $i];
            }else{
                $groups = $groups . ";" . $_GET['group' . $i];
            }
    }
         header("Location: " . "index.php?action=preferences&subcommand=addgroup" . $groups);
    }else{
    
    if($_GET['more']=='more'){
       $nr_groups = $nr_groups + 1; 
    }

    echo '<table border=0 cellspacing=3 cellpadding=2>';
        echo "<TR>\n";
        echo '<TD class="smallTitle" colspan=2>Add groups</TD>' . "\n";
        echo "</TR>\n";
    echo '</table>';

    /* displays the 'add group' formular for metadata */
    echo '<form name="addgroup" action="index.php">';
    echo '<input type="hidden" name="action" value="preferences">' . "\n";
    echo '<input type="hidden" name="subcommand" value="addgroupform">' . "\n";
    echo '<input type="hidden" name="nrgroups" value=' . $nr_groups . '>' . "\n";
    echo '<input type="hidden" name="add" value=false>' . "\n";
    

    echo '<table border=0 cellspacing=2 cellpadding=2>';
    for($i=1; $i<=$nr_groups; $i++){
        $value = "";
        if(!empty($_GET['group' . $i])){
            $value = $_GET['group' . $i];
        }
        echo '<tr>
                <td class="shortinfo" colspan=1>Group ' . $i . ':</td>
                <td class="shortinfo" colspan=1><input type="text" name="group' . $i . '" value="' . $value . '" size=30 ></td>
            </tr>';
    }

    echo '<tr>
            <td colspan=1>&nbsp;</td>
            <td colspan=1><table border=0 cellspacing=2 cellpadding=2>
            <tr>
                <td align="left"><input type="submit" value="more" name="more"></td>
                <td align="left"><input type="submit" value="add" name="add"></td>
            </tr>
            </table></td>
        </table>
        </form>';
    }
}

function add_group(){
    // get current groups
    $list_groups = shell_exec("../py/chiara.py sys listgroups");
    $allLines = explode("\n", $list_groups);
    $current_groups[] = array();
    foreach ($allLines as $line){
        $elements = explode("\t", $line);
        if(!empty($elements[1])){
            $current_groups[] = $elements[1];
        }
    }

    // add groups
    $output = "";
    $groups =  explode(";",$_GET["groups"]);
    foreach(array_unique($groups) as $group) {
        if(!empty($group)){
            if(in_array($group, $current_groups)){
                $output = $output . "Group " . $group . " already exists!\n";
            }else{
                shell_exec("../py/chiara.py sys addgroup " . $group); 
                $output = $output . "Add group '" . $group . "'\n";
            }
        }
    }
    $output = $output . "success";
    markup_success_failure($output);
}

function remove_group_form(){
    $nr_groups = $_GET['nrgroups'];
    
    if($_GET['remove']=="remove"){
        $groups="";
        for($i=1; $i<=$nr_groups; $i++){
            if(empty($groups)){
               $groups="&groups=" . $_GET['group' . $i];
            }else{
                $groups = $groups . ";" . $_GET['group' . $i];
            }
    }
         header("Location: " . "index.php?action=preferences&subcommand=removegroup" . $groups);
    }else{
    
    if($_GET['more']=='more'){
       $nr_groups = $nr_groups + 1; 
    }

    echo '<table border=0 cellspacing=3 cellpadding=2>';
        echo "<TR>\n";
        echo '<TD class="smallTitle" colspan=2>Remove groups</TD>' . "\n";
        echo "</TR>\n";
    echo '</table>';

    /* displays the 'remove group' formular for metadata */
    echo '<form name="removegroup" action="index.php">';
    echo '<input type="hidden" name="action" value="preferences">' . "\n";
    echo '<input type="hidden" name="subcommand" value="removegroupform">' . "\n";
    echo '<input type="hidden" name="nrgroups" value=' . $nr_groups . '>' . "\n";
    echo '<input type="hidden" name="remove" value=false>' . "\n";
    

    echo '<table border=0 cellspacing=2 cellpadding=2>';
    
    $list_groups = shell_exec("../py/chiara.py sys listgroups");
    $allLines = explode("\n", $list_groups);
    for($i=1; $i<=$nr_groups; $i++){
        $value = "";
        if(!empty($_GET['group' . $i])){
            $value = $_GET['group' . $i];
        }
        echo '<tr>
                <td class="shortinfo" colspan=1>Group ' . $i . ':</td>
                <td class="shortinfo" colspan=1><select name="group' . $i . '">';
        foreach ($allLines as $line){
            $elements = explode("\t", $line);
            if(!empty($elements[1])){
                if(!strcmp($elements[1],$_GET["group" . $i])){
                    echo '<option selected value="' . $elements[1] . '">' . $elements[1] . "</option>";
                }else{
                    echo '<option value="' . $elements[1] . '">' . $elements[1] . "</option>";
                }
            }
        }
        echo '</select></td></tr>';
    }

    echo '<tr>
            <td colspan=1>&nbsp;</td>
            <td colspan=1><table border=0 cellspacing=2 cellpadding=2>
            <tr>
                <td align="left"><input type="submit" value="more" name="more"></td>
                <td align="left"><input type="submit" value="remove" name="remove"></td>
            </tr>
            </table></td>
        </table>
        </form>';
    }    
}

function remove_group(){
    $output = "";
    $groups =  explode(";",$_GET["groups"]);
    foreach(array_unique($groups) as $group) {
        if(!empty($group)){
            shell_exec("../py/chiara.py sys rmgroup " . $group); 
            $output = $output . "Remove group '" . $group . "'\n";
        }
    }
    $output = $output . "success";
    markup_success_failure($output);
}

function add_users_to_group_form(){
    $nr_users = $_GET['nrusers'];
    
    if($_GET['add']=="add"){
        $users="";
        for($i=1; $i<=$nr_users; $i++){
            if(empty($users)){
               $users="&users=" . $_GET['user' . $i];
            }else{
                $users = $users . ";" . $_GET['user' . $i];
            }
    }
         header("Location: " . "index.php?action=preferences&subcommand=adduserstogroup" . $users . "&group=" . $_GET['group']);
    }else{
    
    if($_GET['more']=='more'){
       $nr_users = $nr_users + 1; 
    }

    echo '<table border=0 cellspacing=3 cellpadding=2>';
        echo "<TR>\n";
        echo '<TD class="smallTitle" colspan=2>Add users</TD>' . "\n";
        echo "</TR>\n";
    echo '</table>';

    /* displays the 'add users to group' formular for metadata */
    echo '<form name="adduserstogroup" action="index.php">';
    echo '<input type="hidden" name="action" value="preferences">' . "\n";
    echo '<input type="hidden" name="subcommand" value="adduserstogroupform">' . "\n";
    echo '<input type="hidden" name="nrusers" value=' . $nr_users . '>' . "\n";
    echo '<input type="hidden" name="add" value=false>' . "\n";
    

    echo '<table border=0 cellspacing=2 cellpadding=2>';
    
    $list_users = shell_exec("../py/chiara.py sys listusers");
    $allLines = explode("\n", $list_users);
    for($i=1; $i<=$nr_users; $i++){
        $value = "";
        if(!empty($_GET['user' . $i])){
            $value = $_GET['user' . $i];
        }
        echo '<tr>
                <td class="shortinfo" colspan=1>User ' . $i . ':</td>
                <td class="shortinfo" colspan=1><select name="user' . $i . '">';
        foreach ($allLines as $line){
            $elements = explode("\t", $line);
            if(!empty($elements[1])){
                if(!strcmp($elements[1],$_GET["user" . $i])){
                    echo '<option selected value="' . $elements[1] . '">' . $elements[1] . "</option>";
                }else{
                    echo '<option value="' . $elements[1] . '">' . $elements[1] . "</option>";
                }
            }
        }
        echo '</select></td></tr>';
    }

    echo '<tr>
            <td colspan=1>&nbsp;</td>
            <td colspan=1><align="left"><input type="submit" value="more" name="more"></td>
            </tr>';
    
    echo "<TR>\n";
    echo '<TD class="smallTitle" colspan=2>to group</TD>' . "\n";
    echo "</TR>\n";
    
    echo '<tr>
            <td class="shortinfo" colspan=1>Group:</td>
            <td class="shortinfo" colspan=1><select name="group' . '">';
    $list_groups = shell_exec("../py/chiara.py sys listgroups");
    $allLines = explode("\n", $list_groups);
    foreach ($allLines as $line){
        $elements = explode("\t", $line);
        if(!empty($elements[1])){
            if(!strcmp($elements[1],$_GET["group"])){
                echo '<option selected value="' . $elements[1] . '">' . $elements[1] . "</option>";
            }else{
                echo '<option value="' . $elements[1] . '">' . $elements[1] . "</option>";
            }
        }
    }
    echo '</select></td></tr>';

    echo '<tr>
            <td colspan=1>&nbsp;</td>
            <td align="left"><input type="submit" value="add" name="add"></td>            
        </tr>';

    echo '</table></form>';
    }    


}

function add_users_to_group(){
    $output = "";
    $users =  explode(";",$_GET["users"]);
    $group = $_GET["group"];
    foreach(array_unique($users) as $user) {
        if(!empty($user)){
            shell_exec("../py/chiara.py sys addtogroup " . $user . " " . $group); 
            $output = $output . "Add user '" . $user . "' to group '" . $group . "'\n";
        }
    }
    $output = $output . "success";
    markup_success_failure($output);
}


function remove_users_from_group_form(){
    $nr_users = $_GET['nrusers'];
    
    if($_GET['remove']=="remove"){
        $users="";
        for($i=1; $i<=$nr_users; $i++){
            if(empty($users)){
               $users="&users=" . $_GET['user' . $i];
            }else{
                $users = $users . ";" . $_GET['user' . $i];
            }
    }
         header("Location: " . "index.php?action=preferences&subcommand=removeusersfromgroup" . $users . "&group=" . $_GET['group']);
    }else{
    
    if($_GET['more']=='more'){
       $nr_users = $nr_users + 1; 
    }

    echo '<table border=0 cellspacing=3 cellpadding=2>';
        echo "<TR>\n";
        echo '<TD class="smallTitle" colspan=2>Remove users</TD>' . "\n";
        echo "</TR>\n";
    echo '</table>';

    /* displays the 'remove users from group' formular for metadata */
    echo '<form name="removeusersfromgroup" action="index.php">';
    echo '<input type="hidden" name="action" value="preferences">' . "\n";
    echo '<input type="hidden" name="subcommand" value="removeusersfromgroupform">' . "\n";
    echo '<input type="hidden" name="nrusers" value=' . $nr_users . '>' . "\n";
    echo '<input type="hidden" name="remove" value=false>' . "\n";
    

    echo '<table border=0 cellspacing=2 cellpadding=2>';
    
    $list_users = shell_exec("../py/chiara.py sys listusers");
    $allLines = explode("\n", $list_users);
    for($i=1; $i<=$nr_users; $i++){
        $value = "";
        if(!empty($_GET['user' . $i])){
            $value = $_GET['user' . $i];
        }
        echo '<tr>
                <td class="shortinfo" colspan=1>User ' . $i . ':</td>
                <td class="shortinfo" colspan=1><select name="user' . $i . '">';
        foreach ($allLines as $line){
            $elements = explode("\t", $line);
            if(!empty($elements[1])){
                if(!strcmp($elements[1],$_GET["user" . $i])){
                    echo '<option selected value="' . $elements[1] . '">' . $elements[1] . "</option>";
                }else{
                    echo '<option value="' . $elements[1] . '">' . $elements[1] . "</option>";
                }
            }
        }
        echo '</select></td></tr>';
    }

    echo '<tr>
            <td colspan=1>&nbsp;</td>
            <td colspan=1><align="left"><input type="submit" value="more" name="more"></td>
            </tr>';
    
    echo "<TR>\n";
    echo '<TD class="smallTitle" colspan=2>from group</TD>' . "\n";
    echo "</TR>\n";
    
    echo '<tr>
            <td class="shortinfo" colspan=1>Group:</td>
            <td class="shortinfo" colspan=1><select name="group' . '">';
    $list_groups = shell_exec("../py/chiara.py sys listgroups");
    $allLines = explode("\n", $list_groups);
    foreach ($allLines as $line){
        $elements = explode("\t", $line);
        if(!empty($elements[1])){
            if(!strcmp($elements[1],$_GET["group"])){
                echo '<option selected value="' . $elements[1] . '">' . $elements[1] . "</option>";
            }else{
                echo '<option value="' . $elements[1] . '">' . $elements[1] . "</option>";
            }
        }
    }
    echo '</select></td></tr>';

    echo '<tr>
            <td colspan=1>&nbsp;</td>
            <td align="left"><input type="submit" value="remove" name="remove"></td>            
        </tr>';

    echo '</table></form>';
    }    
}

function remove_users_from_group(){
    $output = "";
    $users =  explode(";",$_GET["users"]);
    $group = $_GET["group"];
    foreach(array_unique($users) as $user) {
        if(!empty($user)){
            shell_exec("../py/chiara.py sys rmfromgroup " . $user . " " . $group); 
            $output = $output . "Remove user '" . $user . "' from group '" . $group . "'\n";
        }
    }
    $output = $output . "success";
    markup_success_failure($output);
}

function list_all_groups(){

    echo '<table border=0 cellspacing=2 cellpadding=2>';
        echo "<TR>\n";
        echo '<TD class="smallTitle" colspan=3>List all groups</TD>' . "\n";
        echo "</TR>\n";
    echo '</table>';

    echo '<table class="listdetails">';
        echo "<THEAD\n";
        echo "<TR>\n";
        echo '<TH class="listdetails" colspan=1>ID</TD>' . "\n";
        echo '<TH class="listdetails" colspan=1>Groups</TD>' . "\n";
        echo '<TH class="listdetails" colspan=1>Users</TD>' . "\n";
        echo "</TR>\n";
        echo "</THEAD\n";
        
        echo "<BODY\n";

    $list_groups = shell_exec("../py/chiara.py sys listgroups");
    $lines_groups = explode("\n",$list_groups);
    
        foreach (array_slice($lines_groups,1,-1) as $line_groups)
        {
            echo "<TR>\n";
            $elements_groups = explode("\t", $line_groups);
            echo '<TD class="listdetails" colspan=1>' . $elements_groups[0] . '</TD>' . "\n";
            echo '<TD class="listdetails" colspan=1>' . $elements_groups[1] . '</TD>' . "\n";
            
            $list_users = shell_exec("../py/chiara.py sys listgroup " . $elements_groups[1]);
            $lines_users = explode("\n",$list_users);
            $users = "";
            foreach (array_slice($lines_users,1,-1) as $line_users){
                $elements_users = explode("\t", $line_users);
                if(empty($users)){
                    $users = $users . $elements_users[1];
                }else{
                    $users = $users . ", " . $elements_users[1];
                }
            }
            echo '<TD class="listdetails" colspan=1>' . $users . '</TD>' . "\n";
            echo "</TR>\n";
        }
        echo "</BODY\n";
    echo '</table>';
 
    echo '<table border=0 cellspacing=2 cellpadding=2></table>';
}

?>
