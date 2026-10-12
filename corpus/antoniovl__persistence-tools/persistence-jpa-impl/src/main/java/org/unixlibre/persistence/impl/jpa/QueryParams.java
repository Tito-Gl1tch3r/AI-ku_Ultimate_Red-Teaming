package org.unixlibre.persistence.impl.jpa;

import javax.persistence.Query;
import javax.persistence.TypedQuery;
import java.util.Map;

/**
 * Created by antoniovl on 14/05/17.
 */
public class QueryParams {

    public static <T> TypedQuery<T> setParameters(TypedQuery<T> query,
                                                  Map<String, Object> params) {
        if (params == null || params.isEmpty()) {
            return query;
        }

        params.forEach(query::setParameter);

        return query;
    }

    public static Query setParameters(Query query,
                                      Map<String, Object> params) {
        if (params == null || params.isEmpty()) {
            return query;
        }

        params.forEach(query::setParameter);

        return query;
    }
}
