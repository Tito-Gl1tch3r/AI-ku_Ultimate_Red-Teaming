using System;
using System.Collections.Generic;
using Simbad.Platform.Core.Events;
using Simbad.Platform.Core.Substance.IdGeneration;

namespace Simbad.Platform.Core.Substance
{
    public abstract class BusinessObject : IEventsHolder
    {
        private readonly List<IEvent> _events;

        public Guid Id { get; set; }

        protected BusinessObject()
        {
            Id = IdGenerator.NewId();
            _events = new List<IEvent>();
        }

        public void Publish(IEvent @event)
        {
            _events.Add(@event);
        }

        public override string ToString()
        {
            return string.Concat("[", GetType().Name, ", ", nameof(Id), " = ", Id, "]");
        }

        public ICollection<IEvent> ExtractEvents()
        {
            var result = new List<IEvent>(_events);
            _events.Clear();
            return result;
        }
    }
}