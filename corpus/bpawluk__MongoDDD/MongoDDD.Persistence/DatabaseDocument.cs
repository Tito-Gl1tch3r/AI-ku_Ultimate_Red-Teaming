using MongoDB.Bson;
using MongoDB.Bson.Serialization.Attributes;
using System;

namespace MongoDDD.Persistence
{
    public class DatabaseDocument<TData, TExternalData>
    {
        [BsonId]
        [BsonRepresentation(BsonType.ObjectId)]
        public string Id { get; set; } = default!;

        public TData Data { get; set; } = default!;

        public TExternalData ExternalData { get; set; } = default!;

        public DateTime Created { get; set; }

        public DateTime? Modified { get; set; }

        public DateTime? Deleted { get; set; }

        public int Version { get; set; }

        public DatabaseDocument(string id, TData data, TExternalData additionalData)
        {
            Id = id;
            Data = data;
            ExternalData = additionalData;
            Created = DateTime.UtcNow;
            Version = 1;
        }
    }
}
