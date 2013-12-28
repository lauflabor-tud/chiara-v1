<?php
    
    $file = "../data/" . $_SERVER['PHP_AUTH_USER'] . $_GET["filepath"];
        
    // download file
    header("Content-Type: octet/stream");
    header("Content-Length: " . filesize($file));           
    header("Content-Disposition: attachment; filename=" . urlencode(basename($_GET["filepath"])));
        
    header("Pragma: no-cache");
    header("Expires: 0");
    header("Cache-Control: must-revalidate");
    
    readfile($file);

?>
