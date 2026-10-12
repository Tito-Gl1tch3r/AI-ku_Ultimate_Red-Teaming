<?php require "../../config/database.php";

session_start();

// This function will populate the comments and comments replies using a loop
function show_comments($comments,$con) {
    $html = '';

    // Iterate the comments using the foreach loop
    foreach ($comments as $comment) {
        //print_r(array_keys($comment));
        $author = $comment['author_id'];

        $stmt = $con->prepare("SELECT * FROM `GVWA`.`customers` WHERE ID =?");
        $stmt->bind_param("i",$author);
        $stmt->execute();
        $res = $stmt->get_result();
        $author = $res->fetch_assoc();

            // Add the comment to the $html variable
            $html .= '
            <div class="comment">
                <div>
                    <h3 class="name">' . $author['username'] . '</h3>
                </div>
                <p class="content">' . $comment['review'] . '</p>
            </div>
            ';
    }
    return $html;
}

// This function is the template for the write comment form
function show_write_comment_form($author_id,$product_id) {
    
    $html = '
    <div class="write_comment" data-comment-id="' . 1 . '">
        <form>
            <input name="author_id" type="hidden" value="' . $author_id . '">
            <input name="product_id" type="hidden" value="' . $product_id . '">
            <textarea name="content" placeholder="Write your comment here..." required></textarea>
            <button type="submit">Submit Comment</button>
        </form>
    </div>
    ';
    return $html;
}

if (isset($_GET['product_id'])) {
    
    $page = $_GET['product_id'];
    // Check if the submitted form variables exist
    if (isset($_POST['author_id'], $_POST['content'])) {

        $author = $_POST['author_id'];
        $content = $_POST['content'];
        $content = stripslashes($content);
        $rating = 1;
        // POST variables exist, insert a new comment into the MySQL comments table (user submitted form)
        $sql = "INSERT INTO reviews (ID,product_ID, author_id, review,rating) VALUES (NULL,$page,$author,'$content',$rating);";
        $stmt = mysqli_query($con,  $sql ) or die( '<pre>' . ((is_object($con)) ? mysqli_error($con) : (($___mysqli_res = mysqli_connect_error()) ? $___mysqli_res : false)) . '</pre>' );
        $error = "Your comment has been submitted";
        $_SESSION["error"] = $error;
        echo '<meta http-equiv="Refresh" content="0;' . "index.php?product_id=$page" . '">';
    }
    $sql = "SELECT author_id,review FROM reviews WHERE product_ID = $page LIMIT 0,500";
    $stmt = mysqli_query($con,  $sql ) or die( '<pre>' . ((is_object($con)) ? mysqli_error($con) : (($___mysqli_res = mysqli_connect_error()) ? $___mysqli_res : false)) . '</pre>' );
    
    $comments = array();
    while($row = mysqli_fetch_assoc($stmt))
        {
            $comments[] = $row;
        }
    // Get the total number of comments
    $stmt = mysqli_query($con,"SELECT COUNT(*) AS total_comments FROM reviews WHERE product_ID = $page");
    $comments_info = mysqli_fetch_assoc($stmt);
} else {
    exit('No product ID specified!');
}
?>


<div class="comment_header">
    <span class="total"><?=$comments_info['total_comments']?> comments</span>
    <a href="#" class="write_comment_btn" data-comment-id="1">Write Comment</a>
</div>


<?=show_comments($comments,$con)?>

<?=show_write_comment_form($_SESSION['id'],$_GET['product_id']) //<audio src/onerror=alert(1)> or <img src=x onerror="&#0000106&#0000097&#0000118&#0000097&#0000115&#0000099&#0000114&#0000105&#0000112&#0000116&#0000058&#0000097&#0000108&#0000101&#0000114&#0000116&#0000040&#0000039&#0000088&#0000083&#0000083&#0000039&#0000041">> 
?>
