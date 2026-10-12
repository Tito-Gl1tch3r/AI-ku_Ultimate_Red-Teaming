package com.mygdx.game;

import com.badlogic.gdx.graphics.g2d.Batch;
import com.badlogic.gdx.graphics.g2d.TextureRegion;
import com.badlogic.gdx.math.Rectangle;

abstract class Ship {
     //Ship characteristics
     float movementSpeed; //world units per seconds
     int shield;

     //position and dimension
     float xPosition, yPosition; //lower-left corner
     float width, height;
     Rectangle boundingBox;

     //laser info
    float laserWidth, laserHeight;
    float laserMovementSpeed;
    float timeBetweenShots;
    float timeSinceLastShot=0;

     //graphics
     TextureRegion shipTextureRegion , shieldTextureRegion, laserTextureRegion;

    public Ship(float movementSpeed, int shield, float width, float height,
                float laserWidth, float laserHeight, float laserMovementSpeed, float timeBetweenShots,
                float xCenter, float yCenter, TextureRegion shipTextureRegion,
                TextureRegion shieldTextureRegion, TextureRegion laserTextureRegion) {
        this.movementSpeed = movementSpeed;
        this.shield = shield;

        this.xPosition = xCenter-width/2;
        this.yPosition = yCenter-height/2;
        this.width = width;
        this.height = height;
        this.boundingBox=new Rectangle(xPosition+width*0.3f,yPosition+height*0.3f,width*0.4f, height*0.5f);

        this.laserWidth = laserWidth;
        this.laserHeight = laserHeight;
        this.laserMovementSpeed = laserMovementSpeed;
        this.timeBetweenShots = timeBetweenShots;
        this.shipTextureRegion  = shipTextureRegion;
        this.shieldTextureRegion = shieldTextureRegion;
        this.laserTextureRegion = laserTextureRegion;
    }

    public void update(float deltaTime) {
        boundingBox.set(xPosition+width*0.3f,yPosition+height*0.3f,width*0.4f, height*0.5f);
        timeSinceLastShot += deltaTime;
    }

    public boolean canFireLaser() {
        return (timeSinceLastShot - timeBetweenShots >= 0);
    }

    public abstract Laser[] fireLasers();

    public boolean intersects(Rectangle otherRectangle){
        return boundingBox.overlaps(otherRectangle);
    }

    public boolean hit(Laser laser){
        if (shield>0){
            shield--;
            return false;
        }
        return true;
    }

    public void translate(float xChange, float yChange){
        xPosition+=xChange;
        yPosition+=yChange;
    }

    public void draw(Batch batch){
        batch.draw(shipTextureRegion , xPosition, yPosition, width, height);
        if (shield>0){
            batch.draw(shieldTextureRegion, xPosition+1, yPosition+2, width-2, height-2);
        }
    }
}
