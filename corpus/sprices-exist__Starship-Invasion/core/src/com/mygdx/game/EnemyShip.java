package com.mygdx.game;

import com.badlogic.gdx.graphics.g2d.Batch;
import com.badlogic.gdx.graphics.g2d.TextureRegion;
import com.badlogic.gdx.math.Vector2;

class EnemyShip extends Ship {

    Vector2 directionVector;
    float timeSinceLastDirectionChange=0;
    float directionChangeFrequency=0.75f;


    public EnemyShip(float movementSpeed, int shield, float width, float height,
                     float laserWidth, float laserHeight, float laserMovementSpeed, float timeBetweenShots,
                     float xCenter, float yCenter,
                     TextureRegion shipTextureRegion, TextureRegion shieldTextureRegion, TextureRegion laserTextureRegion) {
        super(movementSpeed, shield, width, height, laserWidth, laserHeight, laserMovementSpeed, timeBetweenShots,
                xCenter, yCenter, shipTextureRegion, shieldTextureRegion, laserTextureRegion);
        directionVector=new Vector2(0,-1);
    }

    public Vector2 getDirectionVector() {
        return directionVector;
    }

    private void RandomizeDirectionVector(){
        double bearing=MyGdxGame.random.nextDouble()*6.283185;//2*pi
        directionVector.x=(float)Math.sin(bearing);
        directionVector.y=(float)Math.cos(bearing);
    }

    @Override
    public void update(float deltaTime) {
        super.update(deltaTime);
        timeSinceLastDirectionChange += deltaTime;
        if (timeSinceLastDirectionChange>directionChangeFrequency){
            RandomizeDirectionVector();
            timeSinceLastDirectionChange-=directionChangeFrequency;
        }
    }

    @Override
    public Laser[] fireLasers() {
        Laser[] laser = new Laser[1];
        laser[0] = new Laser(xPosition + width * 0.51f, yPosition - height*0.1f,
                laserWidth, laserHeight,
                laserMovementSpeed, laserTextureRegion);

        timeSinceLastShot = 0;

        return laser;
    }

    @Override
    public void draw(Batch batch){
        batch.draw(shipTextureRegion , xPosition, yPosition, width, height);
        if (shield>0){
            batch.draw(shieldTextureRegion, xPosition+width*0.3f, yPosition+height*0.12f, width-width*0.6f, height-height*0.6f);
        }
    }
}
