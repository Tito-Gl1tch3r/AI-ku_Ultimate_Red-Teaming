package com.smartnsoft.sampleokhttp;

import java.io.IOException;
import java.util.List;

import android.os.Bundle;
import android.support.v7.app.AppCompatActivity;
import android.util.Log;
import android.view.View;
import android.view.View.OnClickListener;

import com.smartnsoft.droid4me.cache.Values.CacheException;
import com.smartnsoft.droid4me.ws.WebServiceClient.CallException;

import com.smartnsoft.sampleokhttp.bo.Post;
import com.smartnsoft.sampleokhttp.ws.ExempleServices;

/**
 * @author Ludovic Roland
 * @since 2018.03.23
 */
public final class MainActivity
    extends AppCompatActivity
{

  private static final String TAG = MainActivity.class.getSimpleName();

  @Override
  protected void onCreate(Bundle savedInstanceState)
  {
    super.onCreate(savedInstanceState);
    setContentView(R.layout.activity_main);

    findViewById(R.id.btn1).setOnClickListener(new OnClickListener()
    {
      @Override
      public void onClick(View v)
      {
        new Thread(new Runnable()
        {
          @Override
          public void run()
          {
            try
            {
              final Post post = ExempleServices.getInstance().getAPost();
              Log.d(MainActivity.TAG, post.toString());
            }
            catch (CallException exception)
            {
              Log.w(MainActivity.TAG, "Cannot retrieve the post", exception);
            }
          }
        }).start();
      }
    });

    findViewById(R.id.btn2).setOnClickListener(new OnClickListener()
    {
      @Override
      public void onClick(View v)
      {
        new Thread(new Runnable()
        {
          @Override
          public void run()
          {
            try
            {
              final List<Post> posts = ExempleServices.getInstance().getPostsForUserId("1");

              for (final Post post : posts)
              {
                Log.d(MainActivity.TAG, post.toString());
              }
            }
            catch (CallException exception)
            {
              Log.w(MainActivity.TAG, "Cannot retrieve the posts", exception);
            }
          }
        }).start();
      }
    });

    findViewById(R.id.btn3).setOnClickListener(new OnClickListener()
    {
      @Override
      public void onClick(View v)
      {
        new Thread(new Runnable()
        {
          @Override
          public void run()
          {
            try
            {
              final Post postToPost = new Post();
              postToPost.userId = 1;
              postToPost.title = "test title";
              postToPost.body = "test body";

              final Post post = ExempleServices.getInstance().postAPost(postToPost);
              Log.d(MainActivity.TAG, post.toString());
            }
            catch (CallException | IOException exception)
            {
              Log.w(MainActivity.TAG, "Cannot post the post", exception);
            }
          }
        }).start();
      }
    });

    findViewById(R.id.btn4).setOnClickListener(new OnClickListener()
    {
      @Override
      public void onClick(View v)
      {
        new Thread(new Runnable()
        {
          @Override
          public void run()
          {
            try
            {
              final List<Post> posts = ExempleServices.getInstance().getPostsFromCache("1");

              for (final Post post : posts)
              {
                Log.d(MainActivity.TAG, post.toString());
              }
            }
            catch (CacheException exception)
            {
              Log.w(MainActivity.TAG, "Cannot retrieve the posts", exception);
            }
          }
        }).start();
      }
    });
  }

}
