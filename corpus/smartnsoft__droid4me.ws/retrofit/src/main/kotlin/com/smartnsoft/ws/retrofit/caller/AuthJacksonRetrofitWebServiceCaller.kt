package com.smartnsoft.ws.retrofit.caller

import android.support.annotation.WorkerThread
import com.smartnsoft.ws.exception.CallException
import com.smartnsoft.ws.exception.JacksonExceptions
import com.smartnsoft.ws.retrofit.api.AuthProvider
import com.smartnsoft.ws.retrofit.api.AuthAPI
import com.smartnsoft.ws.retrofit.bo.AccessToken
import com.smartnsoft.ws.retrofit.bo.ErrorResponse
import com.smartnsoft.ws.retrofit.bo.LoginBody
import com.smartnsoft.ws.retrofit.bo.ResponseWithError
import okhttp3.*
import retrofit2.Call
import retrofit2.Retrofit
import java.io.IOException
import java.util.concurrent.TimeUnit

/**
 * @author Anthony Msihid
 * @since 2019.07.10
 */

/**
 * A class where you configure your service with an implemented authenticator
 *
 * @param[authProvider] [AuthProvider] object with the configuration for the authentication.
 * @param[api] interface where you implement your retrofit calls, see [Retrofit.create].
 * @param[baseUrl] base url of the API you want to reach.
 * @param[connectTimeout] the connect timeout is applied when connecting a TCP socket to the target host.
 * @param[readTimeout] the read timeout is applied to both the TCP socket and for individual read IO operations including on [Source] of the [Response].
 * @param[writeTimeout] the write timeout is applied for individual write IO operations.
 * @param[builtInCache] class to configure the cache and its default values. You must [setupCache]. If set to null, the built in cache is disabled and you don't need to [setupCache]. See [BuiltInCache].
 *
 */
abstract class AuthJacksonRetrofitWebServiceCaller<API>
@JvmOverloads
constructor(private val authProvider: AuthProvider,
            api: Class<API>,
            baseUrl: String,
            connectTimeout: Long = CONNECT_TIMEOUT,
            readTimeout: Long = READ_TIMEOUT,
            writeTimeout: Long = WRITE_TIMEOUT,
            builtInCache: BuiltInCache? = BuiltInCache())
  : JacksonRetrofitWebServiceCaller<API>(api, baseUrl, connectTimeout, readTimeout, writeTimeout, builtInCache)
{
  companion object
  {

    protected const val MAX_RETRIES = 1

  }

  private inner class TokenAuthenticatorInterceptor
    : Authenticator, Interceptor
  {
    override fun authenticate(route: Route?, response: Response): Request?
    {
      var callException: CallException? = null

      authProvider.apply {
        val accessToken = getAccessToken()

        // We don't want to try to refresh the token more than [MAX_RETRIES]
        if (responseCount(response) <= MAX_RETRIES && accessToken != null)
        {
          val accessTokenResponse = try
          {
            executeAuth(authService?.refreshToken("${getBaseRoute()}${getRefreshEndpoint()}", accessToken.refreshToken))
          }
          catch (exception: Exception)
          {
            callException = CallException("Call of refresh token failed with exception.", exception)
            null
          }

          if (accessTokenResponse?.successResponse != null)
          {
            debug("Token refreshed, new token is: ${accessTokenResponse.successResponse.accessToken}")

            setAccessToken(accessTokenResponse.successResponse)

            getAccessToken()?.apply {
              val newAuthorization = "${this.tokenType} ${this.accessToken}"

              // We don't want to try the call with the same token twice
              if (response.request().header("Authorization") != newAuthorization)
              {
                return response.request().newBuilder()
                    .header("Authorization", newAuthorization)
                    .build()
              }
            }
          }
          else if (accessTokenResponse?.errorResponse != null)
          {
            warn("Call of refresh token http status is '${accessTokenResponse.errorResponse.statusCode}' with message: '${accessTokenResponse.errorResponse.message}'")

            if (accessTokenResponse.errorResponse.statusCode == 401 || accessTokenResponse.errorResponse.statusCode == 403)
            {
              callException = CallException("Unable to refresh token.", Throwable(accessTokenResponse.errorResponse.message), accessTokenResponse.errorResponse.statusCode)
              setAccessToken(null)
            }
          }
        }

        callException?.apply {
          throw this
        }

        return null
      }
    }

    override fun intercept(chain: Interceptor.Chain): Response
    {
      val newRequest = chain.request().newBuilder()
      newRequest.header("Accept", "application/json")

      authProvider.apply {
        getXApiKey().takeIf { XApiKey -> XApiKey.isNotBlank() }?.apply {
          newRequest.header("XApiKey", this)
        }

        getAccessToken()?.takeIf { accessToken -> accessToken.tokenType.isNotBlank() && accessToken.accessToken.isNotBlank() }?.apply {
          newRequest.header("Authorization", "$tokenType $accessToken")
        }
      }

      return chain.proceed(newRequest.build())
    }

    private fun responseCount(response: Response): Int
    {
      var responseHolder: Response? = response
      var result = 1

      while (result <= MAX_RETRIES && responseHolder?.priorResponse() != null)
      {
        result++
        responseHolder = response.priorResponse()
      }

      return result
    }
  }

  private val httpAuthClient: OkHttpClient by lazy {
    OkHttpClient.Builder()
        .connectTimeout(connectTimeout, TimeUnit.MILLISECONDS)
        .readTimeout(readTimeout, TimeUnit.MILLISECONDS)
        .writeTimeout(writeTimeout, TimeUnit.MILLISECONDS)
        .addNetworkInterceptor(TokenAuthenticatorInterceptor())
        .build()
  }

  private val authService: AuthAPI? by lazy {
    authProvider.run {
      val serviceBuilder = Retrofit
          .Builder()
          .baseUrl(getBaseRoute())
          .client(httpAuthClient)

      converterFactories.forEach { converterFactory ->
        serviceBuilder.addConverterFactory(converterFactory)
      }

      return@run serviceBuilder.build().create(AuthAPI::class.java)
    }
  }


  /**
   * Method to login the user with the implemented authenticator.
   *
   * @param[username] the username of the user to connect.
   * @param[password] the password of the user to connect.
   *
   * @return the success of the connection.
   */
  @WorkerThread
  protected fun loginUser(username: String, password: String): ResponseWithError<AccessToken, ErrorResponse>?
  {
    val responseWithError: ResponseWithError<AccessToken, ErrorResponse>? = try
    {
      executeAuth(authService?.authToken("${authProvider.getBaseRoute()}${authProvider.getLoginEndpoint()}", LoginBody(username, password)))
    }
    catch (exception: Exception)
    {
      warn("Call of login failed with exception: ${exception.printStackTrace()}")

      null
    }

    authProvider.setAccessToken(responseWithError?.successResponse)

    return responseWithError
  }

  final override fun setupAuthenticator(): Authenticator?
  {
    return TokenAuthenticatorInterceptor()
  }

  final override fun setupFirstAppInterceptors(): List<Interceptor>?
  {
    return listOf(TokenAuthenticatorInterceptor())
  }

  @Throws(CallException::class, Exception::class)
  final override fun shouldDoSecondCall(response: Response?, exception: Exception?): Boolean
  {
    return when
    {
      response?.code() == 401 || response?.code() == 403                                         ->
      {
        // Invalidate token
        authProvider.setAccessToken(null)
        false
      }
      exception is CallException && (exception.statusCode == 401 || exception.statusCode == 403) ->
      {
        // Invalidate token
        authProvider.setAccessToken(null)
        throw exception
      }
      else                                                                                       ->
      {
        if (exception != null)
        {
          if (exception is CallException)
          {
            val message = "Server-side error with message '${exception.message}' and statusCode '${exception.statusCode}'"
            exception.cause?.also { throwable ->
              log.error(message, throwable)
            } ?: run {
              log.error(message)
            }
          }
          else
          {
            val message = "Error happened server-side"
            exception.cause?.also { throwable ->
              log.error(message, throwable)
            } ?: run {
              log.error(message)
            }
          }
        }

        super.shouldDoSecondCall(response, exception)
      }
    }
  }

  @WorkerThread
  @Throws(IOException::class, JacksonExceptions.JacksonParsingException::class, CallException::class, CacheException::class, Exception::class)
  private fun executeAuth(call: Call<AccessToken>?): ResponseWithError<AccessToken, ErrorResponse>?
  {
    call?.request()?.let { request ->
      debug("Starting execution of auth call ${request.method()} to ${request.url()}")

      val newRequest = request.newBuilder().build()
      val response: Response? = httpAuthClient.newCall(newRequest).execute()
      val success = response?.isSuccessful
      val responseBody = response?.peekBody(Long.MAX_VALUE)?.string()

      return if (success == true)
      {
        ResponseWithError(successResponse = mapResponseToObject(responseBody, AccessToken::class.java))
      }
      else
      {
        ResponseWithError(errorResponse = mapResponseToObject(responseBody, ErrorResponse::class.java))
      }
    } ?: return null
  }
}