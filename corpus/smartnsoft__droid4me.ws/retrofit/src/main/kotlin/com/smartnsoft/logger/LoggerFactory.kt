package com.smartnsoft.logger

/**
 * @author Anthony Msihid
 * @since 2019.07.18
 */
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

import android.util.Log

/**
 * In order to have an entry point for the logging interface. Because, when we use the Android logger, there are problems during the unitary tests on
 * a desktop machine.
 *
 *
 *
 *
 * By default, the [AndroidLogger] implementation is used.
 *
 *
 *
 *
 *
 * In order to tune the [Logger] implementation that should be used at runtime, you may define the `SmartConfigurator` class, as explained
 * in [LoggerFactory.LoggerConfigurator].
 *
 *
 *
 *
 *
 * If no `SmartConfigurator` class is present in the classpath, when the the Java system property `droid4me.logging` is defined with
 * the value "false", the logging uses the standard error and output streams. This is useful when unit-testing the framework.
 *
 *
 * @author Édouard Mercier
 * @since 2008.01.15
 */
object LoggerFactory
{

  // Used for a synchronization purpose.
  private val synchronizationObject = Any()

  /**
   * Tunes the logging system verbosity. The `Logger#isXXXEnabled()` method return values will depend on this trigger level. Defaults to
   * `Log.WARN`.
   *
   *
   *
   *
   * It uses the Android built-in [android.util.Log] attributes for defining those log levels.
   *
   */
  var logLevel = android.util.Log.WARN

  /**
   * Remembers internally which [Logger] implementation to use.
   */
  private var loggerImplementation: LoggerImplementation? = null

  /**
   * Remembers the [LoggerFactory.LoggerConfigurator] that will be used to instantiate [Logger] instances.
   */
  private var loggerConfigurator: LoggerConfigurator? = null

  /**
   * The interface that should be implemented through the `SmartConfigurator` class (with no package name, because of Android restriction), in
   * order to indicate to the framework which [Logger] implementation should be used.
   */
  interface LoggerConfigurator
  {

    /**
     * The method will be invoked by the [LoggerFactory.getInstance] every time a logger needs to be created.
     *
     * @param category the logger category, which is a common concept to the [android.util.Log], `java java.util.logging.Logging`, `Log4J`
     * libraries
     * @return the [Logger] that should be used for logging on that category; is not allowed to be `null`
     * @see .getLogger
     */
    fun getLogger(category: String?): Logger

    /**
     * The method will be invoked by the [LoggerFactory.getInstance] every time a logger needs to be created.
     *
     * @param theClass the logger category, which is a common concept to the [android.util.Log], `java.util.logging.Logging`, `Log4J`
     * libraries
     * @return the [Logger] that should be used for logging on that category; is not allowed to be `null`
     * @see .getLogger
     */
    fun getLogger(theClass: Class<*>): Logger

  }

  /**
   * Enumerates various logger implementations.
   */
  private enum class LoggerImplementation
  {
    AndroidLogger, NativeLogger, Other
  }

  /**
   * @param category the category used for logging
   * @return a new instance of [Logger] implementation, holding the provided `category`
   * @see .getInstance
   */
  fun getInstance(category: String): Logger
  {
    return getInstance(category, null)
  }

  /**
   * @param theClass the class used for computing the logging category
   * @return a new instance of [Logger] implementation, holding the provided `category`
   */
  fun getInstance(theClass: Class<*>): Logger
  {
    return getInstance(null, theClass)
  }

  private fun getInstance(category: String?, theClass: Class<*>?): Logger
  {
    synchronized(synchronizationObject) {
      // We need to synchronize this part of the code
      if (loggerImplementation == null)
      {
        // The logger implementation has not been decided yet
        if (retrieveCustomLoggerInstance("SmartConfigurator") == false)
        {
          if (retrieveCustomLoggerInstance("com.smartnsoft.droid4me.SmartConfigurator") == false)
          {
            // This means that the project does not expose the class which enables to configure the logging system
            if (System.getProperty("droid4me.logging", "true") == "false" == true)
            {
              loggerImplementation = LoggerFactory.LoggerImplementation.NativeLogger
            }
            else
            {
              loggerImplementation = LoggerFactory.LoggerImplementation.AndroidLogger
            }
          }
        }
        // The logger implementation has not been decided yet
        val loggerConfiguratorClassFqn = "SmartConfigurator"
        try
        {
          val loggerConfiguratorClass = Class.forName(loggerConfiguratorClassFqn)
          loggerConfigurator = loggerConfiguratorClass.newInstance() as LoggerConfigurator
          loggerImplementation = LoggerFactory.LoggerImplementation.Other
        }
        catch (exception: Exception)
        {


        }

        if (logLevel >= android.util.Log.INFO)
        {
          Log.d("LoggerFactory", "Using the logger '" + loggerImplementation + "'")
        }
      }
    }

    when (loggerImplementation)
    {
      LoggerFactory.LoggerImplementation.Other         -> return if (theClass != null)
      {
        loggerConfigurator?.getLogger(theClass) ?: AndroidLogger(theClass)
      }
      else
      {
        loggerConfigurator?.getLogger(category) ?: AndroidLogger(category)
      }
      LoggerFactory.LoggerImplementation.AndroidLogger -> return theClass?.let { AndroidLogger(it) }
          ?: AndroidLogger(category)
      LoggerFactory.LoggerImplementation.NativeLogger  -> return theClass?.let { NativeLogger(it) }
          ?: NativeLogger(category)
      else                                                                   -> return theClass?.let { AndroidLogger(it) }
          ?: AndroidLogger(category)
    }
  }

  private fun retrieveCustomLoggerInstance(loggerConfiguratorClassFqn: String): Boolean
  {
    try
    {
      val loggerConfiguratorClass = Class.forName(loggerConfiguratorClassFqn)
      loggerConfigurator = loggerConfiguratorClass.newInstance() as LoggerConfigurator
      loggerImplementation = LoggerFactory.LoggerImplementation.Other
      return true
    }
    catch (rollbackException: Exception)
    {
      // This means that the project does not expose the class which enables to configure the logging system
      return false
    }

  }

}
