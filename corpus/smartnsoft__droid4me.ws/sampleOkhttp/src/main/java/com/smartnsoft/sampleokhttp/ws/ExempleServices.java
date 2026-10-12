package com.smartnsoft.sampleokhttp.ws;

import java.io.IOException;
import java.io.InputStream;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import android.util.Xml.Encoding;

import com.smartnsoft.droid4me.cache.Persistence;
import com.smartnsoft.droid4me.cache.Persistence.PersistenceException;
import com.smartnsoft.droid4me.cache.Values.CacheException;
import com.smartnsoft.droid4me.ws.WSUriStreamParser.KeysAggregator;
import com.smartnsoft.droid4me.ws.WithCacheWSUriStreamParser.SimpleIOStreamerSourceKey;
import com.smartnsoft.droid4me.wscache.BackedWSUriStreamParser;
import com.smartnsoft.droid4me.wscache.BackedWSUriStreamParser.BackedUriStreamedMap;

import com.fasterxml.jackson.core.type.TypeReference;
import com.smartnsoft.sampleokhttp.bo.Post;
import com.smartnsoft.ws.okhttp.JacksonOkHttpClientWebServiceCaller;
import com.smartnsoft.ws.okhttp.ReuseOkHttpClient;

/**
 * @author Ludovic Roland
 * @since 2018.03.23
 */
@ReuseOkHttpClient
public final class ExempleServices
    extends JacksonOkHttpClientWebServiceCaller
{

  private static final String URL = "https://jsonplaceholder.typicode.com";

  private static volatile ExempleServices instance;

  // We accept the "out-of-order writes" case
  public static ExempleServices getInstance()
  {
    if (instance == null)
    {
      synchronized (ExempleServices.class)
      {
        if (instance == null)
        {
          instance = new ExempleServices();
        }
      }
    }

    return instance;
  }

  private final BackedWSUriStreamParser.BackedUriStreamedMap<List<Post>, String, CallException, PersistenceException> postStreamParser = new BackedUriStreamedMap<List<Post>, String, CallException, PersistenceException>(Persistence.getInstance(), this)
  {

    @Override
    public List<Post> parse(String parameter, Map<String, List<String>> headers, InputStream inputStream)
        throws CallException
    {
      return jacksonParser.deserializeJson(inputStream, new TypeReference<List<Post>>() {});
    }

    @Override
    public KeysAggregator<String> computeUri(String userId)
    {
      final Map<String, String> parameters = new HashMap<>();
      parameters.put("userId", userId);

      return SimpleIOStreamerSourceKey.fromUriStreamerSourceKey(new HttpCallTypeAndBody(computeUri(ExempleServices.URL, "posts", parameters)), null);
    }

  };

  private ExempleServices()
  {
    super(5_000, 5_000, false);
  }

  @Override
  protected String getUrlEncoding()
  {
    return Encoding.UTF_8.toString();
  }

  @Override
  protected String getContentEncoding()
  {
    return Encoding.ISO_8859_1.toString();
  }

  public Post getAPost()
      throws CallException
  {
    final HttpResponse httpResponse = runRequest(ExempleServices.URL + "/posts/1");
    return jacksonParser.deserializeJson(httpResponse.inputStream, Post.class);
  }

  public List<Post> getPostsForUserId(String userId)
      throws CallException
  {
    final Map<String, String> parameters = new HashMap<>();
    parameters.put("userId", userId);

    final HttpResponse httpResponse = runRequest(computeUri(ExempleServices.URL, "posts", parameters));
    return jacksonParser.deserializeJson(httpResponse.inputStream, new TypeReference<List<Post>>() {});
  }

  public Post postAPost(Post post)
      throws CallException, IOException
  {
    final Map<String, String> headers = new HashMap<>();
    headers.put("Content-type", "application/json; charset=UTF-8");

    final HttpResponse httpResponse = runRequest(ExempleServices.URL + "/posts", CallType.Post, headers, null, jacksonParser.serializeJson(post), null);
    return jacksonParser.deserializeJson(httpResponse.inputStream, Post.class);
  }

  public List<Post> getPostsFromCache(String userId)
      throws CacheException
  {
    return postStreamParser.backed.getRetentionValue(true, 5 * 60 * 1000, null, userId);
  }


}
