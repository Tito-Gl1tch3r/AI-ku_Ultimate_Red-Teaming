package com.smartnsoft.ws.retrofit.caller

import com.fasterxml.jackson.core.type.TypeReference
import com.fasterxml.jackson.databind.JsonMappingException
import com.fasterxml.jackson.databind.ObjectMapper
import com.fasterxml.jackson.module.kotlin.KotlinModule
import com.smartnsoft.ws.exception.JacksonExceptions
import com.smartnsoft.ws.retrofit.caller.RetrofitWebServiceCaller.BuiltInCache
import okhttp3.Response
import retrofit2.Retrofit
import retrofit2.converter.jackson.JacksonConverterFactory
import retrofit2.converter.scalars.ScalarsConverterFactory

/**
 * @author David Fournier
 * @since 2018.03.26
 */

/**
 * A class where you configure your service
 *
 * @param[api] interface where you implement your retrofit calls, see [Retrofit.create].
 * @param[baseUrl] base url of the API you want to reach.
 * @param[connectTimeout] the connect timeout is applied when connecting a TCP socket to the target host.
 * @param[readTimeout] the read timeout is applied to both the TCP socket and for individual read IO operations including on [Source] of the [Response].
 * @param[writeTimeout] the write timeout is applied for individual write IO operations.
 * @param[withBuiltInCache] class to configure the cache and its default values. You must [setupCache]. If set to null, the built in cache is disabled and you don't need to [setupCache]. See [BuiltInCache].
 *
 */
abstract class JacksonRetrofitWebServiceCaller<API>
@JvmOverloads
constructor(api: Class<API>,
            baseUrl: String,
            connectTimeout: Long = CONNECT_TIMEOUT,
            readTimeout: Long = READ_TIMEOUT,
            writeTimeout: Long = WRITE_TIMEOUT,
            withBuiltInCache: BuiltInCache? = BuiltInCache())
  : RetrofitWebServiceCaller<API>(api, baseUrl, connectTimeout, readTimeout, writeTimeout, withBuiltInCache, arrayOf(JacksonConverterFactory.create(), ScalarsConverterFactory.create()))
{
  private val mapper = ObjectMapper()
      .registerModule(KotlinModule())

  override fun <T> mapResponseToObject(responseBody: String?, clazz: Class<T>): T?
  {
    try
    {
      return mapper.readValue(responseBody, clazz)
    }
    catch (exception: JsonMappingException)
    {
      throw JacksonExceptions.JacksonParsingException(exception)
    }
    catch (exception: Exception)
    {
      throw JacksonExceptions.JacksonParsingException(exception)
    }
  }

  override fun <T> mapResponseToObject(responseBody: String?, typeReference: TypeReference<T>): T?
  {
    try
    {
      return mapper.readValue(responseBody, typeReference)
    }
    catch (exception: JsonMappingException)
    {
      throw JacksonExceptions.JacksonParsingException(exception)
    }
    catch (exception: Exception)
    {
      throw JacksonExceptions.JacksonParsingException(exception)
    }
  }
}