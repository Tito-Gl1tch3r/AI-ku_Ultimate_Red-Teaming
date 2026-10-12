using System;
using System.Collections.Generic;
using Rebus.Sagas;

namespace Rebus.Firestore.Sagas.Extensions
{
    public static class SagaDataExtensions
    {
        public static Dictionary<string, object> ToMap(this ISagaData sagaData)
        {
            var result = new Dictionary<string, object>();
            foreach (var propertyInfo in sagaData.GetType().GetProperties())
            {
                var propertyType = propertyInfo.GetType();
                if (propertyType.IsIntrinsicType())
                {
                    result.Add(propertyInfo.Name, propertyInfo.GetValue(sagaData));
                }
                else
                {

                }
            }

            return result;
        }

        public static bool IsIntrinsicType(this Type type)
        {
            bool IsNullableSimpleType(Type t)
            {
                var underlyingType = Nullable.GetUnderlyingType(t);
                return underlyingType != null && t.IsIntrinsicType();
            }

            return type.IsPrimitive ||
                   type.IsEnum ||
                   type == typeof(string) ||
                   type == typeof(decimal) ||
                   type == typeof(DateTime) ||
                   type == typeof(DateTimeOffset) ||
                   type == typeof(TimeSpan) ||
                   type == typeof(Guid) ||
                   IsNullableSimpleType(type);
        }
    }
}