package com.smartnsoft.ws.exception

import java.io.InterruptedIOException
import java.net.SocketException
import java.net.SocketTimeoutException
import java.net.UnknownHostException
import javax.net.ssl.SSLException

/**
 * @author Anthony Msihid
 * @since 2019.07.18
 */

/**
 * The exception that will be thrown if any problem occurs during a web service call.
 */
@Suppress("unused")
open class CallException
constructor(message: String? = null, throwable: Throwable? = null, val statusCode: Int = 0)
  : Exception(message, throwable)
{

  constructor(throwable: Throwable? = null) : this(null, throwable, 0)

  constructor(message: String? = null, statusCode: Int = 0) : this(message, null, statusCode)

  constructor(throwable: Throwable? = null, statusCode: Int = 0) : this(null, throwable, statusCode)

  companion object
  {
    /**
     * Indicates whether the cause of the provided exception is due to a connectivity problem.
     *
     * @param throwable the exception to test
     * @return `true` if the [Throwable] was triggered because of a connectivity problem with Internet
     */
    fun isConnectivityProblem(throwable: Throwable): Boolean
    {
      var newThrowable = throwable
      var cause: Throwable? = newThrowable.cause

      // We investigate over the whole cause stack
      while (cause != null)
      {
        if (cause is UnknownHostException || cause is SocketException || cause is SocketTimeoutException || cause is InterruptedIOException || cause is SSLException)
        {
          return true
        }
        newThrowable = cause
        cause = newThrowable.cause
      }
      return false
    }
  }

  /**
   * @return `true` is the current exception is linked to a connectivity problem with Internet.
   * @see .isConnectivityProblem
   */
  val isConnectivityProblem: Boolean
    get() = isConnectivityProblem(this)

}
