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
 * The logger implementation for Android.
 *
 *
 *
 *
 * This implementation can only be used when the code integrating the library runs environment with the Android runtime.
 *
 *
 * @author Édouard Mercier
 * @see LoggerFactory
 *
 * @since 2007.12.23
 */
class AndroidLogger(private val category: String?) : Logger
{

  constructor(theClass: Class<*>) : this(theClass.simpleName)

  override val isDebugEnabled: Boolean
    get() = LoggerFactory.logLevel <= Log.DEBUG

  override val isInfoEnabled: Boolean
    get() = LoggerFactory.logLevel <= Log.INFO

  override val isWarnEnabled: Boolean
    get() = LoggerFactory.logLevel <= Log.WARN

  override val isErrorEnabled: Boolean
    get() = LoggerFactory.logLevel <= Log.ERROR

  override val isFatalEnabled: Boolean
    get() = LoggerFactory.logLevel <= Log.ERROR

  override fun debug(message: String)
  {
    Log.d(category, message)
  }

  override fun info(message: String)
  {
    Log.i(category, message)
  }

  override fun warn(message: String)
  {
    Log.w(category, message)
  }

  override fun warn(message: String, throwable: Throwable)
  {
    Log.w(category, message, throwable)
  }

  override fun warn(message: StringBuffer, throwable: Throwable)
  {
    warn(message.toString(), throwable)
  }

  override fun error(message: String)
  {
    Log.e(category, message)
  }

  override fun error(message: String, throwable: Throwable)
  {
    Log.e(category, message, throwable)
  }

  override fun error(message: StringBuffer, throwable: Throwable)
  {
    error(message.toString(), throwable)
  }

  override fun fatal(message: String)
  {
    error(message)
  }

  override fun fatal(message: String, throwable: Throwable)
  {
    error(message, throwable)
  }

}
