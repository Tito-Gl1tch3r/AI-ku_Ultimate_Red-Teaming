package test

import android.util.Log
import com.smartnsoft.retrofitsample.ws.RDLVApi
import com.smartnsoft.ws.exception.CallException
import com.smartnsoft.ws.retrofit.api.AuthProvider
import com.smartnsoft.ws.retrofit.bo.AccessToken
import com.smartnsoft.ws.retrofit.bo.ErrorResponse
import com.smartnsoft.ws.retrofit.bo.ResponseWithError
import com.smartnsoft.ws.retrofit.caller.AuthJacksonRetrofitWebServiceCaller
import com.smartnsoft.ws.retrofit.caller.RetrofitWebServiceCaller
import org.junit.FixMethodOrder
import org.junit.Test
import org.junit.runner.RunWith
import org.junit.runners.MethodSorters
import org.junit.runners.Parameterized
import java.io.File
import java.lang.Exception


/**
 * @author Anthony Msihid
 * @since 2019.08.23
 */
@FixMethodOrder(MethodSorters.NAME_ASCENDING)
@RunWith(Parameterized::class)
class RDLVAuthenticator(private val shouldReturnErrorResponse: Boolean)
{
  enum class RequestBehavior
  {
    NORMAL,
    WRONG_TOKEN,
    WRONG_TOKEN_AND_REFRESH,
    WRONG_XAPIKEY,
    EMPTY_XAPIKEY
  }

  companion object
  {
    @JvmStatic
    @Parameterized.Parameters(name = "shouldReturnErrorResponse = {0}")
    fun data(): List<Array<Boolean>>
    {
      return mutableListOf(arrayOf(true), arrayOf(false))
    }

    private var privateAccessToken: AccessToken? = null

    private class AuthSimpleWebServiceCaller(val authProvider: AuthProvider, builtInCache: BuiltInCache? = BuiltInCache(), baseUrl: String) : AuthJacksonRetrofitWebServiceCaller<RDLVApi>(api = RDLVApi::class.java, baseUrl = baseUrl, builtInCache = builtInCache, authProvider = authProvider)
    {

      init
      {
        setupCache(File("./"), "RDLV")
      }

      fun login(username: String, password: String): ResponseWithError<AccessToken, ErrorResponse>?
      {
        return loginUser(username, password)
      }

      fun getClients(): okhttp3.Response?
      {
        return executeResponse(service.getClients())
      }

      fun get404(): okhttp3.Response?
      {
        return executeResponse(service.get404(), CachePolicy(fetchPolicyType = FetchPolicyType.ONLY_NETWORK))
      }
    }

    private lateinit var serviceCaller: AuthSimpleWebServiceCaller

    @JvmStatic
    fun initializeService(requestBehavior: RequestBehavior, shouldReturnErrorResponse: Boolean )
    {
      val authProvider = object : AuthProvider
      {
        override fun getBaseRoute(): String
        {
          return RDLVApi.baseRoute
        }

        override fun getXApiKey(): String
        {
          return when (requestBehavior)
          {
            RequestBehavior.WRONG_XAPIKEY -> "wrong_xapikey"
            RequestBehavior.EMPTY_XAPIKEY -> ""
            else                          -> RDLVApi.xApiToken
          }
        }

        override fun getAccessToken(): AccessToken?
        {
          return privateAccessToken
        }

        override fun setAccessToken(accessToken: AccessToken?)
        {
          accessToken.apply {
            privateAccessToken = accessToken
          }
        }
      }

      serviceCaller = AuthSimpleWebServiceCaller(baseUrl = authProvider.getBaseRoute(), authProvider = authProvider, builtInCache = RetrofitWebServiceCaller.BuiltInCache(shouldReturnErrorResponse = shouldReturnErrorResponse))

      when (requestBehavior)
      {
        RequestBehavior.WRONG_TOKEN             ->
        {
          authProvider.setAccessToken(privateAccessToken?.let { realAccessToken ->
            AccessToken("wrong_token", realAccessToken.refreshToken, realAccessToken.tokenType, realAccessToken.expiresIn)
          })
        }
        RequestBehavior.WRONG_TOKEN_AND_REFRESH ->
        {
          authProvider.setAccessToken(privateAccessToken?.let { realAccessToken ->
            AccessToken("wrong_token", "wrong_refresh", realAccessToken.tokenType, realAccessToken.expiresIn)
          })
        }
        else                                    ->
        {
          // Normal
        }
      }
    }
  }

  @Test
  fun test_01_loginOk()
  {
    initializeService(RequestBehavior.NORMAL, shouldReturnErrorResponse)
    serviceCaller.authProvider.setAccessToken(null)
    serviceCaller.getCache()?.delete()

    val response = serviceCaller.login("j.dehais@equinoa.com", "api")
    val success = response?.successResponse != null

    assert(success && serviceCaller.authProvider.getAccessToken() != null)
  }

  @Test
  fun test_02_getInfoWithWrongApiKey()
  {
    initializeService(RequestBehavior.WRONG_XAPIKEY, shouldReturnErrorResponse)

    try
    {
      val response = serviceCaller.getClients()

      assert(response?.isSuccessful == false && response.code == 403 && serviceCaller.authProvider.getAccessToken() == null)
    }
    catch (exception: CallException)
    {
      Log.e("RDLVAuthenticator", "Unable to get clients with exception :", exception)

      assert(exception.statusCode == 403 && serviceCaller.authProvider.getAccessToken() == null)
    }
    catch (exception: Exception)
    {
      Log.e("RDLVAuthenticator", "Unable to get clients with exception :", exception)

      assert(false)
    }
  }

  @Test
  fun test_03_relogAfter403()
  {
    initializeService(RequestBehavior.NORMAL, shouldReturnErrorResponse)

    val response = serviceCaller.login("j.dehais@equinoa.com", "api")
    val success = response?.successResponse != null

    assert(success && serviceCaller.authProvider.getAccessToken() != null)
  }

  @Test
  fun test_04_404()
  {
    initializeService(RequestBehavior.NORMAL, shouldReturnErrorResponse)

    try
    {
      val response = serviceCaller.get404()

      assert(response?.isSuccessful == false && response.code == 404 && serviceCaller.authProvider.getAccessToken() != null)
    }
    catch (exception: CallException)
    {
      Log.e("RDLVAuthenticator", "Unable to get page with exception :", exception)

      assert(exception.statusCode == 404 && serviceCaller.authProvider.getAccessToken() != null)
    }
    catch (exception: Exception)
    {
      assert(false)
    }
  }

  @Test
  fun test_05_getInfoAfterLogin()
  {
    initializeService(RequestBehavior.NORMAL, shouldReturnErrorResponse)

    // Waiting a bit
    Thread.sleep(1_000)

    try
    {
      val response = serviceCaller.getClients()

      assert(response?.isSuccessful == true && response.code == 200 && serviceCaller.authProvider.getAccessToken() != null)
    }
    catch (exception: Exception)
    {
      Log.e("RDLVAuthenticator", "Unable to get clients with exception :", exception)

      assert(false)
    }
  }

  @Test
  fun test_06_getInfoWithEmptyApiKey()
  {
    initializeService(RequestBehavior.EMPTY_XAPIKEY, shouldReturnErrorResponse)

    try
    {
      val response = serviceCaller.getClients()

      assert(response?.isSuccessful == false && response.code == 403 && serviceCaller.authProvider.getAccessToken() == null)
    }
    catch (exception: CallException)
    {
      Log.e("RDLVAuthenticator", "Unable to get clients with exception :", exception)

      assert(exception.statusCode == 403 && serviceCaller.authProvider.getAccessToken() == null)
    }
    catch (exception: Exception)
    {
      Log.e("RDLVAuthenticator", "Unable to get clients with exception :", exception)

      assert(false)
    }
  }

  @Test
  fun test_07_relogAfter403()
  {
    initializeService(RequestBehavior.NORMAL, shouldReturnErrorResponse)

    val response = serviceCaller.login("j.dehais@equinoa.com", "api")
    val success = response?.successResponse != null

    assert(success && serviceCaller.authProvider.getAccessToken() != null)
  }

  @Test
  fun test_08_wrongAccessAndRefreshToken()
  {
    initializeService(RequestBehavior.WRONG_TOKEN_AND_REFRESH, shouldReturnErrorResponse)

    try
    {
      serviceCaller.getClients()

      assert(false)
    }
    catch (exception: Exception)
    {
      Log.e("RDLVAuthenticator", "Unable to get clients with exception :", exception)

      if (exception is CallException)
      {
        assert(exception.statusCode == 401 && serviceCaller.authProvider.getAccessToken() == null)
      }
      else
      {
        assert(false)
      }
    }
  }

  @Test
  fun test_09_relogAfter403()
  {
    initializeService(RequestBehavior.NORMAL, shouldReturnErrorResponse)

    val response = serviceCaller.login("j.dehais@equinoa.com", "api")
    val success = response?.successResponse != null

    assert(success && serviceCaller.authProvider.getAccessToken() != null)
  }

  @Test
  fun test_10_getInfoAfterRefresh()
  {
    initializeService(RequestBehavior.WRONG_TOKEN, shouldReturnErrorResponse)
    val oldToken = serviceCaller.authProvider.getAccessToken()

    try
    {
      serviceCaller.getClients()
      val newToken = serviceCaller.authProvider.getAccessToken()

      assert(newToken != null && oldToken != newToken)
    }
    catch (exception: Exception)
    {
      Log.e("RDLVAuthenticator", "Unable to get clients with exception :", exception)

      assert(false)
    }
  }

  @Test
  fun test_11_loginKo()
  {
    initializeService(RequestBehavior.NORMAL, shouldReturnErrorResponse)

    serviceCaller.authProvider.setAccessToken(null)
    val response = serviceCaller.login("wrong@equinoa.com", "wrong")
    val fail = response?.errorResponse != null

    assert(fail && serviceCaller.authProvider.getAccessToken() == null)
  }
}