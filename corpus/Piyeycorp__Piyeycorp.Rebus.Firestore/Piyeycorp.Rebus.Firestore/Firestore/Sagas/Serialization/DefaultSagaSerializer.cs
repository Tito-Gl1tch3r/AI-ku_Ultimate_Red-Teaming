using System;
using Rebus.Sagas;
using Rebus.Serialization;

namespace Rebus.Firestore.Sagas.Serialization
{
    public class DefaultSagaSerializer : ObjectSerializer, ISagaSerializer
    {
        public string SerializeToString(ISagaData obj)
        {
            return base.SerializeToString(obj);
        }

        public ISagaData DeserializeFromString(Type type, string str)
        {
            var sagaData = DeserializeFromString(str) as ISagaData;
            return !type.IsInstanceOfType(sagaData) ? null : sagaData;
        }
    }
}
