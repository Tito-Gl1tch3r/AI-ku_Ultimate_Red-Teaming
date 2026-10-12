package com.smartnsoft.retrofitsample

import android.os.Bundle
import android.support.v7.app.AppCompatActivity
import android.util.Log
import com.smartnsoft.retrofitsample.ws.MyWebServiceCaller
import com.smartnsoft.retrofitsample.ws.TimeWebServiceCaller
import com.smartnsoft.ws.exception.CallException
import kotlinx.android.synthetic.main.activity_main.*
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.GlobalScope
import kotlinx.coroutines.launch
import java.lang.Exception

class MainActivity
  : AppCompatActivity()
{
  companion object
  {
    const val TAG = "WEB SERVICE"
  }

  override fun onCreate(savedInstanceState: Bundle?)
  {
    super.onCreate(savedInstanceState)
    setContentView(R.layout.activity_main)

    rootView.setOnClickListener {
      GlobalScope.launch(Dispatchers.IO) {
        try
        {
          TimeWebServiceCaller.getTime()?.also {
            Log.w(TAG, "getTime: $it")
          }

          /*TimeWebServiceCaller.getTime()?.also {
            Log.w(TAG, "getTime: $it")
          }

          MyWebServiceCaller.getString()?.also {
            Log.d(TAG, "getString: $it")
          }

          MyWebServiceCaller.getIp()?.also {
            Log.d(TAG, "getIp: ${it.origin}")
          }

          MyWebServiceCaller.delete().also {
            Log.d(TAG, "deletion complete: $it")
          }

          MyWebServiceCaller.post("127.0.0.1")?.also {
            Log.d(TAG, "post: ${it.form.ip}")
          }

          MyWebServiceCaller.put("127.0.0.2")?.also {
            Log.d(TAG, "put: ${it.form.ip}")
          }

          MyWebServiceCaller.status(200)?.also {
            Log.d(TAG, "status : ${it.isSuccessful}")
          }

          TimeWebServiceCaller.getTime3()?.also {
            Log.w(TAG, "getTime3: $it")
          }

          TimeWebServiceCaller.getTime2()?.also {
            Log.w(TAG, "getTime2: $it")
            TimeWebServiceCaller.removeEntryFromCache("${TimeApi.url}time/now")
            Log.w(TAG, "getTime2: $it")
          }*/
        }
        catch (callException: CallException)
        {
          Log.d(TAG, "callException: ${callException.message}")
        }
        catch (exception: Exception)
        {
          Log.e(TAG, "Error on webservice", exception)
        }

        try
        {
          MyWebServiceCaller.status(400)?.also {
            Log.d(TAG, "status : ${it.isSuccessful}")
          }
        }
        catch (callException: CallException)
        {
          Log.d(TAG, "callException: ${callException.message}")
        }
        catch (exception: Exception)
        {
          Log.e(TAG, "Error on webservice", exception)
        }
      }
    }
  }
}
