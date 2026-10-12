package test

import com.smartnsoft.retrofitsample.bo.IP
import com.smartnsoft.retrofitsample.ws.MyWebServiceCaller
import com.smartnsoft.ws.retrofit.caller.RetrofitWebServiceCaller
import junit.framework.Assert.*
import org.junit.AfterClass
import org.junit.Before
import org.junit.BeforeClass
import org.junit.Test
import java.io.File
import java.lang.Exception

/**
 * @author David Fournier
 * @since 2019.06.19
 */

class Test
{

  companion object
  {

    @BeforeClass
    @JvmStatic
    fun setup()
    {
      File("./http-cache").deleteRecursively()
      MyWebServiceCaller.setupCache(File("./"), "first.db")
    }

    @AfterClass
    @JvmStatic
    fun tearDown()
    {
      File("./http-cache").deleteRecursively()
    }
  }

  @Before
  fun deleteCache()
  {
    "./http-cache/first.db".apply {
      if (File(this).exists())
      {
        File(this).deleteRecursively()
        File(this).mkdir()
      }
    }
  }

  @Test
  fun mustSetCache_cacheNotSet_throwsIllegalStateException()
  {
    val response = MyWebServiceCaller.getString()
    assertTrue(response is String)
    assertTrue(response != null)

    MyWebServiceCaller.getIp()
    Thread.sleep(2000)

    MyWebServiceCaller.delete()
    MyWebServiceCaller.post("127.0.0.1")
    MyWebServiceCaller.put("127.0.0.2")
    MyWebServiceCaller.status(200)
    //MyWebServiceCaller.status(400)
  }

  @Test
  fun cache()
  {
    assertCacheEmpty()
    val ip = MyWebServiceCaller.getIp(fetchPolicyType = RetrofitWebServiceCaller.FetchPolicyType.ONLY_NETWORK, cacheRetentionPolicyInSeconds = 0, customKey = null)
    assertTrue(ip is IP)
    assertNotNull(ip)
    assertTrue(ip?.origin == "91.151.70.8, 91.151.70.8")
    assertCacheEmpty()
  }

  @Test
  fun cache2()
  {
    assertCacheEmpty()
    val ip = MyWebServiceCaller.getIp(fetchPolicyType = RetrofitWebServiceCaller.FetchPolicyType.NETWORK_THEN_CACHE, cacheRetentionPolicyInSeconds = 2, customKey = null)
    assertTrue(ip is IP)
    assertNotNull(ip)
    assertTrue(ip?.origin == "91.151.70.8, 91.151.70.8")
    val ipCached = MyWebServiceCaller.getIp(fetchPolicyType = RetrofitWebServiceCaller.FetchPolicyType.ONLY_CACHE, customKey = null)
    assertTrue(ipCached == ip)
    Thread.sleep(2_000L)
    assertCacheEmpty()
  }

  private fun assertCacheEmpty()
  {
    try
    {
      MyWebServiceCaller.getIp(fetchPolicyType = RetrofitWebServiceCaller.FetchPolicyType.ONLY_CACHE, customKey = null)
      assertTrue(false) // Should not happen as call throws an exception
    }
    catch (exception: Exception)
    {
      assertTrue(exception is RetrofitWebServiceCaller.CacheException)
    }
  }
}