<?php
function navigation_bar() {
  echo "
  <!DOCTYPE html><html><head>
<meta charset=\"UTF-8\">
<title>GVW</title>
  
  <link href=\"../../css/style.css\" type=\"text/css\" rel=\"stylesheet\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1, shrink-to-fit=no\">
  <link rel=\"stylesheet\" type=\"text/css\" href=\"https://stackpath.bootstrapcdn.com/bootstrap/4.1.0/css/bootstrap.min.css\" integrity=\"sha384-9gVQ4dYFwwWSjIDZnLEWnxCjeSWFphJiwGPXr1jddIhOegiu1FwO5qRGvFXOdJZ4\" crossorigin=\"anonymous\">
  <link rel=\"stylesheet\" type=\"text/css\" href=\"https://maxcdn.bootstrapcdn.com/font-awesome/4.7.0/css/font-awesome.min.css\" integrity=\"sha384-wvfXpqpZZVQGK6TAh5PVlGOfQNHSoD2xbE+QkPxCAFlNEevoEH3Sl0sibVcOQVnN\" crossorigin=\"anonymous\">
  </head>
  <body is=\"dmx-app\">
  <header class=\"bg-dark text-secondary border-bottom border-secondary\">
  <div class=\"container\">
    <div class=\"row\">
      <div class=\"col\">
        <nav class=\"navbar navbar-expand-lg navbar-dark bg-dark justify-content-between p-0\">
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
            <nav class=\"navbar navbar-expand-lg navbar-dark bg-dark justify-content-between\">
              <a class=\"navbar-brand mr-auto ml-auto\" href=\"../../index.php\">Home</a>
              <button class=\"navbar-toggler\" type=\"button\" data-toggle=\"collapse\" data-target=\"#navbar1_collapse\" aria-controls=\"navbar1_collapse\" aria-expanded=\"false\" aria-label=\"Toggle navigation\">
                <span class=\"navbar-toggler-icon\"></span>
              </button>
              <div class=\"collapse navbar-collapse justify-content-center\" id=\"navbar1_collapse\">
                <div class=\"navbar-nav\">
                  <a class=\"nav-item nav-link\" href=\"../../index.php\">Home</a>
                  <a class=\"nav-item nav-link\" href=\"../SQLi/items.php\">Items</a>
";
                  if(!isset($_SESSION['id'])){
                    echo '<a class="nav-item nav-link" href="../SQLi/user_login.php">Customer Sign in</a>';
                    echo '<a class="nav-item nav-link" href="../SQLi/seller_login.php">Seller Sign in</a>';
                }
                  else{
                    $id = $_SESSION['id'];
                    echo "<a class=\"nav-item nav-link\" href=\"../ShoppingCart/shoppingCart.php\">Checkout</a>";
                    echo "<a class=\"nav-item nav-link\" href=\"../profiles/index.php?id=$id\">Profile</a>";
                    echo "<a class=\"nav-item nav-link\" href=\"../Files/uploadNewItem.php\">Upload Item</a>";
                    echo "<a class=\"nav-item nav-link\" href=\../../logout.php>Logout</a><br>";
                  }
          
                echo "</div>";
              echo "</div>";
            echo "</nav>      </div></div></div></header>";

            echo '<script type="text/javascript" src="https://code.jquery.com/jquery-3.2.1.slim.min.js" integrity="sha384-KJ3o2DKtIkvYIK3UENzmM7KCkRr/rE9/Qpg6aAZGJwFDMVNA/GpGFF93hXpG5KkN" crossorigin="anonymous"></script>';
            echo '<script type="text/javascript" src="https://cdnjs.cloudflare.com/ajax/libs/popper.js/1.14.0/umd/popper.min.js" integrity="sha384-cs/chFZiN24E4KMATLdqdvsezGxaGsi4hLGOzlXwp5UZB1LY//20VyM2taTB4QvJ" crossorigin="anonymous"></script>';
            echo '<script type="text/javascript" src="https://stackpath.bootstrapcdn.com/bootstrap/4.1.0/js/bootstrap.min.js" integrity="sha384-uefMccjFJAIv6A+rW+L4AHf99KvxDjWSu1z9VI8SKNVmz4sk7buKt/6v9KI65qnm" crossorigin="anonymous"></script>';
        
}





?>