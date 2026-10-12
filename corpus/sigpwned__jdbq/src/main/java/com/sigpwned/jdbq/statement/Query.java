/*-
 * =================================LICENSE_START==================================
 * jdbq
 * ====================================SECTION=====================================
 * Copyright (C) 2022 Andy Boothe
 * ====================================SECTION=====================================
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 * 
 *      http://www.apache.org/licenses/LICENSE-2.0
 * 
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 * ==================================LICENSE_END===================================
 */
package com.sigpwned.jdbq.statement;

import java.io.InterruptedIOException;
import java.io.UncheckedIOException;
import com.google.cloud.bigquery.Job;
import com.sigpwned.jdbq.Handle;
import com.sigpwned.jdbq.result.FieldValueListsResultSet;
import com.sigpwned.jdbq.result.ResultSet;
import com.sigpwned.jdbq.result.ResultSetScanner;

public class Query extends SqlStatement<Query> implements ResultBearing {
  public Query(Handle handle, String sql) {
    super(handle, sql);
  }

  @Override
  public <R> R scanResultSet(ResultSetScanner<R> mapper) {
    return mapper.scanResultSet(this::execute, getContext());
  }

  private ResultSet execute() {
    Job job = internalExecute();
    try {
      return new FieldValueListsResultSet(job.getQueryResults().getValues());
    } catch (InterruptedException e) {
      // This should never happen, since internalExecute() waits for job completion.
      Thread.currentThread().interrupt();
      throw new UncheckedIOException(new InterruptedIOException());
    }
  }
}
