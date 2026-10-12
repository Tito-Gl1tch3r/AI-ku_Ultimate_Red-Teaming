package com.smartnsoft.sampleokhttp;

import android.app.Application;

import com.smartnsoft.droid4me.cache.DbPersistence;
import com.smartnsoft.droid4me.cache.Persistence;
import com.smartnsoft.droid4me.ws.WebServiceCaller;

/**
 * @author Ludovic Roland
 * @since 2018.03.30
 */
public final class MyApplication
    extends Application
{

  @Override
  public void onCreate()
  {
    super.onCreate();

    if (BuildConfig.DEBUG)
    {
      WebServiceCaller.ARE_DEBUG_LOG_ENABLED = true;
    }

    // We initialize the cache persistence
    final String cacheDirectoryPath = getExternalCacheDir() != null ? getExternalCacheDir().getAbsolutePath() : getCacheDir().getAbsolutePath();
    Persistence.CACHE_DIRECTORY_PATHS = new String[] { cacheDirectoryPath };
    DbPersistence.FILE_NAMES = new String[] { DbPersistence.DEFAULT_FILE_NAME };
    DbPersistence.TABLE_NAMES = new String[] { "data" };
    Persistence.INSTANCES_COUNT = 1;
    Persistence.IMPLEMENTATION_FQN = DbPersistence.class.getName();
  }

}
