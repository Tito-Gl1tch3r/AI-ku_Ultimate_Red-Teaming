package test

import com.smartnsoft.retrofitsample.ws.InfoAPI
import com.smartnsoft.retrofitsample.ws.InfoContainer
import com.smartnsoft.ws.retrofit.api.AuthProvider
import com.smartnsoft.ws.retrofit.bo.AccessToken
import com.smartnsoft.ws.retrofit.bo.ErrorResponse
import com.smartnsoft.ws.retrofit.bo.ResponseWithError
import com.smartnsoft.ws.retrofit.caller.AuthJacksonRetrofitWebServiceCaller
import okhttp3.*
import okhttp3.mockwebserver.Dispatcher
import org.junit.Test
import java.io.File
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.RecordedRequest
import okhttp3.mockwebserver.MockWebServer
import org.json.JSONObject
import java.lang.Exception


/**
 * @author David Fournier
 * @since 2019.06.20
 */
class Authenticator
{

  companion object
  {

    enum class ServerBehavior
    {
      NORMAL,
      TOKEN_ERROR,
      TOKEN_AND_REFRESH_ERROR,
      WRONG_XAPIKEY,
      EMPTY_XAPIKEY,
      SAME_REFRESH
    }

    private class AuthSimpleWebServiceCaller(val authProvider: AuthProvider, builtInCache: BuiltInCache? = BuiltInCache(shouldReturnErrorResponse = true), baseUrl: String) : AuthJacksonRetrofitWebServiceCaller<InfoAPI>(api = InfoAPI::class.java, baseUrl = baseUrl, builtInCache = builtInCache, authProvider = authProvider)
    {

      init
      {
        setupCache(File("./"), "auth")
      }

      fun info(): Response?
      {
        return executeResponse(service.getInfo(), CachePolicy(FetchPolicyType.NETWORK_THEN_CACHE, 120))
      }

      fun infoOnlyCache(): Response?
      {
        return executeResponse(service.getInfo(), CachePolicy(FetchPolicyType.ONLY_CACHE))
      }

      fun infoWithError(): ResponseWithError<InfoContainer, ErrorResponse>?
      {
        return executeWithErrorResponse(InfoContainer::class.java, service.getInfo(), ErrorResponse::class.java, CachePolicy(FetchPolicyType.NETWORK_THEN_CACHE, 120))
      }

      fun login(username: String, password: String): Boolean
      {
        return loginUser(username, password)?.successResponse != null
      }


    }

    var mockServerBaseUrl: String = ""

    private lateinit var serviceCaller: AuthSimpleWebServiceCaller

    @JvmStatic
    fun initializeServer(behavior: ServerBehavior)
    {
      val server = MockWebServer()
      server.start()
      mockServerBaseUrl = server.url("/").toString()

      val dispatcher = object : Dispatcher()
      {
        @Throws(InterruptedException::class)
        override fun dispatch(request: RecordedRequest): MockResponse
        {
          val xApiKey = request.headers["XApiKey"]
          val xApiKeyServer = if (behavior == Companion.ServerBehavior.WRONG_XAPIKEY) "yosoleil" else InfoAPI.apiToken

          if (xApiKey == null || xApiKey != xApiKeyServer)
          {
            return MockResponse().setResponseCode(403)
                .setBody("""{
                              "status_code": 403,
                              "message": "Forbidden"
                            }"""
                )
          }

          when (request.path)
          {
            "/login"   ->
            {
              val params = try
              {
                JSONObject(request.body.toString().removePrefix("[text=").removeSuffix("]"))
              }
              catch (exception: Exception)
              {
                null
              }

              if (behavior == Companion.ServerBehavior.SAME_REFRESH)
              {
                if (params?.get("username") == "user" && params["password"] == "pwd")
                {
                  return MockResponse().setResponseCode(200)
                      .setBody("""{
                                  "access_token": "abc",
                                  "refresh_token": "123",
                                  "expires_in": 3000,
                                  "token_type": "Bearer"
                                }"""
                      )
                }
                else
                {
                  return MockResponse().setResponseCode(403)
                      .setBody("""{
                                  "status_code": 403,
                                  "message": "Forbidden"
                                }"""
                      )
                }
              }
              else
              {
                if (params?.get("username") == "user" && params["password"] == "pwd")
                {
                  return MockResponse().setResponseCode(200)
                      .setBody("""{
                                  "access_token": "abc",
                                  "refresh_token": "123",
                                  "expires_in": 3000,
                                  "token_type": "Bearer"
                                }"""
                      )
                }
                else
                {
                  return MockResponse().setResponseCode(403)
                      .setBody("""{
                                  "status_code": 403,
                                  "message": "Forbidden"
                                }"""
                      )
                }
              }
            }
            "/refresh" ->
            {
              val params = try
              {
                request.body.toString().removePrefix("[text=").removeSuffix("]").split("&").map {
                  val keyValue = it.split("=")
                  keyValue[0] to keyValue[1]
                }.toMap()
              }
              catch (exception: Exception)
              {
                null
              }

              if (behavior == Companion.ServerBehavior.SAME_REFRESH)
              {
                if (params?.get("refresh_token") == "123")
                {
                  return MockResponse().setResponseCode(200)
                      .setBody("""{
                                  "access_token": "abc",
                                  "refresh_token": "123",
                                  "expires_in": 3000,
                                  "token_type": "Bearer"
                                }"""
                      )
                }
                else
                {
                  return MockResponse().setResponseCode(403)
                      .setBody("""{
                                  "status_code": 403,
                                  "message": "Forbidden"
                                }"""
                      )
                }
              }
              else
              {
                if (params?.get("refresh_token") == "123")
                {
                  return MockResponse().setResponseCode(200)
                      .setBody("""{
                                  "access_token": "def",
                                  "refresh_token": "456",
                                  "expires_in": 3000,
                                  "token_type": "Bearer"
                                }"""
                      )
                }
                else
                {
                  return MockResponse().setResponseCode(403)
                      .setBody("""{
                                  "status_code": 403,
                                  "message": "Forbidden"
                                }"""
                      )
                }
              }
            }
            "/info"    ->
            {
              if (request.getHeader("Authorization")?.isNotBlank() == true)
              {
                when (behavior)
                {
                  Companion.ServerBehavior.NORMAL                  ->
                  {
                    if (request.getHeader("Authorization") == "Bearer abc")
                      return MockResponse().setResponseCode(200).setBody(
                          """{
                            "info": {
                              "name": "Lucas Albuquerque",
                              "age": "21",
                              "gender": "male"
                            }
                          }"""
                      )
                    else
                      return MockResponse().setResponseCode(401)
                          .setBody("""{
                                      "status_code": 401,
                                      "message": "Unauthorized"
                                    }"""
                          )
                  }
                  Companion.ServerBehavior.TOKEN_ERROR             ->
                  {
                    if (request.getHeader("Authorization") == "Bearer def")
                      return MockResponse().setResponseCode(200).setBody(
                          """{
                            "info": {
                              "name": "Lucas Albuquerque",
                              "age": "21",
                              "gender": "male"
                            }
                          }"""
                      )
                    else
                      return MockResponse().setResponseCode(401)
                          .setBody("""{
                                      "status_code": 401,
                                      "message": "Unauthorized"
                                    }"""
                          )
                  }
                  Companion.ServerBehavior.TOKEN_AND_REFRESH_ERROR ->
                  {
                    if (request.getHeader("Authorization") == "Bearer ghi")
                      return MockResponse().setResponseCode(200).setBody(
                          """{
                            "info": {
                              "name": "Lucas Albuquerque",
                              "age": "21",
                              "gender": "male"
                            }
                          }"""
                      )
                    else
                      return MockResponse().setResponseCode(401)
                          .setBody("""{
                                      "status_code": 401,
                                      "message": "Unauthorized"
                                    }"""
                          )
                  }
                  Companion.ServerBehavior.SAME_REFRESH            ->
                  {
                    if (request.getHeader("Authorization") == "Bearer def")
                      return MockResponse().setResponseCode(200).setBody(
                          """{
                            "info": {
                              "name": "Lucas Albuquerque",
                              "age": "21",
                              "gender": "male"
                            }
                          }"""
                      )
                    else
                      return MockResponse().setResponseCode(401)
                          .setBody("""{
                                      "status_code": 401,
                                      "message": "Unauthorized"
                                    }"""
                          )
                  }
                  Companion.ServerBehavior.WRONG_XAPIKEY,
                  Companion.ServerBehavior.EMPTY_XAPIKEY           ->
                  {
                    return MockResponse().setResponseCode(403)
                        .setBody("""{
                                  "status_code": 403,
                                  "message": "Forbidden"
                                }"""
                        )
                  }
                }
              }
              else
              {
                return MockResponse().setResponseCode(403)
                    .setBody("""{
                                  "status_code": 403,
                                  "message": "Forbidden"
                                }"""
                    )
              }
            }
            else       ->
            {
              return MockResponse().setResponseCode(404)
                  .setBody("""{
                            "status_code": 404,
                            "message": "Not found"
                          }"""
                  )
            }
          }
        }
      }
      server.dispatcher = dispatcher

      val tokenProvider = object : AuthProvider
      {
        override fun getBaseRoute(): String
        {
          return mockServerBaseUrl
        }

        override fun getXApiKey(): String
        {
          return if (behavior == Companion.ServerBehavior.EMPTY_XAPIKEY) "" else InfoAPI.apiToken
        }

        var _accessToken: AccessToken? = null

        override fun getAccessToken(): AccessToken?
        {
          return _accessToken
        }

        override fun setAccessToken(accessToken: AccessToken?)
        {
          accessToken.apply {
            _accessToken = accessToken
          }
        }
      }

      serviceCaller = AuthSimpleWebServiceCaller(baseUrl = mockServerBaseUrl, authProvider = tokenProvider)
    }
  }

  @Test
  fun loginAndInfoOK()
  {
    initializeServer(Companion.ServerBehavior.NORMAL)

    serviceCaller.authProvider.setAccessToken(null)
    serviceCaller.login("user", "pwd")

    assert(serviceCaller.infoWithError()?.successResponse != null && serviceCaller.authProvider.getAccessToken() != null)
  }

  @Test
  fun refreshTokenOK()
  {
    initializeServer(Companion.ServerBehavior.TOKEN_ERROR)

    serviceCaller.authProvider.setAccessToken(null)
    serviceCaller.login("user", "pwd")

    assert(serviceCaller.infoWithError()?.successResponse != null && serviceCaller.authProvider.getAccessToken() != null)
  }

  @Test
  fun loginKO()
  {
    initializeServer(Companion.ServerBehavior.NORMAL)

    serviceCaller.authProvider.setAccessToken(null)
    serviceCaller.login("usr", "pwd")

    assert(serviceCaller.infoWithError()?.errorResponse?.statusCode == 403 && serviceCaller.authProvider.getAccessToken() == null)
  }

  @Test
  fun wrongXApiKey()
  {
    initializeServer(Companion.ServerBehavior.WRONG_XAPIKEY)

    serviceCaller.authProvider.setAccessToken(null)
    serviceCaller.login("user", "pwd")

    assert(serviceCaller.infoWithError()?.errorResponse?.statusCode == 403 && serviceCaller.authProvider.getAccessToken() == null)
  }


  @Test
  fun emptyXApiKey()
  {
    initializeServer(Companion.ServerBehavior.EMPTY_XAPIKEY)

    serviceCaller.authProvider.setAccessToken(null)
    serviceCaller.login("user", "pwd")

    assert(serviceCaller.infoWithError()?.errorResponse?.statusCode == 403 && serviceCaller.authProvider.getAccessToken() == null)
  }

  @Test
  fun tokenIsTheSame()
  {
    initializeServer(Companion.ServerBehavior.SAME_REFRESH)

    serviceCaller.authProvider.setAccessToken(null)
    serviceCaller.login("user", "pwd")

    assert(serviceCaller.infoWithError()?.errorResponse?.statusCode == 401 && serviceCaller.authProvider.getAccessToken() == null)
  }

  @Test
  fun tokenAndRefreshKO()
  {
    initializeServer(Companion.ServerBehavior.TOKEN_AND_REFRESH_ERROR)

    serviceCaller.authProvider.setAccessToken(null)
    serviceCaller.login("user", "pwd")

    assert(serviceCaller.infoWithError()?.errorResponse?.statusCode == 401 && serviceCaller.authProvider.getAccessToken() == null)
  }

  @Test
  fun noCacheReturnOn401()
  {
    initializeServer(Companion.ServerBehavior.NORMAL)

    serviceCaller.authProvider.setAccessToken(null)
    serviceCaller.login("user", "pwd")
    serviceCaller.info()
    serviceCaller.authProvider.setAccessToken(null)

    assert(serviceCaller.infoWithError()?.errorResponse?.statusCode == 403 && serviceCaller.authProvider.getAccessToken() == null)
    assert(serviceCaller.infoOnlyCache()?.code == 200)
  }
}