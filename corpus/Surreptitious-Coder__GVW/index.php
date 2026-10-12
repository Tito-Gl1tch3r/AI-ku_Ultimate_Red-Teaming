
<!DOCTYPE html>
<html>
<body>

<?php

error_reporting(E_ALL ^ E_WARNING);
session_start();



if(isset($_SESSION["error"])){
  $error = $_SESSION["error"];
  echo "<span>$error</span>";
}
unset($_SESSION["error"]);

function navigation_bar() {
  echo "
  <!DOCTYPE html><html><head>
<meta charset=\"UTF-8\">
<title>Items</title>
  
  <link href=\"../css/style.css\" type=\"text/css\" rel=\"stylesheet\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1, shrink-to-fit=no\">
  <link rel=\"stylesheet\" type=\"text/css\" href=\"https://stackpath.bootstrapcdn.com/bootstrap/4.1.0/css/bootstrap.min.css\" integrity=\"sha384-9gVQ4dYFwwWSjIDZnLEWnxCjeSWFphJiwGPXr1jddIhOegiu1FwO5qRGvFXOdJZ4\" crossorigin=\"anonymous\">
  <link rel=\"stylesheet\" type=\"text/css\" href=\"https://maxcdn.bootstrapcdn.com/font-awesome/4.7.0/css/font-awesome.min.css\" integrity=\"sha384-wvfXpqpZZVQGK6TAh5PVlGOfQNHSoD2xbE+QkPxCAFlNEevoEH3Sl0sibVcOQVnN\" crossorigin=\"anonymous\">
  </head>
  <body is=\"dmx-app\">
  <header class=\"bg-dark text-secondary border-bottom border-secondary\">
  <div class=\"container\">
    <div class=\"row\">
      <div class=\"col\">
        <nav class=\"navbar navbar-expand-lg navbar-dark bg-black justify-content-between p-0\">
          <a class=\"navbar-brand mr-auto ml-auto\" href=\"#\">GVW</a>
        </nav>
      </div>
    </div>
  </div>
</header>
    <header class=\"bg-dark text-secondary\">
      <div class=\"container\">
        <div class=\"row\">
          <div class=\"col\">
            <nav class=\"navbar navbar-expand-lg navbar-dark bg-black justify-content-between\">
            <a class=\"nav-item nav-link\"> Home</a>
              <button class=\"navbar-toggler\" type=\"button\" data-toggle=\"collapse\" data-target=\"#navbar1_collapse\" aria-controls=\"navbar1_collapse\" aria-expanded=\"false\" aria-label=\"Toggle navigation\">
                <span class=\"navbar-toggler-icon\"></span>
              </button>
              <div class=\"collapse navbar-collapse\" id=\"navbar1_collapse\">
                <div class=\"navbar-nav\">
                  <a class=\"nav-item nav-link\" href=\"exploits/SQLi/items.php\">Items</a>
";
                  if(!isset($_SESSION['id'])){
                    echo '<a class="nav-item nav-link" href="exploits/SQLi/user_login.php">Customer Sign in</a>';
                    echo '<a class="nav-item nav-link" href="exploits/SQLi/seller_login.php">Seller Sign in</a>';
                }
                  else{
                    $id = $_SESSION['id'];
                    echo "<a class=\"nav-item nav-link\" href=\"exploits/ShoppingCart/shoppingCart.php\">Checkout</a>";
                    echo "<a class=\"nav-item nav-link\" href=\"exploits/profiles/index.php?id=$id\">Profile</a>";
                    echo "<a class=\"nav-item nav-link\" href=\"exploits/Files/uploadNewItem.php\">Upload Item</a>";
                    echo "<a class=\"nav-item nav-link\" href=./logout.php>Logout</a><br>";
                  }
          
                echo "</div>";
              echo "</div>";
            echo "</nav>      </div></div></div></header>";

            echo '<script type="text/javascript" src="https://code.jquery.com/jquery-3.2.1.slim.min.js" integrity="sha384-KJ3o2DKtIkvYIK3UENzmM7KCkRr/rE9/Qpg6aAZGJwFDMVNA/GpGFF93hXpG5KkN" crossorigin="anonymous"></script>';
            echo '<script type="text/javascript" src="https://cdnjs.cloudflare.com/ajax/libs/popper.js/1.14.0/umd/popper.min.js" integrity="sha384-cs/chFZiN24E4KMATLdqdvsezGxaGsi4hLGOzlXwp5UZB1LY//20VyM2taTB4QvJ" crossorigin="anonymous"></script>';
            echo '<script type="text/javascript" src="https://stackpath.bootstrapcdn.com/bootstrap/4.1.0/js/bootstrap.min.js" integrity="sha384-uefMccjFJAIv6A+rW+L4AHf99KvxDjWSu1z9VI8SKNVmz4sk7buKt/6v9KI65qnm" crossorigin="anonymous"></script>';
        
}







navigation_bar();

if(!isset($_SESSION['id'])) {
  echo "Hello Anonymous user";
} else {
  echo "<i><h4>Hello  " . $_SESSION['username']. "</h4></i>";
}

unset($_SESSION["error"]);

?>

<section id="intro" class="bg-white">
  <div class="container">
    <div class="row">
      <div class="col-lg-8">
      <u>
        <h3 class="section-title">What is this application?</h3>
      </u>
        <p class="lead">
        Welcome to Glasgow's Vunerable Web-Application, or GVW for short.
        The intended purpose is to act as a more realistic scenario to exploit rather than other web applications that just tell you
        where the vunerability lies, so it is up to you, the user, to find and exploit the vulnerabilties hidden. This application also offers
        the user the chance to edit the code and try to fix the more obvious flaws and some helpful reset buttons incase things go slightly wrong.
        To make things easier,
        below is a list of the **intended** vunerabilities, as there maybe some unintended ones along the way:

</p>
<p>
        <strong> XSS vulnerabilties </strong>
        <br>
        <strong> Username enumeration </strong>
        <br>
        <strong> SQL injections </strong>
        <br>
        <strong> File upload vulnerability </strong>
        <br>
        <strong> Unrestricted File upload vulnerability </strong>
        <br>
        <strong> Directory traversal vulnerabilties </strong>
        <br>
        <strong> Vertical privilege escalation </strong>
        <br>
        <strong> Logic flaws in the checkout </strong>
        <br>
        <strong> Web application firewall vulnerabilities </strong>
      </p>

<u>
      <h3 class="section-title">Resources</h3>
      <p class="lead">
</u>

      Below are resources that may come in handy:

      <h4> The OWASP top 10 </h4>
      https://owasp.org/www-project-top-ten/

      <p>
      <h4> File upload vulnerabilties </h4>
      https://www.hacksplaining.com/exercises/file-upload

      <p>
      <h4> XSS filter evasion </h4>
      https://www.acunetix.com/blog/web-security-zone/xss-filter-evasion-basics/
</p>

      </div>
    </div>
  </div>


</body>
</html>