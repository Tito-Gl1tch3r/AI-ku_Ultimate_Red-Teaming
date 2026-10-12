using System;

namespace MongoDDD.Core
{
    public abstract class AggregateRoot<TAggregateState>
    {
        private int _version = -1;

        protected TAggregateState _state = default!;

        public string Id { get; private set; } = default!;

        public AggregateRoot() { }

        public AggregateRoot(string id)
        {
            Id = id;
        }

        internal AggregateSnapshot<TAggregateState> CreateSnapshot()
        {
            if (string.IsNullOrWhiteSpace(Id))
            {
                throw new InvalidOperationException($"You cannot create a snapshot of {GetType().Name} with empty ID.");
            }

            if (_state is null)
            {
                throw new InvalidOperationException($"You cannot create a snapshot of {GetType().Name} with empty state.");
            }

            return new AggregateSnapshot<TAggregateState>(Id, _version, _state);
        }

        internal void Restore(AggregateSnapshot<TAggregateState> snapshot)
        {
            Id = snapshot.Id;
            _version = snapshot.Version;
            _state = snapshot.State;
        }
    }
}
