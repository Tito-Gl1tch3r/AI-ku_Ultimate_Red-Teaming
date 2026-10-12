<?php require "../../config/database.php";

$target_dir = "../../assets/acccounts/";

$target_file = $target_dir . basename($_FILES["image"]["name"]);
$uploadOk = 1;
$imageFileType = strtolower(pathinfo($target_file,PATHINFO_EXTENSION));

$PHPUploadPath = $target_dir;

$WarningHtml = '';

$id = $_GET['id'][0];
$type = $_GET['type'];

if( !is_writable( $PHPUploadPath ) ) {
    $error= "<div class=\"warning\">Incorrect folder permissions: {$PHPUploadPath}<br /><em>Folder is not writable.</em></div>";
    $_SESSION['error'] = $error;
    header("location: index.php?id=$id");
    exit;
}


if(!isset($_GET['type']) || $_GET['type']== "none" ){
    $error = "invalid parameters";
    $_SESSION['error'] = $error;
    header("location: index.php?id=$id");
    exit;
}

if ($_FILES['image']['size'] > 0 && $_FILES['image']['size'] < 30000000) {
    $check = getimagesize($_FILES["image"]["tmp_name"]);
    if ($check !== false) {
        if ($check["mime"] != "image/png") {
            $error = "File is not png image.";
            $_SESSION['error'] = $error;
            header("location: index.php?id=$id");
            exit;
        } else {
            if (move_uploaded_file($_FILES[ 'image' ][ 'tmp_name' ], $target_file)) {
                echo '<pre>Your image was uploaded.</pre>';
            }

            
                $sql = "UPDATE `GVWA`.$type SET image=\"$target_file\" where id=$id";
                if(mysqli_query($con, $sql)){
                    $error = "Records were updated successfully.";
                    $_SESSION['error'] = $error;
                    header("location: index.php?id=$id");
                    exit;
                } else {
                   $error = "ERROR: Could not execute $sql. " . mysqli_error($con);
                   $_SESSION['error'] = $error;
                    header("location: index.php?id=$id");
                    exit;
                }
                #$id = mysqli_query($con, $sql) or die('<pre>' . ((is_object($con)) ? mysqli_error($con) : (($___mysqli_res = mysqli_connect_error()) ? $___mysqli_res : false)) . '</pre>');
                echo "Item uploaded successfully";
        
        }
    }
    } else {
        echo "File is not an image or is larger than 3kb";
    }

?>