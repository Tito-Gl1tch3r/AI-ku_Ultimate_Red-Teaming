package com.smartnsoft.retrofitsample.ws

import com.smartnsoft.retrofitsample.bo.IP
import com.smartnsoft.retrofitsample.bo.PostResponse
import com.smartnsoft.ws.retrofit.caller.JacksonRetrofitWebServiceCaller
import okhttp3.Response

/**
 *
 * @author David Fournier
 * @since 2017.10.27
 */
object MyWebServiceCaller
  : JacksonRetrofitWebServiceCaller<WSApi>(api = WSApi::class.java, baseUrl = WSApi.url)
{
  fun getString(): String?
  {
    return execute(service.getString())
  }

  fun getIp(fetchPolicyType: FetchPolicyType = FetchPolicyType.CACHE_THEN_NETWORK, cacheRetentionPolicyInSeconds: Int = 20, customKey: String? = "ip"): IP?
  {
    return execute(IP::class.java, service.getIp(), CachePolicy(fetchPolicyType, cacheRetentionPolicyInSeconds = cacheRetentionPolicyInSeconds, customKey = customKey))
  }

  fun getIp2(): IP?
  {
    return execute(IP::class.java, service.getIp(), CachePolicy(FetchPolicyType.CACHE_THEN_NETWORK, allowedTimeExpiredCacheInSeconds = 100, customKey = "ip2"))
  }

  fun getIp3(): IP?
  {
    return execute(IP::class.java, service.getIp(), CachePolicy(FetchPolicyType.CACHE_THEN_NETWORK, allowedTimeExpiredCacheInSeconds = 100, customKey = "ip3"))
  }

  fun delete(): String?
  {
    return execute(service.delete())
  }

  fun post(ip: String): PostResponse?
  {
    return execute(PostResponse::class.java, service.post(ip))
  }

  fun put(ip: String): PostResponse?
  {
    return execute(PostResponse::class.java, service.put(ip))
  }

  fun status(code: Int): Response?
  {
    return executeResponse(service.status(code))
  }
}