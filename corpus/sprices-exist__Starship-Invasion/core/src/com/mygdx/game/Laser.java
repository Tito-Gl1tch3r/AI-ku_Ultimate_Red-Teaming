package com.mygdx.game;

import com.badlogic.gdx.graphics.g2d.Batch;
import com.badlogic.gdx.graphics.g2d.TextureRegion;
import com.badlogic.gdx.math.Rectangle;

class Laser {
    //position and dimensions
    float xPosition, yPosition;  //bottom centre of the laser
    float width, height;

    //laser physical characteristics
    float movementSpeed; //world units per second

    //graphics
    TextureRegion textureRegion;

    public Laser(float xCentre, float yBottom, float width, float height, float movementSpeed, TextureRegion textureRegion) {
        this.xPosition = xCentre - width/2;
        this.yPosition = yBottom;
        this.width = width;
        this.height = height;
        this.movementSpeed = movementSpeed;
        this.textureRegion = textureRegion;
    }

    public void draw(Batch batch) {
        batch.draw(textureRegion, xPosition-width/2, yPosition, width, height);
    }

    public Rectangle getBoundingBox(){
        return new Rectangle(xPosition,yPosition,width,height);
    }

}
