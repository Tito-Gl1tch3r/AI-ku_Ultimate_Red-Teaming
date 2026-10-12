// The MIT License (MIT)
//
// Copyright (c) 2017 Smart&Soft
//
// Permission is hereby granted, free of charge, to any person obtaining a copy
// of this software and associated documentation files (the "Software"), to deal
// in the Software without restriction, including without limitation the rights
// to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
// copies of the Software, and to permit persons to whom the Software is
// furnished to do so, subject to the following conditions:
//
// The above copyright notice and this permission notice shall be included in all
// copies or substantial portions of the Software.
//
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
// IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
// FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
// AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
// LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
// OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
// SOFTWARE.

package com.smartnsoft.ws.okhttp;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.UnknownHostException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import android.support.annotation.CallSuper;
import android.support.annotation.NonNull;
import android.text.TextUtils;

import com.smartnsoft.droid4me.log.Logger;
import com.smartnsoft.droid4me.log.LoggerFactory;
import com.smartnsoft.droid4me.ws.WebServiceCaller;

import okhttp3.FormBody;
import okhttp3.Headers;
import okhttp3.MediaType;
import okhttp3.MultipartBody;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.RequestBody;
import okhttp3.Response;
import okhttp3.ResponseBody;
import okhttp3.internal.Util;
import okio.Buffer;

/**
 * @author Ludovic Roland
 * @since 2016.04.28
 */
public abstract class OkHttpClientWebServiceCaller
    extends WebServiceCaller
{

  public enum RequestBodyType
  {
    FormBody, MultipartBody, JsonBody
  }

  protected final static Logger log = LoggerFactory.getInstance(OkHttpClientWebServiceCaller.class);

  private final int readTimeOutInMilliseconds;

  private final int connectTimeOutInMilliseconds;

  private final boolean acceptGzip;

  private OkHttpClient httpClient;

  protected OkHttpClientWebServiceCaller(int readTimeOutInMilliseconds, int connectTimeOutInMilliseconds,
      boolean acceptGzip)
  {
    this.readTimeOutInMilliseconds = readTimeOutInMilliseconds;
    this.connectTimeOutInMilliseconds = connectTimeOutInMilliseconds;
    this.acceptGzip = acceptGzip;
  }

  /**
   * Equivalent to calling {@link #runRequest(String, CallType, Map, String)} with {@code callType} parameter set to
   * {@code CallType.Get} and {@code body} and {@code parameters} parameters set to {@code null}.
   *
   * @see #runRequest(String, CallType, Map, String)
   */
  @Override
  public final HttpResponse runRequest(String uri)
      throws CallException
  {
    return runRequest(uri, CallType.Get, null, null);
  }

  /**
   * Equivalent to calling {@link #runRequest(String, CallType, Map, Map, String, List)} with {@code headers} and the {@code file} parameters set to {@code null}.
   *
   * @see #runRequest(String, CallType, Map, Map, String, List)
   */
  @Override
  public final HttpResponse runRequest(String uri, CallType callType, Map<String, String> parameters, String body)
      throws CallException
  {
    return runRequest(uri, callType, null, parameters, body, null);
  }

  /**
   * Performs an HTTP request corresponding to the provided parameters.
   *
   * @param uri        the URI being requested
   * @param callType   the HTTP method
   * @param headers    the headers of the HTTP request
   * @param parameters if the HTTP method is set to {@link CallType#Post} or {@link CallType#Put}, this is the form data of the
   *                   request
   * @param body       if the HTTP method is set to {@link CallType#Post} or {@link CallType#Put}, this is the string body of the
   *                   request
   * @param files      if the HTTP method is set to {@link CallType#Post} or {@link CallType#Put}, this is the file data of the
   *                   request
   * @return the input stream of the HTTP method call; cannot be {@code null}
   * @throws CallException if the status code of the HTTP response does not belong to the [{@link HttpURLConnection#HTTP_OK}, {@link HttpURLConnection#HTTP_MULT_CHOICE}] range.
   *                       Also if a connection issue occurred: the exception will {@link Throwable#getCause() embed} the cause of the exception. If the
   *                       {@link #isConnected()} method returns {@code false}, no request will be attempted and a {@link CallException}
   *                       exception will be thrown (embedding a {@link UnknownHostException} exception).
   * @see #runRequest(String)
   * @see #runRequest(String, CallType, Map, String)
   */
  @Override
  public HttpResponse runRequest(String uri, CallType callType, Map<String, String> headers,
      Map<String, String> parameters, String body, List<MultipartFile> files)
      throws CallException
  {
    Response response = null;

    try
    {
      response = performHttpRequest(uri, callType, headers, parameters, body, files);

      final Map<String, List<String>> headerFields = new HashMap<>();
      final Headers responseHeaders = response.headers();
      for (int index = 0, size = responseHeaders.size(); index < size; index++)
      {
        final String headerName = responseHeaders.name(index);
        final String headerValue = responseHeaders.value(index);

        if (headerFields.containsKey(headerName) == false)
        {
          headerFields.put(headerName, new ArrayList<String>());
        }

        headerFields.get(headerName).add(headerValue);
      }

      final int statusCode = response.code();
      final InputStream inputStream = getContent(uri, callType, response.body());

      return new HttpResponse(headerFields, statusCode, inputStream, inputStream);
    }
    catch (CallException exception)
    {
      throw exception;
    }
    catch (Exception exception)
    {
      throw new CallException(exception);
    }
    finally
    {
      if (response != null)
      {
        response.close();
      }
    }
  }

  /**
   * Forces the internal {@link OkHttpClient} to be renewed the next time the {@link #getHttpClient()} method will be invoked, i.e. the next time an
   * HTTP method will be executed a new {@link OkHttpClient} instance will be created. This will not affect any pending HTTP method execution.
   * <p/>
   * <p>
   * It is up to the caller to previously {@code client.dispatcher().executorService().shutdown()}, {@code client.connectionPool().evictAll()} or {@code client.cache().close()} the client if necessary.
   * </p>
   *
   * @see #getHttpClient()
   */
  public synchronized final void resetHttpClient()
  {
    if (log.isInfoEnabled())
    {
      log.info("Resetting the HTTP client");
    }

    httpClient = null;
  }

  public RequestBodyType getBodyType(String uri, CallType callType, Map<String, String> headers,
      Map<String, String> parameters, String body, List<MultipartFile> files)
  {
    return RequestBodyType.MultipartBody;
  }

  /**
   * Is responsible for returning an HTTP client instance, used for actually running the HTTP requests. The method implementation relies on the
   * {@link #computeHttpClient()} method, if no {@link OkHttpClient} is currently created.
   *
   * @return a valid HTTP client
   * @throws CallException is the invocation of the {@link #computeHttpClient()} threw an exception
   * @see #computeHttpClient()
   * @see #resetHttpClient()
   */
  protected synchronized final OkHttpClient getHttpClient()
      throws CallException
  {
    final ReuseOkHttpClient reuseHttpClientAnnotation = this.getClass().getAnnotation(ReuseOkHttpClient.class);

    if (reuseHttpClientAnnotation != null)
    {
      if (httpClient == null)
      {
        try
        {
          httpClient = computeHttpClient().build();
        }
        catch (Exception exception)
        {
          throw new CallException("Cannot instantiate the 'HttpClient'", exception);
        }
      }
      return httpClient;
    }
    else
    {
      try
      {
        return computeHttpClient().build();
      }
      catch (Exception exception)
      {
        throw new CallException("Cannot instantiate the 'HttpClient'", exception);
      }
    }
  }

  /**
   * This method will be invoked by the {@link #getHttpClient()} method, when it needs to use a new {@link OkHttpClient}. The method should be
   * overridden, when the {@link OkHttpClient} to use should be customized; a typical case is when the connection time-outs, the HTTP {@code User-Agent}
   * parameters need to fine-tuned.
   * <p/>
   * <p>
   * In the case the class uses {@link ReuseOkHttpClient} annotation, this method will be invoked only once.
   * </p>
   *
   * @return an HTTP client that will be used for running HTTP requests
   */
  protected OkHttpClient.Builder computeHttpClient()
  {
    return new OkHttpClient.Builder();
  }

  /**
   * Invoked when the result of the HTTP request is not <code>20X</code>. The default implementation logs the problem and throws an exception.
   *
   * @param uri           the URI of the HTTP call
   * @param callType      the type of the HTTP method
   * @param request       the original request
   * @param headers       the original headers of the request. They can be edited in order to manage some scenarios with tokens
   * @param attemptsCount the number of attempts that have been run for this HTTP method. Starts at <code>1</code>
   * @return {@code true} if you want the request to be re-run if it has failed
   * @throws CallException if you want the call to be considered as not OK
   */
  protected boolean onStatusCodeNotOk(String uri, CallType callType, Request request, Map<String, String> headers,
      Response response, int attemptsCount)
      throws CallException
  {
    final String message = "The result code of the call to the web method '" + uri + "' is not OK (not 20X). Status: " + (TextUtils.isEmpty(response.message()) == false ? response.message() : "") + " (" + response.code() + ")";

    if (log.isErrorEnabled() == true)
    {
      log.error(message);
    }

    response.close();

    throw new CallException(message, response.code());
  }

  @CallSuper
  protected void onBeforeHttpRequestExecution(OkHttpClient httpClient, Request.Builder requestBuilder,
      CallType callType)
      throws CallException
  {
    if (acceptGzip == true)
    {
      requestBuilder.addHeader("Accept-Encoding", "gzip");
    }
  }

  /**
   * Invoked on every call, in order to extract the input stream from the response.
   * <p>
   * <p>
   * If the content type is gzipped, this is the ideal place for unzipping it.
   * </p>
   *
   * @param uri          the web call initial URI
   * @param callType     the kind of request
   * @param responseBody the {@link ResponseBody} object
   * @return the (decoded) input stream of the response or null if the {@link CallType} <code>Verb.Head</code>
   * @throws IOException if some exception occurred while extracting the content of the response
   */
  protected InputStream getContent(String uri, CallType callType, ResponseBody responseBody)
      throws IOException
  {
    if (callType.verb != Verb.Head)
    {
      final InputStream content = new ByteArrayInputStream(responseBody.bytes());

      if (WebServiceCaller.ARE_DEBUG_LOG_ENABLED == true && log.isDebugEnabled() == true)
      {
        final InputStream debugContent;
        final int length = (int) (responseBody.contentLength() <= WebServiceCaller.BODY_MAXIMUM_SIZE_LOGGED_IN_BYTES ? responseBody.contentLength() : WebServiceCaller.BODY_MAXIMUM_SIZE_LOGGED_IN_BYTES);

        if (content.markSupported() == true)
        {
          debugContent = content;
        }
        else
        {
          final int bufferMaxLength = (int) (length < 0 ? WebServiceCaller.BODY_MAXIMUM_SIZE_LOGGED_IN_BYTES : length);
          final ByteArrayOutputStream outputStream = new ByteArrayOutputStream();
          final byte[] buffer = new byte[8192];
          int bufferLength = 0;

          try
          {
            while ((bufferLength = content.read(buffer)) > 0 && bufferLength <= bufferMaxLength)
            {
              outputStream.write(buffer, 0, bufferLength);
            }
          }
          catch (IndexOutOfBoundsException exception)
          {
            if (log.isWarnEnabled())
            {
              log.warn("Could not copy the input stream corresponding to the HTTP response content in order to log it", exception);
            }

            return content;
          }

          try
          {
            content.close();
          }
          catch (IOException exception)
          {
            if (log.isWarnEnabled() == true)
            {
              log.warn("Could not close the input stream corresponding to the HTTP response content", exception);
            }
          }

          try
          {
            outputStream.close();
          }
          catch (IOException exception)
          {
            if (log.isWarnEnabled() == true)
            {
              log.warn("Could not close the input stream corresponding to the copy of the HTTP response content", exception);
            }
          }

          debugContent = new ByteArrayInputStream(outputStream.toByteArray());
        }

        try
        {
          debugContent.mark(length);
          final String bodyAsString = getString(debugContent);
          log.debug("The body of the HTTP response corresponding to the URI '" + uri + "' is : '" + bodyAsString + "'");
        }
        catch (IOException exception)
        {
          if (log.isWarnEnabled() == true)
          {
            log.warn("Cannot log the HTTP body of the response", exception);
          }
        }
        finally
        {
          debugContent.reset();
        }

        return debugContent;
      }

      return content;
    }

    return null;
  }

  protected Response performHttpRequest(String uri, CallType callType, Map<String, String> headers,
      Map<String, String> parameters, String body, List<MultipartFile> files)
      throws IOException, CallException
  {
    final Request.Builder requestBuilder = new Request.Builder();

    switch (callType.verb)
    {
      default:
      case Get:
        requestBuilder.get();
        break;
      case Head:
        requestBuilder.head();
        break;
      case Post:
        requestBuilder.post(computeRequestBody(uri, callType, headers, parameters, body, files));
        break;
      case Put:
        requestBuilder.put(computeRequestBody(uri, callType, headers, parameters, body, files));
        break;
      case Delete:
        requestBuilder.delete(computeRequestBody(uri, callType, headers, parameters, body, files));
        break;
    }
    return performHttpRequest(uri, callType, headers, parameters, body, files, requestBuilder, 0);
  }

  protected int getConnectTimeOut()
  {
    return connectTimeOutInMilliseconds;
  }

  protected int getReadTimeOut()
  {
    return readTimeOutInMilliseconds;
  }

  private RequestBody computeRequestBody(String uri, CallType callType, Map<String, String> headers,
      Map<String, String> parameters, String body, List<MultipartFile> files)
      throws IOException
  {
    if ((parameters == null || parameters.size() == 0) && TextUtils.isEmpty(body) == true && (files == null || files.size() == 0))
    {
      return Util.EMPTY_REQUEST;
    }

    final RequestBodyType bodyType = getBodyType(uri, callType, headers, parameters, body, files);

    if (bodyType == RequestBodyType.MultipartBody)
    {
      return computeMultipartBody(parameters, body, files);
    }

    if (bodyType == RequestBodyType.JsonBody)
    {
      return computeJsonBody(body);
    }

    return computeFormBody(parameters);
  }

  private RequestBody computeJsonBody(String body)
  {
    return RequestBody.create(MediaType.parse("application/json; charset=utf-8"), body);
  }

  private RequestBody computeFormBody(Map<String, String> parameters)
  {
    final FormBody.Builder builder = new FormBody.Builder();

    if (parameters != null && parameters.isEmpty() == false)
    {
      for (final Map.Entry<String, String> parameter : parameters.entrySet())
      {
        builder.add(parameter.getKey(), parameter.getValue());
      }
    }

    return builder.build();
  }

  @NonNull
  private RequestBody computeMultipartBody(Map<String, String> parameters, String body,
      List<MultipartFile> files)
      throws IOException
  {
    final MultipartBody.Builder builder = new MultipartBody.Builder();
    builder.setType(MultipartBody.FORM);

    if (files != null && files.isEmpty() == false)
    {
      for (final MultipartFile file : files)
      {
        builder.addFormDataPart(file.name, file.fileName, RequestBody.create(MediaType.parse(file.contentType), inputStreamToByteArray(file.inputStream)));
      }
    }

    if (parameters != null && parameters.isEmpty() == false)
    {
      for (final Map.Entry<String, String> parameter : parameters.entrySet())
      {
        builder.addFormDataPart(parameter.getKey(), parameter.getValue());
      }
    }

    if (TextUtils.isEmpty(body) == false)
    {
      builder.addPart(RequestBody.create(null, body));
    }

    return builder.build();
  }

  private byte[] inputStreamToByteArray(InputStream is)
      throws IOException
  {
    final ByteArrayOutputStream baos = new ByteArrayOutputStream();
    int reads = is.read();

    while (reads != -1)
    {
      baos.write(reads);
      reads = is.read();
    }

    return baos.toByteArray();
  }

  /**
   * Is responsible for returning an HTTP client instance, used for actually running the HTTP requests.
   * <p>
   * <p>
   * The current implementation returns a {@link Response} instance.
   * </p>
   *
   * @return a valid HTTP client
   * @throws CallException is the uri is {@code null} or the connectivity has been lost
   */
  private Response performHttpRequest(String uri, CallType callType, Map<String, String> headers,
      Map<String, String> paramaters, String body, List<MultipartFile> files, Request.Builder requestBuilder,
      int attemptsCount)
      throws IOException, CallException
  {
    if (uri == null)
    {
      throw new CallException("Cannot perform an HTTP request with a null URI!");
    }

    if (isConnected == false)
    {
      throw new CallException(new UnknownHostException("No connectivity"));
    }

    if (attemptsCount == 0)
    {
      requestBuilder.url(uri);
    }

    requestBuilder.headers(new Headers.Builder().build());
    if (headers != null && headers.isEmpty() == false)
    {
      for (final Map.Entry<String, String> header : headers.entrySet())
      {
        requestBuilder.addHeader(header.getKey(), header.getValue());
      }
    }

    final OkHttpClient httpClient = getHttpClient();

    onBeforeHttpRequestExecution(httpClient, requestBuilder, callType);

    final Request request = requestBuilder.build();

    if (log.isDebugEnabled() == true)
    {
      final StringBuilder sb = new StringBuilder();
      final StringBuilder curlSb = new StringBuilder();
      boolean logCurlCommand = false;

      if (WebServiceCaller.ARE_DEBUG_LOG_ENABLED == true)
      {
        try
        {
          curlSb.append("\n>> ").append("curl --request ").append(callType.toString().toUpperCase()).append(" \"").append(uri).append("\"");

          if (request.body() != null)
          {
            if (request.body().contentLength() <= WebServiceCaller.BODY_MAXIMUM_SIZE_LOGGED_IN_BYTES)
            {
              logCurlCommand = true;

              try
              {
                final String bodyAsString = bodyAsString(request);
                sb.append(" with body '").append(bodyAsString).append("'");
                curlSb.append(" --data \"").append(bodyAsString).append("\"");
              }
              catch (IOException exception)
              {
                if (log.isWarnEnabled())
                {
                  log.warn("Cannot log the HTTP body", exception);
                }
              }
            }

            final Headers requestHeaders = request.headers();
            for (int index = 0, size = requestHeaders.size(); index < size; index++)
            {
              curlSb.append(" --header \"").append(requestHeaders.name(index)).append(": ").append(requestHeaders.value(index).replace("\"", "\\\"")).append("\n");
            }
          }
          else
          {
            logCurlCommand = true;
          }
        }
        catch (Exception exception)
        {
          if (log.isWarnEnabled())
          {
            log.warn("Cannot log the HTTP request", exception);
          }
        }
      }

      log.debug("Running the HTTP " + callType + " request '" + uri + "'" + sb.toString() + (logCurlCommand == true ? curlSb.toString() : ""));
    }

    final long start = System.currentTimeMillis();
    final Response response = httpClient.newCall(request).execute();
    final int statusCode = response.code();
    final StringBuilder responseHeadersSb = new StringBuilder();

    if (WebServiceCaller.ARE_DEBUG_LOG_ENABLED == true && log.isDebugEnabled() == true)
    {
      final Headers responseHeaders = response.headers();
      for (int index = 0, size = responseHeaders.size(); index < size; index++)
      {
        if (responseHeadersSb.length() > 0)
        {
          responseHeadersSb.append(",");
        }

        responseHeadersSb.append("(\"").append(responseHeaders.name(index)).append(": ").append(responseHeaders.value(index).replace("\"", "\\\"")).append("\")");
      }
    }

    if (log.isDebugEnabled() == true)
    {
      log.debug("The call to the HTTP " + callType + " request '" + uri + "' took " + (System.currentTimeMillis() - start) + " ms and returned the status code " + statusCode + (responseHeadersSb.length() <= 0 ? "" : " with the HTTP headers:" + responseHeadersSb.toString()));
    }

    if (!(statusCode >= HttpURLConnection.HTTP_OK && statusCode <= HttpURLConnection.HTTP_MULT_CHOICE))
    {
      if (onStatusCodeNotOk(uri, callType, request, headers, response, attemptsCount + 1) == true)
      {
        return performHttpRequest(uri, callType, headers, paramaters, body, files, requestBuilder, attemptsCount + 1);
      }
    }

    return response;
  }

  private String bodyAsString(Request request)
      throws IOException
  {
    final Request copy = request.newBuilder().build();
    final Buffer buffer = new Buffer();
    copy.body().writeTo(buffer);

    return buffer.readUtf8();
  }

}