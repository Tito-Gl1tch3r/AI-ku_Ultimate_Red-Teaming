<?php
/**
 * This view is used by console/controllers/MigrateController.php
 * The following variables are available in this view:
 */

/* @var $className string the new migration class name */
/* @var $timing string the timing of the event BEFORE|AFTER */
/* @var $event string the type of event INSERT|UPDATE|DELETE */

$triggerName=sprintf("t%s%s_%s",strtolower($timing[0] ?? ''),strtolower($event[0] ?? ''),$table);
echo "<?php\n";
?>

use yii\db\Migration;

class <?= $className ?> extends Migration
{
  public $DROP_SQL="DROP TRIGGER IF EXISTS {{%<?=$triggerName?>}}";
<?php if($action=='delete' || $action=='drop'):?>
  public $CREATE_SQL="SELECT true";
<?php else:?>
  public $CREATE_SQL="CREATE TRIGGER {{%<?=$triggerName?>}} <?=$timing?> <?=$event?> ON {{%<?=$table?>}} FOR EACH ROW
  thisBegin:BEGIN
  IF (@TRIGGER_CHECKS = FALSE) THEN
      LEAVE thisBegin;
  END IF;
    YOUR CODE HERE
  END";
<?php endif;?>


  public function up()
  {
    $this->db->createCommand($this->DROP_SQL)->execute();
    $this->db->createCommand($this->CREATE_SQL)->execute();
  }

  public function down()
  {
    $this->db->createCommand($this->DROP_SQL)->execute();
  }
}