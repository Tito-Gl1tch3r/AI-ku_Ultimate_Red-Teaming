package com.smartnsoft.ws.retrofit.caller

import android.support.annotation.WorkerThread
import com.fasterxml.jackson.core.type.TypeReference
import com.smartnsoft.ws.exception.CallException
import com.smartnsoft.ws.exception.JacksonExceptions
import com.smartnsoft.ws.retrofit.caller.RetrofitWebServiceCaller.BuiltInCache
import com.smartnsoft.ws.retrofit.caller.RetrofitWebServiceCaller.FetchPolicyType.*
import com.smartnsoft.ws.retrofit.bo.ResponseWithError
import com.smartnsoft.logger.Logger
import com.smartnsoft.logger.LoggerFactory
import okhttp3.*
import retrofit2.Call
import retrofit2.Converter
import retrofit2.Retrofit
import java.io.File
import java.io.IOException
import java.net.URI
import java.net.URISyntaxException
import java.util.*
import java.util.concurrent.TimeUnit
import kotlin.collections.ArrayList

/**
 *
 * @author David Fournier
 * @since 2017.10.12
 */

/**
 * A class where you configure your service
 *
 * @param[api] interface where you implement your retrofit calls, see [Retrofit.create].
 * @param[baseUrl] base url of the API you want to reach.
 * @param[connectTimeout] the connect timeout is applied when connecting a TCP socket to the target host.
 * @param[readTimeout] the read timeout is applied to both the TCP socket and for individual read IO operations including on [Source] of the [Response].
 * @param[writeTimeout] the write timeout is applied for individual write IO operations.
 * @param[builtInCache] class to configure the cache and its default values. You must [setupCache]. If set to null, the built in cache is disabled and you don't need to [setupCache]. See [BuiltInCache].
 * @param[converterFactories] array of converter factory for serialization and deserialization of objects.
 *
 */
@Suppress("UNCHECKED_CAST", "unused")
abstract class RetrofitWebServiceCaller<API>(protected val api: Class<API>,
                                             protected val baseUrl: String,
                                             protected val connectTimeout: Long = CONNECT_TIMEOUT,
                                             protected val readTimeout: Long = READ_TIMEOUT,
                                             protected val writeTimeout: Long = WRITE_TIMEOUT,
                                             protected val builtInCache: BuiltInCache? = BuiltInCache(),
                                             protected val converterFactories: Array<Converter.Factory> = emptyArray())
{

  /**
   * An enum that define the way the [Call] has to be done. Possible values are:
   *
   *
   * [ONLY_NETWORK] - Fetch to network, or fail.
   *
   * [ONLY_CACHE] - Fetch in [Cache], or fail.
   *
   * [NETWORK_THEN_CACHE] - Fetch to network, then fetch in [Cache], or fail.
   *
   * [CACHE_THEN_NETWORK] - Fetch in [Cache], then fetch to network, or fail.
   *
   * [SERVER] - Use the cache-control of server's headers.
   *
   */
  enum class FetchPolicyType
  {

    ONLY_NETWORK,
    ONLY_CACHE,
    NETWORK_THEN_CACHE,
    CACHE_THEN_NETWORK,
    SERVER
  }

  companion object
  {

    const val ONLY_CACHE_UNSATISFIABLE_ERROR_CODE = 504

    const val CUSTOM_CACHE_URL_PREFIX = "https://default.customkeycache.smart/"

    const val SMART_ORIGINAL_URL_HEADER = "Smart-Original-URL"

    const val SMART_SERVER_DATE_HEADER = "Smart-Server-Date"

    const val PRAGMA_HEADER = "Pragma"

    const val DATE_HEADER = "Date"

    const val CACHE_CONTROL_HEADER = "Cache-Control"

    const val CACHE_BASE_PATH = "http-cache/"

    const val CONNECT_TIMEOUT = 10 * 1000L                  // 10 seconds

    const val READ_TIMEOUT = 10 * 1000L                     // 10 seconds

    const val WRITE_TIMEOUT = 10 * 1000L                    // 10 seconds

    const val CACHE_SIZE = 10 * 1024 * 1024L                // 10 Mb

    const val DEFAULT_CACHE_TIME_IN_SECONDS = 60 * 60 * 1000  // 1 hour
  }

  class CacheException(message: String?) : RuntimeException(message)

  /**
   * Class to configure the behavior of the [Cache] and its default values.
   *
   * @param[defaultFetchPolicyType] enum that define the way all the [Call] are done, see [FetchPolicyType].
   * @param[defaultCacheRetentionTimeInSeconds] default time in seconds all the [Call] will cache the [Response] (= maxAge).
   * @param[defaultAllowedTimeExpiredCacheInSeconds] default time in seconds you allow all the cached [Response] to be valid after their expiration (= maxStale).
   * @param[defaultUseClientDateForCache] if true, override all the date of the [Response] with the client date. Useful if the server time is misconfigured.
   * @param[shouldReturnErrorResponse] set to true if you want to get error response instead of an exception.
   *
   */
  class BuiltInCache
  @JvmOverloads
  constructor(val defaultFetchPolicyType: FetchPolicyType = FetchPolicyType.NETWORK_THEN_CACHE,
              val defaultCacheRetentionTimeInSeconds: Int? = RetrofitWebServiceCaller.DEFAULT_CACHE_TIME_IN_SECONDS,
              val defaultAllowedTimeExpiredCacheInSeconds: Int? = null,
              val defaultUseClientDateForCache: Boolean = true,
              val shouldReturnErrorResponse: Boolean = false)

  /**
   * Class to configure the behavior of the [Call].
   *
   * @param[fetchPolicyType] enum that define the way the call is done, see [FetchPolicyType].
   * @param[cacheRetentionPolicyInSeconds] time in seconds the call will cache the [Response] (= maxAge).
   * @param[allowedTimeExpiredCacheInSeconds] time in seconds you allow the cached [Response] to be valid after its expiration (= maxStale).
   * @param[useClientDateForCache] if true, override the date of the [Response] with the client date. Useful if the server time is misconfigured.
   * @param[customKey] use this if you want to store the [Response] with a custom key in [Cache] (rather than its url, used by default).
   *
   */
  inner class CachePolicy
  @JvmOverloads
  constructor(val fetchPolicyType: FetchPolicyType = builtInCache?.defaultFetchPolicyType
      ?: FetchPolicyType.ONLY_NETWORK,
              val cacheRetentionPolicyInSeconds: Int? = builtInCache?.defaultCacheRetentionTimeInSeconds,
              val allowedTimeExpiredCacheInSeconds: Int? = builtInCache?.defaultAllowedTimeExpiredCacheInSeconds,
              val useClientDateForCache: Boolean = builtInCache?.defaultUseClientDateForCache ?: true,
              val customKey: String? = null)

  // This class is instantiated only once and does not leak as RetrofitWebServiceCaller is a Singleton.
  // So it is OK to declare it `inner`, to pass the `isConnected` boolean.
  private inner class AppCacheInterceptor
  @JvmOverloads
  constructor(private val shouldReturnErrorResponse: Boolean = false)
    : Interceptor
  {

    private val log: Logger by lazy {
      LoggerFactory.getInstance(AppCacheInterceptor::class.java)
    }

    override fun intercept(chain: Interceptor.Chain): Response?
    {
      if (cacheDir == null)
      {
        /**
         * Note: see [setupCache] to fix this exception.
         */
        throw IllegalStateException("If you use the built-in cache, you have to set your cache directory before performing any call!")
      }

      val originalRequestUrl = chain.request().url()
      val cachePolicy = chain.request().tag() as? RetrofitWebServiceCaller<API>.CachePolicy
      val fetchPolicyType = cachePolicy?.fetchPolicyType

      if (fetchPolicyType != null)
      {
        val request = buildRequest(chain.request(), cachePolicy)
        var firstTry: Response? = null
        var firstException: Exception? = null

        val shouldDoSecondCall = try
        {
          firstTry = chain.proceed(request)

          shouldDoSecondCall(firstTry, null)
        }
        catch (exception: Exception)
        {
          firstException = exception

          val errorMessage = "Call of ${chain.request().method()} to ${chain.request().url()} with cache policy ${fetchPolicyType.name} failed."
          debug(errorMessage)

          shouldDoSecondCall(firstTry, exception)
        }

        // Fails fast if the connectivity is known to be lost
        if (hasConnectivity().not())
        {
          if (fetchPolicyType == FetchPolicyType.ONLY_NETWORK)
          {
            val errorMessage = "Call of ${chain.request().method()} to ${chain.request().url()} with cache policy ${fetchPolicyType.name} failed because the network is not connected."
            debug(errorMessage)

            return onStatusCodeNotOk(firstTry, firstException)
          }
        }

        val secondRequest: Request
        when
        {
          (firstTry == null || firstTry.code() == ONLY_CACHE_UNSATISFIABLE_ERROR_CODE) && fetchPolicyType == FetchPolicyType.CACHE_THEN_NETWORK ->
          {
            debug("Call of ${request.method()} to ${request.url()} with cache policy ${fetchPolicyType.name} failed to find a cached response. Trying call to network.")

            // Fails fast if the connectivity is known to be lost
            if (hasConnectivity().not())
            {
              val errorMessage = "Call of ${chain.request().method()} to ${chain.request().url()} with cache policy ${fetchPolicyType.name} failed because the network is not connected."
              debug(errorMessage)

              return onStatusCodeNotOk(firstTry, firstException)
            }

            secondRequest = buildNetworkRequest(request, cachePolicy, originalRequestUrl)
          }
          (firstTry == null || firstTry.isSuccessful.not()) && fetchPolicyType == FetchPolicyType.NETWORK_THEN_CACHE                            ->
          {
            debug("Call of ${request.method()} to ${request.url()} with cache policy ${fetchPolicyType.name} failed to find a network response. Trying call to cache.")

            secondRequest = buildCacheRequest(request, cachePolicy)
          }
          (firstTry == null || firstTry.code() == ONLY_CACHE_UNSATISFIABLE_ERROR_CODE) && fetchPolicyType == FetchPolicyType.ONLY_CACHE         ->
          {
            debug("Call of ${request.method()} to ${request.url()} with cache policy ${fetchPolicyType.name} failed to find a cached response. Failing.")

            return onStatusCodeNotOk(firstTry, CacheException("Call of ${request.method()} to ${request.url()} with cache policy ${fetchPolicyType.name} failed to find a cached response. Failing."))
          }
          (firstTry == null || firstTry.isSuccessful.not())                                                                                     ->
          {
            debug("Call of ${request.method()} to ${request.url()} with cache policy $fetchPolicyType failed to find a response. Failing.")

            return onStatusCodeNotOk(firstTry, firstException)
          }
          else                                                                                                                                  ->
          {
            debug("Call of ${firstTry.request().method()} to ${firstTry.request().url()} with cache policy $fetchPolicyType successful.")

            return firstTry
          }
        }

        if (shouldDoSecondCall)
        {
          chain.proceed(secondRequest).also { secondTry ->
            return when
            {
              fetchPolicyType == FetchPolicyType.NETWORK_THEN_CACHE && secondTry.code() == ONLY_CACHE_UNSATISFIABLE_ERROR_CODE ->
              {
                debug("Second call of ${request.method()} to ${request.url()} with cache policy ${fetchPolicyType.name} failed to find a cached response. Failing.")

                onStatusCodeNotOk(secondTry)
              }
              secondTry.isSuccessful.not()                                                                                     ->
              {
                debug("Second call of ${secondTry.request().method()} to ${secondTry.request().url()} with cache policy ${fetchPolicyType.name} failed to find a network response. Failing.")

                onStatusCodeNotOk(secondTry)
              }
              else                                                                                                             ->
              {
                debug("Second call of ${request.method()} to ${request.url()} with cache policy ${fetchPolicyType.name} was successful.")

                secondTry
              }
            }
          }
        }
        else
        {
          return onStatusCodeNotOk(firstTry, firstException)
        }
      }

      throw IllegalStateException("Cache Policy is malformed")
    }

    @Throws(CallException::class, CacheException::class, Exception::class)
    fun onStatusCodeNotOk(response: Response?, exception: Exception? = null): Response?
    {
      if (response != null && shouldReturnErrorResponse.not())
      {
        throw CallException(response.message(), statusCode = response.code())
      }
      else if (response == null && exception != null)
      {
        throw when (exception)
        {
          is CacheException -> CacheException(exception.message)
          is CallException  -> CallException(exception.message, exception, exception.statusCode)
          else              -> exception
        }
      }
      else
      {
        return response
      }
    }

    private fun debug(message: String)
    {
      if (log.isDebugEnabled)
      {
        log.debug(message)
      }
    }

  }

  private inner class NetworkCacheInterceptor : Interceptor
  {

    override fun intercept(chain: Interceptor.Chain): Response?
    {
      val cachePolicy = chain.request().tag() as? RetrofitWebServiceCaller<API>.CachePolicy
      val fetchPolicyType = cachePolicy?.fetchPolicyType

      if (fetchPolicyType != null)
      {
        return rewriteResponse(chain.proceed(chain.request()), cachePolicy)
      }

      throw IllegalStateException("Cache Policy is malformed")
    }
  }

  protected open val log: Logger by lazy {
    LoggerFactory.getInstance(RetrofitWebServiceCaller::class.java)
  }

  protected open val service: API by lazy {
    val serviceBuilder = Retrofit
        .Builder()
        .baseUrl(baseUrl)
        .client(httpClient)

    converterFactories.forEach { converterFactory ->
      serviceBuilder.addConverterFactory(converterFactory)
    }

    return@lazy serviceBuilder.build().create(api)
  }

  protected val httpClient: OkHttpClient by lazy {
    computeHttpClient().build()
  }

  private var isHttpClientInitialized = false

  private var isConnected = true

  private var cacheDir: File? = null

  private var cachePathName: String? = null

  private var cacheSize: Long = RetrofitWebServiceCaller.CACHE_SIZE

  abstract fun <T> mapResponseToObject(responseBody: String?, clazz: Class<T>): T?

  abstract fun <T> mapResponseToObject(responseBody: String?, typeReference: TypeReference<T>): T?

  open fun hasConnectivity(): Boolean =
      isConnected

  open fun setConnectivity(isConnected: Boolean)
  {
    this.isConnected = isConnected
  }

  open fun computeHttpClient(): OkHttpClient.Builder
  {
    val okHttpClientBuilder = OkHttpClient.Builder()
        .connectTimeout(connectTimeout, TimeUnit.MILLISECONDS)
        .readTimeout(readTimeout, TimeUnit.MILLISECONDS)
        .writeTimeout(writeTimeout, TimeUnit.MILLISECONDS)

    setupAuthenticator()?.also { authenticator ->
      okHttpClientBuilder.authenticator(authenticator)
    }

    setupFirstAppInterceptors()?.forEach { interceptor ->
      okHttpClientBuilder.addInterceptor(interceptor)
    }

    setupAppInterceptors()?.forEach { interceptor ->
      okHttpClientBuilder.addInterceptor(interceptor)
    }

    setupFirstNetworkInterceptors()?.forEach { interceptor ->
      okHttpClientBuilder.addNetworkInterceptor(interceptor)
    }

    setupNetworkInterceptors()?.forEach { interceptor ->
      okHttpClientBuilder.addNetworkInterceptor(interceptor)
    }

    if (builtInCache != null)
    {
      okHttpClientBuilder.addNetworkInterceptor(NetworkCacheInterceptor())
      okHttpClientBuilder.addInterceptor(AppCacheInterceptor(builtInCache.shouldReturnErrorResponse))
    }

    cacheDir?.also { cacheDirectory ->
      cacheDirectory.setReadable(true)
      okHttpClientBuilder.cache(Cache(File(cacheDirectory, "${RetrofitWebServiceCaller.CACHE_BASE_PATH}$cachePathName"), cacheSize))
    }

    isHttpClientInitialized = true

    return okHttpClientBuilder
  }

  /**
   * Override this method to setup an [Authenticator].
   *
   * @return the [Authenticator] that the [httpClient] builder will use.
   */
  open fun setupAuthenticator(): Authenticator?
  {
    return null
  }

  /**
   * Override this method to setup an app [Interceptor] list (= always intercept call).
   *
   * @return the [Interceptor] list that the [httpClient] builder will use.
   *
   * Pay attention that the order you add them is important.
   */
  open fun setupAppInterceptors(): List<Interceptor>?
  {
    return null
  }

  /**
   * Override this method to setup an app [Interceptor] list (= always intercept call).
   *
   * @return the [Interceptor] list that the [httpClient] builder will use.
   *
   * Pay attention that the order you add them is important. These items are set first.
   */
  open fun setupFirstAppInterceptors(): List<Interceptor>?
  {
    return null
  }

  /**
   * Override this method to setup a network [Interceptor] list (= only intercept network call).
   *
   * @return the [Interceptor] list that the [httpClient] builder will use.
   *
   * Pay attention that the order you add them is important.
   */
  open fun setupNetworkInterceptors(): List<Interceptor>?
  {
    return null
  }

  /**
   * Override this method to setup a network [Interceptor] list (= only intercept network call).
   *
   * @return the [Interceptor] list that the [httpClient] builder will use.
   *
   * Pay attention that the order you add them is important. These items are set first.
   */
  open fun setupFirstNetworkInterceptors(): List<Interceptor>?
  {
    return null
  }

  /**
   * Override this method if you want to block the second call of policies : [NETWORK_THEN_CACHE] and [CACHE_THEN_NETWORK].
   *
   * @param[response] the [Response] of the first call.
   * @param[exception] the [Exception] of the first call.
   *
   * @return false if you want to block the 2nd call. True otherwise.
   */
  open fun shouldDoSecondCall(response: Response?, exception: Exception?): Boolean
  {
    return true
  }

  /**
   * Method to set the [File] and its max size for caching with [httpClient].
   *
   * @param[cacheDir] the [File] to use.
   * @param[cachePathName] the name for the cache to use in its [File]. Try to use different names for each service to have better behavior and control.
   * @param[cacheSize] the max size for the [Cache] (in [Byte]).
   */
  @JvmOverloads
  fun setupCache(cacheDir: File, cachePathName: String, cacheSize: Long = RetrofitWebServiceCaller.CACHE_SIZE)
  {
    if (builtInCache == null)
    {
      throw IllegalStateException("You must not setup your cache file as the builtInCache is set to null!")
    }
    if (isHttpClientInitialized)
    {
      throw IllegalStateException("You must setup your cache file before performing any call!")
    }

    this.cacheDir = cacheDir
    this.cachePathName = cachePathName
    this.cacheSize = cacheSize
  }

  /**
   * Method to get the [Cache] of the [httpClient].
   *
   * @return the [Cache] instance of the [httpClient].
   */
  fun getCache(): Cache?
  {
    return httpClient.cache()
  }

  /**
   * Method to get the entries (urls) in the [Cache].
   *
   * @return the [String] list of url's entries in [Cache].
   */
  fun getCacheUrls(): MutableList<String>
  {
    val cacheUrls = ArrayList<String>()
    httpClient.cache()?.urls()?.forEach { url ->
      cacheUrls.add(url)
    }

    return cacheUrls
  }

  /**
   * Method to remove an entry from [Cache].
   *
   * @param[urlOfEntry] response of the url we want to remove from cache.
   * @param[ignoreUrlParameters] ignore url parameters for removing.
   *
   * @return the number of entry removed.
   */
  @Throws(URISyntaxException::class)
  @JvmOverloads
  fun removeEntryFromCache(urlOfEntry: String, ignoreUrlParameters: Boolean = false): Int
  {
    var entryRemoved = 0
    val urlToRemove = if (ignoreUrlParameters)
    {
      val uri = URI(urlOfEntry)
      URI(uri.scheme, uri.authority, uri.path, null, uri.fragment).toString()
    }
    else
    {
      urlOfEntry
    }

    val iterator = httpClient.cache()?.urls()
    while (iterator?.hasNext() == true)
    {
      val value = if (ignoreUrlParameters)
      {
        val uri = URI(iterator.next())
        URI(uri.scheme, uri.authority, uri.path, null, uri.fragment).toString()
      }
      else
      {
        iterator.next()
      }

      if (value == urlToRemove)
      {
        iterator.remove()
        entryRemoved++
      }
    }

    return entryRemoved
  }

  // TODO: RemoveEntriesStratingWithFromCache(urlOfEntryStartingWith)
  // TODO: Dimension for caching ? (DATA, USER..). Maybe in a way like customKey but for all urls / keys.

  /**
   * Method to remove a custom entry from [Cache].
   *
   * @param[customKeyOfEntry] response of the custom key we want to remove from cache.
   *
   * @return true if the entry is removed, false otherwise.
   */
  fun removeCustomEntryFromCache(customKeyOfEntry: String): Boolean
  {
    val iterator = httpClient.cache()?.urls()
    while (iterator?.hasNext() == true)
    {
      val value = iterator.next()
      if (value == "${RetrofitWebServiceCaller.CUSTOM_CACHE_URL_PREFIX}$customKeyOfEntry")
      {
        iterator.remove()

        return true
      }
    }

    return false
  }

  @WorkerThread
  @JvmOverloads
  @Throws(IOException::class, CallException::class, CacheException::class, Exception::class)
  protected fun <T> executeResponse(call: Call<T>?, cachePolicy: CachePolicy = CachePolicy()): Response?
  {
    call?.request()?.let { request ->
      debug("Starting execution of call ${request.method()} to ${request.url()} with cache policy ${cachePolicy.fetchPolicyType.name}")

      val newRequest = request.newBuilder().tag(if (builtInCache != null) cachePolicy else null).build()
      val response: Response? = httpClient.newCall(newRequest).execute()

      response?.peekBody(Long.MAX_VALUE)?.close()

      return response
    } ?: return null
  }

  @WorkerThread
  @JvmOverloads
  @Throws(IOException::class, JacksonExceptions.JacksonParsingException::class, CallException::class, CacheException::class, Exception::class)
  protected fun <T> execute(clazz: Class<T>, call: Call<T>?, cachePolicy: CachePolicy = CachePolicy()): T?
  {
    call?.request()?.let { request ->
      debug("Starting execution of call ${request.method()} to ${request.url()} with cache policy ${cachePolicy.fetchPolicyType.name}")

      val newRequest = request.newBuilder().tag(if (builtInCache != null) cachePolicy else null).build()
      val response: Response? = httpClient.newCall(newRequest).execute()
      val responseBody = response?.peekBody(Long.MAX_VALUE)?.string()

      return mapResponseToObject(responseBody, clazz)
    } ?: return null
  }

  @WorkerThread
  @JvmOverloads
  @Throws(IOException::class, JacksonExceptions.JacksonParsingException::class, CallException::class, CacheException::class, Exception::class)
  protected fun <SuccessClass, ErrorClass> executeWithErrorResponse(clazz: Class<SuccessClass>, call: Call<SuccessClass>?, errorClazz: Class<ErrorClass>, cachePolicy: CachePolicy = CachePolicy()): ResponseWithError<SuccessClass, ErrorClass>?
  {
    call?.request()?.let { request ->
      debug("Starting execution of call ${request.method()} to ${request.url()} with cache policy ${cachePolicy.fetchPolicyType.name}")

      val newRequest = request.newBuilder().tag(if (builtInCache != null) cachePolicy else null).build()
      val response: Response? = httpClient.newCall(newRequest).execute()
      val success = response?.isSuccessful
      val responseBody = response?.peekBody(Long.MAX_VALUE)?.string()

      return if (success == true)
      {
        ResponseWithError(successResponse = mapResponseToObject(responseBody, clazz))
      }
      else
      {
        ResponseWithError(errorResponse = mapResponseToObject(responseBody, errorClazz))
      }
    } ?: return null
  }

  @WorkerThread
  @JvmOverloads
  @Throws(IOException::class, JacksonExceptions.JacksonParsingException::class, CallException::class, CacheException::class, Exception::class)
  protected fun <T> execute(typeReference: TypeReference<T>, call: Call<T>?, cachePolicy: CachePolicy = CachePolicy()): T?
  {
    call?.request()?.let { request ->
      debug("Starting execution of call ${request.method()} to ${request.url()} with cache policy ${cachePolicy.fetchPolicyType.name}")

      val newRequest = request.newBuilder().tag(if (builtInCache != null) cachePolicy else null).build()
      val response: Response? = httpClient.newCall(newRequest).execute()
      val responseBody = response?.peekBody(Long.MAX_VALUE)?.string()

      return mapResponseToObject(responseBody, typeReference)
    } ?: return null
  }

  @WorkerThread
  @JvmOverloads
  @Throws(IOException::class, JacksonExceptions.JacksonParsingException::class, CallException::class, CacheException::class, Exception::class)
  protected fun <SuccessClass, ErrorClass> executeWithErrorResponse(typeReference: TypeReference<SuccessClass>, call: Call<SuccessClass>?, errorClazz: Class<ErrorClass>, cachePolicy: CachePolicy = CachePolicy()): ResponseWithError<SuccessClass, ErrorClass>?
  {
    call?.request()?.let { request ->
      debug("Starting execution of call ${request.method()} to ${request.url()} with cache policy ${cachePolicy.fetchPolicyType.name}")

      val newRequest = request.newBuilder().tag(if (builtInCache != null) cachePolicy else null).build()
      val response: Response? = httpClient.newCall(newRequest).execute()
      val success = response?.isSuccessful
      val responseBody = response?.peekBody(Long.MAX_VALUE)?.string()

      return if (success == true)
      {
        ResponseWithError(successResponse = mapResponseToObject(responseBody, typeReference))
      }
      else
      {
        ResponseWithError(errorResponse = mapResponseToObject(responseBody, errorClazz))
      }
    } ?: return null
  }

  @WorkerThread
  @JvmOverloads
  @Throws(IOException::class, CallException::class, CacheException::class, Exception::class)
  protected fun <T> execute(call: Call<T>?, cachePolicy: CachePolicy = CachePolicy()): String?
  {
    call?.request()?.let { request ->
      debug("Starting execution of call ${request.method()} to ${request.url()} with cache policy ${cachePolicy.fetchPolicyType.name}")

      val newRequest = request.newBuilder().tag(if (builtInCache != null) cachePolicy else null).build()
      val response: Response? = httpClient.newCall(newRequest).execute()

      return response?.peekBody(Long.MAX_VALUE)?.string()
    } ?: return null
  }

  protected fun debug(message: String)
  {
    if (log.isDebugEnabled)
    {
      log.debug(message)
    }
  }

  protected fun warn(message: String)
  {
    if (log.isWarnEnabled)
    {
      log.warn(message)
    }
  }

  private fun buildRequest(request: Request, cachePolicy: CachePolicy): Request
  {
    val newRequest = when (cachePolicy.fetchPolicyType)
    {
      FetchPolicyType.ONLY_CACHE,
      FetchPolicyType.CACHE_THEN_NETWORK ->
      {
        buildCacheRequest(request, cachePolicy)
      }
      FetchPolicyType.ONLY_NETWORK,
      FetchPolicyType.NETWORK_THEN_CACHE ->
      {
        buildNetworkRequest(request)
      }
      FetchPolicyType.SERVER             -> request
    }

    return newRequest.newBuilder().tag(cachePolicy).build()
  }

  private fun buildNetworkRequest(request: Request, cachePolicy: CachePolicy? = null, originalRequestUrl: HttpUrl? = null): Request
  {
    val cacheControl = CacheControl.Builder().noCache()

    val requestBuilder = request.newBuilder()
        .removeHeader(RetrofitWebServiceCaller.PRAGMA_HEADER)
        .header(RetrofitWebServiceCaller.CACHE_CONTROL_HEADER, cacheControl.build().toString())

    if (cachePolicy?.customKey != null && originalRequestUrl != null)
    {
      requestBuilder.url(originalRequestUrl)
    }

    return requestBuilder.build()
  }

  private fun buildCacheRequest(request: Request, cachePolicy: CachePolicy): Request
  {
    val cacheControl = CacheControl.Builder().onlyIfCached()

    if (cachePolicy.allowedTimeExpiredCacheInSeconds != null && cachePolicy.allowedTimeExpiredCacheInSeconds > 0)
    {
      cacheControl.maxStale(cachePolicy.allowedTimeExpiredCacheInSeconds, TimeUnit.SECONDS)
    }

    val requestBuilder = request.newBuilder()
        .removeHeader(RetrofitWebServiceCaller.PRAGMA_HEADER)
        .header(RetrofitWebServiceCaller.CACHE_CONTROL_HEADER, cacheControl.build().toString())

    if (cachePolicy.customKey != null)
    {
      requestBuilder.url("${RetrofitWebServiceCaller.CUSTOM_CACHE_URL_PREFIX}${cachePolicy.customKey}")
    }

    return requestBuilder.build()
  }

  private fun rewriteResponse(response: Response, cachePolicy: CachePolicy): Response
  {
    when (cachePolicy.fetchPolicyType)
    {
      FetchPolicyType.ONLY_NETWORK,
      FetchPolicyType.NETWORK_THEN_CACHE,
      FetchPolicyType.ONLY_CACHE,
      FetchPolicyType.CACHE_THEN_NETWORK ->
      {
        val cacheControl = if (cachePolicy.cacheRetentionPolicyInSeconds == null || cachePolicy.cacheRetentionPolicyInSeconds < 0)
        {
          CacheControl.Builder()
              .noStore()
              .build()
              .toString()
        }
        else
        {
          CacheControl.Builder()
              .maxAge(cachePolicy.cacheRetentionPolicyInSeconds, TimeUnit.SECONDS)
              .build()
              .toString()
        }

        val responseBuilder = response.newBuilder()
            .removeHeader(RetrofitWebServiceCaller.PRAGMA_HEADER)
            .header(RetrofitWebServiceCaller.CACHE_CONTROL_HEADER, cacheControl)

        if (cachePolicy.useClientDateForCache)
        {
          response.header(RetrofitWebServiceCaller.DATE_HEADER)?.also { serverDate ->
            responseBuilder.header(RetrofitWebServiceCaller.SMART_SERVER_DATE_HEADER, serverDate)
          }
          responseBuilder.header(RetrofitWebServiceCaller.DATE_HEADER, Date().toString())
        }

        if (cachePolicy.customKey != null)
        {
          responseBuilder.header(RetrofitWebServiceCaller.SMART_ORIGINAL_URL_HEADER, response.request().url().toString())

          val customRequest = response.request().newBuilder().url("${RetrofitWebServiceCaller.CUSTOM_CACHE_URL_PREFIX}${cachePolicy.customKey}").build()
          responseBuilder.request(customRequest)
        }

        return responseBuilder.build()
      }
      FetchPolicyType.SERVER             -> return response
    }
  }
}