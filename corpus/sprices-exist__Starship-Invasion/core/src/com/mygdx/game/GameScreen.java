package com.mygdx.game;

import com.badlogic.gdx.Gdx;
import com.badlogic.gdx.Input;
import com.badlogic.gdx.Screen;
import com.badlogic.gdx.audio.Music;
import com.badlogic.gdx.graphics.Camera;
import com.badlogic.gdx.graphics.Color;
import com.badlogic.gdx.graphics.OrthographicCamera;
import com.badlogic.gdx.graphics.Texture;
import com.badlogic.gdx.graphics.g2d.BitmapFont;
import com.badlogic.gdx.graphics.g2d.SpriteBatch;
import com.badlogic.gdx.graphics.g2d.TextureAtlas;
import com.badlogic.gdx.graphics.g2d.TextureRegion;
import com.badlogic.gdx.graphics.g2d.freetype.FreeTypeFontGenerator;
import com.badlogic.gdx.math.Rectangle;
import com.badlogic.gdx.math.Vector2;
import com.badlogic.gdx.utils.Align;
import com.badlogic.gdx.utils.viewport.StretchViewport;
import com.badlogic.gdx.utils.viewport.Viewport;

import java.util.LinkedList;
import java.util.ListIterator;
import java.util.Locale;

public class GameScreen implements Screen{


    private static final float TOUCH_MOVEMENT_THRESHOLD = 0.5f;
    //screen
    private Camera camera;
    private Viewport viewport;

    //graphics
    private SpriteBatch batch;
    private TextureAtlas textureAtlas;
    private TextureAtlas explosionAtlas;

    //private Texture background;
    private TextureRegion[] backgrounds;
    private TextureRegion playerShipTextureRegion, playerShieldTextureRegion, enemyShipTextureRegion, enemyShieldTextureRegion,
            playerLaserTextureRegion, enemyLaserTextureRegion;

    //explosions
    private TextureRegion[] enemyExplosions;
    private TextureRegion[] playerExplosions;

    //timing
    private float[] backgroundOffsets = {0,0,0,0};
    private float backgroundMaxScrollingSpeed;
    private float timeBetweenEnemySpawns = 3f;
    private float timeBetweenSpawnChange = 0;
    private float enemySpawnTimer=0;

    //world parameters
    private final float WORLD_WIDTH=72;
    private final float WORLD_HEIGHT=128;

    //game objects
    private PlayerShip playerShip;
    private LinkedList<EnemyShip> enemyShipList;
    private LinkedList<Laser> playerLaserList;
    private LinkedList<Laser> enemyLaserList;
    private LinkedList<Explosion> explosionList;

    private int score=0;

    //HUD
    BitmapFont font;
    float hudVerticalMargin,hudLeftX,hudRightX,hudCentreX,hudRow1Y,hudRow2Y,hudSectionWidth;


    GameScreen(){
        camera = new OrthographicCamera();
        viewport = new StretchViewport(WORLD_WIDTH,WORLD_HEIGHT,camera);
/*        background = new Texture("darkPurpleStarscape.png");
        backgroundOffset = 0;*/
        Music music = Gdx.audio.newMusic(Gdx.files.internal("audio.mp3"));
        music.play();
        music.setLooping(true);

        //set up texture atlas
        textureAtlas=new TextureAtlas("images.atlas");
        explosionAtlas=new TextureAtlas("explosions.atlas");
        enemyExplosions=new TextureRegion[12];
        playerExplosions=new TextureRegion[11];

        enemyExplosions[0]=explosionAtlas.findRegion("ship21");
        enemyExplosions[1]=explosionAtlas.findRegion("ship22");
        enemyExplosions[2]=explosionAtlas.findRegion("ship23");
        enemyExplosions[3]=explosionAtlas.findRegion("ship24");
        enemyExplosions[4]=explosionAtlas.findRegion("ship25");
        enemyExplosions[5]=explosionAtlas.findRegion("ship26");
        enemyExplosions[6]=explosionAtlas.findRegion("ship27");
        enemyExplosions[7]=explosionAtlas.findRegion("ship28");
        enemyExplosions[8]=explosionAtlas.findRegion("ship29");
        enemyExplosions[9]=explosionAtlas.findRegion("ship210");
        enemyExplosions[10]=explosionAtlas.findRegion("ship211");
        enemyExplosions[11]=explosionAtlas.findRegion("ship212");

        playerExplosions[0]=explosionAtlas.findRegion("ship31");
        playerExplosions[1]=explosionAtlas.findRegion("ship32");
        playerExplosions[2]=explosionAtlas.findRegion("ship33");
        playerExplosions[3]=explosionAtlas.findRegion("ship34");
        playerExplosions[4]=explosionAtlas.findRegion("ship35");
        playerExplosions[5]=explosionAtlas.findRegion("ship36");
        playerExplosions[6]=explosionAtlas.findRegion("ship37");
        playerExplosions[7]=explosionAtlas.findRegion("ship38");
        playerExplosions[8]=explosionAtlas.findRegion("ship39");
        playerExplosions[9]=explosionAtlas.findRegion("ship310");
        playerExplosions[10]=explosionAtlas.findRegion("ship311");


        backgrounds=new TextureRegion[4];
        backgrounds[0]=textureAtlas.findRegion("Starscape00");
        backgrounds[1]=textureAtlas.findRegion("Starscape01");
        backgrounds[2]=textureAtlas.findRegion("Starscape02");
        backgrounds[3]=textureAtlas.findRegion("Starscape03");

        backgroundMaxScrollingSpeed = (float)(WORLD_HEIGHT)/4;

        //initialize texture regions
        playerShipTextureRegion=textureAtlas.findRegion("Ship3");
        enemyShipTextureRegion=textureAtlas.findRegion("Ship2");
        playerShieldTextureRegion=textureAtlas.findRegion("shield2");
        enemyShieldTextureRegion=textureAtlas.findRegion("shield1");
        enemyShieldTextureRegion.flip(false,true);
        playerLaserTextureRegion=textureAtlas.findRegion("laserBlue13");
        enemyLaserTextureRegion=textureAtlas.findRegion("laserRed03");

        //set up game objects
        playerShip=new PlayerShip(48,6,18,18, 0.4f, 4, 50, 0.2f,
                WORLD_WIDTH/2, WORLD_HEIGHT/4, playerShipTextureRegion, playerShieldTextureRegion, playerLaserTextureRegion);

        enemyShipList=new LinkedList<EnemyShip>();

        playerLaserList = new LinkedList<Laser>();
        enemyLaserList = new LinkedList<Laser>();
        explosionList = new LinkedList<Explosion>();

        batch = new SpriteBatch();

        prepareHUD();
    }


    private void prepareHUD(){
        //bmp font
        FreeTypeFontGenerator fontGenerator=new FreeTypeFontGenerator(Gdx.files.internal("EOTGfont.ttf"));
        FreeTypeFontGenerator.FreeTypeFontParameter fontParameter=new FreeTypeFontGenerator.FreeTypeFontParameter();

        fontParameter.size=72;
        fontParameter.borderWidth=3.6f;
        fontParameter.color=new Color(1,1,1,0.3f);
        fontParameter.borderColor=new Color(0,0,0,0.3f);

        font=fontGenerator.generateFont(fontParameter);
        //scale
        font.getData().setScale(0.1f);

        //margins and stuff
        hudVerticalMargin = font.getCapHeight()/2;
        hudLeftX = font.getCapHeight()/2;
        hudRightX = WORLD_WIDTH*2/3 - hudLeftX;
        hudCentreX = WORLD_WIDTH/3 ;
        hudRow1Y = WORLD_HEIGHT-hudVerticalMargin;
        hudRow2Y = hudRow1Y-hudVerticalMargin-font.getCapHeight();
        hudSectionWidth = WORLD_WIDTH/3;

    }


    @Override
    public void show() {

    }

    @Override
    public void render(float deltaTime) {
        batch.begin();

        //scroll
        renderBackground(deltaTime);

        detectInput(deltaTime);
        playerShip.update(deltaTime);

        SpawnEnemyShips(deltaTime);

        ListIterator<EnemyShip>enemyShipListIterator = enemyShipList.listIterator();

        while (enemyShipListIterator.hasNext()){
            EnemyShip enemyShip=enemyShipListIterator.next();
            moveEnemy(enemyShip, deltaTime);
            enemyShip.update(deltaTime);
            enemyShip.draw(batch);
        }

        //player ships
        playerShip.draw(batch);

        //lasers
        renderLasers(deltaTime);

        //detect laser/ship collisions
        detectCollisions();

        //explosions
        renderExplosions(deltaTime);

        //hud
        updateAndRenderHUD();

        ChangeSpawnTime(deltaTime);

        batch.end();
    }

    private void ChangeSpawnTime(float deltaTime){
        if(timeBetweenSpawnChange>30f && timeBetweenEnemySpawns>0.9f){
            timeBetweenEnemySpawns-=0.15f;
            timeBetweenSpawnChange-=30f;
        }
        else {
            timeBetweenSpawnChange+=deltaTime;
        }
    }

    private void updateAndRenderHUD(){
        //top row labels
        font.draw(batch, "Score", hudLeftX, hudRow1Y, hudSectionWidth, Align.left, false);
        font.draw(batch, "Shield", hudCentreX, hudRow1Y, hudSectionWidth, Align.center, false);
        font.draw(batch, "Lives", hudRightX, hudRow1Y, hudSectionWidth, Align.right, false);
        //second row values
        font.draw(batch, String.format(Locale.getDefault(), "%06d",score), hudLeftX, hudRow2Y, hudSectionWidth, Align.left, false);
        font.draw(batch, String.format(Locale.getDefault(), "%02d",playerShip.shield), hudCentreX, hudRow2Y, hudSectionWidth, Align.center, false);
        font.draw(batch, String.format(Locale.getDefault(), "%02d",playerShip.lives), hudRightX, hudRow2Y, hudSectionWidth, Align.right, false);
    }

    private void SpawnEnemyShips(float deltaTime){
        enemySpawnTimer+=deltaTime;
        if(enemySpawnTimer>timeBetweenEnemySpawns) {
            enemyShipList.add(new EnemyShip((int) (MyGdxGame.random.nextFloat() * 25) + 25, 2, 16, 16, 0.3f, 5, 55, 0.7f,
                    MyGdxGame.random.nextFloat() * (WORLD_WIDTH - 10) + 5, WORLD_HEIGHT - 5, enemyShipTextureRegion, enemyShieldTextureRegion, enemyLaserTextureRegion));
            enemySpawnTimer-=timeBetweenEnemySpawns;
        }
    }

    private void moveEnemy(EnemyShip enemyShip, float deltaTime){
        //check max distance, randomize

        float leftLimit, rightLimit, upLimit, downLimit;
        leftLimit = -enemyShip.boundingBox.x;
        downLimit = (float)WORLD_HEIGHT/2-enemyShip.boundingBox.y;
        rightLimit = WORLD_WIDTH-enemyShip.boundingBox.x-enemyShip.boundingBox.width;
        upLimit = WORLD_HEIGHT-enemyShip.boundingBox.y-enemyShip.boundingBox.height;

        float xMove = enemyShip.getDirectionVector().x * enemyShip.movementSpeed * deltaTime;
        float yMove = enemyShip.getDirectionVector().y * enemyShip.movementSpeed * deltaTime;

        if (xMove > 0) xMove = Math.min(xMove, rightLimit);
        else xMove = Math.max(xMove,leftLimit);

        if (yMove > 0) yMove = Math.min(yMove, upLimit);
        else yMove = Math.max(yMove,downLimit);

        enemyShip.translate(xMove,yMove);
    }

    private void detectInput(float deltaTime){
        //keyboard input

        float leftLimit, rightLimit, upLimit, downLimit;
        leftLimit = -playerShip.boundingBox.x;
        downLimit = -playerShip.boundingBox.y;
        rightLimit = WORLD_WIDTH-playerShip.boundingBox.x-playerShip.boundingBox.width;
        upLimit = (float)WORLD_HEIGHT/2-playerShip.boundingBox.y-playerShip.boundingBox.height;
        if (Gdx.input.isKeyPressed(Input.Keys.RIGHT) && rightLimit>0){
            playerShip.translate(Math.min(playerShip.movementSpeed*deltaTime, rightLimit), 0f);
        }
        if (Gdx.input.isKeyPressed(Input.Keys.UP) && upLimit>0){
            playerShip.translate(0f, Math.min(playerShip.movementSpeed*deltaTime, upLimit));
        }
        if (Gdx.input.isKeyPressed(Input.Keys.LEFT) && leftLimit<0){
            playerShip.translate(Math.max(-playerShip.movementSpeed*deltaTime, leftLimit), 0f);
        }
        if (Gdx.input.isKeyPressed(Input.Keys.DOWN) && downLimit<0){
            playerShip.translate(0f, Math.max(-playerShip.movementSpeed*deltaTime, downLimit));
        }

        //touch/mouse input
        if (Gdx.input.isTouched()) {
            //get the screen position of the touch
            float xTouchPixels = Gdx.input.getX();
            float yTouchPixels = Gdx.input.getY();

            //convert to world position
            Vector2 touchPoint = new Vector2(xTouchPixels, yTouchPixels);
            touchPoint = viewport.unproject(touchPoint);

            //calculate the x and y differences
            Vector2 playerShipCentre = new Vector2(
                    playerShip.boundingBox.x + playerShip.boundingBox.width/2,
                    playerShip.boundingBox.y + playerShip.boundingBox.height/2);

            float touchDistance = touchPoint.dst(playerShipCentre);

            if (touchDistance > TOUCH_MOVEMENT_THRESHOLD) {
                float xTouchDifference = touchPoint.x - playerShipCentre.x;
                float yTouchDifference = touchPoint.y - playerShipCentre.y;

                //scale to the maximum speed of the ship
                float xMove = xTouchDifference / touchDistance * playerShip.movementSpeed * deltaTime;
                float yMove = yTouchDifference / touchDistance * playerShip.movementSpeed * deltaTime;

                if (xMove > 0) xMove = Math.min(xMove, rightLimit);
                else xMove = Math.max(xMove,leftLimit);

                if (yMove > 0) yMove = Math.min(yMove, upLimit);
                else yMove = Math.max(yMove,downLimit);

                playerShip.translate(xMove,yMove);
            }
        }
    }

    private void detectCollisions(){
        //check if player laser intersects enemy ship
        ListIterator<Laser> laserListIterator = playerLaserList.listIterator();
        while(laserListIterator.hasNext()) {
            Laser laser = laserListIterator.next();
            ListIterator<EnemyShip>enemyShipListIterator=enemyShipList.listIterator();
            while (enemyShipListIterator.hasNext()) {
                EnemyShip enemyShip=enemyShipListIterator.next();
                if (enemyShip.intersects(laser.getBoundingBox())) {
                    //contact with enemy ship
                    laserListIterator.remove();
                    if(enemyShip.hit(laser)){
                        enemyShipListIterator.remove();
                        explosionList.add(new Explosion(enemyExplosions,new Rectangle(enemyShip.xPosition,enemyShip.yPosition,enemyShip.width,enemyShip.height),0.7f));
                        score+=15;
                    }
                }
            }
        }
        //check if enemy laser intersects player ship
        laserListIterator = enemyLaserList.listIterator();
        while(laserListIterator.hasNext()) {
            Laser laser = laserListIterator.next();
            if (playerShip.intersects(laser.getBoundingBox())){
                //contact with enemy ship
                if(playerShip.hit(laser)){
                    explosionList.add(new Explosion(playerExplosions,new Rectangle(playerShip.xPosition,playerShip.yPosition,playerShip.width,playerShip.height),1f));
                    playerShip.shield=10;
                    playerShip.lives--;
                }
                laserListIterator.remove();
                break;
            }
        }
    }

    private void renderExplosions(float deltaTime){
        ListIterator<Explosion>explosionListIterator=explosionList.listIterator();
        while (explosionListIterator.hasNext()){
            Explosion explosion=explosionListIterator.next();
            explosion.update(deltaTime);
            if (explosion.isFinished()){
                explosionListIterator.remove();
            }
            else {
                explosion.draw(batch);
            }
        }
    }

    private void renderLasers(float deltaTime){
        if (playerShip.canFireLaser()){
            Laser[] lasers = playerShip.fireLasers();
            for (Laser laser: lasers){
                playerLaserList.add(laser);
            }
        }
        //enemy lasers
        ListIterator<EnemyShip> enemyShipListIterator = enemyShipList.listIterator();
        while (enemyShipListIterator.hasNext()){
            EnemyShip enemyShip = enemyShipListIterator.next();
            if (enemyShip.canFireLaser()){
                Laser[] lasers = enemyShip.fireLasers();
                for (Laser laser: lasers){
                    enemyLaserList.add(laser);
                }
            }
        }

        //draw
        //remove old
        ListIterator<Laser> iterator = playerLaserList.listIterator();
        while(iterator.hasNext()) {
            Laser laser = iterator.next();
            laser.draw(batch);
            laser.yPosition += laser.movementSpeed*deltaTime;
            if (laser.yPosition > WORLD_HEIGHT) {
                iterator.remove();
            }
        }
        iterator = enemyLaserList.listIterator();
        while(iterator.hasNext()) {
            Laser laser = iterator.next();
            laser.draw(batch);
            laser.yPosition -= laser.movementSpeed*deltaTime;
            if (laser.yPosition + laser.height < 0) {
                iterator.remove();
            }
        }
    }

    private void renderBackground(float deltaTime){
        backgroundOffsets[0] += deltaTime*backgroundMaxScrollingSpeed/8;
        backgroundOffsets[1] += deltaTime*backgroundMaxScrollingSpeed/4;
        backgroundOffsets[2] += deltaTime*backgroundMaxScrollingSpeed/2;
        backgroundOffsets[3] += deltaTime*backgroundMaxScrollingSpeed;

        for (int layer=0;layer<backgroundOffsets.length;layer++){
            if (backgroundOffsets[layer]>WORLD_HEIGHT){
                backgroundOffsets[layer]=0;
            }
            batch.draw(backgrounds[layer],0,-backgroundOffsets[layer],WORLD_WIDTH,WORLD_HEIGHT);
            batch.draw(backgrounds[layer],0,-backgroundOffsets[layer]+WORLD_HEIGHT,WORLD_WIDTH,WORLD_HEIGHT);
        }

    }


    @Override
    public void resize(int width, int height) {
        viewport.update(width,height,true);
        batch.setProjectionMatrix(camera.combined);
    }

    @Override
    public void pause() {

    }

    @Override
    public void resume() {

    }

    @Override
    public void hide() {

    }

    @Override
    public void dispose() {

    }
}
