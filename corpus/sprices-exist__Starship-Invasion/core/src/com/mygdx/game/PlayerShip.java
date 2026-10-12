package com.mygdx.game;

import com.badlogic.gdx.graphics.g2d.Batch;
import com.badlogic.gdx.graphics.g2d.TextureRegion;

class PlayerShip extends Ship {

    int lives;

    public PlayerShip(float movementSpeed, int shield, float width, float height, float laserWidth, float laserHeight,
                      float laserMovementSpeed, float timeBetweenShots, float xCenter, float yCenter,
                      TextureRegion shipTextureRegion, TextureRegion shieldTextureRegion, TextureRegion laserTextureRegion) {
        super(movementSpeed, shield, width, height, laserWidth, laserHeight, laserMovementSpeed, timeBetweenShots,
                xCenter, yCenter, shipTextureRegion, shieldTextureRegion, laserTextureRegion);
        lives=3;
    }

    @Override
    public Laser[] fireLasers() {
        Laser[] laser = new Laser[1];
        laser[0] = new Laser(xPosition + width * 0.5f, yPosition + height * 0.83f,
                laserWidth, laserHeight,
                laserMovementSpeed, laserTextureRegion);

        timeSinceLastShot = 0;
        return laser;
    }

    @Override
    public void draw(Batch batch){
        batch.draw(shipTextureRegion , xPosition, yPosition, width, height);
        if (shield>0){
            batch.draw(shieldTextureRegion, xPosition+width*0.25f, yPosition+height*0.4f, width-width*0.5f, height-height*0.5f);
        }
    }
}
