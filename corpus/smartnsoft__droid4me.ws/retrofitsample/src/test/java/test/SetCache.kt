package test

import com.smartnsoft.retrofitsample.bo.IP
import com.smartnsoft.retrofitsample.ws.WSApi
import com.smartnsoft.ws.retrofit.caller.JacksonRetrofitWebServiceCaller
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

/**
 * @author David Fournier
 * @since 2019.06.19
 */

class SetCache
{

  private class SimpleWebServiceCaller(builtInCache: BuiltInCache? = BuiltInCache())
    : JacksonRetrofitWebServiceCaller<WSApi>(api = WSApi::class.java, baseUrl = WSApi.url, withBuiltInCache = builtInCache)
  {
    fun getIp(): IP?
    {
      return execute(IP::class.java, service.getIp(), CachePolicy(FetchPolicyType.CACHE_THEN_NETWORK, cacheRetentionPolicyInSeconds = 20, customKey = "ip"))
    }
  }

  @Test(expected = IllegalStateException::class)
  fun mustSetCache_cacheNotSet_throwsIllegalStateException()
  {
    val serviceCaller = SimpleWebServiceCaller()
    try
    {
      serviceCaller.getIp()
    }
    catch (exception: Exception)
    {
      assertEquals("If you use the built-in cache, you have to set your cache directory before performing any call!", exception.message)
      throw exception
    }
  }

  @Test
  fun mustNotSetCache_cacheNotSet_doesNotThrow()
  {
    SimpleWebServiceCaller(builtInCache = null).getIp()
    assertTrue(true)
  }

  @Test(expected = IllegalStateException::class)
  fun mustNotSetCache_cacheSet_doesNotThrow()
  {
    val serviceCaller = SimpleWebServiceCaller(builtInCache = null)
    try
    {
      serviceCaller.setupCache(File(""), "")
    }
    catch (exception: Exception)
    {
      assertEquals("You must not setup your cache file as the builtInCache is set to null!", exception.message)
      throw exception
    }
  }
}