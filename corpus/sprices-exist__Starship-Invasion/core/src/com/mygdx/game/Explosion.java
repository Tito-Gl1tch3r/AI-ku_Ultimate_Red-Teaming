package com.mygdx.game;

import com.badlogic.gdx.graphics.g2d.Animation;
import com.badlogic.gdx.graphics.g2d.SpriteBatch;
import com.badlogic.gdx.graphics.g2d.TextureRegion;
import com.badlogic.gdx.math.Rectangle;


class Explosion {
    private Animation<TextureRegion> explosionAnimation;
    private float explosionTimer;
    private Rectangle boundingBox;
    Explosion(TextureRegion textures[], Rectangle boundingBox, float totalAnimationTime){
        this.boundingBox=boundingBox;

        explosionAnimation=new Animation<TextureRegion>(totalAnimationTime/textures.length,textures);
        explosionTimer=0;
    }
    public void update(float deltaTime){
        explosionTimer+=deltaTime;
    }
    public void draw(SpriteBatch batch){
        batch.draw(explosionAnimation.getKeyFrame(explosionTimer),boundingBox.x,boundingBox.y,boundingBox.width,boundingBox.height);
    }
    public boolean isFinished(){
        return explosionAnimation.isAnimationFinished(explosionTimer);
    }
}
